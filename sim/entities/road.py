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

from typing import Dict, List, Optional, TYPE_CHECKING

from sim.map.routing_provider import SegmentKey
from sim.entities.traffic_data import (
    CongestionLevel,
    TrafficRange,
    multiplier_to_congestion_level,
)
from sim.entities.position import Position

if TYPE_CHECKING:
    pass  # Keep for potential future type-only imports


class Road:
    """
    Represents a road segment for route traversal.

    Provides id, name, pointcollection, length, and maxspeed attributes
    needed for route traversal and road subscription management.

    Traffic can be applied via traffic ranges to modify effective speed
    and duration. The original pointcollection is preserved; when traffic
    is applied, active_pointcollection returns traffic-adjusted points.

    Road segments are identified by segment_key: a tuple of start/end coordinates,
    enabling consistent identification across different routes that share the
    same road infrastructure.
    """

    def __init__(
        self,
        road_id: int,
        name: Optional[str],
        pointcollection: List[Position],
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
        if not pointcollection:
            raise ValueError(f"Road {road_id} requires non-empty pointcollection")

        self.id = road_id
        self.name = name
        self.pointcollection = pointcollection
        self.length = length
        self.maxspeed = maxspeed

        # Base duration at free flow speed
        self._base_duration = length / maxspeed if maxspeed > 0 else 0.0

        # Node tracking for granular traffic (using Position objects)
        self._traffic_ranges: Dict[SegmentKey, TrafficRange] = {}
        self._traffic_pointcollection: Optional[List[Position]] = None

        # Build node index
        self._build_node_index()

    def _build_node_index(self) -> None:
        """Build node list and index from pointcollection."""
        self._nodes: List[Position] = []
        self._node_index: Dict[Position, int] = {}
        for pos in self.pointcollection:
            # Position is now hashable, use it directly
            if pos not in self._node_index:
                self._nodes.append(pos)
                self._node_index[pos] = len(self._nodes) - 1

    @property
    def nodes(self) -> List[Position]:
        """Get ordered list of node positions.

        Returns:
            Copy of the internal nodes list as Position objects
        """
        return self._nodes.copy()

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

    @property
    def duration(self) -> float:
        """Get effective duration considering traffic.

        Uses minimum multiplier across all traffic ranges (most restrictive).
        Lower multiplier = higher duration = slower travel.
        Returns base_duration if no traffic ranges.

        Returns:
            Effective duration in seconds
        """
        multiplier = self.traffic_multiplier
        effective_multiplier = max(multiplier, 0.01)
        return self._base_duration / effective_multiplier

    @property
    def base_duration(self) -> float:
        """Get the original duration (free flow).

        This value is never modified by traffic events.

        Returns:
            Base duration in seconds at free flow speed
        """
        return self._base_duration

    @property
    def current_speed(self) -> float:
        """Get current effective speed based on traffic multiplier.

        Uses minimum multiplier across all traffic ranges (most restrictive).

        Returns:
            Current speed in m/s (maxspeed * traffic_multiplier)
        """
        return self.maxspeed * self.traffic_multiplier

    @property
    def traffic_multiplier(self) -> float:
        """Get current traffic speed multiplier for this road.

        Returns minimum multiplier across all traffic ranges (most restrictive).

        Returns:
            Speed multiplier (0.01 to 1.0), 1.0 means free flow (no traffic)
        """
        if not self._traffic_ranges:
            return 1.0
        return min(r.multiplier for r in self._traffic_ranges.values())

    @property
    def congestion_level(self) -> CongestionLevel:
        """Get current congestion level for this road.

        Derived from the minimum traffic multiplier (most restrictive).

        Returns:
            CongestionLevel enum value (FREE_FLOW if no traffic)
        """
        return multiplier_to_congestion_level(self.traffic_multiplier)

    @property
    def active_pointcollection(self) -> List[Position]:
        """Get the active point collection (traffic or default).

        Returns:
            Traffic-adjusted points if traffic ranges exist,
            otherwise default pointcollection
        """
        if self._traffic_ranges:
            if self._traffic_pointcollection is None:
                self._traffic_pointcollection = self._generate_traffic_points()
            return self._traffic_pointcollection

        return self.pointcollection

    def clear_traffic(self) -> None:
        """Clear all traffic ranges.

        Returns:
            None
        """
        self._traffic_ranges.clear()
        self._traffic_pointcollection = None

    def _project_onto_road_direction(self, coord: tuple[float, float]) -> float:
        """Project a coordinate onto the road's direction vector.

        Args:
            coord: (lon, lat) coordinate tuple

        Returns:
            Scalar projection along road direction (higher = further along road)
        """
        road_start = self._nodes[0].get_position()
        road_end = self._nodes[-1].get_position()

        # Road direction vector
        dx = road_end[0] - road_start[0]
        dy = road_end[1] - road_start[1]

        # Vector from road start to coordinate
        px = coord[0] - road_start[0]
        py = coord[1] - road_start[1]

        # Dot product gives projection along direction
        return px * dx + py * dy

    def add_traffic_range(self, segment_key: SegmentKey, multiplier: float) -> bool:
        """Add or update a traffic range for this road.

        If a range with the same segment_key already exists, it is replaced.
        This ensures each segment_key has at most one traffic range per road.

        Args:
            segment_key: ((start_lon, start_lat), (end_lon, end_lat))
            multiplier: Speed multiplier (0.01-1.0), 1.0 = free flow

        Returns:
            True if traffic range was added/updated, False if segment not in road
        """
        start_coords, end_coords = segment_key

        # Convert tuple coordinates to Position for lookup
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])

        start_idx = self._node_index.get(start_pos)
        end_idx = self._node_index.get(end_pos)

        # Both nodes must be absent for no match
        if start_idx is None and end_idx is None:
            return False

        # Reject traffic going opposite to road direction using coordinate projection
        start_proj = self._project_onto_road_direction(start_coords)
        end_proj = self._project_onto_road_direction(end_coords)
        if start_proj > end_proj:
            return False

        # Resolve bounds for partial overlaps
        start_idx = start_idx if start_idx is not None else 0
        end_idx = end_idx if end_idx is not None else len(self._nodes) - 1

        # Create and store traffic range (O(1) replace if exists)
        self._traffic_ranges[segment_key] = TrafficRange(
            start_index=start_idx,
            end_index=end_idx,
            multiplier=multiplier,
            segment_key=segment_key,
        )

        # Invalidate cached points
        self._traffic_pointcollection = None

        return True

    def get_multiplier_at_index(self, index: int) -> float:
        """Get effective multiplier at a node index.

        Checks all traffic ranges. If index falls within multiple ranges,
        returns the minimum multiplier (most restrictive).

        Args:
            index: Node index to check

        Returns:
            Multiplier (0.01-1.0), 1.0 if no traffic at index
        """
        min_mult = 1.0
        for r in self._traffic_ranges.values():
            if r.start_index <= index <= r.end_index:
                min_mult = min(min_mult, r.multiplier)
        return min_mult

    def remove_traffic(self, segment_key: SegmentKey) -> bool:
        """Remove traffic for a specific segment_key.

        Args:
            segment_key: The segment_key to remove

        Returns:
            True if found and removed, False otherwise
        """
        if segment_key in self._traffic_ranges:
            del self._traffic_ranges[segment_key]
            self._traffic_pointcollection = None  # Invalidate cache
            return True
        return False

    def _generate_traffic_points(self) -> List[Position]:
        """Generate traffic-adjusted points with per-segment multipliers.

        For each segment (node pair), determines the effective multiplier
        and generates appropriately spaced points.

        Returns:
            List of Position objects with traffic-adjusted spacing
        """
        if len(self._nodes) < 2:
            return list(self.pointcollection)

        points: List[Position] = []
        total_nodes = len(self._nodes)

        # Calculate total coordinate length for proportioning
        # Nodes are Position objects
        total_coord_length = sum(
            (
                (
                    self._nodes[j + 1].get_position()[0]
                    - self._nodes[j].get_position()[0]
                )
                ** 2
                + (
                    self._nodes[j + 1].get_position()[1]
                    - self._nodes[j].get_position()[1]
                )
                ** 2
            )
            ** 0.5
            for j in range(total_nodes - 1)
        )

        if total_coord_length <= 0:
            return list(self.pointcollection)

        for i in range(total_nodes - 1):
            seg_start = self._nodes[i].get_position()  # [lon, lat]
            seg_end = self._nodes[i + 1].get_position()  # [lon, lat]

            # Segment coordinate length
            seg_length = (
                (seg_end[0] - seg_start[0]) ** 2 + (seg_end[1] - seg_start[1]) ** 2
            ) ** 0.5

            multiplier = self.get_multiplier_at_index(i)
            effective_speed = self.maxspeed * max(multiplier, 0.01)

            # Approximate segment meters based on proportion
            segment_meters = (seg_length / total_coord_length) * self.length
            num_points = max(1, int(segment_meters / effective_speed))

            for j in range(num_points):
                frac = j / num_points
                x = seg_start[0] + frac * (seg_end[0] - seg_start[0])
                y = seg_start[1] + frac * (seg_end[1] - seg_start[1])
                points.append(Position([x, y]))

        # Final point
        if self._nodes:
            final = self._nodes[-1].get_position()  # [lon, lat]
            points.append(Position([final[0], final[1]]))

        return points if points else list(self.pointcollection)
