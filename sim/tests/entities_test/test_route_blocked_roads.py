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

import pytest
from unittest.mock import Mock, patch

from sim.entities.route import Route
from sim.entities.road import Road
from sim.entities.position import Position
from sim.map.routing_provider import RoutingProvider, RouteResult, RouteStep


@pytest.fixture
def test_config() -> dict:
    """Provides a basic test configuration."""
    return {
        "tick_duration": 1,
        "start_time": "2025-01-01 00:00:00",
    }


@pytest.fixture
def mock_routing_provider() -> RoutingProvider:
    """Provides a mock routing provider."""
    return Mock(spec=RoutingProvider)


@pytest.fixture
def sample_route_result() -> RouteResult:
    """Provides a simple 3-point route for testing."""
    return RouteResult(
        coordinates=[
            Position([0.0, 0.0]),
            Position([1.0, 0.0]),
            Position([2.0, 0.0]),
        ],
        distance=2000,
        duration=300,
        steps=[
            RouteStep(
                name="Test Step",
                distance=2000,
                duration=300,
                geometry=[
                    Position([0.0, 0.0]),
                    Position([1.0, 0.0]),
                    Position([2.0, 0.0]),
                ],
            ),
        ],
        segments=[],
    )


class TestBlockedPositions:
    """Test-suite for vehicle behavior when encountering blocked positions."""

    def test_next_returns_current_position_when_next_is_occupied(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """When next position is occupied, next() returns current position
        without incrementing.
        """
        # Create 3 positions:
        # first unoccupied, second occupied (blocked), third unoccupied
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=True)  # BLOCKED
        pos3 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        # First call: returns first position
        first = route.next()
        assert first == pos1
        assert route.current_point_index == 1

        # Second call: next position (pos2) is occupied
        # Should return current position (pos1) without incrementing
        second = route.next()
        assert second == pos1
        assert route.current_point_index == 1  # Index did NOT increment

    def test_vehicle_waits_at_blocked_position_on_retry(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """Vehicle retries from same position when blocked,
        same result until unblocked.
        """
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=True)  # BLOCKED
        pos3 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        # Traverse to pos1
        route.next()

        # Try to advance 5 times while pos2 is blocked
        for i in range(5):
            result = route.next()
            assert result == pos1, f"Iteration {i}: Expected to stay at pos1"
            assert (
                route.current_point_index == 1
            ), f"Iteration {i}: Index should not increment"

    def test_vehicle_continues_after_blockage_clears(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """Once blocked position becomes unoccupied, vehicle advances."""
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=True)  # Initially BLOCKED
        pos3 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        # Traverse to pos1
        route.next()
        assert route.current_point_index == 1

        # Try to advance while blocked
        result = route.next()
        assert result == pos1

        # Unblock the position
        pos2.occupied = False

        # Now next() should return pos2 and increment
        result = route.next()
        assert result == pos2
        assert route.current_point_index == 2

        # Next call should return pos3
        result = route.next()
        assert result == pos3
        assert (
            route.current_point_index == 3
        )  # Max index = 2, so now finished or transitioned

    def test_first_position_occupied(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """When first position is occupied, vehicle is placed there and waits."""
        pos1 = Position([0.0, 0.0], occupied=True)  # First position BLOCKED
        pos2 = Position([1.0, 0.0], occupied=False)
        pos3 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        # First call should return pos1 (place vehicle there) without incrementing
        first = route.next()
        assert first == pos1
        assert route.current_point_index == 0  # Did not increment

        # Second call: still blocked, returns same position
        second = route.next()
        assert second == pos1
        assert route.current_point_index == 0

        # Unblock and try again
        pos1.occupied = False
        third = route.next()
        assert third == pos2
        # Now should increment to attempt pos2
        assert route.current_point_index == 2

    def test_multiple_consecutive_blockages(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """Vehicle waits when multiple consecutive positions are blocked."""
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=True)  # BLOCKED
        pos3 = Position([2.0, 0.0], occupied=True)  # Also BLOCKED
        pos4 = Position([3.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3, pos4],
            length=3000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        # Traverse to pos1
        route.next()
        assert route.current_point_index == 1

        # Blocked at pos2
        result = route.next()
        assert result == pos1
        assert route.current_point_index == 1

        # Unblock pos2, but pos3 is still blocked
        pos2.occupied = False
        result = route.next()
        assert result == pos2
        assert route.current_point_index == 2

        # Now blocked at pos3
        result = route.next()
        assert result == pos2
        assert route.current_point_index == 2

        # Unblock pos3
        pos3.occupied = False
        result = route.next()
        assert result == pos3
        assert route.current_point_index == 3

        # Unblocked pos4 available
        result = route.next()
        assert result == pos4
        assert route.current_point_index == 4

    def test_blockage_across_road_transitions(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
    ) -> None:
        """Vehicle handles blocked positions that span across road boundaries."""
        # This tests that occupancy checking works even across multiple roads
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=True)  # Blocked, end of road1

        pos3 = Position(
            [1.0, 0.0], occupied=True
        )  # Same location, start of road2 (blocked)
        pos4 = Position([2.0, 0.0], occupied=False)

        road1 = Road(
            road_id=1,
            name="road1",
            pointcollection=[pos1, pos2],
            length=1000,
            maxspeed=10,
        )

        road2 = Road(
            road_id=2,
            name="road2",
            pointcollection=[pos3, pos4],
            length=1000,
            maxspeed=10,
        )

        route_result = RouteResult(
            coordinates=[pos1, pos2, pos3, pos4],
            distance=2000,
            duration=300,
            steps=[
                RouteStep(
                    name="Test Road 1 to 2",
                    distance=2000,
                    duration=300,
                    geometry=[pos1, pos2, pos3, pos4],
                ),
            ],
            segments=[],
        )

        route = Route(
            route_result, mock_routing_provider, test_config, roads=[road1, road2]
        )

        # Traverse to pos1
        route.next()
        assert route.current_road_index == 0

        # Try to continue: blocked at road boundary
        result = route.next()
        assert result == pos1

    def test_blockage_with_traffic_change_scenario(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """Vehicle blocked position logic coexists with traffic point changes."""
        # Simulate a scenario where traffic reduces point count while vehicle is blocked
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([0.5, 0.0], occupied=True)  # BLOCKED (added by traffic)
        pos3 = Position([1.0, 0.0], occupied=False)
        pos4 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3, pos4],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        # Traverse to pos1
        route.next()
        assert route.current_point_index == 1

        # Blocked at pos2
        result = route.next()
        assert result == pos1
        assert route.current_point_index == 1

        # Traffic clears (removes pos2) - now route has 3 positions
        road.pointcollection = [pos1, pos3, pos4]

        # Vehicle should still be waiting since next_position (was pos2) is gone
        # After traffic change, current_point_index should map forward
        # The duplicate check should kick in and we continue
        result = route.next()
        # Should move forward since new pos at index 1 is pos3 (unoccupied)
        assert route.current_point_index >= 1

    def test_transition_buffer_waits_when_next_point_is_occupied(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """If next transition-buffer point is occupied,
        wait without consuming buffer.
        """
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=False)
        pos3 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        # Set a current position first.
        first = route.next()
        assert first == pos1

        transition_blocked = Position([0.2, 0.0], occupied=True)
        transition_following = Position([0.4, 0.0], occupied=False)
        route._transition_buffer = [transition_blocked, transition_following]

        # While blocked, route should wait at current position and not consume buffer.
        result = route.next()
        assert result == pos1
        assert len(route._transition_buffer) == 2
        assert route._transition_buffer[0] == transition_blocked

    def test_transition_buffer_resumes_after_unblocked(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """Transition-buffer traversal resumes immediately when blocked point clears."""
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=False)
        pos3 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        first = route.next()
        assert first == pos1

        transition_blocked = Position([0.2, 0.0], occupied=True)
        transition_following = Position([0.4, 0.0], occupied=False)
        route._transition_buffer = [transition_blocked, transition_following]

        # First tick while blocked: wait.
        blocked_result = route.next()
        assert blocked_result == pos1
        assert len(route._transition_buffer) == 2

        # Unblock and verify next call consumes the transition point.
        transition_blocked.occupied = False
        resumed_result = route.next()
        assert resumed_result == transition_blocked
        assert len(route._transition_buffer) == 1

    def test_generated_transition_waits_if_first_point_is_occupied(
        self,
        test_config: dict,
        mock_routing_provider: RoutingProvider,
        sample_route_result: RouteResult,
    ) -> None:
        """When generated transition starts blocked, route waits and keeps buffer."""
        pos1 = Position([0.0, 0.0], occupied=False)
        pos2 = Position([1.0, 0.0], occupied=False)
        pos3 = Position([2.0, 0.0], occupied=False)

        road = Road(
            road_id=1,
            name="test_road",
            pointcollection=[pos1, pos2, pos3],
            length=2000,
            maxspeed=10,
        )

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )

        first = route.next()
        assert first == pos1
        assert route.current_point_index == 1

        transition_blocked = Position([0.2, 0.0], occupied=True)
        transition_following = Position([0.4, 0.0], occupied=False)

        with patch.object(route, "get_distance_to_next_event", return_value=1.0):
            with patch.object(
                road,
                "generate_curve",
                return_value=[transition_blocked, transition_following],
            ):
                result = route.next()

        assert result == pos1
        assert route.current_point_index == 1
        assert len(route._transition_buffer) == 2
        assert route._transition_buffer[0] == transition_blocked
