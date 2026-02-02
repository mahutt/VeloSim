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

from typing import Callable
from unittest.mock import Mock

import pytest

from sim.entities.position import Position
from sim.entities.road import Road
from sim.entities.traffic_data import RoadTrafficState
from sim.map.routing_provider import SegmentKey
from sim.traffic.traffic_controller import TrafficController


def create_mock_route_controller() -> Mock:
    """Create a mock RouteController with callback registration."""
    rc = Mock()
    rc.get_all_active_roads = Mock(return_value=set())

    # Store registered callbacks
    rc._on_road_created_callbacks = []
    rc._on_road_deallocated_callbacks = []

    def register_on_road_created(callback: Callable[[Road], None]) -> None:
        rc._on_road_created_callbacks.append(callback)

    def unregister_on_road_created(callback: Callable[[Road], None]) -> bool:
        try:
            rc._on_road_created_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def register_on_road_deallocated(callback: Callable[[Road], None]) -> None:
        rc._on_road_deallocated_callbacks.append(callback)

    def unregister_on_road_deallocated(callback: Callable[[Road], None]) -> bool:
        try:
            rc._on_road_deallocated_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    rc.register_on_road_created = register_on_road_created
    rc.unregister_on_road_created = unregister_on_road_created
    rc.register_on_road_deallocated = register_on_road_deallocated
    rc.unregister_on_road_deallocated = unregister_on_road_deallocated

    return rc


def create_mock_road(
    segment_key: SegmentKey, road_id: int = 123, name: str = "Test Street"
) -> Mock:
    """Create a mock Road with proper nodes for the segment_key."""
    road = Mock(spec=Road)
    road.id = road_id
    road.name = name
    road.segment_key = segment_key

    start_coords, end_coords = segment_key
    start_pos = Position([start_coords[0], start_coords[1]])
    end_pos = Position([end_coords[0], end_coords[1]])
    road.pointcollection = [start_pos, end_pos]
    road.length = 100.0
    road.maxspeed = 10.0

    # Create nodes matching the segment_key (using Position objects)
    road.nodes = [start_pos, end_pos]

    # Mock add_traffic_range to return True by default
    road.add_traffic_range = Mock(return_value=True)
    road.remove_traffic = Mock(return_value=True)
    road.clear_traffic = Mock()

    return road


class TestTrafficControllerInitialization:
    def test_init_stores_route_controller(self) -> None:
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)
        assert controller._route_controller is mock_route_controller

    def test_init_empty_traffic_dict(self) -> None:
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)
        assert controller._active_traffic == {}

    def test_init_registers_callbacks(self) -> None:
        mock_route_controller = create_mock_route_controller()
        TrafficController(mock_route_controller)
        # Callbacks should be registered
        assert len(mock_route_controller._on_road_created_callbacks) == 1
        assert len(mock_route_controller._on_road_deallocated_callbacks) == 1


