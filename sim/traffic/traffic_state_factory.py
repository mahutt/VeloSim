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

from typing import List, Optional

from sim.entities.position import Position
from sim.entities.traffic_data import (
    RoadTrafficState,
    multiplier_to_congestion_level,
)


class TrafficStateFactory:
    """Factory for creating RoadTrafficState objects.

    Encapsulates creation logic and validation, including boundary condition
    handling (multiplier clamped to 0.01-1.0 to prevent division by zero).
    """

    @staticmethod
    def create(
        multiplier: float,
        traffic_points: List[Position],
        source: Optional[str] = None,
        tick: Optional[int] = None,
    ) -> RoadTrafficState:
        """Create a RoadTrafficState with proper congestion level.

        Args:
            multiplier: Speed factor (0.0-1.0), 1.0 = free flow
            traffic_points: Pre-generated traffic point collection
            source: Optional source identifier for tracking
            tick: Optional simulation tick timestamp

        Returns:
            RoadTrafficState with validated multiplier and derived congestion level
        """
        # Boundary condition: clamp to prevent division by zero
        clamped = max(0.01, min(1.0, multiplier))

        return RoadTrafficState(
            multiplier=clamped,
            congestion_level=multiplier_to_congestion_level(clamped),
            last_updated=tick,
            source_event=source,
            traffic_pointcollection=traffic_points,
        )
