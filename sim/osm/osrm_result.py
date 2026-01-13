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

# OSRM Result Types - Typed wrappers for OSRM API response data.
#
# This module provides dataclasses that map to OSRM (Open Source Routing Machine)
# API response structures, enabling type-safe access to routing data.
#
# OSRM API Documentation Reference:
#     https://project-osrm.org/docs/v5.5.1/api/
#
# Terminology (from OSRM docs):
#     Route: A complete path through waypoints with total distance/duration.
#         See: https://project-osrm.org/docs/v5.5.1/api/#route-object
#
#     RouteLeg: A route segment between two waypoints. Contains steps and
#         annotations when requested.
#         See: https://project-osrm.org/docs/v5.5.1/api/#routeleg-object
#
#     RouteStep: A maneuver followed by travel along a single way. Contains
#         distance, duration, geometry, and road name.
#         See: https://project-osrm.org/docs/v5.5.1/api/#routestep-object
#
#     Annotation: Fine-grained metadata for each coordinate along the route.
#         Contains arrays for distance, duration, and OSM node IDs.
#         See: https://project-osrm.org/docs/v5.5.1/api/#annotation-object
#
#         Structure:
#             - nodes: [N] array of OSM node IDs along the route
#             - distance: [N-1] array of distances (metres) between consecutive nodes
#             - duration: [N-1] array of durations (seconds) between consecutive nodes
#
#     Coordinates: All coordinates use [longitude, latitude] format (GeoJSON order).

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class OSRMSegment:
    """
    Represents a single segment between two OSM nodes in an OSRM route.

    Derived from OSRM's Annotation object which provides fine-grained metadata
    for each coordinate along a route. When `annotations=true` is requested,
    OSRM returns arrays of OSM node IDs, distances, and durations.

    OSRM Annotation Reference:
        https://project-osrm.org/docs/v5.5.1/api/#annotation-object

        The annotation structure contains:
        - nodes: [N] array of OSM node IDs along the route
        - distance: [N-1] array of distances in metres between consecutive nodes
        - duration: [N-1] array of durations in seconds between consecutive nodes

        Each OSRMSegment represents one edge (node[i] → node[i+1]) with its
        corresponding distance[i] and duration[i] values.

    The segment_id (node_start, node_end) tuple uniquely identifies a road
    segment in the OSM network, allowing for:
    - Road reuse across multiple routes
    - Traffic data association with specific road segments
    - Efficient road ↔ route many-to-many relationship management

    Attributes:
        node_start: Starting OSM node ID for this segment (from annotation.nodes[i])
        node_end: Ending OSM node ID for this segment (from annotation.nodes[i+1])
        distance: Length of this segment in meters (from annotation.distance[i])
        duration: Base time to traverse in seconds (from annotation.duration[i])
        geometry: List of [lon, lat] coordinate pairs defining the segment's path
        road_name: Street or road name (None if unnamed)
    """

    node_start: int
    node_end: int
    distance: float
    duration: float
    geometry: List[List[float]]
    road_name: Optional[str] = None

    def get_segment_id(self) -> Tuple[int, int]:
        """
        Get the unique segment identifier as a tuple of OSM node IDs.

        Returns:
            Tuple of (node_start, node_end) that uniquely identifies this
            road segment in the OSM network.
        """
        return (self.node_start, self.node_end)

    @classmethod
    def from_annotation_data(
        cls,
        node_start: int,
        node_end: int,
        distance: float,
        duration: float,
        geometry: List[List[float]],
        road_name: Optional[str] = None,
    ) -> "OSRMSegment":
        """
        Create an OSRMSegment from OSRM annotation data.

        This factory method constructs a segment from the data extracted
        from OSRM's annotation arrays (nodes, distances, durations).

        Args:
            node_start: Starting OSM node ID
            node_end: Ending OSM node ID
            distance: Segment distance in meters
            duration: Segment duration in seconds
            geometry: List of [lon, lat] coordinates for this segment
            road_name: Optional street name

        Returns:
            OSRMSegment instance with the provided data
        """
        return cls(
            node_start=node_start,
            node_end=node_end,
            distance=distance,
            duration=duration,
            geometry=geometry,
            road_name=road_name,
        )