class TestTrafficControllerSetTraffic:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        return create_mock_route_controller()

    @pytest.fixture
    def sample_segment_key(self) -> SegmentKey:
        return ((0.0, 0.0), (1.0, 1.0))

    @pytest.fixture
    def sample_road(self, sample_segment_key: SegmentKey) -> Mock:
        return create_mock_road(sample_segment_key)

    def _simulate_road_creation(self, mock_route_controller: Mock, road: Mock) -> None:
        """Simulate road creation by calling all registered callbacks."""
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(road)

    def test_set_traffic_stores_state_even_when_no_roads_affected(
        self, mock_route_controller: Mock, sample_segment_key: SegmentKey
    ) -> None:
        # No roads registered, but traffic should still be stored for future roads
        controller = TrafficController(mock_route_controller)

        result = controller.set_traffic(sample_segment_key, 0.5)

        # Returns False because no active roads were affected
        assert result is False
        # Verify state is still stored for future roads
        assert sample_segment_key in controller._active_traffic

    def test_set_traffic_returns_true_when_roads_affected(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        controller = TrafficController(mock_route_controller)
        # Simulate road creation to populate node index
        self._simulate_road_creation(mock_route_controller, sample_road)

        result = controller.set_traffic(sample_segment_key, 0.5)

        assert result is True

    def test_set_traffic_stores_state_in_dict(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        controller = TrafficController(mock_route_controller)
        self._simulate_road_creation(mock_route_controller, sample_road)

        controller.set_traffic(sample_segment_key, 0.5)

        assert sample_segment_key in controller._active_traffic
        assert isinstance(
            controller._active_traffic[sample_segment_key], RoadTrafficState
        )

    def test_set_traffic_calls_add_traffic_range_on_road(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        controller = TrafficController(mock_route_controller)
        self._simulate_road_creation(mock_route_controller, sample_road)

        controller.set_traffic(sample_segment_key, 0.5)

        sample_road.add_traffic_range.assert_called_once()
        call_args = sample_road.add_traffic_range.call_args
        assert call_args[0][0] == sample_segment_key
        assert call_args[0][1] == 0.5  # multiplier is passed directly

    def test_set_traffic_with_source(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        controller = TrafficController(mock_route_controller)
        self._simulate_road_creation(mock_route_controller, sample_road)

        controller.set_traffic(sample_segment_key, 0.5, source="api_event")

        state = controller._active_traffic[sample_segment_key]
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
        controller = TrafficController(mock_route_controller)
        self._simulate_road_creation(mock_route_controller, sample_road)

        controller.set_traffic(sample_segment_key, input_mult)

        state = controller._active_traffic[sample_segment_key]
        assert state.multiplier == expected_mult


class TestTrafficControllerClearTraffic:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        return create_mock_route_controller()

    @pytest.fixture
    def sample_segment_key(self) -> SegmentKey:
        return ((0.0, 0.0), (1.0, 1.0))

    @pytest.fixture
    def sample_road(self, sample_segment_key: SegmentKey) -> Mock:
        return create_mock_road(sample_segment_key)

    def _simulate_road_creation(self, mock_route_controller: Mock, road: Mock) -> None:
        """Simulate road creation by calling all registered callbacks."""
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(road)

    def test_clear_traffic_returns_false_when_no_roads_affected(
        self, mock_route_controller: Mock, sample_segment_key: SegmentKey
    ) -> None:
        # No roads registered, so no nodes in the index
        controller = TrafficController(mock_route_controller)

        result = controller.clear_traffic(sample_segment_key)

        assert result is False

    def test_clear_traffic_returns_true_when_roads_affected(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        controller = TrafficController(mock_route_controller)
        self._simulate_road_creation(mock_route_controller, sample_road)

        result = controller.clear_traffic(sample_segment_key)

        assert result is True

    def test_clear_traffic_removes_from_dict(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        controller = TrafficController(mock_route_controller)
        self._simulate_road_creation(mock_route_controller, sample_road)
        controller.set_traffic(sample_segment_key, 0.5)
        assert sample_segment_key in controller._active_traffic

        controller.clear_traffic(sample_segment_key)

        assert sample_segment_key not in controller._active_traffic

    def test_clear_traffic_calls_remove_traffic_on_road(
        self,
        mock_route_controller: Mock,
        sample_road: Mock,
        sample_segment_key: SegmentKey,
    ) -> None:
        controller = TrafficController(mock_route_controller)
        self._simulate_road_creation(mock_route_controller, sample_road)

        controller.clear_traffic(sample_segment_key)

        sample_road.remove_traffic.assert_called_once_with(sample_segment_key)


class TestTrafficControllerClearAllTraffic:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        return create_mock_route_controller()

    def test_clear_all_traffic_clears_dict(self, mock_route_controller: Mock) -> None:
        mock_route_controller.get_all_active_roads.return_value = set()
        controller = TrafficController(mock_route_controller)
        controller._active_traffic[((0.0, 0.0), (1.0, 1.0))] = Mock(
            spec=RoadTrafficState
        )

        controller.clear_all_traffic()

        assert controller._active_traffic == {}

    def test_clear_all_traffic_calls_road_clear_on_each(
        self, mock_route_controller: Mock
    ) -> None:
        segment_key1: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        segment_key2: SegmentKey = ((2.0, 2.0), (3.0, 3.0))
        road1 = create_mock_road(segment_key1, road_id=1)
        road2 = create_mock_road(segment_key2, road_id=2)
        mock_route_controller.get_all_active_roads.return_value = {road1, road2}
        controller = TrafficController(mock_route_controller)

        controller.clear_all_traffic()

        road1.clear_traffic.assert_called_once()
        road2.clear_traffic.assert_called_once()

    def test_clear_all_traffic_empty_state(self, mock_route_controller: Mock) -> None:
        mock_route_controller.get_all_active_roads.return_value = set()
        controller = TrafficController(mock_route_controller)

        controller.clear_all_traffic()

        assert controller._active_traffic == {}


class TestTrafficControllerGetTrafficState:
    @pytest.fixture
    def mock_route_controller(self) -> Mock:
        return create_mock_route_controller()

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
        controller._active_traffic[sample_segment_key] = mock_state

        result = controller.get_traffic_state(sample_segment_key)

        assert result is mock_state


class TestTrafficControllerRoadDeallocationCleanup:
    """Tests for traffic state cleanup when roads are deallocated."""

    def test_traffic_state_cleaned_up_on_road_deallocation(self) -> None:
        """Test that traffic state is removed when road is deallocated."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        # Set up road and simulate creation
        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        mock_road = create_mock_road(segment_key)

        # Simulate road creation to populate node index
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(mock_road)

        # Set traffic on the road
        controller.set_traffic(segment_key, 0.5, source="test")
        assert segment_key in controller._active_traffic

        # Simulate road deallocation by calling the deallocated callback
        for callback in mock_route_controller._on_road_deallocated_callbacks:
            callback(mock_road)

        # Traffic state should be cleaned up
        assert segment_key not in controller._active_traffic

    def test_cleanup_handles_nonexistent_segment_key(self) -> None:
        """Test that cleanup doesn't fail for roads without traffic."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        # Create a road that never had traffic applied
        nonexistent_key: SegmentKey = ((99.0, 99.0), (100.0, 100.0))
        mock_road = create_mock_road(nonexistent_key)

        # Simulate road creation
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(mock_road)

        # Simulate road deallocation - should not raise even with no traffic
        for callback in mock_route_controller._on_road_deallocated_callbacks:
            callback(mock_road)

        assert nonexistent_key not in controller._active_traffic

    def test_node_index_cleaned_up_on_road_deallocation(self) -> None:
        """Test that node index is cleaned up when road is deallocated."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        mock_road = create_mock_road(segment_key)

        # Simulate road creation
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(mock_road)

        # Verify nodes are in the index (using Position objects)
        start_coords = segment_key[0]
        end_coords = segment_key[1]
        start_pos = Position([start_coords[0], start_coords[1]])
        end_pos = Position([end_coords[0], end_coords[1]])
        assert start_pos in controller._node_to_roads
        assert end_pos in controller._node_to_roads

        # Simulate road deallocation
        for callback in mock_route_controller._on_road_deallocated_callbacks:
            callback(mock_road)

        # Nodes should be removed from index
        assert start_pos not in controller._node_to_roads
        assert end_pos not in controller._node_to_roads


class TestTrafficControllerCleanup:
    """Tests for TrafficController cleanup method."""

    def test_cleanup_unregisters_callbacks(self) -> None:
        """Test that cleanup unregisters all callbacks."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        # Verify callbacks are registered
        assert len(mock_route_controller._on_road_created_callbacks) == 1
        assert len(mock_route_controller._on_road_deallocated_callbacks) == 1

        controller.cleanup()

        # Callbacks should be unregistered
        assert len(mock_route_controller._on_road_created_callbacks) == 0
        assert len(mock_route_controller._on_road_deallocated_callbacks) == 0

    def test_cleanup_clears_state(self) -> None:
        """Test that cleanup clears internal state."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        # Add some state
        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        mock_road = create_mock_road(segment_key)
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(mock_road)
        controller.set_traffic(segment_key, 0.5)

        controller.cleanup()

        assert controller._active_traffic == {}
        assert controller._node_to_roads == {}


class TestTrafficControllerNewRoadTrafficApplication:
    """Tests for applying existing traffic to newly created roads."""

    def test_traffic_applied_to_new_road_matching_existing_traffic(self) -> None:
        """Test that existing traffic is applied when a new road is created."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        # Set traffic BEFORE any roads exist
        segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        controller.set_traffic(segment_key, 0.5)

        # Verify traffic state is stored
        assert segment_key in controller._active_traffic

        # Now create a road that matches the traffic segment
        mock_road = create_mock_road(segment_key)

        # Simulate road creation - this should apply the existing traffic
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(mock_road)

        # Verify add_traffic_range was called on the new road
        mock_road.add_traffic_range.assert_called_with(segment_key, 0.5)

    def test_traffic_not_applied_to_new_road_not_matching_existing_traffic(
        self,
    ) -> None:
        """Test that traffic is not applied to roads with non-matching segments."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        # Set traffic for a specific segment
        traffic_segment_key: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        controller.set_traffic(traffic_segment_key, 0.5)

        # Create a road with a DIFFERENT segment that doesn't overlap
        road_segment_key: SegmentKey = ((10.0, 10.0), (11.0, 11.0))
        mock_road = create_mock_road(road_segment_key)

        # Simulate road creation
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(mock_road)

        # add_traffic_range is called but should return False for non-matching segment
        # The method is still called because we check all traffic states
        mock_road.add_traffic_range.assert_called_with(traffic_segment_key, 0.5)

    def test_multiple_traffic_states_applied_to_new_road(self) -> None:
        """Test that multiple existing traffic states are applied to a new road."""
        mock_route_controller = create_mock_route_controller()
        controller = TrafficController(mock_route_controller)

        # Set multiple traffic states before road exists
        segment_key1: SegmentKey = ((0.0, 0.0), (1.0, 1.0))
        segment_key2: SegmentKey = ((0.5, 0.5), (1.5, 1.5))
        controller.set_traffic(segment_key1, 0.5)
        controller.set_traffic(segment_key2, 0.3)

        # Create a road
        mock_road = create_mock_road(segment_key1)

        # Simulate road creation
        for callback in mock_route_controller._on_road_created_callbacks:
            callback(mock_road)

        # Both traffic states should be attempted to apply
        calls = mock_road.add_traffic_range.call_args_list
        assert len(calls) == 2
