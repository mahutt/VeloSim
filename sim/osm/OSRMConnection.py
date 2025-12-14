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

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from pandas import Series

"""
OSRMConnection - Simplified routing using OSRM HTTP API

This class delegates all routing operations to an OSRM
(Open Source Routing Machine) server.
It maintains minimal local state, only tracking blocked road coordinates.

Key design principles:
- Delegate node snapping, routing, and distance calculations to OSRM
- Use coordinate-based road blocking instead of graph manipulation
- Provide compatibility wrappers for legacy code expecting node IDs
- Keep implementation simple and stateless
"""

logger = logging.getLogger(__name__)


class OSRMConnection:
    """
    Simplified routing interface using OSRM HTTP API.

    This implementation delegates all routing work to an OSRM server, maintaining
    only a set of blocked road coordinates for filtering routes.

    Attributes:
        osrm_base_url (str): Base URL of the OSRM server
        blocked_roads (Dict[Tuple[float, float], float]): Map of (lon, lat)
            to radius in degrees
        _session (requests.Session): Persistent HTTP session for better
            performance
    """

    _instance = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "OSRMConnection":
        if cls._instance is None:
            cls._instance = super(OSRMConnection, cls).__new__(cls)
        return cls._instance

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
        if hasattr(self, "_initialized"):
            return

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

        self.blocked_roads: Dict[Tuple[float, float], float] = {}
        self._session = requests.Session()
        self._initialized = True

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
        check_blocked: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Get shortest path between two coordinates using OSRM.

        Args:
            start_lon: Starting longitude
            start_lat: Starting latitude
            end_lon: Ending longitude
            end_lat: Ending latitude
            check_blocked: Whether to check for blocked roads in the route

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

            # Check if route passes through blocked areas
            if check_blocked and self._route_intersects_blocked(coordinates):
                logger.info("Route intersects blocked roads, attempting alternative")
                # TODO: Implement alternative route finding or
                # waypoint injection
                # For now, return None to indicate blocked route
                return None

            return {
                "coordinates": coordinates,
                "distance": distance,
                "duration": duration,
                "steps": steps,  # Add detailed step information
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
        result = self.shortest_path_coords(
            start_lon, start_lat, end_lon, end_lat, check_blocked=False
        )
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
    # Road blocking methods
    # ============================================================================

    def block_road_area(self, lon: float, lat: float, radius: float = 0.001) -> None:
        """
        Block a circular area around a coordinate.

        This adds the coordinate to the blocked set. When routing, paths that
        pass through this area will be rejected.

        Args:
            lon: Longitude of center point
            lat: Latitude of center point
            radius: Radius in degrees (approximately 100m at 0.001)

        Returns:
            None
        """
        self.blocked_roads[(lon, lat)] = radius
        logger.debug(f"Blocked road area at ({lon}, {lat}) with radius {radius}")

    def unblock_road_area(self, lon: float, lat: float) -> None:
        """
        Remove a blocked road area.

        Args:
            lon: Longitude of blocked point
            lat: Latitude of blocked point

        Returns:
            None
        """
        self.blocked_roads.pop((lon, lat), None)
        logger.debug(f"Unblocked road area at ({lon}, {lat})")

    def clear_blocked_roads(self) -> None:
        """Clear all blocked roads.

        Returns:
            None
        """
        self.blocked_roads.clear()
        logger.info("Cleared all blocked roads")

    def _route_intersects_blocked(
        self, coordinates: List[List[float]], tolerance: float = 0.001
    ) -> bool:
        """Check if a route passes through any blocked areas.

        Analyzes each line segment of the route to determine if it comes within
        the blocked radius of any blocked point. This is more accurate than just
        checking waypoints.

        Args:
            coordinates: List of [lon, lat] waypoints defining the route.
            tolerance: Additional tolerance in degrees added to each blocked
                radius. Defaults to 0.001 degrees (~100m).

        Returns:
            True if any segment of the route intersects a blocked area, False otherwise.
        """
        if not self.blocked_roads:
            return False

        # Check each line segment of the route
        for i in range(len(coordinates) - 1):
            p1_lon, p1_lat = coordinates[i]
            p2_lon, p2_lat = coordinates[i + 1]

            # Check if this segment comes within range of any blocked point
            for (blocked_lon, blocked_lat), radius in self.blocked_roads.items():
                dist = self._point_to_segment_distance(
                    blocked_lon, blocked_lat, p1_lon, p1_lat, p2_lon, p2_lat
                )
                if dist < (radius + tolerance):
                    return True

        return False

    @staticmethod
    def _point_to_segment_distance(
        px: float, py: float, x1: float, y1: float, x2: float, y2: float
    ) -> float:
        """
        Calculate the minimum distance from a point to a line segment.

        Args:
            px, py: Point coordinates
            x1, y1: Line segment start coordinates
            x2, y2: Line segment end coordinates

        Returns:
            Minimum distance from point to segment (Euclidean approximation)
        """
        # Vector from segment start to point
        dx = x2 - x1
        dy = y2 - y1

        # Handle degenerate case where segment is a point
        if dx == 0 and dy == 0:
            return float(((px - x1) ** 2 + (py - y1) ** 2) ** 0.5)

        # Project point onto line (parameterized by t)
        # t=0 is at (x1,y1), t=1 is at (x2,y2)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

        # Find closest point on segment
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy

        # Return distance to nearest point
        return float(((px - nearest_x) ** 2 + (py - nearest_y) ** 2) ** 0.5)

    # ============================================================================
    # Compatibility wrappers for node-based interface
    # ============================================================================

    @staticmethod
    def _coord_to_virtual_node(lon: float, lat: float) -> int:
        """Convert a coordinate to a virtual node ID for backward compatibility.

        Creates a stable MD5 hash of the coordinates to generate a consistent
        integer node ID. This allows legacy code expecting node-based interfaces
        to work with coordinate-based routing.

        Args:
            lon: Longitude coordinate.
            lat: Latitude coordinate.

        Returns:
            Virtual node ID as an integer hash (first 8 hex digits of MD5).
        """
        # Create a stable hash from coordinates
        coord_str = f"{lon:.6f},{lat:.6f}"
        return int(hashlib.md5(coord_str.encode()).hexdigest()[:8], 16)

    @staticmethod
    def _virtual_node_to_coord(
        node_id: int, coord_lookup: Dict[int, Tuple[float, float]]
    ) -> Tuple[float, float]:
        """Convert a virtual node ID back to coordinates.

        Looks up the coordinates for a given virtual node ID. Since node IDs
        are hashed, this requires an external lookup dictionary maintained by
        the calling code.

        Args:
            node_id: Virtual node ID to look up.
            coord_lookup: Dictionary mapping node IDs to (lon, lat) tuples.

        Returns:
            Tuple of (lon, lat), or (0.0, 0.0) if node_id not found.
        """
        return coord_lookup.get(node_id, (0.0, 0.0))

    def shortest_path(
        self,
        start_node: int,
        end_node: int,
        coord_lookup: Optional[Dict[int, Tuple[float, float]]] = None,
    ) -> Optional[List[int]]:
        """
        Compatibility wrapper for node-based shortest path queries.

        This method is provided for backward compatibility with code expecting
        node IDs. New code should use shortest_path_coords() instead.

        Args:
            start_node: Starting node ID (virtual or real)
            end_node: Ending node ID (virtual or real)
            coord_lookup: Dictionary mapping node IDs to (lon, lat) coordinates

        Returns:
            List of virtual node IDs representing the path, or None if no path found
        """
        if coord_lookup is None:
            raise ValueError("coord_lookup dictionary required for node-based routing")

        # Convert nodes to coordinates
        start_coord = coord_lookup.get(start_node)
        end_coord = coord_lookup.get(end_node)

        if not start_coord or not end_coord:
            logger.error(
                f"Cannot find coordinates for nodes {start_node} or {end_node}"
            )
            return None

        # Get route as coordinates
        result = self.shortest_path_coords(*start_coord, *end_coord)
        if not result:
            return None

        # Convert coordinate path to virtual node IDs
        path = [
            self._coord_to_virtual_node(lon, lat) for lon, lat in result["coordinates"]
        ]
        return path

    def coordinates_to_nearest_node(self, lon: float, lat: float) -> int:
        """
        Compatibility wrapper that snaps to road and returns virtual node ID.

        New code should use snap_to_road() directly for coordinates.

        Args:
            lon: Longitude
            lat: Latitude

        Returns:
            Virtual node ID for the snapped location
        """
        snapped_lon, snapped_lat = self.snap_to_road(lon, lat)
        return self._coord_to_virtual_node(snapped_lon, snapped_lat)

    def get_node_coordinates(self, node_id: int) -> Optional[Series]:
        """
        Compatibility wrapper for getting node coordinates.

        This returns a pandas Series with 'x' and 'y' keys for compatibility
        with legacy code expecting node-based interfaces.

        Note: This requires maintaining a coord_lookup externally, or the node
        must be derived from _coord_to_virtual_node() with known coordinates.

        Args:
            node_id: Virtual node ID

        Returns:
            Series with 'x' (lon) and 'y' (lat), or None if not found
        """
        # This is a limitation of the virtual node approach - we can't
        # reverse the hash without maintaining a lookup table
        logger.warning(
            "get_node_coordinates() called but requires external "
            "coord_lookup. Consider using coordinate-based methods instead."
        )
        return None

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

    # Compatibility methods for edge-based operations
    def get_all_edges(self) -> Any:
        """Get all edges in the road network.

        Compatibility method for legacy code expecting edge-based operations.
        Returns an empty DataFrame since OSRM delegates all routing to the
        server and doesn't maintain local edge data.

        Returns:
            Empty pandas DataFrame.
        """
        import pandas as pd

        return pd.DataFrame()

    def set_edges(self, edges: Any) -> None:
        """Set edges in the road network.

        Compatibility method for legacy code expecting edge-based operations.
        This is a no-op for OSRM since all routing is delegated to the server
        and no local edge data is maintained.

        Args:
            edges: Edge data (ignored).

        Returns:
            None
        """
        pass


# Convenience singleton getter
def get_osrm_connection(osrm_url: Optional[str] = None) -> OSRMConnection:
    """
    Get the singleton OSRMConnection instance.

    Args:
        osrm_url: Base URL of OSRM server (only used on first call)

    Returns:
        OSRMConnection singleton instance
    """
    return OSRMConnection(osrm_url)
