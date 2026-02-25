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
from typing import Optional, Tuple

import requests

from sim.osm.osrm_result import OSRMResult

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
        # Priority: explicit parameter > env vars (OSRM_URL, OSRM_LOCAL_URL,
        # OSRM_PUBLIC_URL) > default localhost:5001
        self.osrm_base_url = (
            osrm_url
            or os.getenv("OSRM_URL")
            or os.getenv("OSRM_LOCAL_URL")
            or os.getenv("OSRM_PUBLIC_URL")
            or "http://localhost:5001"  # Default for local development
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
    ) -> Optional[OSRMResult]:
        """
        Get shortest path between two coordinates using OSRM.

        Args:
            start_lon: Starting longitude
            start_lat: Starting latitude
            end_lon: Ending longitude
            end_lat: Ending latitude

        Returns:
            OSRMResult with route data, or None if no valid route found
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
                logger.warning(
                    "OSRM returned no routes: %s",
                    data.get("code", "Unknown error"),
                )
                return None

            return OSRMResult.from_osrm_response(data)

        except requests.RequestException as e:
            logger.error(f"OSRM request failed: {e}")
            return None
        except ValueError as e:
            logger.error(f"Failed to parse OSRM response: {e}")
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
        return result.distance if result else None

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
    # Utility methods
    # ============================================================================

    def get_route_details(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float,
    ) -> Optional[OSRMResult]:
        """
        Get detailed route information including turn-by-turn instructions.

        Args:
            start_lon: Starting longitude
            start_lat: Starting latitude
            end_lon: Ending longitude
            end_lat: Ending latitude

        Returns:
            OSRMResult with route info including steps, or None if not found
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

            return OSRMResult.from_osrm_response(data)

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
