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
from typing import Any, Dict, Optional, Tuple

import requests

from sim.osm.graphhopper_result import GraphHopperResult

logger = logging.getLogger(__name__)


class GraphHopperConnection:
    """HTTP client for GraphHopper routing API."""

    def __init__(
        self,
        graphhopper_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self._session = requests.Session()
        self._base_url = self._determine_graphhopper_url(graphhopper_url)
        self._timeout = timeout or int(os.getenv("GRAPHHOPPER_TIMEOUT", "20"))
        self._verify_graphhopper_connection()
        logger.info("GraphHopper connection established: %s", self._base_url)

    def _determine_graphhopper_url(self, provided_url: Optional[str]) -> str:
        if provided_url:
            return provided_url.rstrip("/")

        env_url = os.getenv("GRAPHHOPPER_URL")
        if env_url:
            return env_url.rstrip("/")

        return "http://localhost:8989"

    def _verify_graphhopper_connection(self) -> None:
        health_urls = [
            f"{self._base_url}/health",
            f"{self._base_url}/status",
        ]

        for url in health_urls:
            try:
                response = self._session.get(url, timeout=5)
                if response.ok:
                    return
            except requests.RequestException:
                continue

        raise ConnectionError(
            f"Cannot connect to GraphHopper server at {self._base_url}"
        )

    def shortest_path_coords(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float,
        profile: str = "car",
        custom_model: Optional[Dict[str, Any]] = None,
    ) -> Optional[GraphHopperResult]:
        """Compute shortest path between two coordinates.

        Args:
            start_lon: Start longitude
            start_lat: Start latitude
            end_lon: End longitude
            end_lat: End latitude
            profile: Routing profile (car, bike, foot, etc.)
            custom_model: Optional GraphHopper custom model for traffic

        Returns:
            GraphHopperResult with route, or None if request fails
        """
        url = f"{self._base_url}/route"
        payload: Dict[str, Any] = {
            "profile": profile,
            "points": [
                [start_lon, start_lat],
                [end_lon, end_lat],
            ],
            "points_encoded": False,
            "instructions": True,
            "calc_points": True,
        }

        if custom_model:
            payload["custom_model"] = custom_model
            payload["ch.disable"] = True

        try:
            response = self._session.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            return GraphHopperResult.from_graphhopper_response(data)
        except requests.HTTPError as e:
            response_text = ""
            if e.response is not None:
                response_text = e.response.text[:1000]
            logger.error(
                "GraphHopper HTTP error",
                extra={
                    "error": str(e),
                    "status_code": e.response.status_code if e.response else None,
                    "response_preview": response_text,
                    "start": (start_lon, start_lat),
                    "end": (end_lon, end_lat),
                    "profile": profile,
                    "has_custom_model": custom_model is not None,
                },
            )
            return None
        except requests.RequestException as e:
            logger.error(
                "GraphHopper request failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "start": (start_lon, start_lat),
                    "end": (end_lon, end_lat),
                    "profile": profile,
                },
            )
            return None
        except ValueError as e:
            logger.error("Failed to parse GraphHopper response: %s", e)
            return None

    def get_distance_coords(
        self,
        start_lon: float,
        start_lat: float,
        end_lon: float,
        end_lat: float,
        profile: str = "car",
        custom_model: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """Get distance in meters between two coordinates.

        Args:
            start_lon: Start longitude
            start_lat: Start latitude
            end_lon: End longitude
            end_lat: End latitude
            profile: Routing profile (car, bike, foot, etc.)
            custom_model: Optional GraphHopper custom model for traffic

        Returns:
            Distance in meters, or None if request fails
        """
        result = self.shortest_path_coords(
            start_lon,
            start_lat,
            end_lon,
            end_lat,
            profile=profile,
            custom_model=custom_model,
        )
        return result.distance if result else None

    def snap_to_road(
        self, lon: float, lat: float, profile: str = "car"
    ) -> Tuple[float, float]:
        """Snap a coordinate to the nearest road.

        Args:
            lon: Longitude
            lat: Latitude
            profile: Routing profile (car, bike, foot, etc.)

        Returns:
            Tuple of (longitude, latitude) snapped to nearest road
        """
        url = f"{self._base_url}/nearest"
        params = {
            "point": f"{lat},{lon}",
            "profile": profile,
        }

        try:
            response = self._session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            point = data.get("coordinates") or data.get("point", {}).get("coordinates")
            if isinstance(point, list) and len(point) >= 2:
                return float(point[0]), float(point[1])
            return lon, lat
        except requests.RequestException as e:
            logger.error("GraphHopper nearest request failed: %s", e)
            return lon, lat

    def close(self) -> None:
        """Close the HTTP session.

        Returns:
            None
        """
        self._session.close()
