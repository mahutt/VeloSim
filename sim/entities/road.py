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

from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .position import Position


class Road:
    """
    Represents a road segment for route traversal.

    Provides id, name, pointcollection, length, and maxspeed attributes
    needed for route traversal and road subscription management.

    Road segments are identified by segment_id: a tuple of (node_start, node_end)
    OSM node IDs, enabling consistent identification across different routes
    that share the same road infrastructure.
    """

    def __init__(
        self,
        road_id: int,
        name: Optional[str],
        pointcollection: List["Position"],
        length: float,
        maxspeed: float,
        segment_id: Optional[Tuple[int, int]] = None,
        node_start: Optional[int] = None,
        node_end: Optional[int] = None,
    ):
        """
        Initialize a road segment.

        Args:
            road_id: Unique identifier for this road segment
            name: Street or road name (None if unnamed)
            pointcollection: List of Position objects along the road
            length: Road length in meters
            maxspeed: Maximum speed in m/s
            segment_id: Optional tuple of (node_start, node_end) OSM node IDs
            node_start: Optional starting OSM node ID
            node_end: Optional ending OSM node ID
        """
        self.id = road_id
        self.name = name
        self.pointcollection = pointcollection
        self.length = length
        self.maxspeed = maxspeed

        # OSM node-based identification
        self.node_start = node_start
        self.node_end = node_end
        # Use provided segment_id or construct from node_start/node_end
        self.segment_id: Optional[Tuple[int, int]] = None
        if segment_id is not None:
            self.segment_id = segment_id
        elif node_start is not None and node_end is not None:
            self.segment_id = (node_start, node_end)

    def __hash__(self) -> int:
        """Hash based on segment_id, or road_id if segment_id is None.

        Returns:
            Hash value for use in sets and dicts
        """
        if self.segment_id is not None:
            return hash(self.segment_id)
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Check equality based on segment_id, or road_id if segment_id is None.

        Args:
            other: Object to compare against

        Returns:
            True if roads are equal, False otherwise
        """
        if not isinstance(other, Road):
            return NotImplemented
        if self.segment_id is not None and other.segment_id is not None:
            return self.segment_id == other.segment_id
        return self.id == other.id

    def get_segment_id(self) -> Optional[Tuple[int, int]]:
        """Get the OSM node-based segment identifier.

        Returns:
            Tuple of (node_start, node_end) if available, None otherwise
        """
        return self.segment_id