@dataclass
class OSRMStep:
    """
    Represents a single step (maneuver + road segment) in an OSRM route.

    Maps to OSRM's RouteStep object. A step consists of a maneuver such as
    a turn or merge, followed by a distance of travel along a single way
    to the subsequent step.

    OSRM RouteStep Reference:
        https://project-osrm.org/docs/v5.5.1/api/#routestep-object

        RouteStep properties (from OSRM docs):
        - distance: Distance from maneuver to subsequent step in meters (float)
        - duration: Estimated travel time in seconds (float)
        - geometry: Unsimplified geometry of the route segment
        - name: Name of the way along which travel proceeds

    Attributes:
        name: Street or road name (None if unnamed)
        distance: Length of this step in meters
        duration: Time to traverse this step in seconds
        geometry: List of [lon, lat] coordinate pairs defining the step's path
        speed: Maximum speed for this step in m/s (derived from annotations,
        None if unavailable)
    """

    name: Optional[str]
    distance: float
    duration: float
    geometry: List[List[float]]
    speed: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OSRMStep":
        """
        Create an OSRMStep from OSRM API response data.

        Args:
            data: Dictionary from OSRM step data

        Returns:
            OSRMStep instance with validated data
        """
        # Handle both formats: geometry as list or as dict with coordinates key
        geometry = data.get("geometry", [])
        if isinstance(geometry, dict):
            geometry = geometry.get("coordinates", [])

        return cls(
            name=data.get("name") or None,
            distance=float(data.get("distance", 0.0)),
            duration=float(data.get("duration", 0.0)),
            geometry=geometry,
            speed=(
                float(data["speed"])
                if "speed" in data and data["speed"] is not None
                else None
            ),
        )


