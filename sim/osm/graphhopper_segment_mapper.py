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

import threading
from typing import Dict, Optional, Tuple

from sim.map.routing_provider import SegmentKey


class GraphHopperSegmentMapper:
    """Thread-safe mapper from SegmentKeys to GraphHopper custom-model areas."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mappings: Dict[str, Dict[SegmentKey, str]] = {}

    def get_or_create_area(
        self,
        sim_id: str,
        segment_key: SegmentKey,
    ) -> Tuple[str, Dict]:
        """Get or create a unique area name for a route segment.

        Used for building GraphHopper custom model areas that apply traffic
        to specific segments. Returns cached area name if already created,
        otherwise generates new unique area name.

        Args:
            sim_id: Simulation ID
            segment_key: (start_coord, end_coord) tuple

        Returns:
            Tuple of (area_name, area_feature_dict) for GraphHopper custom model
        """
        cached = self._get_cached(sim_id, segment_key)
        if cached is not None:
            area_name = cached
            return area_name, self._area_feature_from_segment(segment_key)

        area_name = self._build_area_name(segment_key)
        self._set_cached(sim_id, segment_key, area_name)
        return area_name, self._area_feature_from_segment(segment_key)

    def _get_cached(self, sim_id: str, segment_key: SegmentKey) -> Optional[str]:
        with self._lock:
            sim_mappings = self._mappings.get(sim_id)
            if sim_mappings is None:
                return None
            return sim_mappings.get(segment_key)

    def _set_cached(self, sim_id: str, segment_key: SegmentKey, area_name: str) -> None:
        with self._lock:
            if sim_id not in self._mappings:
                self._mappings[sim_id] = {}
            self._mappings[sim_id][segment_key] = area_name

    @staticmethod
    def _build_area_name(segment_key: SegmentKey) -> str:
        start, end = segment_key
        return (
            (
                f"seg_{round(start[0], 5)}_{round(start[1], 5)}_"
                f"{round(end[0], 5)}_{round(end[1], 5)}"
            )
            .replace("-", "m")
            .replace(".", "p")
        )

    @staticmethod
    def _area_feature_from_segment(segment_key: SegmentKey) -> Dict:
        (start_lon, start_lat), (end_lon, end_lat) = segment_key

        delta_lon = end_lon - start_lon
        delta_lat = end_lat - start_lat

        length = (delta_lon**2 + delta_lat**2) ** 0.5
        if length == 0:
            offset_lon = 0.00005
            offset_lat = 0.00005
        else:
            scale = 0.00005 / length
            offset_lon = -delta_lat * scale
            offset_lat = delta_lon * scale

        polygon = [
            [start_lon + offset_lon, start_lat + offset_lat],
            [end_lon + offset_lon, end_lat + offset_lat],
            [end_lon - offset_lon, end_lat - offset_lat],
            [start_lon - offset_lon, start_lat - offset_lat],
            [start_lon + offset_lon, start_lat + offset_lat],
        ]

        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon],
            },
            "properties": {},
        }

    def clear_sim(self, sim_id: str) -> None:
        """Clear all cached area mappings for a simulation.

        Args:
            sim_id: Simulation ID

        Returns:
            None
        """
        with self._lock:
            self._mappings.pop(sim_id, None)


graphhopper_segment_mapper = GraphHopperSegmentMapper()
