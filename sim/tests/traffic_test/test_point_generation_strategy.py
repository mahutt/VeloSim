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

import dataclasses
from typing import Callable

import pytest

from sim.entities.point_generation import RoadPointContext
from sim.entities.position import Position
from sim.traffic.strategies.local_traffic_strategy import LocalTrafficPointStrategy


def _default_multiplier(idx: int) -> float:
    """Default multiplier function: free flow at all indices."""
    return 1.0


def _make_context(
    nodes: list[Position],
    maxspeed: float = 10.0,
    length: float = 400.0,
    pointcollection: list[Position] | None = None,
    multiplier_fn: Callable[[int], float] | None = None,
) -> RoadPointContext:
    """Helper to build a RoadPointContext."""
    if pointcollection is None:
        pointcollection = list(nodes)
    if multiplier_fn is None:
        multiplier_fn = _default_multiplier
    return RoadPointContext(
        nodes=nodes,
        maxspeed=maxspeed,
        length=length,
        pointcollection=pointcollection,
        get_multiplier_at_index=multiplier_fn,
    )


class TestRoadPointContext:
    def test_context_is_frozen(self) -> None:
        ctx = _make_context(
            nodes=[Position([0.0, 0.0]), Position([1.0, 0.0])],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.maxspeed = 99.0  # type: ignore[misc]


class TestLocalTrafficPointStrategy:
    def _make_nodes(self, count: int = 5) -> list[Position]:
        return [Position([float(i), 0.0]) for i in range(count)]

    def test_uniform_multiplier_matches_free_flow(self) -> None:
        """All 1.0 multipliers → same density as free flow."""
        strategy = LocalTrafficPointStrategy()
        nodes = self._make_nodes(5)
        ctx = _make_context(nodes=nodes, maxspeed=10.0, length=400.0)

        points = strategy.generate(ctx)

        # At 10 m/s and 400m total, each of 4 segments is 100m → 10 pts each
        # Plus 1 final point = 41 total
        assert len(points) == 41

    def test_low_multiplier_increases_density(self) -> None:
        """0.25 multiplier → ~4x more points than free flow."""
        strategy = LocalTrafficPointStrategy()
        nodes = self._make_nodes(5)

        free_flow_ctx = _make_context(nodes=nodes, maxspeed=10.0, length=400.0)
        free_flow_points = strategy.generate(free_flow_ctx)

        congested_ctx = _make_context(
            nodes=nodes,
            maxspeed=10.0,
            length=400.0,
            multiplier_fn=lambda idx: 0.25,
        )
        congested_points = strategy.generate(congested_ctx)

        # Congested should have roughly 4x more points
        ratio = len(congested_points) / len(free_flow_points)
        assert ratio > 3.0

    def test_per_segment_multiplier(self) -> None:
        """Different multipliers per segment produce varying density."""
        strategy = LocalTrafficPointStrategy()
        nodes = self._make_nodes(3)  # 2 segments

        def varying_mult(idx: int) -> float:
            return 1.0 if idx == 0 else 0.25

        ctx = _make_context(
            nodes=nodes,
            maxspeed=10.0,
            length=200.0,
            multiplier_fn=varying_mult,
        )
        points = strategy.generate(ctx)

        # Count points in each segment
        seg0 = [p for p in points if p.get_position()[0] < 1.0]
        seg1 = [p for p in points if 1.0 <= p.get_position()[0] < 2.0]

        # Segment 1 should have ~4x more points than segment 0
        assert len(seg1) > len(seg0) * 2

    def test_single_node_fallback(self) -> None:
        """< 2 nodes → returns pointcollection as-is."""
        strategy = LocalTrafficPointStrategy()
        nodes = [Position([5.0, 5.0])]
        pc = [Position([5.0, 5.0])]
        ctx = _make_context(nodes=nodes, pointcollection=pc)

        result = strategy.generate(ctx)
        assert len(result) == 1
        assert result[0].get_position() == [5.0, 5.0]

    def test_zero_length_fallback(self) -> None:
        """All nodes same position → returns pointcollection."""
        strategy = LocalTrafficPointStrategy()
        same_pos = Position([1.0, 1.0])
        nodes = [same_pos, same_pos]
        pc = [same_pos, same_pos]
        ctx = _make_context(nodes=nodes, pointcollection=pc, length=0.0)

        result = strategy.generate(ctx)
        assert len(result) == 2
