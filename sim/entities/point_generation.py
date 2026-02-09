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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, List

from sim.entities.position import Position


@dataclass(frozen=True)
class RoadPointContext:
    """Immutable snapshot of road state needed for point generation.

    Decouples strategy implementations from the Road entity so strategies
    can live in sim/traffic without importing Road.
    """

    nodes: List[Position]
    maxspeed: float
    length: float
    pointcollection: List[Position]
    get_multiplier_at_index: Callable[[int], float]


class PointGenerationStrategy(ABC):
    """Abstract base class for traffic point generation strategies.

    Each strategy encapsulates a different algorithm for generating
    traffic-adjusted point collections based on road context.
    """

    @abstractmethod
    def generate(self, context: RoadPointContext) -> List[Position]:
        """Generate traffic-adjusted points for a road.

        Args:
            context: Immutable snapshot of the road's current state.

        Returns:
            List of Position objects with traffic-adjusted spacing.
        """
