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
from typing import TYPE_CHECKING, Optional
from sim.entities.map_payload import MapPayload
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
    TRANSITION_THRESHOLD = 100  # 100 meters

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
    def find_nearest_index(
        points: list[Position], target: Position, min_idx: int = 0
    ) -> int:
        """Find the index of the point nearest to target in geographic space.

        Used when traffic changes a road's pointcollection mid-traversal.
        Geographic proximity prevents the position jump (rubber-banding) caused
        by ratio-based mapping on non-uniform point distributions.

        Args:
            points: The new pointcollection to search.
            target: The driver's last known geographic position.
            min_idx: Minimum index to consider (inclusive). Enforces
                forward-only search to prevent backward mapping.

        Returns:
            Index of the nearest point (>= min_idx). O(n) — only called on
            traffic changes.
        """
        target_pos = target.get_position()
        start = max(0, min_idx)
        best_idx = start
        best_dist_sq = float("inf")
        for i in range(start, len(points)):
            pos = points[i].get_position()
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
        route_recalculation_interval_seconds: int | None = None,
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
            route_recalculation_interval_seconds: Elapsed route time in seconds
                between automatic route refresh attempts. Defaults to
                MapPayload default interval when omitted.
                RouteController normally provides this value.
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
        self._pending_stop_dwell: Position | None = None
        self._visited_stop_points: set[tuple[int, float, float]] = set()
        self._last_stop_position: tuple[float, float] | None = (
            None  # Track last stop location globally
        )

        # Store routing provider for recalculation
        self.routing_provider = routing_provider

        # Store config for speed calculations
        self.config = config

        # Store RouteController reference for road management
        self.route_controller: "RouteController | None" = route_controller
        if route_recalculation_interval_seconds is None:
            route_recalculation_interval_seconds = (
                MapPayload.default_route_recalculation_interval_seconds()
            )

        self._route_recalculation_interval_seconds = (
            MapPayload.normalize_route_recalculation_interval_seconds(
                route_recalculation_interval_seconds
            )
        )
        self._elapsed_seconds_since_recalculation = 0

        # Extract route data from RouteResult
        self.coordinates = route_data.coordinates
        self.distance = route_data.distance
        self.duration = route_data.duration
        self.steps = route_data.steps
        self.stop_sign_positions = list(getattr(route_data, "stop_sign_positions", []))

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

        # Global traffic event indices for a route
        self._event_indices: list[tuple[int, int]] = (
            []
        )  # Global (start, end) index pairs
        self._next_event_idx: int = (
            0  # Pointer (index) to next upcoming index in global range
        )

        self._transition_buffer: list[Position] = []

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
        else:
            self._elapsed_seconds_since_recalculation = 0

        return success

    def _maybe_recalculate_for_elapsed_time(self) -> None:
        """Refresh route after a configurable elapsed time threshold."""
        if self.is_finished or not self.route_controller:
            return

        self._elapsed_seconds_since_recalculation += 1
        if (
            self._elapsed_seconds_since_recalculation
            < self._route_recalculation_interval_seconds
        ):
            return

        # Keep going on success; failed recalculation marks route as finished.
        self.recalculate()
        return

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

    def _get_wait_position(self, blocked_position: Position) -> Position:
        """Return the position to hold while blocked without advancing.

        Prefers the last emitted position. Falls back to the current route
        position when available. If neither exists, uses the blocked position
        as a safe fallback.

        Args:
            blocked_position: The blocked point that triggered waiting.

        Returns:
            Position to return while waiting.
        """
        if self._last_returned_position is not None:
            return self._last_returned_position

        current_position = self._get_current_position()
        if current_position is not None:
            self._last_returned_position = current_position
            return current_position

        self._last_returned_position = blocked_position
        return blocked_position

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

    def get_stop_sign_coordinates(self) -> list[list[float]]:
        """Return unique stop-sign coordinates associated with this route.

        Returns:
            list[list[float]]: Unique stop-sign coordinates as [lon, lat].
        """
        unique_coords: list[list[float]] = []
        seen: set[tuple[float, float]] = set()

        for stop_sign in self.stop_sign_positions:
            coord = stop_sign.get_position()
            key = (coord[0], coord[1])
            if key in seen:
                continue
            seen.add(key)
            unique_coords.append(coord)

        if self.route_controller is not None:
            for road in self.roads:
                for stop_sign in self.route_controller.get_stop_signs_for_road(road):
                    coord = stop_sign.get_position()
                    key = (coord[0], coord[1])
                    if key in seen:
                        continue
                    seen.add(key)
                    unique_coords.append(coord)

        return unique_coords

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
        """Rebuild cached traffic triples and global event indices after a
        road's traffic changed.

        Called by TrafficController when traffic is applied/removed on a road
        belonging to this route. Rebuilds the full triple list from all roads,
        as well as the global event indices.

        Returns:
            None
        """
        triples: list[TrafficTriple] = []
        coord_offset = 0
        for r in self.roads:
            # Use geometry length if available. Otherwise, fallback to pointcollection
            geom_len = len(r.geometry) if r.geometry else len(r.pointcollection)
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
            coord_offset += max(geom_len - 1, 0)  # shared boundary point
        self._traffic_triples_cache = triples
        if self._transition_buffer:
            if self._last_returned_position:
                self._sync_indices_after_transition(self._last_returned_position)
            self._transition_buffer = []
        self._rebuild_global_event_indices()
        self._has_traffic_changed = True

    def get_distance_traveled(self) -> float:
        """Get total distance traveled along the route so far.

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

    def _rebuild_global_event_indices(self) -> None:
        """Rebuilds the global event list in O(N) linear time.

        Returns:
            None
        """
        self._event_indices = []
        coord_offset = 0

        for road in self.roads:
            # Get length of road segment. Fallback to pointcollection length
            geom_len = (
                len(road.geometry) if road.geometry else len(road.pointcollection)
            )

            # Get sorted ranges from the road
            for geom_start, geom_end, level in road.get_traffic_geometry_ranges():
                self._event_indices.append(
                    (geom_start + coord_offset, geom_end + coord_offset)
                )

            coord_offset += max(geom_len - 1, 0)

        self._next_event_idx = 0
        self._update_next_event_index()

    def _update_next_event_index(self) -> None:
        """Advances pointer/index if the driver has passed the end of an event.

        Returns:
            None
        """
        current_global_idx = self._get_current_global_geometry_index()

        while (
            self._next_event_idx < len(self._event_indices)
            and current_global_idx >= self._event_indices[self._next_event_idx][1]
        ):
            self._next_event_idx += 1

    def _get_current_global_geometry_index(self) -> int:
        """Maps current road/point index to the global geometry indices.

        Returns:
            Current point index of the driver according to the global geometry indices.
        """
        if not self.roads:
            return 0

        # When route is finished, clamp to the last global index.
        if self.current_road_index >= len(self.roads):
            last_idx = 0
            for road in self.roads:
                geom_len = (
                    len(road.geometry) if road.geometry else len(road.pointcollection)
                )
                last_idx += max(geom_len - 1, 0)
            return last_idx

        offset = 0
        for road in self.roads[: self.current_road_index]:
            # if geometry is missing, fallback to length of pointcollection
            geom_len = (
                len(road.geometry) if road.geometry else len(road.pointcollection)
            )
            offset += max(geom_len - 1, 0)

        # Map interpolated point index back to geometry index ratio
        current_road = self.roads[self.current_road_index]
        point_collection_len = len(current_road.active_pointcollection)
        geom_len = (
            len(current_road.geometry)
            if current_road.geometry
            else len(current_road.pointcollection)
        )

        if point_collection_len <= 1:
            return offset

        # Use geographic projection for correct progress when traffic
        # creates non-uniform point spacing.
        try:
            progress = current_road.get_progress_at_index(self.current_point_index)
            return offset + int(progress * max(geom_len - 1, 0))
        except (TypeError, AttributeError):
            progress = self.current_point_index / (point_collection_len - 1)
            return offset + int(progress * max(geom_len - 1, 0))

    def get_distance_to_next_event(self) -> Optional[float]:
        """Gets the distance from the current index to the next traffic event by
        calculating Distance(Next Event Start) - Distance(Current Position)

        Returns:
            Distance from current index to the next traffic event in the route.
            Otherwise, None if there are no next events.
        """
        self._update_next_event_index()

        if self._next_event_idx >= len(self._event_indices):
            return None

        next_start_idx = self._event_indices[self._next_event_idx][0]

        # Calculate distance to the start of the event
        dist_to_event = self.get_distance_at_global_coordinate_index(next_start_idx)
        current_dist = self.get_distance_traveled()

        return max(0.0, dist_to_event - current_dist)

    def get_distance_at_global_coordinate_index(self, global_idx: int) -> float:
        """Helper function to get the total distance till global_idx in the
        global ruler. Sums road lengths up to a specific global geometry index.

        Args:
            global_idx: Start index of the next traffic event in the global ruler.

        Returns:
            Sum of road lengths up to global_idx
        """
        total_dist = 0.0
        offset = 0

        for road in self.roads:
            geom_len = (
                len(road.geometry) if road.geometry else len(road.pointcollection)
            )
            # Checks if global_idx is between the start and end of the current road
            # If true, found the target point and break from loop
            if offset <= global_idx < offset + max(geom_len, 1):
                local_idx = global_idx - offset  # exact distance within that road

                # If the road only has 1 point, progress is effectively 0
                if geom_len > 1:
                    # Map geometry index to road distance
                    total_dist += (local_idx / (geom_len - 1)) * road.length
                # else: total_dist stays the same (we are at the start of this point)
                break

            total_dist += road.length
            offset += max(geom_len - 1, 0)

        return total_dist

    def _get_upcoming_traffic_multiplier(self) -> float:
        """Helper function to retrieve the next traffic event and get its multiplier.

        Returns:
            The congestion multiplier of the next upcoming event. Defaults to FREE_FLOW.
        """
        if self._next_event_idx >= len(self._event_indices):
            return 1.0  # free flow if no more events

        next_event_start = self._event_indices[self._next_event_idx][0]

        # Get road multiplier of next event
        offset = 0
        for road in self.roads:
            geom_len = (
                len(road.geometry) if road.geometry else len(road.pointcollection)
            )
            if offset <= next_event_start <= offset + max(geom_len - 1, 0):
                local_geom_idx = next_event_start - offset
                # Convert geometry-space index to node-space index.
                # get_multiplier_at_index expects pointcollection indices,
                # not geometry indices — these are different coordinate spaces.
                if geom_len > 1:
                    frac = local_geom_idx / (geom_len - 1)
                    pc_len = len(road.pointcollection)
                    node_idx = min(int(frac * max(pc_len - 1, 0)), pc_len - 1)
                    return road.get_multiplier_at_index(node_idx)
                return road.get_multiplier_at_index(local_geom_idx)

            offset += max(geom_len - 1, 0)

        return 1.0

    def _sync_indices_after_transition(self, final_pos: Position) -> None:
        """Finds the road and index that best matches the final position of
        the smooth transition, searching forward-only to prevent backward jumps.

        Args:
            final_pos: Final position of a smooth transition curve

        Returns:
            None
        """
        best_road_idx = self.current_road_index
        best_point_idx = self.current_point_index
        min_dist = float("inf")
        target_pos = final_pos.get_position()

        # Search from the last current road index
        for road_idx in range(self.current_road_index, len(self.roads)):
            road = self.roads[road_idx]
            points = road.active_pointcollection

            # On the current road, only search forward from current position
            # to prevent backward mapping. On subsequent roads, search all.
            search_start = (
                self.current_point_index if road_idx == self.current_road_index else 0
            )
            local_idx = self.find_nearest_index(points, final_pos, min_idx=search_start)

            # Calculate distance from candidate position to the final position
            candidate_pos = points[local_idx].get_position()
            dx = candidate_pos[0] - target_pos[0]
            dy = candidate_pos[1] - target_pos[1]
            dist = dx * dx + dy * dy

            # If new distance smaller than last best, better match
            if dist < min_dist:
                min_dist = dist
                best_road_idx = road_idx
                best_point_idx = local_idx

        # Ensure the synced point is not behind the curve endpoint.
        # The nearest active_pc point may be slightly before the curve's
        # final position due to grid misalignment.  Advancing by one
        # guarantees normal traversal resumes at or past the curve endpoint.
        road = self.roads[best_road_idx]
        active_pts = road.active_pointcollection
        synced_dist = road.get_distance_at_index(best_point_idx)
        if self._last_returned_position is not None and best_point_idx + 1 < len(
            active_pts
        ):
            # Estimate the curve endpoint's road distance via projection
            lrp = self._last_returned_position.get_position()
            nodes = road.pointcollection
            if len(nodes) >= 2:
                s = nodes[0].get_position()
                e = nodes[-1].get_position()
                dx = e[0] - s[0]
                dy = e[1] - s[1]
                rd2 = dx * dx + dy * dy
                if rd2 > 0:
                    last_dist = (
                        max(
                            0.0,
                            min(
                                ((lrp[0] - s[0]) * dx + (lrp[1] - s[1]) * dy) / rd2,
                                1.0,
                            ),
                        )
                        * road.length
                    )
                    if synced_dist < last_dist:
                        best_point_idx += 1

        # Update indices with best match to continue traversal
        self.current_road_index = best_road_idx
        self.current_point_index = best_point_idx
        self._last_point_count = len(road.active_pointcollection)

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

        # If the previous tick reached a stop-sign point, dwell for one tick.
        if (
            self._pending_stop_dwell is not None
            and self._last_returned_position is not None
        ):
            dwell_pos = self._pending_stop_dwell
            self._pending_stop_dwell = None
            return dwell_pos

        # If we are transition, use next transition position
        if self._transition_buffer:
            next_transition_pos = self._transition_buffer[0]

            # Keep wait semantics consistent with normal traversal: if the next
            # transition point is occupied, do not consume the buffer point.
            if next_transition_pos.occupied:
                return self._get_wait_position(next_transition_pos)

            pos = self._transition_buffer.pop(0)
            self._last_returned_position = pos

            # Sync if last point in the buffer
            if not self._transition_buffer:
                self._sync_indices_after_transition(pos)
                self._update_next_event_index()  # Advance event pointer

                # Prevent normal traversal from remapping
                current_road = self.roads[self.current_road_index]
                self._last_point_count = len(current_road.active_pointcollection)

            return pos

        self._maybe_recalculate_for_elapsed_time()

        # Smooth transition if distance to next event < threshold
        dist_to_event = self.get_distance_to_next_event()
        if dist_to_event is not None and dist_to_event < self.TRANSITION_THRESHOLD:
            current_road = self.roads[self.current_road_index]
            # v0 = effective speed at the driver's current position.
            progress = current_road.get_progress_at_index(self.current_point_index)
            pc_len = len(current_road.pointcollection)
            if pc_len > 1:
                node_idx = min(int(progress * (pc_len - 1)), pc_len - 1)
                v0 = current_road.maxspeed * current_road.get_multiplier_at_index(
                    node_idx
                )
            else:
                v0 = current_road.current_speed
            # Determine final speed (maxspeed * upcoming traffic multiplier)
            vf = current_road.maxspeed * self._get_upcoming_traffic_multiplier()

            current_distance_on_road = current_road.get_distance_at_index(
                self.current_point_index
            )
            self._transition_buffer = current_road.generate_curve(
                v0, vf, dist_to_event, distance_offset=current_distance_on_road
            )
            if self._transition_buffer:
                first_transition_pos = self._transition_buffer[0]
                if first_transition_pos.occupied:
                    return self._get_wait_position(first_transition_pos)

                pos = self._transition_buffer.pop(0)
                self._last_returned_position = pos
                # Sync if last point in the buffer
                if not self._transition_buffer:
                    self._sync_indices_after_transition(pos)
                    self._update_next_event_index()  # Advance event pointer

                    # Prevent normal traversal from remapping
                    current_road = self.roads[self.current_road_index]
                    self._last_point_count = len(current_road.active_pointcollection)
                return pos
            # else: traverse normally

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
            # Get the position we're attempting to move to
            candidate_point = active_points[self.current_point_index]

            # Check if the next position is occupied, which could be blocked by
            # traffic (or some other road event.)
            if candidate_point.occupied:
                # The next position is occupied, so the vehicle must wait.
                point_to_return = self._get_wait_position(candidate_point)
                # Don't increment current_point_index, instead retry next tick
            else:
                # Stop-sign behavior: when first reaching a stop-sign point on a road,
                # schedule a one-tick dwell after returning that point.
                if self.route_controller is not None and hasattr(
                    self.route_controller, "is_stop_sign_at_position"
                ):
                    matched_sign: Position | None = None
                    if hasattr(
                        self.route_controller, "get_matching_stop_sign_at_position"
                    ):
                        raw_match = (
                            self.route_controller.get_matching_stop_sign_at_position(
                                current_road, candidate_point
                            )
                        )
                        if isinstance(raw_match, Position):
                            matched_sign = raw_match

                    is_stop_sign = matched_sign is not None
                    if matched_sign is None:
                        is_stop_sign = self.route_controller.is_stop_sign_at_position(
                            current_road, candidate_point
                        )
                    if matched_sign is not None:
                        sign_lon, sign_lat = matched_sign.get_position()
                        stop_key = (
                            current_road.id,
                            round(sign_lon, 7),
                            round(sign_lat, 7),
                        )
                    else:
                        cand_lon, cand_lat = candidate_point.get_position()
                        stop_key = (
                            current_road.id,
                            round(cand_lon, 7),
                            round(cand_lat, 7),
                        )
                    if (
                        stop_key not in self._visited_stop_points
                        and is_stop_sign is True
                    ):
                        CLUSTER_TOL_DEGREES = 0.00015
                        skip_duplicate = False

                        if self._last_stop_position is not None:
                            if matched_sign is not None:
                                curr_lon, curr_lat = matched_sign.get_position()
                            else:
                                curr_lon, curr_lat = candidate_point.get_position()

                            last_lon, last_lat = self._last_stop_position
                            dx = curr_lon - last_lon
                            dy = curr_lat - last_lat
                            dist_sq = (dx * dx) + (dy * dy)
                            cluster_tol_sq = CLUSTER_TOL_DEGREES * CLUSTER_TOL_DEGREES

                            if dist_sq <= cluster_tol_sq:
                                skip_duplicate = True

                        if not skip_duplicate:
                            self._visited_stop_points.add(stop_key)
                            self._pending_stop_dwell = candidate_point

                            # Track this stop location for future duplicate checking
                            if matched_sign is not None:
                                sign_lon, sign_lat = matched_sign.get_position()
                                self._last_stop_position = (sign_lon, sign_lat)
                            else:
                                point_lon, point_lat = candidate_point.get_position()
                                self._last_stop_position = (point_lon, point_lat)

                # Next position on the road is available. The vehicle can
                # proceed with normal traversal
                if (
                    self._last_returned_position is None
                    or candidate_point != self._last_returned_position
                ):
                    point_to_return = candidate_point
                    self._last_returned_position = candidate_point
                else:
                    # Duplicate check: same position as last returned
                    # If we were blocked here before, increment to move forward
                    pass

                # Advance index for next call
                self.current_point_index += 1

        return point_to_return
