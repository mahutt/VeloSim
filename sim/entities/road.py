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
from sim.entities.point_generation import PointGenerationStrategy, RoadPointContext

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
        geometry: Optional[List[Position]] = None,
    ):
        """
        Initialize a road segment.

        Args:
            road_id: Unique identifier for this road segment
            name: Street or road name (None if unnamed)
            pointcollection: List of Position objects along the road
            length: Road length in meters
            maxspeed: Maximum speed in m/s
            geometry: Raw provider geometry positions (sparse shape).
                Used by PositionRegistry for intersection matching.
                Separate from the interpolated pointcollection.
        """
        if not pointcollection:
            raise ValueError(f"Road {road_id} requires non-empty pointcollection")

        self.id = road_id
        self.name = name
        self.pointcollection = pointcollection
        self.length = length
        self.maxspeed = maxspeed
        self.geometry = geometry

        # Base duration at free flow speed
        self._base_duration = length / maxspeed if maxspeed > 0 else 0.0

        # Node tracking for granular traffic (using Position objects)
        self._traffic_ranges: Dict[SegmentKey, TrafficRange] = {}
        self._traffic_pointcollection: Optional[List[Position]] = None

        # Pluggable point generation strategy (None = use internal fallback)
        self._point_strategy: Optional[PointGenerationStrategy] = None

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

    def get_distance_at_index(self, index: int) -> float:
        """Get cumulative distance from road start to a point index.

        Since the total road length is fixed and traffic only changes the
        number of points (more points = slower speed = less distance per point),
        distance is simply proportional to progress through the point collection:
        ``index / (n - 1) * length``.

        Args:
            index: Point index in active_pointcollection.

        Returns:
            Cumulative distance in meters from road start.
        """
        n = len(self.active_pointcollection)
        if n <= 1:
            return 0.0
        clamped = max(0, min(index, n - 1))
        return (clamped / (n - 1)) * self.length

    @property
    def active_pointcollection(self) -> List[Position]:
        """Get the active point collection (traffic or default).

        If a point strategy is set, delegates to it. Otherwise falls
        back to the internal _generate_traffic_points() method.

        Returns:
            Traffic-adjusted points if traffic ranges exist,
            otherwise default pointcollection
        """
        if self._traffic_ranges:
            if self._traffic_pointcollection is None:
                if self._point_strategy is not None:
                    context = RoadPointContext(
                        nodes=self._nodes,
                        maxspeed=self.maxspeed,
                        length=self.length,
                        pointcollection=self.pointcollection,
                        get_multiplier_at_index=self.get_multiplier_at_index,
                    )
                    self._traffic_pointcollection = self._point_strategy.generate(
                        context
                    )
                else:
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

    def set_point_strategy(self, strategy: Optional[PointGenerationStrategy]) -> None:
        """Set or clear the point generation strategy.

        When set, active_pointcollection delegates to the strategy.
        When None, falls back to the internal _generate_traffic_points().

        Args:
            strategy: Strategy instance, or None to clear.

        Returns:
            None.
        """
        self._point_strategy = strategy
        self._traffic_pointcollection = None  # Invalidate cache

    def apply_traffic_for_overlap(
        self,
        overlap_positions: List[Position],
        multiplier: float,
        segment_key: SegmentKey,
    ) -> bool:
        """Apply traffic using overlapping geometry positions from PositionRegistry.

        TC does NOT know the index scheme. Road projects overlap positions onto
        its geometry, maps to pointcollection indices via fraction mapping, then
        creates a TrafficRange internally.

        Args:
            overlap_positions: Shared positions between road geometry and event
                geometry, as determined by the PositionRegistry.
            multiplier: Speed multiplier (0.01-1.0), 1.0 = free flow.
            segment_key: Original segment_key for the traffic event.

        Returns:
            True if a traffic range was created, False if overlap could not
            be projected.
        """
        if not overlap_positions or not self.geometry or len(self.geometry) < 2:
            return False

        # Build a geometry index for fraction computation
        geom_index: Dict[Position, int] = {}
        for i, pos in enumerate(self.geometry):
            if pos not in geom_index:
                geom_index[pos] = i

        # Find geometry indices of overlap positions
        overlap_indices = []
        for pos in overlap_positions:
            idx = geom_index.get(pos)
            if idx is not None:
                overlap_indices.append(idx)

        if not overlap_indices:
            return False

        # Fraction range within geometry
        min_geom_idx = min(overlap_indices)
        max_geom_idx = max(overlap_indices)
        geom_count = len(self.geometry) - 1
        if geom_count <= 0:
            return False

        start_frac = min_geom_idx / geom_count
        end_frac = max_geom_idx / geom_count

        # Map fractions to pointcollection indices
        pc_count = len(self._nodes) - 1
        if pc_count <= 0:
            return False

        start_idx = max(0, int(start_frac * pc_count))
        end_idx = min(pc_count, int(end_frac * pc_count + 0.5))

        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx

        # Create traffic range
        self._traffic_ranges[segment_key] = TrafficRange(
            start_index=start_idx,
            end_index=end_idx,
            multiplier=multiplier,
            segment_key=segment_key,
            geom_start_index=min_geom_idx,
            geom_end_index=max_geom_idx,
        )
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

    def get_traffic_geometry_ranges(self) -> list[tuple[int, int, CongestionLevel]]:
        """Get traffic ranges sorted by geometry index for O(N) route rebuilding.

        Returns sorted (geom_start, geom_end, congestion_level)
        for each non-FREE_FLOW range.

        Returns:
            Sorted list of tuples with geometry start index, end index,
            and congestion level.
        """
        # Sort locally by the geometry index
        sorted_ranges = sorted(
            self._traffic_ranges.values(), key=lambda x: x.geom_start_index
        )

        ranges: list[tuple[int, int, CongestionLevel]] = []
        for tr in sorted_ranges:
            level = multiplier_to_congestion_level(tr.multiplier)
            if level != CongestionLevel.FREE_FLOW:
                ranges.append((tr.geom_start_index, tr.geom_end_index, level))
        return ranges

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
