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

from typing import Callable, Optional
from unittest.mock import Mock

import pytest

from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_data import RoadTrafficState
from sim.map.routing_provider import SegmentKey
from sim.traffic.traffic_controller import TrafficController


class TestTrafficControllerInitialization:
    def test_init_stores_route_controller(self) -> None:
        mock_route_controller = Mock()
        controller = TrafficController(mock_route_controller)
        assert controller._route_controller is mock_route_controller

    def test_init_empty_traffic_dict(self) -> None:
        mock_route_controller = Mock()
        controller = TrafficController(mock_route_controller)
        assert controller._segment_key_to_traffic == {}


class TestTrafficControllerSetTraffic:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        rc = Mock()
        rc.get_road_by_segment_key = Mock(return_value=None)
        rc.get_all_active_roads = Mock(return_value=set())
        rc.generate_point_collection = Mock(
            return_value=[Position([0.0, 0.0]), Position([1.0, 1.0])]
        )
        return rc

    @pytest.fixture
    def sample_road(self) -> Mock:
        road = Mock(spec=Road)
        road.id = 123
        road.name = "Test Street"
        road.pointcollection = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        road.length = 100.0
        road.maxspeed = 10.0
        return road

    @pytest.fixture
    def sample_segment_key(self) -> SegmentKey:
        return ((0.0, 0.0), (1.0, 1.0))

    def test_set_traffic_returns_false_for_missing_road(
        self, mock_route_controller: Mock, sample_segment_key: SegmentKey
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = None
        controller = TrafficController(mock_route_controller)

        result = controller.set_traffic(sample_segment_key, 0.5)

        assert result is False

    def test_set_traffic_returns_true_for_found_road(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)

        result = controller.set_traffic(sample_segment_key, 0.5)

        assert result is True

    def test_set_traffic_stores_state_in_dict(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)

        controller.set_traffic(sample_segment_key, 0.5)

        assert sample_segment_key in controller._segment_key_to_traffic
        assert isinstance(
            controller._segment_key_to_traffic[sample_segment_key], RoadTrafficState
        )

    def test_set_traffic_calls_road_set_traffic_state(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)

        controller.set_traffic(sample_segment_key, 0.5)

        sample_road.set_traffic_state.assert_called_once()

    def test_set_traffic_with_source(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)

        controller.set_traffic(sample_segment_key, 0.5, source="api_event")

        state = controller._segment_key_to_traffic[sample_segment_key]
        assert state.source_event == "api_event"

    @pytest.mark.parametrize(
        "input_mult,expected_mult",
        [
            (0.0, 0.01),
            (-0.5, 0.01),
            (1.5, 1.0),
            (0.5, 0.5),
        ],
    )
    def test_set_traffic_multiplier_clamping(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
        input_mult: float,
        expected_mult: float,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)

        controller.set_traffic(sample_segment_key, input_mult)

        state = controller._segment_key_to_traffic[sample_segment_key]
        assert state.multiplier == expected_mult


class TestTrafficControllerClearTraffic:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        rc = Mock()
        rc.get_road_by_segment_key = Mock(return_value=None)
        rc.get_all_active_roads = Mock(return_value=set())
        rc.generate_point_collection = Mock(
            return_value=[Position([0.0, 0.0]), Position([1.0, 1.0])]
        )
        return rc

    @pytest.fixture
    def sample_road(self) -> Mock:
        road = Mock(spec=Road)
        road.id = 123
        road.name = "Test Street"
        road.pointcollection = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        road.length = 100.0
        road.maxspeed = 10.0
        return road

    @pytest.fixture
    def sample_segment_key(self) -> SegmentKey:
        return ((0.0, 0.0), (1.0, 1.0))

    def test_clear_traffic_returns_false_for_missing_road(
        self, mock_route_controller: Mock, sample_segment_key: SegmentKey
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = None
        controller = TrafficController(mock_route_controller)

        result = controller.clear_traffic(sample_segment_key)

        assert result is False

    def test_clear_traffic_returns_true_for_found_road(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)

        result = controller.clear_traffic(sample_segment_key)

        assert result is True

    def test_clear_traffic_removes_from_dict(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)
        controller.set_traffic(sample_segment_key, 0.5)
        assert sample_segment_key in controller._segment_key_to_traffic

        controller.clear_traffic(sample_segment_key)

        assert sample_segment_key not in controller._segment_key_to_traffic

    def test_clear_traffic_calls_road_clear_traffic(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        mock_route_controller.get_road_by_segment_key.return_value = sample_road
        controller = TrafficController(mock_route_controller)

        controller.clear_traffic(sample_segment_key)

        sample_road.clear_traffic.assert_called_once()


class TestTrafficControllerClearAllTraffic:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        rc = Mock()
        rc.get_road_by_segment_key = Mock(return_value=None)
        rc.get_all_active_roads = Mock(return_value=set())
        rc.generate_point_collection = Mock(
            return_value=[Position([0.0, 0.0]), Position([1.0, 1.0])]
        )
        return rc

    def test_clear_all_traffic_clears_dict(self, mock_route_controller: Mock) -> None:
        mock_route_controller.get_all_active_roads.return_value = set()
        controller = TrafficController(mock_route_controller)
        controller._segment_key_to_traffic[((0.0, 0.0), (1.0, 1.0))] = Mock(
            spec=RoadTrafficState
        )

        controller.clear_all_traffic()

        assert controller._segment_key_to_traffic == {}

    def test_clear_all_traffic_calls_road_clear_on_each(
        self, mock_route_controller: Mock
    ) -> None:
        road1 = Mock(spec=Road)
        road2 = Mock(spec=Road)
        mock_route_controller.get_all_active_roads.return_value = {road1, road2}
        controller = TrafficController(mock_route_controller)

        controller.clear_all_traffic()

        road1.clear_traffic.assert_called_once()
        road2.clear_traffic.assert_called_once()

    def test_clear_all_traffic_empty_state(self, mock_route_controller: Mock) -> None:
        mock_route_controller.get_all_active_roads.return_value = set()
        controller = TrafficController(mock_route_controller)

        controller.clear_all_traffic()

        assert controller._segment_key_to_traffic == {}


class TestTrafficControllerGetTrafficState:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        rc = Mock()
        rc.get_road_by_segment_key = Mock(return_value=None)
        rc.get_all_active_roads = Mock(return_value=set())
        rc.generate_point_collection = Mock(
            return_value=[Position([0.0, 0.0]), Position([1.0, 1.0])]
        )
        return rc

    @pytest.fixture
    def sample_segment_key(self) -> SegmentKey:
        return ((0.0, 0.0), (1.0, 1.0))

    def test_get_traffic_state_returns_none_for_missing(
        self, mock_route_controller: Mock, sample_segment_key: SegmentKey
    ) -> None:
        controller = TrafficController(mock_route_controller)

        result = controller.get_traffic_state(sample_segment_key)

        assert result is None

    def test_get_traffic_state_returns_state(
        self, mock_route_controller: Mock, sample_segment_key: SegmentKey
    ) -> None:
        controller = TrafficController(mock_route_controller)
        mock_state = Mock(spec=RoadTrafficState)
        controller._segment_key_to_traffic[sample_segment_key] = mock_state

        result = controller.get_traffic_state(sample_segment_key)

        assert result is mock_state


class TestTrafficControllerGenerateTrafficPoints:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        rc = Mock()
        rc.get_road_by_segment_key = Mock(return_value=None)
        rc.get_all_active_roads = Mock(return_value=set())
        rc.generate_point_collection = Mock(
            return_value=[Position([0.0, 0.0]), Position([1.0, 1.0])]
        )
        return rc

    def test_generate_traffic_points_empty_pointcollection_raises(
        self, mock_route_controller: Mock
    ) -> None:
        controller = TrafficController(mock_route_controller)
        road = Mock(spec=Road)
        road.id = 123
        road.name = "Empty Road"
        road.pointcollection = []
        road.length = 100.0
        road.maxspeed = 10.0

        with pytest.raises(ValueError) as exc_info:
            controller._generate_traffic_points(road, 0.5)

        assert "Empty Road" in str(exc_info.value)
        assert "123" in str(exc_info.value)

    def test_generate_traffic_points_zero_effective_speed_raises(
        self, mock_route_controller: Mock
    ) -> None:
        controller = TrafficController(mock_route_controller)
        road = Mock(spec=Road)
        road.id = 456
        road.name = "Zero Speed Road"
        road.pointcollection = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        road.length = 100.0
        road.maxspeed = 0.0

        with pytest.raises(ValueError) as exc_info:
            controller._generate_traffic_points(road, 0.5)

        assert "Effective speed must be > 0" in str(exc_info.value)

    def test_generate_traffic_points_calls_route_controller(
        self, mock_route_controller: Mock
    ) -> None:
        controller = TrafficController(mock_route_controller)
        road = Mock(spec=Road)
        road.id = 123
        road.name = "Test Road"
        road.pointcollection = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        road.length = 100.0
        road.maxspeed = 10.0

        controller._generate_traffic_points(road, 0.5)

        mock_route_controller.generate_point_collection.assert_called_once()

    def test_generate_traffic_points_uses_effective_speed(
        self, mock_route_controller: Mock
    ) -> None:
        controller = TrafficController(mock_route_controller)
        road = Mock(spec=Road)
        road.id = 123
        road.name = "Test Road"
        road.pointcollection = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        road.length = 100.0
        road.maxspeed = 10.0

        controller._generate_traffic_points(road, 0.5)

        call_kwargs = mock_route_controller.generate_point_collection.call_args.kwargs
        assert call_kwargs["maxspeed"] == 5.0

    def test_generate_traffic_points_returns_positions(
        self, mock_route_controller: Mock
    ) -> None:
        expected_points = [
            Position([0.0, 0.0]),
            Position([0.5, 0.5]),
            Position([1.0, 1.0]),
        ]
        mock_route_controller.generate_point_collection.return_value = expected_points
        controller = TrafficController(mock_route_controller)
        road = Mock(spec=Road)
        road.id = 123
        road.name = "Test Road"
        road.pointcollection = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        road.length = 100.0
        road.maxspeed = 10.0

        result = controller._generate_traffic_points(road, 0.5)

        assert result == expected_points


class TestTrafficControllerRoadDeallocationCleanup:
    """Tests for traffic state cleanup when roads are deallocated."""

    def test_traffic_state_cleaned_up_on_road_deallocation(self) -> None:
        """Test that traffic state is removed when road is deallocated."""
        mock_route_controller = Mock()
        mock_route_controller.generate_point_collection.return_value = [
            Position([0.0, 0.0]),
            Position([1.0, 1.0]),
        ]

        # Capture the callback registered by TrafficController
        registered_callback = None

        def capture_callback(callback: Callable[[SegmentKey], None]) -> None:
            nonlocal registered_callback
            registered_callback = callback

        mock_route_controller.register_on_road_deallocated = capture_callback

        controller = TrafficController(mock_route_controller)

        # Verify callback was registered
        assert registered_callback is not None

        # Set up a road with traffic
        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        mock_road = Mock(spec=Road)
        mock_road.pointcollection = [Position([0.0, 0.0]), Position([1.0, 1.0])]
        mock_road.length = 100.0
        mock_road.maxspeed = 10.0

        mock_route_controller.get_road_by_segment_key.return_value = mock_road

        # Set traffic on the road
        controller.set_traffic(segment_key, 0.5, source="test")
        assert segment_key in controller._segment_key_to_traffic

        # Simulate road deallocation by calling the callback
        registered_callback(segment_key)

        # Traffic state should be cleaned up
        assert segment_key not in controller._segment_key_to_traffic

    def test_cleanup_handles_nonexistent_segment_key(self) -> None:
        """Test that cleanup doesn't fail for segment keys without traffic."""
        mock_route_controller = Mock()

        registered_callback: Optional[Callable[[SegmentKey], None]] = None

        def capture_callback(callback: Callable[[SegmentKey], None]) -> None:
            nonlocal registered_callback
            registered_callback = callback

        mock_route_controller.register_on_road_deallocated = capture_callback

        controller = TrafficController(mock_route_controller)

        # Call cleanup on a segment that never had traffic - should not raise
        nonexistent_key: SegmentKey = ((99.0, 99.0), (100.0, 100.0))
        assert registered_callback is not None
        registered_callback(nonexistent_key)  # Should not raise

        assert nonexistent_key not in controller._segment_key_to_traffic
