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

from typing import List

from sim.entities.point_generation import PointGenerationStrategy, RoadPointContext
from sim.entities.position import Position


class LocalTrafficPointStrategy(PointGenerationStrategy):
    """Generates traffic-adjusted points using per-segment multipliers.

    Direct extraction of the algorithm from Road._generate_traffic_points().
    For each segment (node pair), determines the effective multiplier
    and generates appropriately spaced points.
    """

    def generate(self, context: RoadPointContext) -> List[Position]:
        """Generate traffic-adjusted points with per-segment multipliers.

        For each segment (node pair), determines the effective multiplier
        and generates appropriately spaced points.

        Args:
            context: Immutable snapshot of road state.

        Returns:
            List of Position objects with traffic-adjusted spacing.
        """
        nodes = context.nodes
        if len(nodes) < 2:
            return list(context.pointcollection)

        total_nodes = len(nodes)

        # Calculate total coordinate length for proportioning
        total_coord_length = sum(
            (
                (nodes[j + 1].get_position()[0] - nodes[j].get_position()[0]) ** 2
                + (nodes[j + 1].get_position()[1] - nodes[j].get_position()[1]) ** 2
            )
            ** 0.5
            for j in range(total_nodes - 1)
        )

        if total_coord_length <= 0:
            return list(context.pointcollection)

        points: List[Position] = []

        for i in range(total_nodes - 1):
            seg_start = nodes[i].get_position()
            seg_end = nodes[i + 1].get_position()

            seg_length = (
                (seg_end[0] - seg_start[0]) ** 2 + (seg_end[1] - seg_start[1]) ** 2
            ) ** 0.5

            multiplier = context.get_multiplier_at_index(i)
            effective_speed = context.maxspeed * max(multiplier, 0.01)

            # Approximate segment meters based on proportion
            segment_meters = (seg_length / total_coord_length) * context.length
            num_points = max(1, int(segment_meters / effective_speed))

            for j in range(num_points):
                frac = j / num_points
                x = seg_start[0] + frac * (seg_end[0] - seg_start[0])
                y = seg_start[1] + frac * (seg_end[1] - seg_start[1])
                points.append(Position([x, y]))

        # Final point
        if nodes:
            final = nodes[-1].get_position()
            points.append(Position([final[0], final[1]]))

        return points if points else list(context.pointcollection)
