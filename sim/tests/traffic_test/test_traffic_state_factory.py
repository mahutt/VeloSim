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
from sim.entities.traffic_data import CongestionLevel, RoadTrafficState
from sim.traffic.traffic_state_factory import TrafficStateFactory


class TestTrafficStateFactory:
    @pytest.fixture
    def sample_traffic_points(self) -> List[Position]:
        return [
            Position([0.0, 0.0]),
            Position([0.5, 0.5]),
            Position([1.0, 1.0]),
        ]

    def test_create_returns_road_traffic_state(
        self, sample_traffic_points: List[Position]
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.5,
            traffic_points=sample_traffic_points,
        )
        assert isinstance(state, RoadTrafficState)

    @pytest.mark.parametrize(
        "input_mult,expected_mult",
        [
            (0.0, 0.01),
            (-0.5, 0.01),
            (-100.0, 0.01),
            (1.5, 1.0),
            (100.0, 1.0),
            (0.01, 0.01),
            (1.0, 1.0),
            (0.5, 0.5),
        ],
    )
    def test_create_multiplier_clamping(
        self,
        input_mult: float,
        expected_mult: float,
        sample_traffic_points: List[Position],
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=input_mult,
            traffic_points=sample_traffic_points,
        )
        assert state.multiplier == expected_mult

    def test_create_with_source(self, sample_traffic_points: List[Position]) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.5,
            traffic_points=sample_traffic_points,
            source="api_event",
        )
        assert state.source_event == "api_event"

    def test_create_with_tick(self, sample_traffic_points: List[Position]) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.5,
            traffic_points=sample_traffic_points,
            tick=100,
        )
        assert state.last_updated == 100

    def test_create_stores_traffic_points(
        self, sample_traffic_points: List[Position]
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.5,
            traffic_points=sample_traffic_points,
        )
        assert state.traffic_pointcollection == sample_traffic_points

    def test_create_with_empty_points_list(self) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.5,
            traffic_points=[],
        )
        assert state.traffic_pointcollection == []

    def test_create_free_flow_congestion(
        self, sample_traffic_points: List[Position]
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=1.0,
            traffic_points=sample_traffic_points,
        )
        assert state.congestion_level == CongestionLevel.FREE_FLOW

    def test_create_moderate_congestion(
        self, sample_traffic_points: List[Position]
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.6,
            traffic_points=sample_traffic_points,
        )
        assert state.congestion_level == CongestionLevel.MODERATE

    def test_create_severe_congestion(
        self, sample_traffic_points: List[Position]
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.1,
            traffic_points=sample_traffic_points,
        )
        assert state.congestion_level == CongestionLevel.SEVERE

    def test_create_source_defaults_to_none(
        self, sample_traffic_points: List[Position]
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.5,
            traffic_points=sample_traffic_points,
        )
        assert state.source_event is None

    def test_create_tick_defaults_to_none(
        self, sample_traffic_points: List[Position]
    ) -> None:
        state = TrafficStateFactory.create(
            multiplier=0.5,
            traffic_points=sample_traffic_points,
        )
        assert state.last_updated is None
