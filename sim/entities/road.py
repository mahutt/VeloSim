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
from sim.entities.traffic_data import CongestionLevel, RoadTrafficState

if TYPE_CHECKING:
    from .position import Position


class Road:
    """
    Represents a road segment for route traversal.

    Provides id, name, pointcollection, length, and maxspeed attributes
    needed for route traversal and road subscription management.

    Traffic state can be applied via RoadTrafficState to modify effective
    speed and duration. The original pointcollection is preserved; when
    traffic is applied, active_pointcollection returns traffic-adjusted
    points if available.

    Road segments are identified by segment_key: a tuple of start/end coordinates,
    enabling consistent identification across different routes that share the
    same road infrastructure.
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

        # Traffic state
        self._base_duration = length / maxspeed if maxspeed > 0 else 0.0
        self._traffic_state: Optional[RoadTrafficState] = None

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

        Computed as base_duration / traffic_state.multiplier.
        Lower multiplier = higher duration = slower travel.
        Returns base_duration if no traffic state.

        Returns:
            Effective duration in seconds
        """
        if self._traffic_state is None:
            return self._base_duration
        effective_multiplier = max(self._traffic_state.multiplier, 0.01)
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

        Returns:
            Current speed in m/s (maxspeed * traffic_state.multiplier)
            Returns maxspeed if no traffic state.
        """
        if self._traffic_state is None:
            return self.maxspeed
        return self.maxspeed * self._traffic_state.multiplier

    @property
    def traffic_multiplier(self) -> float:
        """Get current traffic speed multiplier for this road.

        Returns:
            Speed multiplier (0.0 to 1.0), 1.0 means free flow (or no traffic)
        """
        if self._traffic_state is None:
            return 1.0
        return self._traffic_state.multiplier

    @property
    def traffic_state(self) -> Optional[RoadTrafficState]:
        """Get the traffic state object, or None if no traffic.

        Returns:
            RoadTrafficState if traffic exists, None otherwise
        """
        return self._traffic_state

    @property
    def congestion_level(self) -> CongestionLevel:
        """Get current congestion level for this road.

        Returns:
            CongestionLevel enum value (FREE_FLOW if no traffic)
        """
        if self._traffic_state is None:
            return CongestionLevel.FREE_FLOW
        return self._traffic_state.congestion_level

    @property
    def active_pointcollection(self) -> List["Position"]:
        """Get the active point collection (traffic or default).

        Returns:
            Traffic-adjusted points if available, otherwise default pointcollection
        """
        if (
            self._traffic_state is not None
            and self._traffic_state.traffic_pointcollection
        ):
            return self._traffic_state.traffic_pointcollection
        return self.pointcollection

    def set_traffic_state(self, state: RoadTrafficState) -> None:
        """Set traffic state.

        Args:
            state: RoadTrafficState to apply

        Returns:
            None
        """
        self._traffic_state = state

    def clear_traffic(self) -> None:
        """Clear traffic state, reverting to default pointcollection.

        Returns:
            None
        """
        self._traffic_state = None
