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

from typing import Dict, List, Optional, Tuple, Union, TYPE_CHECKING
from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.osrm_result import OSRMResult, OSRMStep
from shapely.geometry import LineString
import numpy as np
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sim.osm.OSRMConnection import OSRMConnection
    from sim.map.MapController import MapController


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
        route_data: Union[OSRMResult, List[int]],
        routing_connection: "OSRMConnection",
        config: Dict,
    ) -> None:
        """
        Initialize a Route from OSRM result.

        Args:
            route_data: OSRMResult instance with route geometry and metadata
            routing_connection: OSRMConnection instance for recalculation
            config: Configuration dictionary with simulation settings
        """
        # Make this object unique.
        Route._route_counter += 1
        self.id: int = Route._route_counter

        # Attributes to keep state of the route's traversal.
        self.current_road_index: int = 0
        self.current_point_index: int = 0
        self.is_finished: bool = False
        self._last_returned_position: Optional[List[float]] = (
            None  # Track last position to avoid duplicates
        )

        # Store routing connection for recalculation
        self.routing_connection = routing_connection

        # Store config for speed calculations
        self.config = config

        # Handle OSRMResult route data
        if isinstance(route_data, OSRMResult):
            self.coordinates = route_data.coordinates
            self.distance = route_data.distance
            self.duration = route_data.duration
            self.steps = route_data.steps

            # Store start/end coordinates for recalculation
            self.start_coord = route_data.start_coord
            self.end_coord = route_data.end_coord

            # Build roads from individual OSRM steps (actual road segments)
            if self.steps:
                self.roads = self._build_roads_from_steps(self.steps)
            else:
                # Fallback: single road from all coordinates
                self.roads = self._build_coordinate_roads(self.coordinates)
        else:
            # Backward compatibility: convert dict to OSRMResult
            # This branch can be removed once all callers use OSRMResult
            raise TypeError(
                f"route_data must be OSRMResult, got {type(route_data).__name__}. "
                "Please update caller to use OSRMResult.from_dict()."
            )

        # Reference to MapController for subscription management
        self.map_controller: Optional["MapController"] = None

        # If no roads were created, the route was finished from the start
        if not self.roads:
            self.is_finished = True

    def _build_roads_from_steps(self, steps: List[OSRMStep]) -> List[Road]:
        """
        Build individual road segments from OSRM steps with accurate speeds.

        Each OSRM step represents an actual road segment with its own:
        - Name (street name)
        - Distance (meters)
        - Duration (seconds)
        - Geometry (coordinates)

        This creates proper road segments with speed-based point spacing.

        Args:
            steps: List of OSRMStep objects

        Returns:
            List of road objects, one per step
        """
        if not steps:
            return []

        # Get default speeds from config
        conversion_factor = self.config["simulation"]["kmh_to_ms_factor"]
        default_speed_kmh = self.config["simulation"]["map_rules"]["roads"][
            "default_road_max_speed"
        ]
        default_speed_ms = default_speed_kmh / conversion_factor

        roads = []

        for step in steps:
            # Extract step data (now type-safe with OSRMStep)
            name = step.name
            distance = step.distance
            duration = step.duration
            coordinates = step.geometry

            if not coordinates or distance <= 0:
                coord_count = len(coordinates) if coordinates else 0
                logger.warning(
                    f"Skipping invalid OSRM step: name='{name}', "
                    f"distance={distance}, coordinates_count={coord_count}"
                )
                continue

            # Use OSRM annotation speed if available (this is the actual speed limit)
            # Otherwise calculate from duration, or use default
            if step.speed and step.speed > 0:
                speed_ms = step.speed
            elif duration > 0:
                speed_ms = distance / duration
            else:
                # Fallback to default speed if duration is missing
                speed_ms = default_speed_ms

            # Create LineString from step coordinates
            linestring = LineString([(lon, lat) for lon, lat in coordinates])

            # Generate evenly-spaced points for this road segment
            positions = self._generate_point_collection(linestring, distance, speed_ms)

            # Create road ID from full geometry
            # (all coordinates define the road's identity)
            road_id = hash(tuple(tuple(coord) for coord in coordinates))

            # Create road object
            road_obj = Road(road_id, name, positions, distance, speed_ms)
            roads.append(road_obj)

        return roads

    def _build_coordinate_roads(self, coordinates: List[List[float]]) -> List[Road]:
        """
        Build road segments from OSRM coordinate list with proper point spacing.

        This creates road-like objects that properly calculate length and generate
        evenly-spaced points based on travel speed, matching the behavior of the
        traditional road class.

        Args:
            coordinates: List of [lon, lat] coordinate pairs from OSRM

        Returns:
            List containing road objects with properly spaced positions
        """
        if not coordinates:
            return []

        # Get speed calculations from config
        conversion_factor = self.config["simulation"]["kmh_to_ms_factor"]
        default_speed_kmh = self.config["simulation"]["map_rules"]["roads"][
            "default_road_max_speed"
        ]
        max_speed_ms = default_speed_kmh / conversion_factor  # m/s

        # Create LineString from coordinates
        # Note: OSRM gives [lon, lat] which is correct for LineString
        linestring = LineString([(lon, lat) for lon, lat in coordinates])

        # Calculate actual length using Shapely (in degrees)
        # For better accuracy, we should use geodesic distance, but this is a start
        length_degrees = linestring.length

        # Convert to approximate meters (rough approximation for Montreal area)
        # At 45° latitude: 1° longitude ≈ 78,850 meters, 1° latitude ≈ 111,320 meters
        # Average approximation: 1° ≈ 95,000 meters
        length_meters = length_degrees * 95000.0

        # If we have distance from OSRM, use it directly
        # (more accurate than approximation)
        if hasattr(self, "distance") and self.distance > 0:
            length_meters = self.distance

        # Generate evenly-spaced points along the route
        positions = self._generate_point_collection(
            linestring, length_meters, max_speed_ms
        )

        # Create a road ID from full geometry
        # (all coordinates define the road's identity)
        road_id = hash(tuple(tuple(coord) for coord in coordinates))

        # Create road object (fallback route has no specific name)
        road_obj = Road(road_id, None, positions, length_meters, max_speed_ms)
        return [road_obj]

    def _generate_point_collection(
        self, linestring: LineString, length: float, maxspeed: float
    ) -> List[Position]:
        """
        Generate evenly-spaced Position objects along a route.

        Points represent where the vehicle will be at each second of travel time.
        Spacing is determined by the max speed: faster roads = larger spacing.

        Args:
            linestring: The route geometry
            length: Route length in meters
            maxspeed: Maximum speed in m/s

        Returns:
            List of Position objects spaced one second apart
        """
        points: List[Position] = []

        if maxspeed <= 0 or length <= 0:
            # Edge case: add start and end only
            coords = list(linestring.coords)
            if coords:
                points.append(Position([float(coords[0][0]), float(coords[0][1])]))
                if len(coords) > 1:
                    points.append(
                        Position([float(coords[-1][0]), float(coords[-1][1])])
                    )
            return points

        # Distance traveled in one second at max speed
        distance_increment = maxspeed  # meters per second

        # Get coordinates
        coords = list(linestring.coords)

        if len(coords) == 2:
            # Simple two-point line
            start_lon, start_lat = coords[0]
            end_lon, end_lat = coords[1]

            # Calculate number of seconds needed to traverse
            time_seconds = length / maxspeed
            num_points = int(np.ceil(time_seconds)) + 1

            # Generate points for each second of travel
            for i in range(num_points):
                distance = min(i * distance_increment, length)
                t = distance / length  # interpolation parameter (0 to 1)

                lon = float(start_lon + t * (end_lon - start_lon))
                lat = float(start_lat + t * (end_lat - start_lat))

                new_position = Position([lon, lat])

                # Avoid duplicates
                if (
                    not points
                    or points[-1].get_position() != new_position.get_position()
                ):
                    points.append(new_position)
        else:
            # Multi-vertex linestring - interpolate along the path
            # Shapely's interpolate uses distance along the line in the same units
            # as the coordinates (degrees in our case)

            # We need to interpolate in degrees, not meters
            # Calculate the ratio
            total_length_degrees = linestring.length

            for i in range(int(np.ceil(length / distance_increment)) + 1):
                distance_meters = min(i * distance_increment, length)

                # Convert meters back to degrees for interpolation
                distance_degrees = (distance_meters / length) * total_length_degrees

                point = linestring.interpolate(distance_degrees)
                new_position = Position([float(point.x), float(point.y)])

                # Avoid duplicates
                if (
                    not points
                    or points[-1].get_position() != new_position.get_position()
                ):
                    points.append(new_position)

            # Always include the exact last point
            last_coord = coords[-1]
            last_position = Position([float(last_coord[0]), float(last_coord[1])])

            if not points or points[-1].get_position() != last_position.get_position():
                points.append(last_position)

        # Ensure we have at least start and end
        if len(points) == 0 and coords:
            points.append(Position([float(coords[0][0]), float(coords[0][1])]))
            if len(coords) > 1 and coords[0] != coords[-1]:
                points.append(Position([float(coords[-1][0]), float(coords[-1][1])]))

        return points

    def subscribe_to_map_controller(self, map_controller: "MapController") -> None:
        """Subscribes this route to all roads it traverses via the MapController.

        Registers this route with the MapController for each road segment it uses.
        This enables the MapController to track which routes are using which roads,
        facilitating traffic management and route updates.

        Args:
            map_controller: The MapController instance that manages road subscriptions
                and traffic routing in the simulation.

        Returns:
            None
        """
        self.map_controller = map_controller
        for road_segment in self.roads:
            map_controller._subscribe_route_to_road(road_segment.id, self)

    def unsubscribe_from_all_roads(self) -> None:
        """Unsubscribes this route from all roads in the MapController.

        Removes this route from all road subscriptions in the MapController.
        This should be called when the route is being recalculated or has finished
        to ensure proper cleanup and prevent memory leaks.

        The method safely handles the case where no MapController is set.

        Returns:
            None
        """
        if self.map_controller:
            for road_segment in self.roads:
                self.map_controller._unsubscribe_route_from_road(road_segment.id, self)

    def unsubscribe_from_road(self, road_id: int) -> None:
        """Unsubscribes this route from a specific road segment.

        Called when the route has passed a road segment and no longer needs
        to be tracked for that road. Removes this route from the MapController's
        subscription list for the specified road.

        Args:
            road_id: The ID of the road segment to unsubscribe from.

        Returns:
            None
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

        current_position = self._get_current_position()
        if not current_position:
            self.is_finished = True
            return False

        success = self._fetch_and_apply_new_route(current_position)
        if not success:
            self.is_finished = True

        return success

    def _get_current_position(self) -> Optional[Tuple[float, float]]:
        """
        Get the current position coordinates from the route traversal state.

        Returns:
            Tuple of (lon, lat) or None if position cannot be determined
        """
        if self.current_road_index >= len(self.roads):
            return None

        current_road = self.roads[self.current_road_index]
        if self.current_point_index >= len(current_road.pointcollection):
            return None

        current_position = current_road.pointcollection[self.current_point_index]
        pos = current_position.get_position()
        return (pos[0], pos[1])

    def _fetch_and_apply_new_route(self, current_position: Tuple[float, float]) -> bool:
        """
        Fetch a new route from OSRM and apply it to this Route object.

        Args:
            current_position: Starting (lon, lat) coordinates

        Returns:
            bool: True if new route was successfully fetched and applied
        """
        try:
            current_lon, current_lat = current_position
            end_lon, end_lat = self.end_coord

            osrm_result_dict = self.routing_connection.shortest_path_coords(
                current_lon, current_lat, end_lon, end_lat
            )

            if not osrm_result_dict:
                logger.warning(f"Route {self.id}: No route found during recalculation")
                return False

            osrm_result = OSRMResult.from_dict(osrm_result_dict)
            new_roads = self._build_new_roads(osrm_result)

            if new_roads:
                self._apply_new_roads(new_roads)
                return True

            return False

        except Exception as e:
            logger.error(f"Route {self.id} recalculation failed: {e}")
            return False

    def _build_new_roads(self, osrm_result: OSRMResult) -> List[Road]:
        """
        Build road segments from OSRM result.

        Args:
            osrm_result: OSRM route result

        Returns:
            List of Road objects
        """
        if osrm_result.steps:
            return self._build_roads_from_steps(osrm_result.steps)
        else:
            return self._build_coordinate_roads(osrm_result.coordinates)

    def _apply_new_roads(self, new_roads: List[Road]) -> None:
        """
        Apply new roads to the route and reset traversal state.

        Args:
            new_roads: List of new Road objects to replace current roads
        """
        self.roads = new_roads
        self.current_road_index = 0
        self.current_point_index = 0

        # Subscribe to new roads
        if self.map_controller:
            for road_segment in self.roads:
                self.map_controller._subscribe_route_to_road(road_segment.id, self)

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

    def next(
        self, as_json: bool = False
    ) -> Optional[Union[Dict[str, Union[int, List[float]]], Position]]:
        """
        Returns the next Position object in the traversal sequence.

        Automatically handles moving from the end of one road segment to the
        beginning of the next. Returns None when the end of the route is reached.
        Skips consecutive duplicate positions.

        Args:
            as_json (bool): If True, returns in JSON format with id and position.
                            If False [default], returns Position object.

        Returns:
            Position object, dict with id and position, or None when finished.
        """
        if self.is_finished:
            return None

        # Find next non-duplicate position
        point_to_return = None
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
                or candidate_point.get_position() != self._last_returned_position
            ):
                point_to_return = candidate_point
                self._last_returned_position = candidate_point.get_position()

            # Move to next position (whether it was duplicate or not)
            self.current_point_index += 1

        if point_to_return is None:
            return None

        # Return based on format
        if as_json:
            return {
                "id": self.id,
                "position": point_to_return.get_position(),
            }
        else:
            return point_to_return
