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

import json
from pathlib import Path
from threading import Lock
from typing import Dict, List, Literal, Set, Tuple, TypedDict, cast

from grafana_logging.logger import get_logger

logger = get_logger(__name__)

ControlKind = Literal["stop", "traffic_signals"]


class ControlCacheEntry(TypedDict):
    """Serialized disk-cache payload for extracted OSM control points."""

    pbf_path: str
    pbf_mtime_ns: int
    pbf_size: int
    stop: List[List[float]]
    traffic_signals: List[List[float]]


class OSMControlIndexStore:
    """Shared cache for control-point extraction from OSM PBF files.

    Loads stop signs and traffic lights in one osmium scan, then serves either
    set by control type. Cache key is the resolved PBF path.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._cache: Dict[str, Dict[ControlKind, List[List[float]]]] = {}

    def _cache_file_for_pbf(self, pbf_path: Path) -> Path:
        return pbf_path.with_suffix(".control_points_cache.json")

    def _current_pbf_fingerprint(self, pbf_path: Path) -> Tuple[int, int]:
        stat = pbf_path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _load_from_disk_cache(
        self, pbf_path: Path
    ) -> Dict[ControlKind, List[List[float]]] | None:
        cache_file = self._cache_file_for_pbf(pbf_path)
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to parse control-point cache: %s", cache_file)
            return None

        if not isinstance(data, dict):
            return None

        pbf_mtime_ns, pbf_size = self._current_pbf_fingerprint(pbf_path)
        if (
            data.get("pbf_path") != str(pbf_path.resolve())
            or data.get("pbf_mtime_ns") != pbf_mtime_ns
            or data.get("pbf_size") != pbf_size
        ):
            return None

        stop = data.get("stop")
        traffic_signals = data.get("traffic_signals")
        if not isinstance(stop, list) or not isinstance(traffic_signals, list):
            return None

        logger.info("Loaded control-point cache from %s", cache_file)
        return {
            "stop": stop,
            "traffic_signals": traffic_signals,
        }

    def _write_disk_cache(
        self, pbf_path: Path, values: Dict[ControlKind, List[List[float]]]
    ) -> None:
        cache_file = self._cache_file_for_pbf(pbf_path)
        pbf_mtime_ns, pbf_size = self._current_pbf_fingerprint(pbf_path)
        payload: ControlCacheEntry = {
            "pbf_path": str(pbf_path.resolve()),
            "pbf_mtime_ns": pbf_mtime_ns,
            "pbf_size": pbf_size,
            "stop": values["stop"],
            "traffic_signals": values["traffic_signals"],
        }
        try:
            cache_file.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to write control-point cache: %s", exc)

    def get_control_coordinates(
        self, pbf_path: Path, control_kind: ControlKind
    ) -> List[List[float]]:
        """Return cached control-point coordinates for a PBF and control kind.

        Args:
            pbf_path: Path to the source OSM PBF file.
            control_kind: Requested control-point type.

        Returns:
            List of ``[lon, lat]`` coordinates for the requested control kind.
        """
        resolved_path = pbf_path.resolve()
        resolved = str(resolved_path)

        cached = self._cache.get(resolved)
        if cached is not None:
            return cached[control_kind]

        with self._lock:
            cached = self._cache.get(resolved)
            if cached is None:
                cached = self._load_from_disk_cache(resolved_path)
                if cached is None:
                    cached = self._load_from_pbf(resolved_path)
                    self._write_disk_cache(resolved_path, cached)
                self._cache[resolved] = cached

        return cached[control_kind]

    def _load_from_pbf(self, pbf_path: Path) -> Dict[ControlKind, List[List[float]]]:
        import osmium

        class _ControlHandler(osmium.SimpleHandler):
            """Collect stop and traffic-signal node coordinates from an OSM file."""

            def __init__(self) -> None:
                super().__init__()
                self.points: Dict[ControlKind, Set[Tuple[float, float]]] = {
                    "stop": set(),
                    "traffic_signals": set(),
                }

            def node(self, n: osmium.osm.Node) -> None:
                """Handle each node and store coordinates for supported controls.

                Args:
                    n: Current OSM node emitted by osmium during PBF scan.

                Returns:
                    None. Coordinates are accumulated in ``self.points``.
                """
                highway = n.tags.get("highway")
                if highway in ("stop", "traffic_signals") and n.location.valid():
                    control_kind = cast(ControlKind, highway)
                    self.points[control_kind].add((n.location.lon, n.location.lat))

        handler = _ControlHandler()
        handler.apply_file(str(pbf_path))

        if not any(handler.points.values()):
            logger.warning("No stop/traffic-signal nodes found in %s", pbf_path)
            return {"stop": [], "traffic_signals": []}

        return {
            "stop": [[lon, lat] for lon, lat in handler.points["stop"]],
            "traffic_signals": [
                [lon, lat] for lon, lat in handler.points["traffic_signals"]
            ],
        }


_global_osm_control_store = OSMControlIndexStore()


def get_osm_control_coordinates(
    pbf_path: Path, control_kind: ControlKind
) -> List[List[float]]:
    """Get cached control-point coordinates from the global store.

    Args:
        pbf_path: Path to the source OSM PBF file.
        control_kind: Requested control-point type.

    Returns:
        List of ``[lon, lat]`` coordinates for the requested control kind.
    """
    return _global_osm_control_store.get_control_coordinates(pbf_path, control_kind)
