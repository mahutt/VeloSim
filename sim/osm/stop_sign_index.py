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
from typing import Iterable, List, Optional, Sequence, Tuple

from grafana_logging.logger import get_logger
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from sim.osm.osm_control_index_store import get_osm_control_coordinates

logger = get_logger(__name__)


class StopSignIndex:
    """Spatial index of stop-sign nodes loaded from an OSM PBF file."""

    def __init__(
        self,
        pbf_path: Optional[str] = None,
        stop_sign_coordinates: Optional[Iterable[List[float]]] = None,
    ) -> None:
        self._pbf_path = pbf_path
        self._lock = Lock()
        self._loaded = False
        self._points: List[Point] = []
        self._point_coords: List[Tuple[float, float]] = []
        self._tree: Optional[STRtree] = None

        # For tests: bypass PBF loading with pre-seeded coordinates.
        if stop_sign_coordinates is not None:
            self._build_from_coordinates(stop_sign_coordinates)
            self._loaded = True

    def find_near_route(
        self,
        route_coordinates: List[List[float]],
        tolerance_degrees: float = 0.00012,
    ) -> List[List[float]]:
        """Return route-aligned stop-sign coordinates with directional filtering.

        Args:
            route_coordinates: Route polyline coordinates as [lon, lat] points.
            tolerance_degrees: Search radius around each route segment in degrees.

        Returns:
            List[List[float]]: Stop-sign coordinates on the route (entry stops only).
        """
        if len(route_coordinates) < 2:
            return []

        self._ensure_loaded()
        if self._tree is None:
            return []

        unique: set[Tuple[float, float]] = set()
        result: List[List[float]] = []

        # Check stop signs against each route segment individually
        for i in range(len(route_coordinates) - 1):
            segment_start = route_coordinates[i]
            segment_end = route_coordinates[i + 1]

            # Create a small buffer around just this segment
            segment_line = LineString([segment_start, segment_end])
            search_area = segment_line.buffer(tolerance_degrees)
            candidate_indices = self._tree.query(search_area)

            # Calculate segment direction vector
            seg_dx = segment_end[0] - segment_start[0]
            seg_dy = segment_end[1] - segment_start[1]
            segment_length_sq = (seg_dx * seg_dx) + (seg_dy * seg_dy)

            if segment_length_sq == 0:
                continue  # Skip zero-length segments

            for idx in candidate_indices:
                candidate_point = self._points[int(idx)]

                # Verify the stop sign is actually close to this segment
                if segment_line.distance(candidate_point) > tolerance_degrees:
                    continue

                coord = self._point_coords[int(idx)]
                if coord in unique:
                    continue

                # DIRECTIONAL FILTER: Only include stops in the MIDDLE of segments
                # - Skip first 10% (exit stops from previous intersection)
                # - Skip last 30% (exit stops for current segment)
                # - Keep 10%-70% range (entry stops including turn points)

                # Calculate vector from segment start to stop sign
                sign_dx = coord[0] - segment_start[0]
                sign_dy = coord[1] - segment_start[1]

                # Dot product tells us how far along segment the stop projects
                dot_product = (sign_dx * seg_dx) + (sign_dy * seg_dy)
                projection_ratio = dot_product / segment_length_sq

                # Only include stops between 10% and 70% of segment
                # This filters both exit stops and stops just after turns
                eps = 1e-9
                if (0.10 - eps) <= projection_ratio <= (0.70 + eps):
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
                    "Stop-sign index not initialized: no PBF found; "
                    "stop-sign overlays disabled."
                )
                self._loaded = True
                return

            try:
                coords = get_osm_control_coordinates(pbf_path, "stop")
                if not coords:
                    logger.warning("No stop-sign nodes found in %s", pbf_path)
                    self._loaded = True
                    return
                self._build_from_coordinates(coords)
            except Exception as e:
                logger.error("Failed to load stop-sign index from PBF: %s", e)
            finally:
                self._loaded = True

    def _build_from_coordinates(
        self, stop_sign_coordinates: Iterable[Sequence[object]]
    ) -> None:
        unique_coords: set[Tuple[float, float]] = set()
        for coord in stop_sign_coordinates:
            if len(coord) != 2:
                continue
            lon, lat = coord[0], coord[1]
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

        env_path = os.getenv("STOP_SIGN_PBF_PATH")
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


_global_stop_sign_index: Optional[StopSignIndex] = None
_global_lock = Lock()


def get_stop_sign_index() -> StopSignIndex:
    """Return process-wide stop-sign index singleton.

    Returns:
        StopSignIndex: Singleton stop-sign index instance.
    """
    global _global_stop_sign_index
    if _global_stop_sign_index is not None:
        return _global_stop_sign_index

    with _global_lock:
        if _global_stop_sign_index is None:
            _global_stop_sign_index = StopSignIndex()
    return _global_stop_sign_index
