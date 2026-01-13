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

from typing import TYPE_CHECKING, Dict, List, Optional
from sim.entities.position import Position
from sim.entities.road import Road
from sim.map.routing_provider import RoutingProvider, RouteResult
from shapely.geometry import LineString
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sim.map.route_controller import RouteController


class Route:
    """
    Owns a list of roads, which contain a list of positions.
    The positions are updated/spaced out given the max speed limit of the road.
    Later, dynamic strategies can allow different ways of updating these points.
    Positions can be traversed calling .next().
    ******.next() should be called at every sim clock second!******
    """

    _route_counter = 0  # Unique ID generation.

    def __init__(
        self,
        route_data: RouteResult,
        routing_provider: RoutingProvider,
        config: Dict,
        roads: List[Road],
        route_controller: Optional["RouteController"] = None,
    ) -> None:
        """
        Initialize a Route from routing result.

        Routes should be created via RouteController.create_route() which handles
        road building and registration.

        Args:
            route_data: RouteResult instance with route geometry and metadata
            routing_provider: RoutingProvider instance for recalculation
            config: Configuration dictionary with simulation settings
            roads: List of Road objects built by RouteController. Required.
            route_controller: RouteController for road/route management.
                Handles road allocation, recalculation, and subscriptions.
        """
        # Make this object unique.
        Route._route_counter += 1
        self.id: int = Route._route_counter

        # Attributes to keep state of the route's traversal.
        self.current_road_index: int = 0
        self.current_point_index: int = 0
        self.is_finished: bool = False
        self._last_returned_position: Position | None = None

        # Store routing provider for recalculation
        self.routing_provider = routing_provider

        # Store config for speed calculations
        self.config = config

        # Store RouteController reference for road management
        self.route_controller: Optional["RouteController"] = route_controller

        # Extract route data from RouteResult
        self.coordinates = route_data.coordinates
        self.distance = route_data.distance
        self.duration = route_data.duration
        self.steps = route_data.steps

        # Store start/end positions for recalculation
        self.start_position = route_data.start_position
        self.end_position = route_data.end_position

        # Roads must be provided (built by RouteController)
        if roads is None:
            raise ValueError(
                "roads parameter is required. "
                "Use RouteController.create_route() to create routes."
            )
        self.roads = roads

        # If no roads were created, the route was finished from the start
        if not self.roads:
            self.is_finished = True

    def unsubscribe_from_all_roads(self) -> None:
        """Unsubscribes this route from all roads.

        Removes this route from all road subscriptions via RouteController.

        This should be called when the route is being recalculated or has finished
        to ensure proper cleanup and prevent memory leaks.

        Returns:
            None
        """
        if self.route_controller:
            self.route_controller.unregister_route(self)

    def unsubscribe_from_road(self, road_id: int) -> None:
        """Unsubscribes this route from a specific road segment.

        Called when the route has passed a road segment and no longer needs
        to be tracked for that road.

        Args:
            road_id: The ID of the road segment to unsubscribe from.

        Returns:
            None
        """
        if not self.route_controller:
            return

        # Find the road object by ID
        for road in self.roads:
            if road.id == road_id:
                self.route_controller.unregister_road_from_route(road, self)
                return

    def recalculate(self) -> bool:
        """
        Recalculates the route from current position to the end destination.
        Delegates to RouteController for road building and registration.

        Returns:
            bool: True if recalculation was successful, False otherwise.
        """
        if self.is_finished:
            return False

        if not self.route_controller:
            logger.warning(
                f"Route {self.id}: Cannot recalculate without RouteController"
            )
            return False

        current_position = self._get_current_position()
        if not current_position:
            self.is_finished = True
            return False

        # Delegate to RouteController
        success = self.route_controller.recalculate_route(self, current_position)
        if not success:
            self.is_finished = True

        return success

    def _get_current_position(self) -> Position | None:
        """
        Get the current position from the route traversal state.

        Returns:
            Position object or None if position cannot be determined
        """
        if self.current_road_index >= len(self.roads):
            return None

        current_road = self.roads[self.current_road_index]
        if self.current_point_index >= len(current_road.pointcollection):
            return None

        return current_road.pointcollection[self.current_point_index]

    def _get_all_points(self) -> list[Position]:
        """
        Gathers all the positions in the route per road, and returns it.
        Filters out consecutive duplicates at road boundaries.
        """

        all_points_objects: list[Position] = []

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

    def get_route_geometry(self) -> LineString:
        """Returns the complete route geometry as a LineString.

        Collects all position points from all road segments in the route,
        filters out consecutive duplicates at road boundaries, and constructs
        a Shapely LineString representing the complete route path.

        This is useful for route visualization, spatial analysis, and calculating
        route properties such as length or intersection with other geometries.

        Returns:
            LineString: Shapely LineString object representing the entire route path,
                with coordinates in (longitude, latitude) format.
        """
        all_points = self._get_all_points()
        coordinates = [p.get_position() for p in all_points]
        return LineString([(lon, lat) for lon, lat in coordinates])

    def get_raw_coordinates(self) -> list[list[float]]:
        """Returns the raw route coordinates (not interpolated).

        These are the sparse coordinate points from the routing response,
        which define the road geometry without second-by-second interpolation.
        Used for visualization on the frontend to reduce payload size.

        Returns:
            List of [lon, lat] coordinate pairs from routing provider.
        """
        return [pos.get_position() for pos in self.coordinates]

    def next(self) -> Position | None:
        """
        Returns the next Position object in the traversal sequence.

        Automatically handles moving from the end of one road segment to the
        beginning of the next. Returns None when the end of the route is reached.
        Skips consecutive duplicate positions.

        Returns:
            Position object or None when finished.
        """
        if self.is_finished:
            return None

        # Find next non-duplicate position
        point_to_return: Position | None = None
        while point_to_return is None and not self.is_finished:
            # Determine the max index for this road
            # (exclude last point if not the final road)
            is_last_road = self.current_road_index >= len(self.roads) - 1
            current_road = self.roads[self.current_road_index]
            max_index = (
                len(current_road.pointcollection)
                if is_last_road
                else len(current_road.pointcollection) - 1
            )

            # Check if we need to move to the next road
            if self.current_point_index >= max_index:
                # Unsubscribe from the road we just finished traversing
                self.unsubscribe_from_road(current_road.id)

                self.current_point_index = 0
                self.current_road_index += 1
                if self.current_road_index >= len(self.roads):
                    # All roads traversed. Before marking as finished, ensure
                    # we return the exact destination (fix for issue #447).
                    # Due to no-corner-snap interpolation, the last road's
                    # last point might not be exactly at the destination.
                    if hasattr(self, "end_position") and self.end_position:
                        if self._last_returned_position != self.end_position:
                            # Return destination as final point
                            point_to_return = self.end_position
                            self._last_returned_position = self.end_position
                            self.is_finished = True
                            break
                    # if there are no roads left, we are done.
                    self.is_finished = True
                    break
                # Update current_road after moving to next road
                current_road = self.roads[self.current_road_index]

            # Get the current position.
            candidate_point = current_road.pointcollection[self.current_point_index]

            # Check if this is a duplicate of the last returned position
            if (
                self._last_returned_position is None
                or candidate_point != self._last_returned_position
            ):
                point_to_return = candidate_point
                self._last_returned_position = candidate_point

            # Move to next position (whether it was duplicate or not)
            self.current_point_index += 1

        return point_to_return
