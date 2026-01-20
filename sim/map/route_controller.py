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

from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING
import logging

from shapely.geometry import LineString

from sim.entities.road import Road
from sim.entities.position import Position
from sim.map.routing_provider import RoutingProvider, RouteResult, SegmentKey

if TYPE_CHECKING:
    from sim.entities.route import Route
    from sim.map.MapController import MapController

logger = logging.getLogger(__name__)


class RouteController:
    """
    Manages the many-to-many relationship between Roads and Routes.

    RouteController is responsible for:
    - Creating and reusing Road objects based on geometry endpoints
    - Tracking which routes use which roads
    - Handling road allocation/deallocation as routes are created/completed
    - Providing lookup methods for roads and routes

    Road objects are reused across routes when they share the same segment_key
    (start/end coordinates), enabling efficient memory usage and consistent data
    across all routes using the same infrastructure. This approach is provider-neutral.
    """

    def __init__(self, map_controller: "MapController") -> None:
        """
        Initialize the RouteController.

        Args:
            map_controller: Parent MapController for road management
        """
        self.map_controller = map_controller

        # Road -> Set of Routes using that road
        self.roads_to_routes: Dict[Road, Set["Route"]] = {}

        # segment_key (start/end coords) -> Road (geometry-based identification)
        self.segment_key_to_road: Dict[SegmentKey, Road] = {}

        # road_id -> Road lookup
        self.road_id_to_road: Dict[int, Road] = {}

        # All active routes
        self.routes: Set["Route"] = set()

        # Callbacks for road deallocation events
        self._on_road_deallocated_callbacks: List[Callable[[SegmentKey], None]] = []

    def get_route_from_positions(
        self,
        start: Position,
        end: Position,
        routing_provider: RoutingProvider,
        config: Dict[str, Any],
    ) -> "Route":
        """
        Create a route from start to end positions.

        Fetches routing data from the routing provider and creates a Route with roads.

        Args:
            start: Starting position
            end: Ending position
            routing_provider: Routing provider for route calculation
            config: Simulation config

        Returns:
            Route object

        Raises:
            ValueError: If no route can be found
        """
        route_result = routing_provider.get_route(start, end)

        if not route_result:
            start_coords = start.get_position()
            end_coords = end.get_position()
            raise ValueError(
                f"No route found from ({start_coords[0]}, {start_coords[1]}) "
                f"to ({end_coords[0]}, {end_coords[1]})"
            )

        return self.create_route(route_result, routing_provider, config)

    def create_route(
        self,
        route_result: RouteResult,
        routing_provider: RoutingProvider,
        config: Dict[str, Any],
    ) -> "Route":
        """
        Create a Route from a RouteResult, reusing existing Road objects.

        Roads are created/reused based on segment_key (geometry endpoints).

        Args:
            route_result: The parsed routing result
            routing_provider: Routing provider for potential rerouting
            config: Configuration dictionary for route creation

        Returns:
            A new Route object with roads registered to this controller
        """
        from sim.entities.route import Route

        # Create roads from steps (logical road segments with proper turn penalties)
        roads = self.create_roads_from_steps(route_result) if route_result.steps else []

        # Create the route with the prepared roads
        route = Route(
            route_result,
            routing_provider,
            config,
            roads=roads,
            route_controller=self,
        )

        # Register the route
        self.routes.add(route)

        # Register road-to-route mappings
        for road in roads:
            self._register_road_to_route(road, route)

        return route

    def generate_point_collection(
        self,
        geometry: List[Position],
        length: float,
        maxspeed: float,
        is_final_segment: bool = False,
    ) -> List[Position]:
        """Generate evenly-spaced positions along a road segment (1 point per second).

        Uses Shapely LineString for interpolation. To avoid corner snapping (#447),
        endpoint is only included if is_final_segment=True.

        Args:
            geometry: List of Position objects defining the road segment
            length: Length of the road segment in meters
            maxspeed: Maximum speed in meters per second
            is_final_segment: If True, include the endpoint in the result

        Returns:
            List of interpolated Position objects along the segment
        """
        if not geometry:
            return []

        # Convert Position objects to coordinate tuples for Shapely
        coords = [pos.get_position() for pos in geometry]

        # Edge case: invalid speed or length
        if maxspeed <= 0 or length <= 0:
            edge_points = [geometry[0]]
            if len(geometry) > 1:
                edge_points.append(geometry[-1])
            return edge_points

        # Shapely handles both 2-point and multi-point geometries uniformly
        linestring = LineString(coords)
        points: List[Position] = []
        num_intervals = int(length / maxspeed)

        for i in range(num_intervals + 1):
            distance = i * maxspeed
            if distance > length:
                break

            # Use normalized interpolation (0 to 1) for consistent behavior
            point = linestring.interpolate(distance / length, normalized=True)
            new_pos = Position([float(point.x), float(point.y)])

            if not points or points[-1].get_position() != new_pos.get_position():
                points.append(new_pos)

        # For final segment, include exact endpoint
        if is_final_segment and points:
            end = linestring.coords[-1]
            end_pos = Position([float(end[0]), float(end[1])])
            if points[-1].get_position() != end_pos.get_position():
                points.append(end_pos)

        return points if points else [geometry[0]]

    def create_roads_from_steps(
        self,
        route_result: RouteResult,
    ) -> List[Road]:
        """
        Create Road objects from RouteSteps.

        Uses steps for smooth animation. Roads are identified and deduplicated
        using geometry-based segment_key (start/end coordinates), which is
        provider-neutral and works with any routing engine.

        Args:
            route_result: RouteResult with steps

        Returns:
            List of Road objects
        """
        roads: List[Road] = []

        for step in route_result.steps:
            if not step.geometry:
                continue

            # Calculate road_id from geometry (use Position coordinates)
            road_id = hash(tuple(tuple(pos.get_position()) for pos in step.geometry))

            # Derive maxspeed from step data
            maxspeed = step.speed if step.speed else 13.89
            if step.duration > 0 and step.distance > 0:
                maxspeed = step.distance / step.duration

            # Generate interpolated positions along the step
            positions = self.generate_point_collection(
                step.geometry, step.distance, maxspeed
            )

            # Skip if no positions were generated
            if not positions:
                continue

            # Build segment_key from geometry endpoints
            start_pos = positions[0].get_position()
            end_pos = positions[-1].get_position()
            segment_key: SegmentKey = (
                (start_pos[0], start_pos[1]),
                (end_pos[0], end_pos[1]),
            )

            # Check if we already have this road (by segment_key or road_id)
            existing_road = None
            if segment_key in self.segment_key_to_road:
                existing_road = self.segment_key_to_road[segment_key]
            elif road_id in self.road_id_to_road:
                existing_road = self.road_id_to_road[road_id]

            if existing_road:
                roads.append(existing_road)
                continue

            road = Road(
                road_id=road_id,
                name=step.name,
                pointcollection=positions,
                length=step.distance,
                maxspeed=maxspeed,
            )

            # Register in lookups
            self.segment_key_to_road[segment_key] = road
            self.road_id_to_road[road_id] = road

            roads.append(road)

        return roads

    def _register_road_to_route(self, road: Road, route: "Route") -> None:
        """Register a road-to-route mapping."""
        if road not in self.roads_to_routes:
            self.roads_to_routes[road] = set()
        self.roads_to_routes[road].add(route)

    def unregister_road_from_route(self, road: Road, route: "Route") -> None:
        """Remove a road-to-route mapping. Deallocates road if no routes remain.

        Args:
            road: The Road to unregister from the route
            route: The Route to unregister the road from

        Returns:
            None
        """
        if road in self.roads_to_routes:
            self.roads_to_routes[road].discard(route)
            if not self.roads_to_routes[road]:
                self._deallocate_road(road)

    def unregister_route(self, route: "Route") -> None:
        """Unregister a route and all its road mappings.

        Args:
            route: The Route to unregister

        Returns:
            None
        """
        if route not in self.routes:
            return
        self.routes.discard(route)
        roads_to_check = [
            road for road, routes in self.roads_to_routes.items() if route in routes
        ]
        for road in roads_to_check:
            self.unregister_road_from_route(road, route)

    def recalculate_route(
        self,
        route: "Route",
        current_position: Position,
    ) -> bool:
        """
        Recalculate a route from current position to its destination.

        Unregisters the route from old roads, fetches a new route from the
        routing provider, builds new roads, and re-registers the route.

        Args:
            route: The Route to recalculate
            current_position: Current Position object

        Returns:
            bool: True if recalculation was successful, False otherwise
        """
        try:
            # Unregister from old roads
            self.unregister_route(route)

            # Fetch new route from routing provider
            route_result = route.routing_provider.get_route(
                current_position, route.end_position
            )

            if not route_result:
                logger.warning(f"Route {route.id}: No route found during recalculation")
                return False

            # Build new roads from steps
            new_roads = (
                self.create_roads_from_steps(route_result) if route_result.steps else []
            )

            if not new_roads:
                logger.warning(
                    f"Route {route.id}: No roads created during recalculation"
                )
                return False

            # Apply new roads to route
            route.roads = new_roads
            route.current_road_index = 0
            route.current_point_index = 0
            route._last_returned_position = None

            # Update route metadata from new route result
            route.coordinates = route_result.coordinates
            route.distance = route_result.distance
            route.duration = route_result.duration
            route.steps = route_result.steps

            # Re-register route and road mappings
            self.routes.add(route)
            for road in new_roads:
                self._register_road_to_route(road, route)

            logger.debug(f"Route {route.id}: Recalculated with {len(new_roads)} roads")
            return True

        except Exception as e:
            logger.error(f"Route {route.id} recalculation failed: {e}")
            return False

    def _deallocate_road(self, road: Road) -> None:
        """Remove a road from all tracking structures when no routes reference it."""
        segment_key = road.segment_key

        # Notify callbacks before removing
        for callback in self._on_road_deallocated_callbacks:
            callback(segment_key)

        self.roads_to_routes.pop(road, None)
        self.segment_key_to_road.pop(segment_key, None)
        self.road_id_to_road.pop(road.id, None)
        logger.debug(f"Deallocated road {road.id} (segment_key={segment_key})")

    def register_on_road_deallocated(
        self, callback: Callable[[SegmentKey], None]
    ) -> None:
        """Register a callback to be notified when a road is deallocated.

        Args:
            callback: Function that takes a SegmentKey and is called when
                     a road with that segment_key is deallocated.

        Returns:
            None
        """
        self._on_road_deallocated_callbacks.append(callback)

    def unregister_on_road_deallocated(
        self, callback: Callable[[SegmentKey], None]
    ) -> bool:
        """Unregister a previously registered road deallocation callback.

        Args:
            callback: The callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        try:
            self._on_road_deallocated_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def get_routes_for_road(self, road: Road) -> Set["Route"]:
        """Get all routes using a specific road (returns a copy).

        Args:
            road: The Road to look up

        Returns:
            Set of Routes using this road
        """
        return self.roads_to_routes.get(road, set()).copy()

    def get_routes_for_segment_key(self, segment_key: SegmentKey) -> Set["Route"]:
        """Get all routes using a road with the given segment_key.

        Args:
            segment_key: Tuple of ((start_lon, start_lat), (end_lon, end_lat))

        Returns:
            Set of Routes using this segment
        """
        road = self.segment_key_to_road.get(segment_key)
        return self.get_routes_for_road(road) if road else set()

    def get_road_by_segment_key(self, segment_key: SegmentKey) -> Optional[Road]:
        """Get a Road by its segment_key (geometry endpoints).

        Args:
            segment_key: Tuple of ((start_lon, start_lat), (end_lon, end_lat))

        Returns:
            The Road if found, None otherwise
        """
        return self.segment_key_to_road.get(segment_key)

    def get_road_by_id(self, road_id: int) -> Optional[Road]:
        """Get a Road by its ID.

        Args:
            road_id: The unique Road ID

        Returns:
            The Road if found, None otherwise
        """
        return self.road_id_to_road.get(road_id)

    def get_all_active_roads(self) -> Set[Road]:
        """Get all roads currently in use by at least one route.

        Returns:
            Set of all active Roads
        """
        return set(self.roads_to_routes.keys())

    def get_active_route_count(self) -> int:
        """Get the number of active routes.

        Returns:
            Number of registered routes
        """
        return len(self.routes)

    def get_active_road_count(self) -> int:
        """Get the number of active roads.

        Returns:
            Number of roads with at least one route
        """
        return len(self.roads_to_routes)

    def clear(self) -> None:
        """Clear all route and road registrations (called during simulation reset).

        Returns:
            None
        """
        self.roads_to_routes.clear()
        self.segment_key_to_road.clear()
        self.road_id_to_road.clear()
        self.routes.clear()
        self._on_road_deallocated_callbacks.clear()
