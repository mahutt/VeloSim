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

from typing import Dict, List, Optional

from sim.entities.point_generation import PointGenerationStrategy, RoadPointContext
from sim.entities.position import Position
from sim.entities.traffic_data import (
    RoadTrafficState,
    multiplier_to_congestion_level,
)
from sim.traffic.strategies.local_traffic_strategy import LocalTrafficPointStrategy


class TrafficStateFactory:
    """Factory for creating RoadTrafficState objects and dispatching strategies.

    Encapsulates creation logic and validation, including boundary condition
    handling (multiplier clamped to 0.01-1.0 to prevent division by zero).

    Also serves as the single dispatch point for point generation strategies,
    mapping event_type strings to PointGenerationStrategy instances.
    """

    _strategies: Dict[str, PointGenerationStrategy] = {
        "local_traffic": LocalTrafficPointStrategy(),
    }
    _default_strategy: PointGenerationStrategy = LocalTrafficPointStrategy()

    @classmethod
    def register_strategy(
        cls, event_type: str, strategy: PointGenerationStrategy
    ) -> None:
        """Register a point generation strategy for an event type.

        Args:
            event_type: The event type string to register for.
            strategy: The strategy instance to use.

        Returns:
            None.
        """
        cls._strategies[event_type] = strategy

    @classmethod
    def get_strategy(cls, event_type: Optional[str] = None) -> PointGenerationStrategy:
        """Look up the strategy for an event type.

        Args:
            event_type: The event type string. None returns default.

        Returns:
            The registered strategy, or default if not found.
        """
        if event_type is None:
            return cls._default_strategy
        return cls._strategies.get(event_type, cls._default_strategy)

    @classmethod
    def generate_points(
        cls,
        context: RoadPointContext,
        event_type: Optional[str] = None,
    ) -> List[Position]:
        """Generate traffic-adjusted points via the appropriate strategy.

        Args:
            context: Immutable snapshot of road state.
            event_type: Optional event type to select strategy.

        Returns:
            List of Position objects with traffic-adjusted spacing.
        """
        strategy = cls.get_strategy(event_type)
        return strategy.generate(context)

    @staticmethod
    def create(
        multiplier: float,
        traffic_points: Optional[List[Position]] = None,
        source: Optional[str] = None,
        tick: Optional[int] = None,
    ) -> RoadTrafficState:
        """Create a RoadTrafficState with proper congestion level.

        Args:
            multiplier: Speed factor (0.0-1.0), 1.0 = free flow
            traffic_points: Pre-generated traffic point collection.
                Defaults to empty list for backward compatibility.
            source: Optional source identifier for tracking
            tick: Optional simulation tick timestamp

        Returns:
            RoadTrafficState with validated multiplier and derived congestion level
        """
        if traffic_points is None:
            traffic_points = []

        # Boundary condition: clamp to prevent division by zero
        clamped = max(0.01, min(1.0, multiplier))

        return RoadTrafficState(
            multiplier=clamped,
            congestion_level=multiplier_to_congestion_level(clamped),
            last_updated=tick,
            source_event=source,
            traffic_pointcollection=traffic_points,
        )