@dataclass
class OSRMResult:
    """
    Represents a complete route result from the OSRM routing engine.

    Maps to OSRM's Route object which represents a route through (potentially
    multiple) waypoints.

    OSRM Route Reference:
        https://project-osrm.org/docs/v5.5.1/api/#route-object

        Route properties (from OSRM docs):
        - distance: Distance traveled by the route in meters (float)
        - duration: Estimated travel time in seconds (float)
        - geometry: Whole geometry of the route (format depends on geometries param)
        - legs: Array of RouteLeg objects between waypoints

    OSRM RouteLeg Reference:
        https://project-osrm.org/docs/v5.5.1/api/#routeleg-object

        RouteLeg contains:
        - steps: Array of RouteStep objects (when steps=true)
        - annotation: Annotation object with node IDs (when annotations=true)

    This class provides type-safe access to OSRM route data, eliminating
    the need for dict.get() fallbacks and null-island checks.

    Attributes:
        coordinates: Complete list of [lon, lat] waypoints for the entire route.
            Note: OSRM uses [longitude, latitude] order (GeoJSON format).
        distance: Total route distance in meters
        duration: Total route duration in seconds
        steps: List of OSRMStep objects (from RouteLeg.steps when steps=true)
        segments: List of OSRMSegment objects with OSM node-based identification.
            Populated from RouteLeg.annotation when annotations=true.
            Falls back to empty list when annotations are unavailable.
    """

    coordinates: List[List[float]]
    distance: float
    duration: float
    steps: List[OSRMStep]
    segments: List[OSRMSegment] = field(default_factory=list)

    @classmethod
    def from_osrm_response(cls, response: Dict[str, Any]) -> "OSRMResult":
        """
        Parse a raw OSRM API response into an OSRMResult.

        This factory method handles the complete parsing of OSRM JSON responses,
        extracting route geometry, steps, and annotation-based segments.

        Args:
            response: Raw JSON response from OSRM route API. Expected structure:
                {
                    "code": "Ok",
                    "routes": [{
                        "geometry": {"coordinates": [[lon, lat], ...]},
                        "distance": float,
                        "duration": float,
                        "legs": [{
                            "steps": [...],
                            "annotation": {"nodes": [...], "distance": [...], ...}
                        }]
                    }]
                }

        Returns:
            OSRMResult instance with parsed route data

        Raises:
            ValueError: If response is invalid or missing required data
        """
        if not isinstance(response, dict):
            raise ValueError(f"Expected dict, got {type(response).__name__}")

        if response.get("code") != "Ok":
            raise ValueError(f"OSRM error: {response.get('code', 'Unknown')}")

        routes = response.get("routes", [])
        if not routes:
            raise ValueError("No routes in OSRM response")

        route = routes[0]

        # Extract coordinates from geometry
        geometry = route.get("geometry", {})
        coordinates = (
            geometry.get("coordinates", []) if isinstance(geometry, dict) else []
        )
        if not coordinates:
            raise ValueError("No coordinates in route geometry")

        distance = float(route.get("distance", 0))
        duration = float(route.get("duration", 0))

        # Parse steps from legs
        steps = cls._parse_steps_from_route(route)

        # Parse segments from annotation nodes
        segments = cls._parse_segments_from_route(route, coordinates)

        return cls(
            coordinates=coordinates,
            distance=distance,
            duration=duration,
            steps=steps,
            segments=segments,
        )

    @classmethod
    def _parse_steps_from_route(cls, route: Dict[str, Any]) -> List["OSRMStep"]:
        """
        Parse OSRMStep objects from OSRM route legs.

        Extracts steps from the first leg and maps annotation speeds to each step.

        Args:
            route: OSRM route object containing legs with steps

        Returns:
            List of OSRMStep objects
        """
        steps: List[OSRMStep] = []

        if "legs" not in route or not route["legs"]:
            return steps

        leg = route["legs"][0]
        leg_steps = leg.get("steps", [])

        # Get speed annotations if available
        annotations = leg.get("annotation", {})
        annotation_speeds = annotations.get("speed", [])

        # Track position in annotation arrays as we process steps
        annotation_index = 0

        for step in leg_steps:
            step_data = {
                "name": step.get("name") or None,
                "distance": step.get("distance", 0),
                "duration": step.get("duration", 0),
                "geometry": step.get("geometry", {}).get("coordinates", []),
            }

            # Map annotation speeds to this step
            step_coords = step.get("geometry", {}).get("coordinates", [])
            num_segments = len(step_coords) - 1 if len(step_coords) > 1 else 0

            if annotation_speeds and num_segments > 0:
                end_index = min(annotation_index + num_segments, len(annotation_speeds))
                step_speeds = annotation_speeds[annotation_index:end_index]

                if step_speeds:
                    step_data["speed"] = max(step_speeds)

                annotation_index = end_index

            steps.append(OSRMStep.from_dict(step_data))

        return steps

    @classmethod
    def _parse_segments_from_route(
        cls,
        route: Dict[str, Any],
        coordinates: List[List[float]],
    ) -> List["OSRMSegment"]:
        """
        Parse OSM node-based segments from OSRM annotation data.

        Extracts annotation.nodes, annotation.distance, and annotation.duration
        from the OSRM response to build segment data with OSM node identifiers.

        Args:
            route: OSRM route object containing legs with annotations
            coordinates: Route coordinates for geometry assignment

        Returns:
            List of OSRMSegment objects with node IDs and geometry
        """
        segments: List[OSRMSegment] = []

        if "legs" not in route or not route["legs"]:
            return segments

        leg = route["legs"][0]
        annotations = leg.get("annotation", {})

        nodes = annotations.get("nodes", [])
        distances = annotations.get("distance", [])
        durations = annotations.get("duration", [])

        # Need at least 2 nodes to form a segment
        if len(nodes) < 2:
            return segments

        # Determine number of segments based on available data
        if len(nodes) - 1 != len(distances) or len(nodes) - 1 != len(durations):
            num_segments = min(len(nodes) - 1, len(distances), len(durations))
        else:
            num_segments = len(nodes) - 1

        # Track coordinate index for geometry assignment
        coord_index = 0

        for i in range(num_segments):
            node_start = nodes[i]
            node_end = nodes[i + 1]
            distance = distances[i]
            duration = durations[i]

            # Extract geometry for this segment
            segment_geometry: List[List[float]] = []
            if coord_index < len(coordinates):
                segment_geometry.append(coordinates[coord_index])
                if coord_index + 1 < len(coordinates):
                    segment_geometry.append(coordinates[coord_index + 1])
                    coord_index += 1
                elif segment_geometry:
                    segment_geometry.append(segment_geometry[-1])

            segments.append(
                OSRMSegment.from_annotation_data(
                    node_start=node_start,
                    node_end=node_end,
                    distance=distance,
                    duration=duration,
                    geometry=segment_geometry,
                    road_name=None,  # Not yet implemented
                )
            )

        return segments

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OSRMResult":
        """
        Create an OSRMResult from pre-parsed data dictionary.

        This factory method handles validation and type conversion for
        dictionaries that have already been structured (e.g., from tests).

        Args:
            data: Pre-parsed dictionary with keys:
                  'coordinates', 'distance', 'duration', 'steps'
                  Optional: 'segments'

        Returns:
            OSRMResult instance with validated and typed data

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        # Validate required fields
        if "coordinates" not in data:
            raise ValueError("Missing required field: 'coordinates'")
        if "distance" not in data:
            raise ValueError("Missing required field: 'distance'")
        if "duration" not in data:
            raise ValueError("Missing required field: 'duration'")

        # Extract and validate coordinates
        coordinates = data["coordinates"]
        if not isinstance(coordinates, list):
            raise ValueError("'coordinates' must be a list")
        if not coordinates:
            raise ValueError("'coordinates' cannot be empty")

        # Convert distance and duration to floats
        try:
            distance = float(data["distance"])
            duration = float(data["duration"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid distance or duration: {e}")

        # Parse steps if present
        steps_data = data.get("steps", [])
        steps = [OSRMStep.from_dict(step) for step in steps_data]

        # Parse segments if present (populated by OSRMConnection from annotations)
        segments: List[OSRMSegment] = []
        segments_data = data.get("segments", [])
        for i, seg in enumerate(segments_data):
            try:
                segments.append(
                    OSRMSegment.from_annotation_data(
                        node_start=seg["node_start"],
                        node_end=seg["node_end"],
                        distance=seg["distance"],
                        duration=seg["duration"],
                        geometry=seg.get("geometry", []),
                        road_name=seg.get("road_name"),
                    )
                )
            except KeyError as e:
                raise ValueError(f"Segment {i} missing required field: {e}")

        return cls(
            coordinates=coordinates,
            distance=distance,
            duration=duration,
            steps=steps,
            segments=segments,
        )

    def __post_init__(self) -> None:
        """Validate data after initialization."""
        if not self.coordinates:
            raise ValueError("coordinates cannot be empty")
        if self.distance < 0:
            raise ValueError("distance cannot be negative")
        if self.duration < 0:
            raise ValueError("duration cannot be negative")
