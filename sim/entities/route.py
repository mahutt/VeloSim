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

import math
from typing import TYPE_CHECKING
from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_data import TrafficTriple
from sim.map.routing_provider import RoutingProvider, RouteResult

from shapely.geometry import LineString
from grafana_logging.logger import get_logger

logger = get_logger(__name__)

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

    @staticmethod
    def map_index_forward(current_idx: int, old_count: int, new_count: int) -> int:
        """Map index from old collection to new, ensuring forward-only progress.

        When traffic changes reduce the number of points mid-traversal, this function
        maps the current index to the new collection such that the driver is placed
        at or ahead of their current progress - never behind.

        Uses ceil() to guarantee forward-only mapping.

        Args:
            current_idx: Current index in the old collection
            old_count: Number of points in the old (original) collection
            new_count: Number of points in the new (active) collection

        Returns:
            Mapped index in the new collection, guaranteed to represent
            progress >= current progress. O(1) time complexity.

        Example:
            >>> Route.map_index_forward(7, 10, 4)  # 78% through, maps to index 3 (100%)
            3
            >>> Route.map_index_forward(3, 10, 4)  # 33% through, maps to index 1 (33%)
            1
        """
        if old_count <= 1 or new_count <= 1:
            return min(current_idx, new_count - 1)
        progress = current_idx / (old_count - 1)
        return min(math.ceil(progress * (new_count - 1)), new_count - 1)

    @staticmethod
    def find_nearest_index(points: list[Position], target: Position) -> int:
        """Find the index of the point nearest to target in geographic space.

        Used when traffic changes a road's pointcollection mid-traversal.
        Geographic proximity prevents the position jump (rubber-banding) caused
        by ratio-based mapping on non-uniform point distributions.

        Args:
            points: The new pointcollection to search.
            target: The driver's last known geographic position.

        Returns:
            Index of the nearest point. O(n) — only called on traffic changes.
        """
        target_pos = target.get_position()
        best_idx = 0
        best_dist_sq = float("inf")
        for i, pt in enumerate(points):
            pos = pt.get_position()
            dx = pos[0] - target_pos[0]
            dy = pos[1] - target_pos[1]
            dist_sq = dx * dx + dy * dy
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_idx = i
        return best_idx

    def __init__(
        self,
        route_data: RouteResult,
        routing_provider: RoutingProvider,
        config: dict,
        roads: list[Road],
        route_controller: "RouteController | None" = None,
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

        # Track point count of current road to detect traffic changes.
        # When count changes (traffic applied/cleared/modified), we remap the index
        # using ratio-based mapping to preserve progress percentage.
        # Reset to None when transitioning to a new road.
        self._last_point_count: int | None = None

        # Store routing provider for recalculation
        self.routing_provider = routing_provider

        # Store config for speed calculations
        self.config = config

        # Store RouteController reference for road management
        self.route_controller: "RouteController | None" = route_controller

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

        # Cached traffic triples (eagerly updated via notify_traffic_changed)
        self._traffic_triples_cache: list[TrafficTriple] = []
        self._has_traffic_changed: bool = False

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

    def _handle_traffic_point_change(self, active_count: int) -> None:
        """Detect and remap index when traffic changes point count.

        Uses geographic proximity when the driver's last position is known.
        This prevents rubber-banding caused by ratio-based mapping on
        non-uniform point distributions (traffic creates dense points in
        affected zones and normal spacing elsewhere).
        """
        if (
            self._last_point_count is not None
            and self._last_point_count != active_count
        ):
            if self._last_returned_position is not None:
                current_road = self.roads[self.current_road_index]
                active_points = current_road.active_pointcollection
                self.current_point_index = Route.find_nearest_index(
                    active_points, self._last_returned_position
                )
            else:
                self.current_point_index = Route.map_index_forward(
                    self.current_point_index,
                    self._last_point_count,
                    active_count,
                )
        self._last_point_count = active_count

    def _get_current_position(self) -> Position | None:
        """
        Get the current position from the route traversal state.

        Returns:
            Position object or None if position cannot be determined
        """
        if self.current_road_index >= len(self.roads):
            return None

        current_road = self.roads[self.current_road_index]
        if self.current_point_index >= len(current_road.active_pointcollection):
            return None

        return current_road.active_pointcollection[self.current_point_index]

    def _get_all_points(self) -> list[Position]:
        """
        Gathers all the positions in the route per road, and returns it.
        Filters out consecutive duplicates at road boundaries.
        """

        all_points_objects: list[Position] = []

        for i, road_segment in enumerate(self.roads):
            points = (
                road_segment.active_pointcollection
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

    @property
    def has_traffic_changed(self) -> bool:
        """Whether traffic triples have changed since last clear.

        Returns:
            True if traffic triples have been updated since the last reset.
        """
        return self._has_traffic_changed

    @has_traffic_changed.setter
    def has_traffic_changed(self, value: bool) -> None:
        """Set the traffic changed flag.

        Args:
            value: New flag state.

        Returns:
            None
        """
        self._has_traffic_changed = value

    def get_traffic_triples(self) -> list[TrafficTriple]:
        """Get cached traffic triples in route coordinate index space.

        Returns the eagerly-maintained cache. Updated via notify_traffic_changed()
        when traffic is applied/removed on any road in this route.

        Returns:
            List of TrafficTriple objects for non-FREE_FLOW segments.
        """
        return self._traffic_triples_cache

    def notify_traffic_changed(self) -> None:
        """Rebuild cached traffic triples after a road's traffic changed.

        Called by TrafficController when traffic is applied/removed on a road
        belonging to this route. Rebuilds the full triple list from all roads.

        Returns:
            None
        """
        triples: list[TrafficTriple] = []
        coord_offset = 0
        for r in self.roads:
            if not r.geometry:
                continue
            geom_len = len(r.geometry)
            for geom_start, geom_end, level in r.get_traffic_geometry_ranges():
                abs_start = coord_offset + geom_start
                abs_end = coord_offset + geom_end
                # Merge with previous if adjacent + same level
                if (
                    triples
                    and triples[-1].congestion_level == level
                    and triples[-1].end_index >= abs_start
                ):
                    triples[-1].end_index = max(triples[-1].end_index, abs_end)
                else:
                    triples.append(TrafficTriple(abs_start, abs_end, level))
            coord_offset += geom_len - 1  # shared boundary point
        self._traffic_triples_cache = triples
        self._has_traffic_changed = True
    def get_distance_travelled(self) -> float:
        """Get total distance travelled along the route so far.

        Sums the length of all completed roads plus partial distance
        on the current road using speed-based distance computation.

        Returns:
            Distance in meters from route start to current position.
        """
        distance = sum(road.length for road in self.roads[: self.current_road_index])

        if self.current_road_index < len(self.roads):
            current_road = self.roads[self.current_road_index]
            distance += current_road.get_distance_at_index(self.current_point_index)

        return distance

    def next(self) -> Position | None:
        """Return the next position in the route traversal.

        Call once per simulation tick to advance the driver along the route.

        Traffic Handling:
            When traffic changes point count mid-traversal, the index is remapped
            using ratio-based mapping to preserve progress percentage.
            Formula: new_idx = ceil(current_idx / (old_count-1) * (new_count-1))

        Returns:
            Position: Next position in traversal, or None if route is finished.
        """
        if self.is_finished:
            return None

        point_to_return: Position | None = None

        while point_to_return is None and not self.is_finished:
            current_road = self.roads[self.current_road_index]
            active_points = current_road.active_pointcollection

            # Skip roads with no points (edge case)
            if not active_points:
                self.unsubscribe_from_road(current_road.id)
                self.current_road_index += 1
                self.current_point_index = 0
                self._last_point_count = None  # Reset for new road
                if self.current_road_index >= len(self.roads):
                    self.is_finished = True
                    break
                continue

            # Remap index if traffic changed point count
            self._handle_traffic_point_change(len(active_points))

            # Max index: last index to visit before transitioning.
            # Non-final roads exclude last point (overlaps with next road's first).
            is_last_road = self.current_road_index >= len(self.roads) - 1
            max_index = len(active_points) if is_last_road else len(active_points) - 1

            # Road transition check
            # If we've reached max_index, transition to the next road segment.
            if self.current_point_index >= max_index:
                self.unsubscribe_from_road(current_road.id)

                self.current_point_index = 0
                self._last_point_count = None  # Reset for new road
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
                continue

            # --- Normal Position Return ---
            # Return the current point (skip if duplicate of last returned).
            candidate_point = active_points[self.current_point_index]

            if (
                self._last_returned_position is None
                or candidate_point != self._last_returned_position
            ):
                point_to_return = candidate_point
                self._last_returned_position = candidate_point

            # Advance index for next call
            self.current_point_index += 1

        return point_to_return
