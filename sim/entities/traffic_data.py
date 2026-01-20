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

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from sim.entities.position import Position


class CongestionLevel(Enum):
    """Traffic congestion levels."""

    FREE_FLOW = "free_flow"  # No congestion, normal speeds
    MODERATE = "moderate"  # Moderate traffic, noticeable slowdown
    SEVERE = "severe"  # Severe congestion, near standstill


def multiplier_to_congestion_level(multiplier: float) -> CongestionLevel:
    """Convert a traffic multiplier to the closest congestion level.

    Uses midpoint thresholds between defined congestion level multipliers
    to determine the appropriate level.

    Args:
        multiplier: Speed multiplier between 0.0 and 1.0

    Returns:
        Closest matching CongestionLevel enum value
    """
    if multiplier >= 0.825:  # > midpoint of FREE_FLOW (1.0) and MODERATE (0.65)
        return CongestionLevel.FREE_FLOW
    elif multiplier >= 0.40:  # > midpoint of MODERATE (0.65) and SEVERE (0.15)
        return CongestionLevel.MODERATE
    else:
        return CongestionLevel.SEVERE


@dataclass
class RoadTrafficState:
    """Traffic state for a road segment.

    Encapsulates traffic-related state for a road. Road objects own an
    optional instance of this class (None = no traffic).

    The traffic_pointcollection can hold points generated for traffic-adjusted
    speed, used via Road.active_pointcollection when traffic is applied.
    """

    multiplier: float = 1.0  # 1.0 = free flow, 0.0 = stopped
    congestion_level: CongestionLevel = CongestionLevel.FREE_FLOW
    last_updated: Optional[int] = None  # Tick timestamp when last changed
    source_event: Optional[str] = None  # Event name that caused the change
    traffic_pointcollection: List["Position"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate multiplier is in valid range."""
        self.multiplier = max(0.0, min(1.0, self.multiplier))
