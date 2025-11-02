"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Optional, List, Tuple, Union, TYPE_CHECKING
from sim.entities.road import road
from sim.DAO.OSMConnection import OSMConnection
from sim.entities.position import Position

if TYPE_CHECKING:
    from sim.controller.MapController import MapController


class Route:
    """
    Owns a list of roads, which contain a list of positions.
    The positions are updated/spaced out given the max speed limit of the road.
    Later, dynamic strategies can allow different ways of updating these points.
    Positions can be traversed calling .next().
    ******.next() should be called at every sim clock second!******
    """

    _route_counter = 0  # Unique ID generation.

    def __init__(self, route_node_ids: List[int], osm_connection: OSMConnection):
        # Make this object unique.
        Route._route_counter += 1
        self.id: int = Route._route_counter

        # Attributes to keep state of the route's traversal.
        self.current_road_index: int = 0
        self.current_point_index: int = 0
        self.is_finished: bool = False
        self._is_first_call: bool = True
        self._last_returned_position: Optional[List[float]] = (
            None  # Track last position to avoid duplicates
        )

        # Store OSM connection and node IDs for recalculation
        self.osm_connection: OSMConnection = osm_connection
        self.start_node_id: int = route_node_ids[0] if route_node_ids else 0
        self.end_node_id: int = route_node_ids[-1] if route_node_ids else 0

        # Reference to MapController for subscription management
        self.map_controller: Optional["MapController"] = None

        # Link all nodes with edges.
        self.roads: List[road] = self._build_road_segments(
            route_node_ids, osm_connection
        )

        # If no roads were created, the route was finished from the start
        if not self.roads:
            self.is_finished = True

    def _build_road_segments(
        self, route_node_ids: List[int], osm_connection: OSMConnection
    ) -> List[road]:
        """
        Takes a list of node IDs and finds the corresponding road edges to
        create a complete list of Road objects for the route.
        """
        road_segments = []
        all_edges = osm_connection.get_all_edges()

        # Traverse over intersection nodes in pairs (i.e, [A, B, C] -> (A,B), (B,C))
        for i in range(len(route_node_ids) - 1):
            start_node_id = route_node_ids[i]
            end_node_id = route_node_ids[i + 1]

            try:
                # Find the specific edge that connects these two nodes
                edge = all_edges[
                    (all_edges["u"] == start_node_id) & (all_edges["v"] == end_node_id)
                ].iloc[0]

                # Create a Road object and add it to our list of roads
                road_segments.append(road(edge))
            except IndexError:
                # Try reverse direction
                # (might be a bidirectional road stored in reverse)
                try:
                    edge = all_edges[
                        (all_edges["u"] == end_node_id)
                        & (all_edges["v"] == start_node_id)
                    ].iloc[0]
                    # Found in reverse
                    # - we could reverse the geometry if needed
                    road_segments.append(road(edge))
                    # Note: This may cause issues if the road geometry
                    # needs to be reversed
                except IndexError:
                    msg = (
                        f"Warning: Could not find a direct edge from "
                        f"{start_node_id} to {end_node_id} in either direction. "
                        f"Skipping this segment."
                    )
                    print(msg)

        return road_segments

    def subscribe_to_map_controller(self, map_controller: "MapController") -> None:
        """
        Subscribes this route to all roads it traverses via the MapController.
        """
        self.map_controller = map_controller
        for road_segment in self.roads:
            map_controller._subscribe_route_to_road(road_segment.id, self)

    def unsubscribe_from_all_roads(self) -> None:
        """
        Unsubscribes this route from all roads in the MapController.
        Should be called when route is being recalculated or finished.
        """
        if self.map_controller:
            for road_segment in self.roads:
                self.map_controller._unsubscribe_route_from_road(road_segment.id, self)

    def unsubscribe_from_road(self, road_id: int) -> None:
        """
        Unsubscribes this route from a specific road.
        Called when the route has passed a road segment.
        """
        if self.map_controller:
            self.map_controller._unsubscribe_route_from_road(road_id, self)

    def recalculate(self) -> bool:
        """
        Recalculates the route from current position to the end destination.
        Unsubscribes from old roads and subscribes to new ones.

        Returns:
            bool: True if recalculation was successful, False otherwise.
        """
        if self.is_finished or not self.map_controller:
            return False

        # Unsubscribe from all current roads
        self.unsubscribe_from_all_roads()

        # Get current position - we need to find the nearest node to current location
        if self.current_road_index < len(self.roads):
            current_road = self.roads[self.current_road_index]
            if self.current_point_index < len(current_road.pointcollection):
                current_position = current_road.pointcollection[
                    self.current_point_index
                ]

                # Find nearest node to current position
                current_node = self.osm_connection.coordinates_to_nearest_node(
                    current_position.get_position()[0],
                    current_position.get_position()[1],
                )

                # Get end node
                end_node = self.osm_connection.get_node_by_id(self.end_node_id)

                if end_node is not None:
                    try:
                        # Calculate new route
                        new_route_node_ids = self.osm_connection.shortest_path(
                            current_node, end_node, self.osm_connection.get_graph()
                        )

                        # Build new road segments
                        new_roads = self._build_road_segments(
                            new_route_node_ids, self.osm_connection
                        )

                        if new_roads:
                            # Update route with new roads
                            self.roads = new_roads
                            self.current_road_index = 0
                            self.current_point_index = 0

                            # Subscribe to new roads
                            for road_segment in self.roads:
                                self.map_controller._subscribe_route_to_road(
                                    road_segment.id, self
                                )

                            return True
                    except Exception as e:
                        print(f"Route {self.id} recalculation failed: {e}")
                        self.is_finished = True
                        return False

        # If we couldn't recalculate, mark as finished
        self.is_finished = True
        return False

    def _get_all_points(self) -> List[Position]:
        """
        Gathers all the positions in the route per road, and returns it.
        Filters out consecutive duplicates at road boundaries.
        """

        all_points_objects: List[Position] = []  # Collection of points

        for i, road_segment in enumerate(self.roads):
            points = (
                road_segment.pointcollection
            )  # access the list of positions in the road segment.
            if i < len(self.roads) - 1:
                # Include all points besides last one,
                # since each road will have an overlapping node.
                points_to_add = points[:-1]
            else:
                # last road will not have anything to overlap with.
                points_to_add = points

            # Add points, filtering out consecutive duplicates
            for point in points_to_add:
                if (
                    not all_points_objects
                    or all_points_objects[-1].get_position() != point.get_position()
                ):
                    all_points_objects.append(point)

        return all_points_objects

    def next(
        self, as_json: bool = False
    ) -> Optional[Union[dict, Position, Tuple[Position, List[Position]]]]:
        """
        Returns the next Position object in the traversal sequence.

        Automatically handles moving from the end of one road segment to the
        beginning of the next. Returns None when the end of the route is reached.
        Skips consecutive duplicate positions.

        On the first call, it also returns the full route.

        Args:
            as_json (bool): If True, returns in JSON format.
                            If False [default], returns a list of Position objects.
        """
        if self.is_finished:
            return None

        # Find next non-duplicate position
        point_to_return = None
        while point_to_return is None and not self.is_finished:
            # Get the current road.
            current_road = self.roads[self.current_road_index]
            # Get the current position.
            candidate_point = current_road.pointcollection[self.current_point_index]

            # Check if this is a duplicate of the last returned position
            if (
                self._last_returned_position is None
                or candidate_point.get_position() != self._last_returned_position
            ):
                point_to_return = candidate_point
                self._last_returned_position = candidate_point.get_position()

            self.current_point_index += 1  # move to the next position

            # Determine the max index for this road
            # (exclude last point if not the final road)
            is_last_road = self.current_road_index >= len(self.roads) - 1
            max_index = (
                len(current_road.pointcollection)
                if is_last_road
                else len(current_road.pointcollection) - 1
            )

            if self.current_point_index >= max_index:
                # if the next position is out of bounds, we should go to the next road.

                # Unsubscribe from the road we just finished traversing
                self.unsubscribe_from_road(current_road.id)

                self.current_point_index = 0
                self.current_road_index += 1
                if self.current_road_index >= len(self.roads):
                    # if there are no roads left, we are done.
                    self.is_finished = True

        if point_to_return is None:
            return None

        # Handling first call, which is to send the entire list of positions.
        if self._is_first_call:
            self._is_first_call = (
                False  # Flag to check if the entire list has been outputted yet.
            )

            if as_json:
                all_points = self._get_all_points()
                coordinates = [p.get_position() for p in all_points]
                return {
                    "id": self.id,
                    "position": point_to_return.get_position(),
                    "route": {"coordinates": coordinates},
                }
            else:
                return (point_to_return, self._get_all_points())

        # Standard return for JSON (next position and its ID).
        if as_json:
            return {"id": self.id, "position": point_to_return.get_position()}
        else:
            return point_to_return  # Otherwise, just return the point.
