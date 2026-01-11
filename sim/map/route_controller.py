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

from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
import logging

from shapely.geometry import LineString

from sim.entities.road import Road
from sim.entities.position import Position
from sim.entities.osrm_result import OSRMResult, OSRMSegment

if TYPE_CHECKING:
    from sim.entities.route import Route
    from sim.map.MapController import MapController
    from sim.osm.OSRMConnection import OSRMConnection

logger = logging.getLogger(__name__)


class RouteController:
    """
    Manages the many-to-many relationship between Roads and Routes.

    RouteController is responsible for:
    - Creating and reusing Road objects based on OSM node-based segment IDs
    - Tracking which routes use which roads
    - Handling road allocation/deallocation as routes are created/completed
    - Providing lookup methods for roads and routes

    Road objects are reused across routes when they share the same segment_id
    (OSM node pair), enabling efficient memory usage and consistent data
    across all routes using the same infrastructure.
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

        # segment_id (node_start, node_end) -> Road
        self.segment_id_to_road: Dict[Tuple[int, int], Road] = {}

        # road_id -> Road lookup
        self.road_id_to_road: Dict[int, Road] = {}

        # All active routes
        self.routes: Set["Route"] = set()

    def get_route_from_positions(
        self,
        start: Position,
        end: Position,
        osrm: "OSRMConnection",
        config: Dict[str, Any],
    ) -> "Route":
        """
        Create a route from start to end positions.

        Fetches routing data from OSRM and creates a Route with roads.

        Args:
            start: Starting position
            end: Ending position
            osrm: OSRM connection for routing
            config: Simulation config

        Returns:
            Route object

        Raises:
            ValueError: If no route can be found
        """
        start_lon, start_lat = start.get_position()
        end_lon, end_lat = end.get_position()

        osrm_result_dict = osrm.shortest_path_coords(
            start_lon, start_lat, end_lon, end_lat
        )

        if not osrm_result_dict:
            raise ValueError(
                f"No route found from ({start_lon}, {start_lat}) "
                f"to ({end_lon}, {end_lat})"
            )

        osrm_result = OSRMResult.from_dict(osrm_result_dict)
        return self.create_route(osrm_result, osrm, config)

    def create_route(
        self,
        osrm_result: OSRMResult,
        osrm_connection: "OSRMConnection",
        config: Dict[str, Any],
    ) -> "Route":
        """
        Create a Route from an OSRMResult, reusing existing Road objects.

        Roads are created/reused based on segment_id (OSM node IDs).

        Args:
            osrm_result: The parsed OSRM routing result
            osrm_connection: OSRM connection for potential rerouting
            config: Configuration dictionary for route creation

        Returns:
            A new Route object with roads registered to this controller
        """
        from sim.entities.route import Route

        # Create roads from steps (logical road segments with proper turn penalties)
        roads = self._create_roads_from_steps(osrm_result) if osrm_result.steps else []

        # Create the route with the prepared roads
        route = Route(
            osrm_result,
            osrm_connection,
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

    def _generate_point_collection(
        self,
        geometry: List[List[float]],
        length: float,
        maxspeed: float,
        is_final_segment: bool = False,
    ) -> List[Position]:
        """
        Generate evenly-spaced positions along a road segment (1 point per second).

        Uses Shapely LineString for interpolation. To avoid corner snapping (#447),
        endpoint is only included if is_final_segment=True.
        """
        if not geometry:
            return []

        # Edge case: invalid speed or length
        if maxspeed <= 0 or length <= 0:
            edge_points = [Position([float(geometry[0][0]), float(geometry[0][1])])]
            if len(geometry) > 1:
                edge_points.append(
                    Position([float(geometry[-1][0]), float(geometry[-1][1])])
                )
            return edge_points

        # Shapely handles both 2-point and multi-point geometries uniformly
        linestring = LineString(geometry)
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

        return (
            points
            if points
            else [Position([float(geometry[0][0]), float(geometry[0][1])])]
        )

    def _map_step_to_segment_ids(
        self,
        step_geometry: List[List[float]],
        segments: List[OSRMSegment],
    ) -> Tuple[Optional[int], Optional[int]]:
        """Map step geometry to OSM node IDs from annotation segments."""
        if not step_geometry or not segments:
            return (None, None)

        step_start = (float(step_geometry[0][0]), float(step_geometry[0][1]))
        step_end = (float(step_geometry[-1][0]), float(step_geometry[-1][1]))
        node_start: Optional[int] = None
        node_end: Optional[int] = None

        # Single pass with early termination
        for seg in segments:
            if not seg.geometry:
                continue
            if node_start is None:
                seg_start = (float(seg.geometry[0][0]), float(seg.geometry[0][1]))
                if self._coords_match(step_start, seg_start):
                    node_start = seg.node_start
            if node_end is None:
                seg_end = (float(seg.geometry[-1][0]), float(seg.geometry[-1][1]))
                if self._coords_match(step_end, seg_end):
                    node_end = seg.node_end
            if node_start is not None and node_end is not None:
                break

        return (node_start, node_end)

    def _coords_match(
        self,
        coord1: Tuple[float, float],
        coord2: Tuple[float, float],
        tolerance: float = 1e-6,
    ) -> bool:
        """Check if two coordinates match within tolerance."""
        return (
            abs(coord1[0] - coord2[0]) < tolerance
            and abs(coord1[1] - coord2[1]) < tolerance
        )

    def _create_roads_from_steps(
        self,
        osrm_result: OSRMResult,
    ) -> List[Road]:
        """
        Create Road objects from OSRMSteps with segment_id from annotations.

        Uses steps for smooth animation while extracting OSM node IDs from
        annotation segments for future data matching. Steps aggregate
        multiple annotation segments into logical road units.

        Args:
            osrm_result: OSRMResult with steps (and optionally segments)

        Returns:
            List of Road objects with segment_id when annotations available
        """
        roads: List[Road] = []
        segments = osrm_result.segments  # May be empty if no annotations

        for step in osrm_result.steps:
            if not step.geometry:
                continue

            # Calculate road_id from geometry
            road_id = hash(tuple(tuple(coord) for coord in step.geometry))

            # Map step to annotation segments for OSM node IDs
            node_start, node_end = self._map_step_to_segment_ids(
                step.geometry, segments
            )
            segment_id = (node_start, node_end) if node_start and node_end else None

            # Check if we already have this road (by segment_id or road_id)
            existing_road = None
            if segment_id and segment_id in self.segment_id_to_road:
                existing_road = self.segment_id_to_road[segment_id]
            elif road_id in self.road_id_to_road:
                existing_road = self.road_id_to_road[road_id]

            if existing_road:
                roads.append(existing_road)
                continue

            # Derive maxspeed from step data
            maxspeed = step.speed if step.speed else 13.89
            if step.duration > 0 and step.distance > 0:
                maxspeed = step.distance / step.duration

            # Generate interpolated positions along the step
            positions = self._generate_point_collection(
                step.geometry, step.distance, maxspeed
            )

            road = Road(
                road_id=road_id,
                name=step.name,
                pointcollection=positions,
                length=step.distance,
                maxspeed=maxspeed,
                segment_id=segment_id,
            )

            # Register in lookups
            if segment_id:
                self.segment_id_to_road[segment_id] = road
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
        current_position: Tuple[float, float],
    ) -> bool:
        """
        Recalculate a route from current position to its destination.

        Unregisters the route from old roads, fetches a new route from OSRM,
        builds new roads, and re-registers the route.

        Args:
            route: The Route to recalculate
            current_position: Current (lon, lat) coordinates

        Returns:
            bool: True if recalculation was successful, False otherwise
        """
        try:
            # Unregister from old roads
            self.unregister_route(route)

            # Fetch new route from OSRM
            current_lon, current_lat = current_position
            end_lon, end_lat = route.end_coord

            osrm_result_dict = route.routing_connection.shortest_path_coords(
                current_lon, current_lat, end_lon, end_lat
            )

            if not osrm_result_dict:
                logger.warning(f"Route {route.id}: No route found during recalculation")
                return False

            osrm_result = OSRMResult.from_dict(osrm_result_dict)

            # Build new roads from steps
            new_roads = (
                self._create_roads_from_steps(osrm_result) if osrm_result.steps else []
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

            # Update route metadata from new OSRM result
            route.coordinates = osrm_result.coordinates
            route.distance = osrm_result.distance
            route.duration = osrm_result.duration
            route.steps = osrm_result.steps

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
        self.roads_to_routes.pop(road, None)
        if road.segment_id is not None:
            self.segment_id_to_road.pop(road.segment_id, None)
        self.road_id_to_road.pop(road.id, None)
        logger.debug(f"Deallocated road {road.id} (segment_id={road.segment_id})")

    def get_routes_for_road(self, road: Road) -> Set["Route"]:
        """Get all routes using a specific road (returns a copy).

        Args:
            road: The Road to look up

        Returns:
            Set of Routes using this road
        """
        return self.roads_to_routes.get(road, set()).copy()

    def get_routes_for_segment_id(self, segment_id: Tuple[int, int]) -> Set["Route"]:
        """Get all routes using a road with the given segment_id.

        Args:
            segment_id: Tuple of (node_start, node_end) OSM node IDs

        Returns:
            Set of Routes using this segment
        """
        road = self.segment_id_to_road.get(segment_id)
        return self.get_routes_for_road(road) if road else set()

    def get_road_by_segment_id(self, segment_id: Tuple[int, int]) -> Optional[Road]:
        """Get a Road by its segment_id (node_start, node_end).

        Args:
            segment_id: Tuple of (node_start, node_end) OSM node IDs

        Returns:
            The Road if found, None otherwise
        """
        return self.segment_id_to_road.get(segment_id)

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
        self.segment_id_to_road.clear()
        self.road_id_to_road.clear()
        self.routes.clear()
