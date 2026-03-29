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

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Optional, Tuple

from grafana_logging.logger import get_logger
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from sim.osm.osm_control_index_store import get_osm_control_coordinates

logger = get_logger(__name__)


class TrafficLightIndex:
    """Spatial index of traffic-light nodes loaded from an OSM PBF file."""

    def __init__(
        self,
        pbf_path: Optional[str] = None,
        traffic_light_coordinates: Optional[Iterable[List[float]]] = None,
    ) -> None:
        self._pbf_path = pbf_path
        self._lock = Lock()
        self._loaded = False
        self._points: List[Point] = []
        self._point_coords: List[Tuple[float, float]] = []
        self._tree: Optional[STRtree] = None

        # For tests: bypass PBF loading with pre-seeded coordinates.
        if traffic_light_coordinates is not None:
            self._build_from_coordinates(traffic_light_coordinates)
            self._loaded = True

    def find_near_route(
        self,
        route_coordinates: List[List[float]],
        tolerance_degrees: float = 0.00012,
    ) -> List[List[float]]:
        """Return unique traffic-light coordinates within tolerance of a route.

        Args:
            route_coordinates: Route polyline coordinates as [lon, lat] points.
            tolerance_degrees: Search radius around the route in degrees.

        Returns:
            List[List[float]]: Unique traffic-light coordinates near the route.
        """
        if len(route_coordinates) < 2:
            return []

        self._ensure_loaded()
        if self._tree is None:
            return []

        route_line = LineString(route_coordinates)
        search_area = route_line.buffer(tolerance_degrees)
        candidate_indices = self._tree.query(search_area)

        unique: set[Tuple[float, float]] = set()
        result: List[List[float]] = []

        for idx in candidate_indices:
            candidate_point = self._points[int(idx)]
            if route_line.distance(candidate_point) > tolerance_degrees:
                continue

            coord = self._point_coords[int(idx)]
            if coord in unique:
                continue
            unique.add(coord)
            result.append([coord[0], coord[1]])

        return result

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._loaded:
                return

            pbf_path = self._resolve_pbf_path()
            if pbf_path is None:
                logger.warning(
                    "Traffic-light index not initialized: no PBF found; "
                    "traffic-light overlays disabled."
                )
                self._loaded = True
                return

            try:
                coords = get_osm_control_coordinates(pbf_path, "traffic_signals")
                if not coords:
                    logger.warning("No traffic-light nodes found in %s", pbf_path)
                    self._loaded = True
                    return
                self._build_from_coordinates(coords)
                logger.info(
                    "Loaded traffic-light index with %s nodes from %s",
                    len(self._points),
                    pbf_path,
                )
            except Exception as e:
                logger.error("Failed to load traffic-light index from PBF: %s", e)
            finally:
                self._loaded = True

    def _build_from_coordinates(
        self, traffic_light_coordinates: Iterable[object]
    ) -> None:
        unique_coords: set[Tuple[float, float]] = set()
        for coord in traffic_light_coordinates:
            if not isinstance(coord, list) or len(coord) != 2:
                continue
            lon, lat = coord
            if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                continue
            unique_coords.add((float(lon), float(lat)))

        self._point_coords = list(unique_coords)
        self._points = [Point(lon, lat) for lon, lat in self._point_coords]
        self._tree = STRtree(self._points) if self._points else None

    def _resolve_pbf_path(self) -> Optional[Path]:
        if self._pbf_path:
            path = Path(self._pbf_path)
            return path if path.exists() else None

        env_path = os.getenv("TRAFFIC_LIGHT_PBF_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        repo_root = Path(__file__).resolve().parents[2]
        search_paths = [
            repo_root / "graphhopper-data" / "montreal-latest.osm.pbf",
            repo_root / "graphhopper-data" / "montreal.osm.pbf",
        ]
        for pbf_path in search_paths:
            if pbf_path.exists():
                return pbf_path
        return None


_global_traffic_light_index: Optional[TrafficLightIndex] = None
_global_lock = Lock()


def get_traffic_light_index() -> TrafficLightIndex:
    """Return process-wide traffic-light index singleton.

    Returns:
        TrafficLightIndex: Singleton traffic-light index instance.
    """
    global _global_traffic_light_index
    if _global_traffic_light_index is not None:
        return _global_traffic_light_index

    with _global_lock:
        if _global_traffic_light_index is None:
            _global_traffic_light_index = TrafficLightIndex()
    return _global_traffic_light_index
