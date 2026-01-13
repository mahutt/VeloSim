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

from typing import List, Optional, TYPE_CHECKING

from sim.map.routing_provider import SegmentKey

if TYPE_CHECKING:
    from .position import Position


class Road:
    """
    Represents a road segment for route traversal.

    Provides id, name, pointcollection, length, and maxspeed attributes
    needed for route traversal and road subscription management.

    Road segments are identified by segment_key: a tuple of start/end coordinates,
    enabling consistent identification across different routes that share the
    same road infrastructure. This approach is provider-neutral and works with
    any routing engine.
    """

    def __init__(
        self,
        road_id: int,
        name: Optional[str],
        pointcollection: List["Position"],
        length: float,
        maxspeed: float,
    ):
        """
        Initialize a road segment.

        Args:
            road_id: Unique identifier for this road segment
            name: Street or road name (None if unnamed)
            pointcollection: List of Position objects along the road
            length: Road length in meters
            maxspeed: Maximum speed in m/s
        """
        self.id = road_id
        self.name = name
        self.pointcollection = pointcollection
        self.length = length
        self.maxspeed = maxspeed

    @property
    def segment_key(self) -> SegmentKey:
        """
        Geometry-based identifier for road deduplication.

        Returns:
            Tuple of ((start_lon, start_lat), (end_lon, end_lat))
        """
        start = self.pointcollection[0].get_position()
        end = self.pointcollection[-1].get_position()
        return ((start[0], start[1]), (end[0], end[1]))

    def __hash__(self) -> int:
        """Hash based on segment_key.

        Returns:
            Hash value for use in sets and dicts
        """
        return hash(self.segment_key)

    def __eq__(self, other: object) -> bool:
        """Check equality based on segment_key.

        Args:
            other: Object to compare against

        Returns:
            True if roads have the same segment_key, False otherwise
        """
        if not isinstance(other, Road):
            return NotImplemented
        return self.segment_key == other.segment_key
