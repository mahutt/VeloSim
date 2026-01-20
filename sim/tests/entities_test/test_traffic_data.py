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

import pytest

from sim.entities.position import Position
from sim.entities.traffic_data import (
    CongestionLevel,
    RoadTrafficState,
    multiplier_to_congestion_level,
)


class TestCongestionLevel:
    def test_congestion_level_values_exist(self) -> None:
        assert CongestionLevel.FREE_FLOW is not None
        assert CongestionLevel.MODERATE is not None
        assert CongestionLevel.SEVERE is not None

    def test_congestion_level_string_values(self) -> None:
        assert CongestionLevel.FREE_FLOW.value == "free_flow"
        assert CongestionLevel.MODERATE.value == "moderate"
        assert CongestionLevel.SEVERE.value == "severe"


class TestMultiplierToCongestionLevel:
    @pytest.mark.parametrize(
        "multiplier,expected",
        [
            (1.0, CongestionLevel.FREE_FLOW),
            (0.9, CongestionLevel.FREE_FLOW),
            (0.825, CongestionLevel.FREE_FLOW),
            (0.824, CongestionLevel.MODERATE),
            (0.6, CongestionLevel.MODERATE),
            (0.40, CongestionLevel.MODERATE),
            (0.39, CongestionLevel.SEVERE),
            (0.2, CongestionLevel.SEVERE),
            (0.1, CongestionLevel.SEVERE),
            (0.0, CongestionLevel.SEVERE),
        ],
    )
    def test_multiplier_to_congestion_level_thresholds(
        self, multiplier: float, expected: CongestionLevel
    ) -> None:
        assert multiplier_to_congestion_level(multiplier) == expected


class TestRoadTrafficState:
    @pytest.fixture
    def sample_positions(self) -> List[Position]:
        return [Position([0.0, 0.0]), Position([1.0, 1.0])]

    def test_default_values(self) -> None:
        state = RoadTrafficState()
        assert state.multiplier == 1.0
        assert state.congestion_level == CongestionLevel.FREE_FLOW
        assert state.last_updated is None
        assert state.source_event is None
        assert state.traffic_pointcollection == []

    def test_with_all_parameters(self, sample_positions: List[Position]) -> None:
        state = RoadTrafficState(
            multiplier=0.5,
            congestion_level=CongestionLevel.MODERATE,
            last_updated=100,
            source_event="test_event",
            traffic_pointcollection=sample_positions,
        )
        assert state.multiplier == 0.5
        assert state.congestion_level == CongestionLevel.MODERATE
        assert state.last_updated == 100
        assert state.source_event == "test_event"
        assert state.traffic_pointcollection == sample_positions

    def test_post_init_clamps_multiplier_above_1(self) -> None:
        state = RoadTrafficState(multiplier=1.5)
        assert state.multiplier == 1.0

    def test_post_init_clamps_negative_multiplier(self) -> None:
        state = RoadTrafficState(multiplier=-0.5)
        assert state.multiplier == 0.0

    def test_post_init_preserves_valid_multiplier(self) -> None:
        state = RoadTrafficState(multiplier=0.5)
        assert state.multiplier == 0.5

    def test_post_init_clamps_large_positive(self) -> None:
        state = RoadTrafficState(multiplier=100.0)
        assert state.multiplier == 1.0

    def test_post_init_clamps_large_negative(self) -> None:
        state = RoadTrafficState(multiplier=-100.0)
        assert state.multiplier == 0.0

    def test_traffic_pointcollection_default_is_empty(self) -> None:
        state = RoadTrafficState()
        assert state.traffic_pointcollection == []

    def test_traffic_pointcollection_with_positions(
        self, sample_positions: List[Position]
    ) -> None:
        state = RoadTrafficState(traffic_pointcollection=sample_positions)
        assert len(state.traffic_pointcollection) == 2
        assert state.traffic_pointcollection[0].get_position() == [0.0, 0.0]
        assert state.traffic_pointcollection[1].get_position() == [1.0, 1.0]

    def test_optional_fields_can_be_none(self) -> None:
        state = RoadTrafficState(last_updated=None, source_event=None)
        assert state.last_updated is None
        assert state.source_event is None
