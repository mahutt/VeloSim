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

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

"""
OSRMConnection - Simplified routing using OSRM HTTP API

This class delegates all routing operations to an OSRM
(Open Source Routing Machine) server.

Key design principles:
- Delegate node snapping, routing, and distance calculations to OSRM
- Keep implementation simple and stateless
"""

logger = logging.getLogger(__name__)


class OSRMConnection:
    """
    Simplified routing interface using OSRM HTTP API.

    This implementation delegates all routing work to an OSRM server.

    Attributes:
        osrm_base_url (str): Base URL of the OSRM server
        _session (requests.Session): Persistent HTTP session for better
            performance
    """

    def __init__(self, osrm_url: Optional[str] = None):
        """
        Initialize OSRM connection.

        Args:
            osrm_url: Base URL of OSRM server. If not provided, will check
                     OSRM_URL, OSRM_LOCAL_URL, or OSRM_PUBLIC_URL environment
                     variables in that order.
                     Examples:
                     - "http://localhost:5000" (local)
                     - "http://router.project-osrm.org" (public demo)

        Raises:
            ValueError: If no OSRM URL is provided or configured via environment
        """
        # Priority: explicit parameter > OSRM_URL > OSRM_LOCAL_URL > OSRM_PUBLIC_URL
        self.osrm_base_url = (
            osrm_url
            or os.getenv("OSRM_URL")
            or os.getenv("OSRM_LOCAL_URL")
            or os.getenv("OSRM_PUBLIC_URL")
        )

        if not self.osrm_base_url:
            raise ValueError(
                "No OSRM server URL configured. Please provide "
                "osrm_url parameter or set one of these environment "
                "variables: OSRM_URL, OSRM_LOCAL_URL, or OSRM_PUBLIC_URL"
            )

        self._session = requests.Session()

        # Verify OSRM server is accessible
        if not self._verify_osrm_connection():
            raise ConnectionError(
                f"Cannot connect to OSRM server at {self.osrm_base_url}"
            )

        logger.info(f"OSRMConnection initialized with server: {self.osrm_base_url}")

    def _verify_osrm_connection(self) -> bool:
        """Verify that the OSRM server is accessible.

        Performs a simple test query between two Montreal coordinates to check
        if the OSRM server is responding correctly.

        Returns:
            True if server responds with status 200, False otherwise.
        """
        try:
            # Simple test query between two points in Montreal
            test_url = (
                f"{self.osrm_base_url}/route/v1/driving/"
                "-73.5673,45.5017;-73.5533,45.5017"
            )
            response = self._session.get(
                test_url, params={"overview": "false"}, timeout=5
            )
            return bool(response.status_code == 200)
        except Exception as e:
            logger.error(f"Failed to connect to OSRM server: {e}")
            return False

    # ============================================================================
    # Core coordinate-based routing methods
    # ============================================================================

    def shortest_path_coords(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Get shortest path between two coordinates using OSRM.

        Args:
            start_lon: Starting longitude
            start_lat: Starting latitude
            end_lon: Ending longitude
            end_lat: Ending latitude

        Returns:
            Dict with keys:

                - 'coordinates': List of [lon, lat] waypoints
                - 'distance': Total distance in meters
                - 'duration': Total duration in seconds

            Returns None if no valid route found
        """
        # Build OSRM route query
        url = (
            f"{self.osrm_base_url}/route/v1/driving/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}"
        )
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "true",
        }

        try:
            response = self._session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok" or not data.get("routes"):
                logger.warning(
                    "OSRM returned no routes: %s",
                    data.get("code", "Unknown error"),
                )
                return None

            route = data["routes"][0]
            coordinates = route["geometry"]["coordinates"]
            distance = route["distance"]
            duration = route["duration"]

            # Extract detailed step information (individual road segments)
            steps = []
            if "legs" in route and len(route["legs"]) > 0:
                leg = route["legs"][0]
                leg_steps = leg.get("steps", [])

                # Get speed annotations if available (per-coordinate segment speeds)
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
                    # Each step has N coordinates, annotations have N-1 segments
                    step_coords = step.get("geometry", {}).get("coordinates", [])
                    num_segments = len(step_coords) - 1 if len(step_coords) > 1 else 0

                    if annotation_speeds and num_segments > 0:
                        # Extract the annotation speeds for this step's segments
                        end_index = min(
                            annotation_index + num_segments, len(annotation_speeds)
                        )
                        step_speeds = annotation_speeds[annotation_index:end_index]

                        # Use max speed for this step (represents speed limit)
                        if step_speeds:
                            step_data["speed"] = max(step_speeds)

                        # Move to next step's annotation position
                        annotation_index = end_index

                    steps.append(step_data)

            # Parse segments from annotation nodes (OSM node-based identification)
            segments = self._parse_segments_from_annotations(route)

            return {
                "coordinates": coordinates,
                "distance": distance,
                "duration": duration,
                "steps": steps,  # Add detailed step information
                "segments": segments,  # OSM node-based segments for RouteController
            }

        except requests.RequestException as e:
            logger.error(f"OSRM request failed: {e}")
            return None

    def get_distance_coords(
        self, start_lon: float, start_lat: float, end_lon: float, end_lat: float
    ) -> Optional[float]:
        """
        Get the distance between two coordinates along the road network.

        Args:
            start_lon: Starting longitude
            start_lat: Starting latitude
            end_lon: Ending longitude
            end_lat: Ending latitude

        Returns:
            Distance in meters, or None if no route found
        """
        result = self.shortest_path_coords(start_lon, start_lat, end_lon, end_lat)
        return result["distance"] if result else None

    def snap_to_road(self, lon: float, lat: float) -> Tuple[float, float]:
        """
        Snap a coordinate to the nearest road using OSRM's nearest service.

        Args:
            lon: Longitude
            lat: Latitude

        Returns:
            Tuple of (snapped_lon, snapped_lat)
        """
        url = f"{self.osrm_base_url}/nearest/v1/driving/{lon},{lat}"
        params = {"number": 1}

        try:
            response = self._session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "Ok" and data.get("waypoints"):
                location = data["waypoints"][0]["location"]
                return tuple(location)
            else:
                # If snapping fails, return original coordinates
                logger.warning(f"Failed to snap coordinate ({lon}, {lat})")
                return (lon, lat)

        except requests.RequestException as e:
            logger.error(f"OSRM nearest request failed: {e}")
            return (lon, lat)

    # ============================================================================
    # Segment parsing methods
    # ============================================================================

    def _parse_segments_from_annotations(
        self, route: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse OSM node-based segments from OSRM annotation data.

        Extracts annotation.nodes, annotation.distance, and annotation.duration
        from the OSRM response to build segment data with OSM node identifiers.

        The OSRM annotation structure is:
        - nodes: [N] array of OSM node IDs along the route
        - distance: [N-1] array of distances between consecutive nodes
        - duration: [N-1] array of durations between consecutive nodes

        Args:
            route: The OSRM route object from the API response

        Returns:
            List of segment dictionaries with keys:
            - node_start: Starting OSM node ID
            - node_end: Ending OSM node ID
            - distance: Segment distance in meters
            - duration: Segment duration in seconds
            - geometry: List of [lon, lat] coordinates for this segment
            - road_name: Optional street name (always None, not yet implemented)
        """
        segments: List[Dict[str, Any]] = []

        if "legs" not in route or not route["legs"]:
            return segments

        leg = route["legs"][0]
        annotations = leg.get("annotation", {})

        nodes = annotations.get("nodes", [])
        distances = annotations.get("distance", [])
        durations = annotations.get("duration", [])

        # Need at least 2 nodes to form a segment
        if len(nodes) < 2:
            logger.debug("No annotation nodes available, skipping segment parsing")
            return segments

        # Validate array lengths
        if len(nodes) - 1 != len(distances) or len(nodes) - 1 != len(durations):
            logger.warning(
                f"Annotation array length mismatch: nodes={len(nodes)}, "
                f"distances={len(distances)}, durations={len(durations)}"
            )
            # Try to proceed with minimum available data
            num_segments = min(len(nodes) - 1, len(distances), len(durations))
        else:
            num_segments = len(nodes) - 1

        # Get route coordinates for geometry assignment
        coordinates = route.get("geometry", {}).get("coordinates", [])

        # Road name mapping is not yet implemented - would require matching
        # segment geometry to step geometry. For now, road_name is always None.
        step_name_map: Dict[Tuple[int, int], Optional[str]] = {}

        # Track coordinate index for geometry assignment
        coord_index = 0

        for i in range(num_segments):
            node_start = nodes[i]
            node_end = nodes[i + 1]
            distance = distances[i]
            duration = durations[i]

            # Extract geometry for this segment
            # Each segment corresponds to one edge between two nodes
            # In the simplified case, we assign 2 coordinates per segment
            segment_geometry: List[List[float]] = []
            if coord_index < len(coordinates):
                # Start coordinate
                segment_geometry.append(coordinates[coord_index])
                # For intermediate segments, the end coordinate of one
                # is the start of the next
                if coord_index + 1 < len(coordinates):
                    segment_geometry.append(coordinates[coord_index + 1])
                    coord_index += 1
                elif segment_geometry:
                    # Last segment - just duplicate the last point
                    segment_geometry.append(segment_geometry[-1])

            # Look up road name from step data
            road_name = step_name_map.get((node_start, node_end))

            segments.append(
                {
                    "node_start": node_start,
                    "node_end": node_end,
                    "distance": distance,
                    "duration": duration,
                    "geometry": segment_geometry,
                    "road_name": road_name,
                }
            )

        logger.debug(f"Parsed {len(segments)} segments from OSRM annotations")
        return segments

    # ============================================================================
    # Utility methods
    # ============================================================================

    def get_route_details(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed route information including turn-by-turn instructions.

        Args:
            start_lon: Starting longitude
            start_lat: Starting latitude
            end_lon: Ending longitude
            end_lat: Ending latitude

        Returns:
            Dict with detailed route info including steps, or None if not found
        """
        url = (
            f"{self.osrm_base_url}/route/v1/driving/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}"
        )
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
            "annotations": "true",
        }

        try:
            response = self._session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != "Ok" or not data.get("routes"):
                return None

            route_data: Dict[str, Any] = data["routes"][0]
            return route_data

        except requests.RequestException as e:
            logger.error(f"OSRM route details request failed: {e}")
            return None

    def close(self) -> None:
        """Close the HTTP session.

        Returns:
            None
        """
        if hasattr(self, "_session"):
            self._session.close()
            logger.info("OSRMConnection closed")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()


# Convenience getter
def get_osrm_connection(osrm_url: Optional[str] = None) -> OSRMConnection:
    """
    Create an OSRMConnection instance.

    Args:
        osrm_url: Base URL of OSRM server

    Returns:
        OSRMConnection instance
    """
    return OSRMConnection(osrm_url)
