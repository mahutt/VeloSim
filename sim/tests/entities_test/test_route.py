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

# mypy: ignore-errors

import pytest
from typing import List
from unittest.mock import Mock, patch
from shapely.geometry import LineString

from sim.entities.route import Route
from sim.entities.road import Road
from sim.entities.position import Position
from sim.entities.traffic_data import CongestionLevel, TrafficRange
from sim.map.routing_provider import RoutingProvider, RouteResult, RouteStep, SegmentKey


def build_roads_from_route_result(route_result: RouteResult) -> List[Road]:
    """
    Build Road objects from RouteResult for testing purposes.

    This is a simplified version of RouteController's road building logic,
    used to provide roads for Route tests without requiring a full controller.
    """
    roads: List[Road] = []

    if route_result.steps:
        for step in route_result.steps:
            if not step.geometry or step.distance <= 0:
                continue

            # Calculate speed from duration or use default
            maxspeed = 13.89  # ~50 km/h default
            if step.speed and step.speed > 0:
                maxspeed = step.speed
            elif step.duration > 0 and step.distance > 0:
                maxspeed = step.distance / step.duration

            # Generate positions (simplified: geometry is now List[Position])
            positions = list(step.geometry)

            road_id = hash(tuple(tuple(pos.get_position()) for pos in step.geometry))
            road = Road(
                road_id=road_id,
                name=step.name,
                pointcollection=positions,
                length=step.distance,
                maxspeed=maxspeed,
            )
            roads.append(road)
    elif route_result.coordinates and len(route_result.coordinates) >= 2:
        # Fallback: create single road from coordinates (now List[Position])
        positions = list(route_result.coordinates)

        road_id = hash(
            tuple(tuple(pos.get_position()) for pos in route_result.coordinates)
        )
        road = Road(
            road_id=road_id,
            name=None,
            pointcollection=positions,
            length=route_result.distance,
            maxspeed=13.89,
        )
        roads.append(road)

    return roads


def apply_test_traffic(road: Road, traffic_points: List[Position]) -> None:
    """
    Apply traffic with specific points to a road for testing purposes.

    This directly sets the road's internal traffic state to simulate traffic
    with a specific point collection. Used for testing Route's index clamping
    behavior without depending on the actual point generation logic.

    Args:
        road: The road to apply traffic to
        traffic_points: The specific points to use as the traffic pointcollection
    """
    # Create a segment key from the road
    segment_key: SegmentKey = road.segment_key

    # Create a traffic range covering the entire road
    traffic_range = TrafficRange(
        start_index=0,
        end_index=len(road.nodes) - 1 if road.nodes else 0,
        multiplier=0.5,
        segment_key=segment_key,
    )

    # Apply traffic directly to internal state
    road._traffic_ranges = [traffic_range]
    road._traffic_pointcollection = traffic_points


@pytest.fixture
def test_config() -> dict:
    """
    Provide test configuration data.
    """
    return {
        "simulation": {
            "kmh_to_ms_factor": 3.6,
            "map_rules": {"roads": {"default_road_max_speed": 30}},
        }
    }


@pytest.fixture
def mock_routing_provider() -> Mock:
    """
    Creates a mock RoutingProvider for coordinate-based routing.
    """
    mock_provider = Mock(spec=RoutingProvider)
    return mock_provider


@pytest.fixture
def sample_route_result() -> RouteResult:
    """
    Returns sample route result with coordinates and steps.
    """
    return RouteResult(
        coordinates=[
            Position([-73.5673, 45.5017]),  # Start point (Montreal area)
            Position([-73.5670, 45.5020]),  # Waypoint 1
            Position([-73.5665, 45.5025]),  # Waypoint 2
            Position([-73.5660, 45.5030]),  # End point
        ],
        distance=300.0,  # meters
        duration=180.0,  # seconds
        steps=[
            RouteStep(
                name="Rue Saint-Denis",
                distance=150.0,
                duration=90.0,
                geometry=[Position([-73.5673, 45.5017]), Position([-73.5670, 45.5020])],
            ),
            RouteStep(
                name="Boulevard de Maisonneuve",
                distance=150.0,
                duration=90.0,
                geometry=[
                    Position([-73.5670, 45.5020]),
                    Position([-73.5665, 45.5025]),
                    Position([-73.5660, 45.5030]),
                ],
            ),
        ],
        segments=[],
    )


@pytest.fixture
def simple_route_result() -> RouteResult:
    """Create a simple RouteResult for testing."""
    step1 = RouteStep(
        name="Main Street",
        distance=100.0,
        duration=7.2,
        geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
        speed=13.88,
    )
    step2 = RouteStep(
        name="Second Avenue",
        distance=150.0,
        duration=10.8,
        geometry=[Position([0.001, 0.0]), Position([0.001, 0.001])],
        speed=13.88,
    )

    return RouteResult(
        coordinates=[
            Position([0.0, 0.0]),
            Position([0.001, 0.0]),
            Position([0.001, 0.001]),
        ],
        distance=250.0,
        duration=18.0,
        steps=[step1, step2],
        segments=[],
    )


@pytest.fixture
def route_result_no_steps() -> RouteResult:
    """Create a RouteResult without steps (fallback mode)."""
    return RouteResult(
        coordinates=[
            Position([0.0, 0.0]),
            Position([0.001, 0.0]),
            Position([0.002, 0.0]),
        ],
        distance=200.0,
        duration=14.4,
        steps=[],
        segments=[],
    )


class TestRouteCreation:
    """Tests for Route object initialization with coordinate-based routing."""

    def test_route_creation_with_valid_route_data(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that a route can be created with valid route data."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        assert route is not None
        assert route.id > 0
        assert route.current_road_index == 0
        assert route.current_point_index == 0
        assert route.is_finished is False
        assert len(route.roads) == 2  # 2 steps in sample data

    def test_route_creation_with_empty_coordinates(
        self, test_config, mock_routing_provider
    ) -> None:
        """Test that a route with empty coordinates creates an empty route."""
        empty_result = RouteResult(
            coordinates=[],
            distance=0,
            duration=0,
            steps=[],
            segments=[],
        )
        roads = build_roads_from_route_result(empty_result)
        route = Route(empty_result, mock_routing_provider, test_config, roads=roads)
        # Route with empty coordinates is finished immediately
        assert route.is_finished is True

    def test_route_unique_ids(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that each route gets a unique ID."""
        roads = build_roads_from_route_result(sample_route_result)
        route1 = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )
        route2 = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        assert route1.id != route2.id

    def test_route_stores_start_and_end_positions(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route stores start and end positions for recalculation."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        assert route.start_position == sample_route_result.start_position
        assert route.end_position == sample_route_result.end_position

    def test_route_builds_road_segments_from_steps(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that road segments are correctly built from route steps."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        # Should create 2 road segments from steps
        assert len(route.roads) == 2
        assert route.roads[0].name == "Rue Saint-Denis"
        assert route.roads[1].name == "Boulevard de Maisonneuve"

        # Check that roads have point collections
        for road in route.roads:
            assert hasattr(road, "pointcollection")
            assert len(road.pointcollection) > 0
            assert all(isinstance(p, Position) for p in road.pointcollection)

    def test_route_fallback_without_steps(
        self, test_config, mock_routing_provider
    ) -> None:
        """Test that route falls back to single road when steps are missing."""
        route_result = RouteResult(
            coordinates=[Position([-73.5673, 45.5017]), Position([-73.5660, 45.5030])],
            distance=200.0,
            duration=120.0,
            steps=[],  # No steps
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Should create 1 road from all coordinates
        assert len(route.roads) == 1
        assert route.roads[0].name is None  # Fallback route has no specific name
        assert len(route.roads[0].pointcollection) > 0

    def test_route_stores_distance_and_duration(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route stores distance and duration from routing result."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        assert route.distance == 300.0
        assert route.duration == 180.0


class TestRouteSubscription:
    """Tests for route subscription via RouteController."""

    def test_route_with_route_controller(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route stores reference to RouteController."""
        roads = build_roads_from_route_result(sample_route_result)
        mock_route_controller = Mock()

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        assert route.route_controller == mock_route_controller

    def test_unsubscribe_from_all_roads(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route can unsubscribe from all roads via RouteController."""
        roads = build_roads_from_route_result(sample_route_result)
        mock_route_controller = Mock()
        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        route.unsubscribe_from_all_roads()

        mock_route_controller.unregister_route.assert_called_once_with(route)

    def test_unsubscribe_from_specific_road(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route can unsubscribe from a specific road via RouteController."""
        roads = build_roads_from_route_result(sample_route_result)
        mock_route_controller = Mock()
        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        road = route.roads[0]
        route.unsubscribe_from_road(road.id)

        mock_route_controller.unregister_road_from_route.assert_called_once_with(
            road, route
        )

    def test_unsubscribe_without_route_controller(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test unsubscribe operations handle missing route_controller gracefully."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        # Should not raise an exception
        route.unsubscribe_from_all_roads()
        route.unsubscribe_from_road(12345)


class TestRouteTraversal:
    """Tests for route traversal using next() with coordinate-based routing."""

    def test_first_call_returns_current_position(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that first call to next() returns current position."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        result = route.next()

        assert isinstance(result, Position)
        # Full route is available via separate method
        full_route = route.get_route_geometry()
        assert isinstance(full_route, LineString)

    def test_subsequent_calls_return_only_position(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that all calls to next() return only the position."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        # First call
        first = route.next()
        assert isinstance(first, Position)

        # Second call
        result = route.next()

        assert isinstance(result, Position)

    def test_traversal_moves_through_roads(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that traversal correctly moves through road segments."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )
        initial_road_index = route.current_road_index

        # Move through all points in first road
        first_road = route.roads[0]
        num_points = len(first_road.pointcollection)

        # Skip duplicates at boundaries by calling next until road changes
        for _ in range(num_points):
            route.next()
            if route.current_road_index > initial_road_index:
                break

        # Should have moved to the next road or finished
        assert route.current_road_index > initial_road_index or route.is_finished

    def test_route_finishes_when_complete(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route is marked as finished when all points are consumed."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        # Count total points (accounting for boundary overlaps)
        all_points = route._get_all_points()
        total_points = len(all_points)

        # Traverse all points
        for _ in range(total_points + 10):  # Extra calls to ensure we reach the end
            result = route.next()
            if result is None:
                break

        assert route.is_finished is True

        # Next call should return None
        assert route.next() is None

    def test_route_unsubscribes_from_completed_roads(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route unsubscribes from roads as they are completed."""
        roads = build_roads_from_route_result(sample_route_result)
        mock_route_controller = Mock()
        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        # Move through all points in first road
        first_road = route.roads[0]
        num_points = len(first_road.pointcollection)

        for _ in range(num_points):
            route.next()
            if route.current_road_index > 0:
                break

        # Should have unsubscribed from the first road via RouteController
        calls = mock_route_controller.unregister_road_from_route.call_args_list
        roads_unsubscribed = [call[0][0] for call in calls]
        assert first_road in roads_unsubscribed

    def test_route_avoids_duplicate_positions(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route skips consecutive duplicate positions."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        positions_returned = []
        for _ in range(50):  # Get multiple positions
            result = route.next()
            if result is None:
                break

            if isinstance(result, Position):
                positions_returned.append(result.get_position())

        # Check no consecutive duplicates
        for i in range(len(positions_returned) - 1):
            assert (
                positions_returned[i] != positions_returned[i + 1]
            ), f"Found duplicate positions at indices {i} and {i+1}"


class TestRouteRecalculation:
    """Tests for route recalculation when roads are disabled with
    coordinate-based routing."""

    def test_recalculate_with_valid_route_controller(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that recalculate works with a valid route controller."""
        roads = build_roads_from_route_result(sample_route_result)

        # Create a mock RouteController
        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = True

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        # Advance the route a bit
        route.next()
        route.next()

        # Recalculate the route
        success = route.recalculate()

        assert success is True
        # Should have called route_controller.recalculate_route
        assert mock_route_controller.recalculate_route.called

    def test_recalculate_delegates_to_route_controller(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """
        Test that recalculation delegates to RouteController.
        """
        roads = build_roads_from_route_result(sample_route_result)

        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = True

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        # Advance and recalculate
        route.next()
        success = route.recalculate()

        assert success is True
        # RouteController handles unsubscribe/resubscribe
        mock_route_controller.recalculate_route.assert_called_once()

    def test_recalculate_preserves_route_id(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that route ID remains the same after recalculation."""
        roads = build_roads_from_route_result(sample_route_result)

        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = True

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )
        original_id = route.id

        route.next()
        route.recalculate()

        assert route.id == original_id

    def test_recalculate_marks_finished_on_failure(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test recalculation marks route finished when controller returns False."""
        roads = build_roads_from_route_result(sample_route_result)

        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = False

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        # Advance the route
        route.next()

        # Recalculate (will fail)
        success = route.recalculate()

        assert success is False
        assert route.is_finished is True

    def test_recalculate_returns_false_if_finished(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that recalculate returns False if route is already finished."""
        roads = build_roads_from_route_result(sample_route_result)

        mock_route_controller = Mock()

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )
        route.is_finished = True

        success = route.recalculate()

        assert success is False
        # RouteController should not be called when already finished
        mock_route_controller.recalculate_route.assert_not_called()

    def test_recalculate_returns_false_without_route_controller(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that recalculate returns False if no route controller is set."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        success = route.recalculate()

        assert success is False


class TestRouteTimedRecalculation:
    """Tests for elapsed-time based automatic route refresh."""

    @pytest.mark.parametrize("invalid_interval", [0, -1])
    def test_non_positive_interval_defaults_to_30_minutes(
        self,
        invalid_interval: int,
        test_config,
        mock_routing_provider,
        sample_route_result,
    ) -> None:
        """Non-positive interval values should fall back to 30 minutes."""
        roads = build_roads_from_route_result(sample_route_result)
        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = True

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
            route_recalculation_interval_seconds=invalid_interval,
        )

        assert route._route_recalculation_interval_seconds == 1800

        route.next()
        assert mock_route_controller.recalculate_route.call_count == 0

    def test_next_triggers_recalculation_after_interval(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Route.next should trigger refresh when interval threshold is reached."""
        roads = build_roads_from_route_result(sample_route_result)
        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = True

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
            route_recalculation_interval_seconds=2,
        )

        route.next()
        assert mock_route_controller.recalculate_route.call_count == 0

        route.next()
        assert mock_route_controller.recalculate_route.call_count == 1

    def test_successful_recalculation_resets_elapsed_counter(
        self, test_config, mock_routing_provider
    ) -> None:
        """A successful refresh should reset the internal elapsed timer."""
        long_route_result = RouteResult(
            coordinates=[
                Position([0.0, 0.0]),
                Position([0.001, 0.0]),
                Position([0.002, 0.0]),
                Position([0.003, 0.0]),
                Position([0.004, 0.0]),
            ],
            distance=500.0,
            duration=100.0,
            steps=[
                RouteStep(
                    name="Long Test Road",
                    distance=500.0,
                    duration=100.0,
                    geometry=[
                        Position([0.0, 0.0]),
                        Position([0.001, 0.0]),
                        Position([0.002, 0.0]),
                        Position([0.003, 0.0]),
                        Position([0.004, 0.0]),
                    ],
                )
            ],
            segments=[],
        )

        roads = build_roads_from_route_result(long_route_result)
        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = True

        route = Route(
            long_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
            route_recalculation_interval_seconds=2,
        )

        route.next()
        route.next()
        assert mock_route_controller.recalculate_route.call_count == 1

        route.next()
        assert mock_route_controller.recalculate_route.call_count == 1

        route.next()
        assert mock_route_controller.recalculate_route.call_count == 2

    def test_route_finishes_when_timed_recalculation_fails(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """A failed timed refresh should mark the route as finished."""
        roads = build_roads_from_route_result(sample_route_result)
        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = False

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
            route_recalculation_interval_seconds=1,
        )

        result = route.next()

        assert result is None
        assert route.is_finished is True
        assert mock_route_controller.recalculate_route.call_count == 1


class TestRouteEdgeCases:
    """Tests for edge cases and error handling with coordinate-based routing."""

    def test_route_with_single_coordinate_pair(
        self, test_config, mock_routing_provider
    ) -> None:
        """Test route creation with a single coordinate.

        A single coordinate without steps creates an empty roads list,
        which results in the route being marked as finished immediately.
        """
        route_result = RouteResult(
            coordinates=[Position([-73.5673, 45.5017])],
            distance=0.0,
            duration=0.0,
            steps=[],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)
        # Route with single coordinate is finished immediately since no roads created
        assert route.is_finished is True

    def test_route_with_two_identical_coordinates(
        self, test_config, mock_routing_provider
    ) -> None:
        """Test route where start and end are the same."""
        route_result = RouteResult(
            coordinates=[Position([-73.5673, 45.5017]), Position([-73.5673, 45.5017])],
            distance=0.0,
            duration=0.0,
            steps=[
                RouteStep(
                    name="Same Location",
                    distance=0.0,
                    duration=0.0,
                    geometry=[
                        Position([-73.5673, 45.5017]),
                        Position([-73.5673, 45.5017]),
                    ],
                )
            ],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Should handle gracefully
        assert route is not None
        # May have minimal points
        if len(route.roads) > 0:
            assert len(route.roads[0].pointcollection) >= 1

    def test_route_with_very_short_distance(
        self, test_config, mock_routing_provider
    ) -> None:
        """Test route with very short distance."""
        route_result = RouteResult(
            coordinates=[Position([-73.5673, 45.5017]), Position([-73.5673, 45.5018])],
            distance=5.0,  # 5 meters
            duration=3.0,
            steps=[
                RouteStep(
                    name="Very Short Street",
                    distance=5.0,
                    duration=3.0,
                    geometry=[
                        Position([-73.5673, 45.5017]),
                        Position([-73.5673, 45.5018]),
                    ],
                )
            ],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Should handle short routes
        assert route is not None
        assert len(route.roads) > 0
        # Should have at least start and end points
        assert len(route.roads[0].pointcollection) >= 2

    def test_route_with_long_distance(self, test_config, mock_routing_provider) -> None:
        """Test route with very long distance can be created."""
        route_result = RouteResult(
            coordinates=[
                Position([-73.5673, 45.5017]),
                Position([-73.5600, 45.5100]),
                Position([-73.5500, 45.5200]),
            ],
            distance=5000.0,  # 5 km
            duration=600.0,  # 10 minutes
            steps=[
                RouteStep(
                    name="Long Street",
                    distance=5000.0,
                    duration=600.0,
                    geometry=[
                        Position([-73.5673, 45.5017]),
                        Position([-73.5600, 45.5100]),
                        Position([-73.5500, 45.5200]),
                    ],
                )
            ],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Should handle long routes
        assert route is not None
        assert len(route.roads) > 0
        # Should have at least the geometry points
        total_points = sum(len(r.pointcollection) for r in route.roads)
        assert total_points >= 3  # At least the 3 geometry coordinates

    def test_route_with_many_steps(self, test_config, mock_routing_provider) -> None:
        """Test route with many road segments."""
        steps = [
            RouteStep(
                name=f"Street {i}",
                distance=100.0,
                duration=60.0,
                geometry=[
                    Position([-73.5673 + i * 0.0005, 45.5017 + i * 0.0003]),
                    Position([-73.5673 + (i + 1) * 0.0005, 45.5017 + (i + 1) * 0.0003]),
                ],
            )
            for i in range(5)
        ]
        route_result = RouteResult(
            coordinates=[
                Position([-73.5673, 45.5017]),
                Position([-73.5670, 45.5020]),
                Position([-73.5665, 45.5025]),
                Position([-73.5660, 45.5030]),
                Position([-73.5655, 45.5035]),
            ],
            distance=500.0,
            duration=300.0,
            steps=steps,
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Should create road for each step
        assert route is not None
        assert len(route.roads) == 5

    def test_route_handles_missing_step_names(
        self, test_config, mock_routing_provider
    ) -> None:
        """Test that route handles steps with missing names."""
        route_result = RouteResult(
            coordinates=[Position([-73.5673, 45.5017]), Position([-73.5660, 45.5030])],
            distance=200.0,
            duration=120.0,
            steps=[
                RouteStep(
                    name=None,  # name is None
                    distance=200.0,
                    duration=120.0,
                    geometry=[
                        Position([-73.5673, 45.5017]),
                        Position([-73.5660, 45.5030]),
                    ],
                )
            ],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Should handle missing names gracefully
        assert route is not None
        assert len(route.roads) > 0
        # Name should be None for unnamed roads
        assert route.roads[0].name is None

    def test_get_all_points_filters_duplicates(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that _get_all_points filters out consecutive duplicates."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        all_points = route._get_all_points()

        # Check no consecutive duplicates
        for i in range(len(all_points) - 1):
            assert all_points[i].get_position() != all_points[i + 1].get_position()

    def test_get_route_geometry_returns_linestring(
        self, test_config, mock_routing_provider, sample_route_result
    ) -> None:
        """Test that get_route_geometry returns a valid LineString."""
        roads = build_roads_from_route_result(sample_route_result)
        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=roads
        )

        geometry = route.get_route_geometry()

        assert isinstance(geometry, LineString)
        assert len(geometry.coords) >= 2  # At least start and end


# ============================================================================
# Additional tests from test_route.py
# ============================================================================


class TestRouteInitialization:
    """Test suite for Route initialization (from test_route.py)."""

    def test_route_with_route_result_and_steps(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test Route initialization with RouteResult containing steps."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        assert route.id > 0
        assert route.current_road_index == 0
        assert route.current_point_index == 0
        assert route.is_finished is False
        assert len(route.roads) == 2  # Should have created 2 roads from 2 steps
        assert route.routing_provider == mock_routing_provider
        assert route.distance == 250.0
        assert route.duration == 18.0
        assert route.start_position.get_position() == [0.0, 0.0]
        assert route.end_position.get_position() == [0.001, 0.001]

    def test_route_with_route_result_no_steps(
        self,
        route_result_no_steps: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test Route initialization with RouteResult without steps (fallback)."""
        roads = build_roads_from_route_result(route_result_no_steps)
        route = Route(
            route_result_no_steps, mock_routing_provider, test_config, roads=roads
        )

        assert route.id > 0
        assert len(route.roads) == 1  # Single fallback road
        assert route.distance == 200.0
        assert route.is_finished is False

    def test_route_with_invalid_type_raises_error(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that passing non-RouteResult data raises AttributeError."""
        with pytest.raises(AttributeError):
            Route(
                {"coordinates": [[0, 0]]},  # type: ignore
                mock_routing_provider,
                test_config,
                roads=[],  # Provide roads to get past missing argument check
            )

    def test_route_with_empty_steps_and_coords(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test Route with minimal valid route (two points)."""
        minimal_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([0.0, 0.0])],
            distance=0.0,
            duration=0.0,
            steps=[],
            segments=[],
        )

        roads = build_roads_from_route_result(minimal_result)

        route = Route(minimal_result, mock_routing_provider, test_config, roads=roads)
        assert len(route.roads) >= 0


class TestRouteTraversalDetailed:
    """Detailed test suite for Route traversal (from test_route.py)."""

    def test_next_first_call(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that first call to next() returns position only."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        result = route.next()

        assert isinstance(result, Position)
        geometry = route.get_route_geometry()
        assert isinstance(geometry, LineString)

    def test_next_subsequent_calls_return_positions(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that all calls to next() return Position objects."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        first = route.next()
        assert isinstance(first, Position)

        second = route.next()
        assert isinstance(second, Position)

        third = route.next()
        assert isinstance(third, Position)

    def test_next_traverses_all_roads(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that next() traverses all roads in sequence."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        positions = []
        result = route.next()
        while result is not None:
            if isinstance(result, Position):
                positions.append(result)
            result = route.next()

        assert route.is_finished is True
        assert route.current_road_index >= len(route.roads)
        assert len(positions) > 0

    def test_next_skips_duplicate_positions(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that next() skips consecutive duplicate positions."""
        step1 = RouteStep(
            name="Road 1",
            distance=50.0,
            duration=3.6,
            geometry=[Position([0.0, 0.0]), Position([0.0005, 0.0])],
            speed=13.88,
        )
        step2 = RouteStep(
            name="Road 2",
            distance=50.0,
            duration=3.6,
            geometry=[Position([0.0005, 0.0]), Position([0.001, 0.0])],
            speed=13.88,
        )

        route_result = RouteResult(
            coordinates=[
                Position([0.0, 0.0]),
                Position([0.0005, 0.0]),
                Position([0.001, 0.0]),
            ],
            distance=100.0,
            duration=7.2,
            steps=[step1, step2],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)

        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        positions = []
        result = route.next()
        while result is not None:
            if isinstance(result, Position):
                pos = result.get_position()
                positions.append(pos)
            result = route.next()

        for i in range(len(positions) - 1):
            assert positions[i] != positions[i + 1]

    def test_next_returns_none_when_finished(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that next() returns None once route is finished."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        result = route.next()
        while result is not None:
            result = route.next()

        assert route.is_finished is True
        assert route.next() is None
        assert route.next() is None


class TestRouteRoadBuilding:
    """Test suite for road building from routing data (from test_route.py)."""

    def test_build_roads_from_steps(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that roads are properly built from route steps."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        assert len(route.roads) == 2
        assert route.roads[0].name == "Main Street"
        assert route.roads[1].name == "Second Avenue"
        assert route.roads[0].length == 100.0
        assert route.roads[1].length == 150.0

    def test_build_coordinate_roads_fallback(
        self,
        route_result_no_steps: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test fallback road building from coordinates."""
        roads = build_roads_from_route_result(route_result_no_steps)
        route = Route(
            route_result_no_steps, mock_routing_provider, test_config, roads=roads
        )

        assert len(route.roads) == 1
        assert route.roads[0].name is None
        assert len(route.roads[0].pointcollection) > 0

    def test_skip_invalid_steps(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that invalid steps are skipped during road building."""
        invalid_step = RouteStep(
            name="Invalid Road",
            distance=0.0,
            duration=0.0,
            geometry=[],
            speed=0.0,
        )
        valid_step = RouteStep(
            name="Valid Road",
            distance=100.0,
            duration=7.2,
            geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            speed=13.88,
        )

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            distance=100.0,
            duration=7.2,
            steps=[invalid_step, valid_step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)

        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        assert len(route.roads) == 1
        assert route.roads[0].name == "Valid Road"


class TestRouteRecalculationDetailed:
    """Detailed test suite for route recalculation (from test_route.py)."""

    def test_recalculate_success(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test successful route recalculation."""
        roads = build_roads_from_route_result(simple_route_result)

        # Create mock RouteController
        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = True

        route = Route(
            simple_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        route.next()
        route.next()

        success = route.recalculate()

        assert success is True
        mock_route_controller.recalculate_route.assert_called_once()

    def test_recalculate_when_finished(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that recalculation fails when route is finished."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )
        route.is_finished = True

        success = route.recalculate()
        assert success is False

    def test_recalculate_without_route_controller(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that recalculation fails without RouteController."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        success = route.recalculate()
        assert success is False

    def test_recalculate_no_route_found(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test recalculation when RouteController returns failure."""
        roads = build_roads_from_route_result(simple_route_result)

        # Create mock RouteController that fails
        mock_route_controller = Mock()
        mock_route_controller.recalculate_route.return_value = False

        route = Route(
            simple_route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        route.next()
        success = route.recalculate()

        assert success is False
        assert route.is_finished is True


class TestRouteHelperMethods:
    """Test suite for Route helper methods (from test_route.py)."""

    def test_get_all_points(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test _get_all_points returns all positions without duplicates."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        all_points = route._get_all_points()

        assert len(all_points) > 0
        assert all(isinstance(p, Position) for p in all_points)

        for i in range(len(all_points) - 1):
            assert all_points[i].get_position() != all_points[i + 1].get_position()

    def test_get_route_geometry(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test get_route_geometry returns valid LineString."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        geometry = route.get_route_geometry()

        assert isinstance(geometry, LineString)
        assert len(geometry.coords) > 0

    def test_get_current_position(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test _get_current_position returns current Position."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        current_pos = route._get_current_position()

        assert current_pos is not None
        assert isinstance(current_pos, Position)
        assert len(current_pos.get_position()) == 2

    def test_get_current_position_when_finished(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test _get_current_position returns None when finished."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        while route.next() is not None:
            pass

        current_pos = route._get_current_position()
        assert current_pos is None


class TestRouteEdgeCasesDetailed:
    """Detailed test suite for edge cases (from test_route.py)."""

    def test_route_with_single_step(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test Route with a single step."""
        step = RouteStep(
            name="Single Road",
            distance=50.0,
            duration=3.6,
            geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            speed=13.88,
        )

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            distance=50.0,
            duration=3.6,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)

        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        assert len(route.roads) == 1
        assert route.roads[0].name == "Single Road"

    def test_route_with_zero_speed_step(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test Route handles step with zero speed gracefully."""
        step = RouteStep(
            name="Zero Speed Road",
            distance=100.0,
            duration=0.0,
            geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            speed=0.0,
        )

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            distance=100.0,
            duration=0.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)

        route = Route(route_result, mock_routing_provider, test_config, roads=roads)
        assert len(route.roads) >= 0

    def test_route_coordinates_match_step_geometry(
        self,
        simple_route_result: RouteResult,
        mock_routing_provider: Mock,
        test_config: dict,
    ) -> None:
        """Test that route coordinates align with step geometries."""
        roads = build_roads_from_route_result(simple_route_result)
        route = Route(
            simple_route_result, mock_routing_provider, test_config, roads=roads
        )

        first_pos = route.roads[0].pointcollection[0].get_position()
        start_coords = simple_route_result.start_position.get_position()
        assert first_pos[0] == pytest.approx(start_coords[0])
        assert first_pos[1] == pytest.approx(start_coords[1])

        last_pos = route.roads[-1].pointcollection[-1].get_position()
        end_coords = simple_route_result.end_position.get_position()
        assert last_pos[0] == pytest.approx(end_coords[0])
        assert last_pos[1] == pytest.approx(end_coords[1])


class TestRouteRequiredRoads:
    """Tests for Route roads parameter validation."""

    def test_route_with_roads_none_raises_error(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that Route raises ValueError when roads is None."""
        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[],
            segments=[],
        )

        with pytest.raises(ValueError, match="roads parameter is required"):
            Route(
                route_result,
                mock_routing_provider,
                test_config,
                roads=None,  # type: ignore
            )


class TestRouteFinalDestination:
    """Tests for Route final destination handling (issue #447)."""

    def test_route_returns_exact_destination_at_end(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that route returns exact destination as final point."""
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([1.0, 1.0])],
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Traverse the entire route
        last_position = None
        while True:
            result = route.next()
            if result is None:
                break
            if isinstance(result, Position):
                last_position = result

        # The last returned position should be the destination
        assert last_position is not None
        final_pos = last_position.get_position()
        assert final_pos[0] == pytest.approx(1.0)
        assert final_pos[1] == pytest.approx(1.0)

    def test_route_finished_after_destination(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that route is marked finished after returning destination."""
        step = RouteStep(
            name="Test Road",
            distance=50.0,
            duration=5.0,
            geometry=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([0.5, 0.5])],
            distance=50.0,
            duration=5.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Traverse to the end
        while route.next() is not None:
            pass

        assert route.is_finished is True
        # Next call should return None
        assert route.next() is None


class TestRouteIndexClampingOnTrafficChange:
    """Tests for Route.next() index clamping when traffic changes mid-traversal.

    When traffic changes reduce the point count on a road while the route is
    being traversed, the index must be clamped to prevent IndexError. The route
    should return the last valid point and then transition to the next road.
    """

    def test_index_clamped_when_traffic_reduces_points(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that index is clamped when traffic reduces point count."""

        # Create a road with 10 points
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance route to index 5
        for _ in range(5):
            route.next()

        assert route.current_point_index == 5

        # Now simulate traffic change that reduces points to 3
        traffic_points = [Position([0.0, i * 0.001]) for i in range(3)]
        apply_test_traffic(roads[0], traffic_points)

        # Call next() - should clamp index to 2 (max valid) and return that point
        point = route.next()

        # Should return the last valid point (index 2)
        assert point is not None
        assert point.get_position() == traffic_points[2].get_position()

    def test_route_transitions_after_clamping(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that route transitions to next road after clamping."""

        # Create two roads
        road1_points = [Position([0.0, i * 0.001]) for i in range(10)]
        road2_points = [Position([0.0, 0.009 + i * 0.001]) for i in range(5)]

        step1 = RouteStep(
            name="First Road",
            distance=100.0,
            duration=10.0,
            geometry=road1_points,
            speed=10.0,
        )
        step2 = RouteStep(
            name="Second Road",
            distance=50.0,
            duration=5.0,
            geometry=road2_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=road1_points + road2_points[1:],
            distance=150.0,
            duration=15.0,
            steps=[step1, step2],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance to index 7 on first road
        for _ in range(7):
            route.next()

        assert route.current_road_index == 0
        assert route.current_point_index == 7

        # Traffic change reduces first road to 3 points
        traffic_points = [Position([0.0, i * 0.001]) for i in range(3)]
        apply_test_traffic(roads[0], traffic_points)

        # Call next() - should clamp and return last point
        point1 = route.next()
        assert point1 is not None

        # Next call should be on second road
        point2 = route.next()
        assert route.current_road_index == 1
        assert point2 is not None

    def test_route_finishes_when_clamped_on_last_road(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that route finishes correctly when clamped on the last road."""

        # Single road with 10 points
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        step = RouteStep(
            name="Only Road",
            distance=100.0,
            duration=10.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance to index 8
        for _ in range(8):
            route.next()

        # Traffic reduces to 2 points
        traffic_points = [Position([0.0, 0.0]), Position([0.0, 0.001])]
        apply_test_traffic(roads[0], traffic_points)

        # Call next() - should clamp index and return a valid point
        point = route.next()
        assert point is not None

        # One more call finishes the route (normal transition at max_index)
        route.next()
        assert route.is_finished is True

    def test_no_infinite_loop_on_repeated_clamping(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that repeated clamping doesn't cause infinite loop."""

        # Single road with 5 points
        original_points = [Position([0.0, i * 0.001]) for i in range(5)]
        step = RouteStep(
            name="Test Road",
            distance=50.0,
            duration=5.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=50.0,
            duration=5.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance to index 4
        for _ in range(4):
            route.next()

        # Traffic reduces to 2 points
        traffic_points = [Position([0.0, 0.0]), Position([0.0, 0.001])]
        apply_test_traffic(roads[0], traffic_points)

        # Should complete without infinite loop (timeout would catch this)
        call_count = 0
        max_calls = 100  # Safety limit
        while not route.is_finished and call_count < max_calls:
            route.next()
            call_count += 1

        assert route.is_finished is True
        assert call_count < max_calls  # Should finish well before limit

    def test_clamping_transitions_to_next_road(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that clamping transitions to next road without duplicates."""
        # Two roads
        road1_points = [Position([0.0, i * 0.001]) for i in range(8)]
        road2_points = [Position([0.0, 0.007 + i * 0.001]) for i in range(4)]

        step1 = RouteStep(
            name="First Road",
            distance=80.0,
            duration=8.0,
            geometry=road1_points,
            speed=10.0,
        )
        step2 = RouteStep(
            name="Second Road",
            distance=40.0,
            duration=4.0,
            geometry=road2_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=road1_points + road2_points[1:],
            distance=120.0,
            duration=12.0,
            steps=[step1, step2],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance to index 6 on first road
        returned_positions = []
        for _ in range(6):
            p = route.next()
            if p:
                returned_positions.append(p.get_position())

        # Traffic reduces first road to 3 points (indices 0,1,2)
        # At index 6, driver maps to index 2 (max), triggering transition
        traffic_points = [Position([0.0, i * 0.001]) for i in range(3)]
        apply_test_traffic(roads[0], traffic_points)

        # Next call should transition to road2 and return its first point
        next_point = route.next()
        assert next_point is not None
        returned_positions.append(next_point.get_position())

        # Continue traversal to completion
        while not route.is_finished:
            p = route.next()
            if p:
                returned_positions.append(p.get_position())

        # Verify route finished and no infinite loops
        assert route.is_finished
        # Verify no consecutive duplicates in returned positions
        for i in range(1, len(returned_positions)):
            assert returned_positions[i] != returned_positions[i - 1]

    def test_cleared_traffic_falls_back_to_original(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that cleared traffic falls back to original points.

        When traffic is cleared, active_pointcollection returns
        the original pointcollection.
        """
        # Single road with 5 points
        original_points = [Position([0.0, i * 0.001]) for i in range(5)]

        step = RouteStep(
            name="Test Road",
            distance=50.0,
            duration=5.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=50.0,
            duration=5.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Start traversal - get first point
        p1 = route.next()
        assert p1 is not None

        # Apply traffic, then clear it
        traffic_points = [Position([0.0, i * 0.001]) for i in range(3)]
        apply_test_traffic(roads[0], traffic_points)
        roads[0].clear_traffic()

        # active_pointcollection should return original points after clearing
        assert len(roads[0].active_pointcollection) == 5

        # Route should continue traversing original points
        p2 = route.next()
        assert p2 is not None
        # Should be the second original point
        assert p2.get_position() == original_points[1].get_position()

    def test_clamping_preserves_original_pointcollection(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that original pointcollection is preserved after traffic change."""
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Apply traffic
        traffic_points = [Position([0.0, i * 0.001]) for i in range(3)]
        apply_test_traffic(roads[0], traffic_points)

        # Traverse and finish
        while route.next() is not None:
            pass

        # Original pointcollection should still have 10 points
        assert len(roads[0].pointcollection) == 10
        # Traffic points should have 3
        assert len(roads[0].active_pointcollection) == 3

    def test_ratio_mapping_never_goes_backward(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that ratio mapping places driver at or ahead, never behind.

        Uses ceil() to ensure the mapped position is always at or ahead of
        the driver's current progress percentage, never behind.
        """
        import math

        # Create road with 10 points
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance to index 7 (78% through: 7/9 = 0.778)
        for _ in range(7):
            route.next()

        assert route.current_point_index == 7

        # Traffic reduces to 4 points
        traffic_points = [Position([0.0, i * 0.003]) for i in range(4)]
        apply_test_traffic(roads[0], traffic_points)

        # Expected mapping with ceil():
        # progress = 7 / (10-1) = 0.778
        # new_index = ceil(0.778 * (4-1)) = ceil(2.33) = 3
        # NOT round(2.33) = 2 which would be 67% (behind 78%)
        expected_index = math.ceil((7 / 9) * 3)
        assert expected_index == 3  # Sanity check

        # Call next() to trigger the mapping
        point = route.next()

        # Should map to index 3 (100%), not index 2 (67%)
        assert point is not None
        assert point.get_position() == traffic_points[3].get_position()

    def test_geographic_proximity_at_various_positions(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test geographic proximity mapping at various progress percentages.

        When traffic changes point density on a road, the driver should stay
        at their geographic position rather than jumping (rubber-banding).
        Traffic points span the same range as original (realistic).
        """
        # Original: 10 points [0.0, 0.000] to [0.0, 0.009]
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        # Traffic: 20 points [0.0, 0.000] to [0.0, 0.009] (2x denser, same range)
        traffic_points = [Position([0.0, i * 0.0009 / 2]) for i in range(20)]
        # Recompute to span same range:
        traffic_points = [Position([0.0, i * 0.009 / 19]) for i in range(20)]

        test_cases = [
            # (advance_count, last_returned_y, expected_nearest_y_approx)
            (3, 0.002, 0.002),  # 22% through — should stay near 0.002
            (5, 0.004, 0.004),  # 44% through — should stay near 0.004
            (7, 0.006, 0.006),  # 67% through — should stay near 0.006
        ]

        for advance_count, last_y, expected_approx_y in test_cases:
            step = RouteStep(
                name="Test Road",
                distance=100.0,
                duration=10.0,
                geometry=list(original_points),
                speed=10.0,
            )

            route_result = RouteResult(
                coordinates=list(original_points),
                distance=100.0,
                duration=10.0,
                steps=[step],
                segments=[],
            )

            roads = build_roads_from_route_result(route_result)
            route = Route(route_result, mock_routing_provider, test_config, roads=roads)

            for _ in range(advance_count):
                route.next()

            apply_test_traffic(roads[0], list(traffic_points))

            point = route.next()
            assert point is not None, f"None at advance={advance_count}"

            # Driver should be at/near their geographic position, not ratio-jumped
            returned_y = point.get_position()[1]
            assert abs(returned_y - expected_approx_y) < 0.001, (
                f"advance={advance_count}: expected ~{expected_approx_y}, "
                f"got {returned_y}"
            )

    def test_ratio_mapping_single_point_fallback(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that single-point edge cases fall back to simple clamping."""
        # Create road with 10 points
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance to index 5
        for _ in range(5):
            route.next()

        # Traffic reduces to 1 point (edge case)
        traffic_points = [Position([0.0, 0.0])]
        apply_test_traffic(roads[0], traffic_points)

        # Should fallback to clamping (index 0, the only valid index)
        point = route.next()

        assert point is not None
        assert point.get_position() == traffic_points[0].get_position()

    def test_geographic_proximity_when_traffic_increases_points(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test geographic proximity when traffic INCREASES point count.

        When traffic gives MORE points over the SAME road extent, the
        driver should stay at their geographic position. Geographic
        proximity finds the nearest point in the denser collection.
        """
        # Create road with 5 points spanning [0, 0.004]
        original_points = [Position([0.0, i * 0.001]) for i in range(5)]
        step = RouteStep(
            name="Test Road",
            distance=50.0,
            duration=5.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=50.0,
            duration=5.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Advance to index 2 (returns points 0,1; _last_returned=[0.0, 0.001])
        for _ in range(2):
            route.next()

        assert route.current_point_index == 2

        # Traffic INCREASES to 10 points spanning same range [0, 0.004]
        traffic_points = [Position([0.0, i * 0.004 / 9]) for i in range(10)]
        apply_test_traffic(roads[0], traffic_points)

        # Geographic proximity: nearest to [0.0, 0.001] in denser collection
        # The first point >= 0.001 is the closest match
        point = route.next()

        # Driver should continue from near their geographic position (~0.001),
        # not jump to 56% progress (which would be ~0.002)
        assert point is not None
        returned_y = point.get_position()[1]
        assert (
            abs(returned_y - 0.001) < 0.001
        ), f"Expected position near 0.001, got {returned_y}"

    def test_geographic_proximity_when_traffic_clears(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test geographic proximity when traffic is cleared.

        When traffic is cleared, the point count reverts to original.
        Geographic proximity ensures the driver stays at their position
        rather than jumping to a ratio-mapped index.
        """
        # Create road with 10 original points spanning [0, 0.009]
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Start traversal (returns point 0, index=1, count=10)
        route.next()

        # Apply traffic with 4 points spanning same range [0, 0.009]
        traffic_points = [Position([0.0, i * 0.003]) for i in range(4)]
        apply_test_traffic(roads[0], traffic_points)

        # next() detects traffic change (10 -> 4)
        # Geographic proximity: nearest to [0.0, 0.0] in [0, 0.003, 0.006, 0.009]
        # → index 0, but equals _last_returned → skips, returns index 1 = [0.0, 0.003]
        p1 = route.next()
        assert p1 is not None
        # _last_returned is now [0.0, 0.003], current_point_index=2

        # Clear traffic (back to 10 points)
        roads[0].clear_traffic()

        # Geographic proximity: nearest to [0.0, 0.003] in original 10 points
        # → index 3 (exact match at [0.0, 0.003]), equals _last_returned → skips
        # → returns index 4 = [0.0, 0.004]
        point = route.next()

        # Driver should continue from near [0.0, 0.003] in original collection,
        # returning the next point after their position
        assert point is not None
        returned_y = point.get_position()[1]
        assert abs(returned_y - 0.004) < 0.001, f"Expected ~0.004, got {returned_y}"

    def test_no_mapping_on_first_call(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that no ratio mapping occurs on first next() call.

        The first call should just return the first point without any
        mapping, as there's no previous count to compare against.
        """
        # Create road with 10 points
        original_points = [Position([0.0, i * 0.001]) for i in range(10)]
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=original_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=original_points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # First call should return first point, no mapping
        point = route.next()

        assert point is not None
        assert point.get_position() == original_points[0].get_position()
        assert route.current_point_index == 1  # Incremented after returning

    def test_point_count_resets_on_road_transition(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that _last_point_count resets when transitioning roads."""
        # Create two roads
        road1_points = [Position([0.0, i * 0.001]) for i in range(5)]
        road2_points = [Position([0.0, 0.004 + i * 0.001]) for i in range(5)]

        step1 = RouteStep(
            name="First Road",
            distance=50.0,
            duration=5.0,
            geometry=road1_points,
            speed=10.0,
        )
        step2 = RouteStep(
            name="Second Road",
            distance=50.0,
            duration=5.0,
            geometry=road2_points,
            speed=10.0,
        )

        route_result = RouteResult(
            coordinates=road1_points + road2_points[1:],
            distance=100.0,
            duration=10.0,
            steps=[step1, step2],
            segments=[],
        )

        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Initially None
        assert route._last_point_count is None

        # Start traversing first road
        route.next()

        # Should have count for first road (5 points, but max_index excludes last)
        assert route._last_point_count == 5

        # Traverse to second road
        while route.current_road_index == 0:
            route.next()

        # After transition, count resets then gets set for new road
        # The next() call that transitions also calls _handle_traffic_point_change
        # on the new road, so it should have the new road's count
        assert route._last_point_count == 5  # Second road also has 5 points


class TestMapIndexForward:
    """Tests for the map_index_forward helper function."""

    def test_basic_forward_mapping(self):
        """Test basic ratio-based mapping."""
        # 78% through (index 7 of 10), maps to index 3 of 4 (100% - ceil)
        assert Route.map_index_forward(7, 10, 4) == 3


class TestRouteStopSignBehavior:
    """Tests for stop-sign dwell behavior during route traversal."""

    def test_route_dwells_one_tick_at_stop_sign(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        points = [
            Position([0.0, 0.0]),
            Position([0.0, 0.001]),
            Position([0.0, 0.002]),
        ]
        step = RouteStep(
            name="Stop Road",
            distance=100.0,
            duration=10.0,
            geometry=points,
            speed=10.0,
        )
        route_result = RouteResult(
            coordinates=points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)

        mock_route_controller = Mock()
        mock_route_controller.is_stop_sign_at_position.side_effect = (
            lambda road, position: position.get_position() == points[1].get_position()
        )

        route = Route(
            route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        p1 = route.next()
        p2 = route.next()
        p3 = route.next()  # dwell tick at stop sign
        p4 = route.next()

        assert p1 is not None and p1.get_position() == points[0].get_position()
        assert p2 is not None and p2.get_position() == points[1].get_position()
        assert p3 is not None and p3.get_position() == points[1].get_position()
        assert p4 is not None and p4.get_position() == points[2].get_position()

    def test_route_no_dwell_when_no_stop_sign(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        points = [
            Position([0.0, 0.0]),
            Position([0.0, 0.001]),
            Position([0.0, 0.002]),
        ]
        step = RouteStep(
            name="Normal Road",
            distance=100.0,
            duration=10.0,
            geometry=points,
            speed=10.0,
        )
        route_result = RouteResult(
            coordinates=points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)

        mock_route_controller = Mock()
        mock_route_controller.is_stop_sign_at_position.return_value = False

        route = Route(
            route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        p1 = route.next()
        p2 = route.next()
        p3 = route.next()

        assert p1 is not None and p1.get_position() == points[0].get_position()
        assert p2 is not None and p2.get_position() == points[1].get_position()
        assert p3 is not None and p3.get_position() == points[2].get_position()

    def test_route_dedupes_same_stop_sign_across_adjacent_points(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        points = [
            Position([0.0, 0.0]),
            Position([0.0, 0.001]),
            Position([0.0, 0.002]),
            Position([0.0, 0.003]),
        ]
        step = RouteStep(
            name="Stop Road",
            distance=120.0,
            duration=12.0,
            geometry=points,
            speed=10.0,
        )
        route_result = RouteResult(
            coordinates=points,
            distance=120.0,
            duration=12.0,
            steps=[step],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)

        mock_route_controller = Mock()
        same_sign = Position([0.0, 0.0015])
        mock_route_controller.get_matching_stop_sign_at_position.side_effect = (
            lambda road, position: (
                same_sign
                if position.get_position()
                in (points[1].get_position(), points[2].get_position())
                else None
            )
        )
        mock_route_controller.is_stop_sign_at_position.return_value = False

        route = Route(
            route_result,
            mock_routing_provider,
            test_config,
            roads=roads,
            route_controller=mock_route_controller,
        )

        p1 = route.next()
        p2 = route.next()
        p3 = route.next()  # one dwell tick for the physical sign
        p4 = route.next()
        p5 = route.next()
        p6 = route.next()

        assert p1 is not None and p1.get_position() == points[0].get_position()
        assert p2 is not None and p2.get_position() == points[1].get_position()
        assert p3 is not None and p3.get_position() == points[1].get_position()
        assert p4 is not None and p4.get_position() == points[2].get_position()
        assert p5 is not None and p5.get_position() == points[3].get_position()
        assert p6 is None

    def test_exact_progress_mapping(self):
        """Test mapping when progress is exactly representable."""
        # 50% through (index 4 of 9), maps to index 2 of 5 (50% exactly)
        # progress = 4/8 = 0.5, ceil(0.5 * 4) = ceil(2.0) = 2
        assert Route.map_index_forward(4, 9, 5) == 2

    def test_uses_ceil_for_forward_only(self):
        """Test that ceil() is used to ensure forward-only progress."""
        # 33% through (index 3 of 10), would round to 1 but ceil gives 2
        # progress = 3/9 = 0.333, ceil(0.333 * 3) = ceil(1.0) = 1
        assert Route.map_index_forward(3, 10, 4) == 1

        # 44% through (index 4 of 10), round would give 1, ceil gives 2
        # progress = 4/9 = 0.444, ceil(0.444 * 3) = ceil(1.33) = 2
        assert Route.map_index_forward(4, 10, 4) == 2

    def test_at_start(self):
        """Test mapping at the start of the route."""
        assert Route.map_index_forward(0, 10, 4) == 0

    def test_at_end(self):
        """Test mapping at the end of the route."""
        assert Route.map_index_forward(9, 10, 4) == 3

    def test_beyond_bounds_clamps_to_max(self):
        """Test that index beyond bounds is clamped to max."""
        # Index 15 in a 10-point collection, mapping to 4 points
        # progress = 15/9 = 1.67, ceil(1.67 * 3) = ceil(5.0) = 5
        # But clamped to max valid index 3
        assert Route.map_index_forward(15, 10, 4) == 3

    def test_single_point_old_collection(self):
        """Test fallback when old collection has single point."""
        assert Route.map_index_forward(0, 1, 4) == 0
        assert Route.map_index_forward(5, 1, 4) == 3  # Clamps to max

    def test_single_point_new_collection(self):
        """Test fallback when new collection has single point."""
        assert Route.map_index_forward(5, 10, 1) == 0
        assert Route.map_index_forward(0, 10, 1) == 0

    def test_same_size_collections(self):
        """Test mapping between same-sized collections."""
        assert Route.map_index_forward(5, 10, 10) == 5
        assert Route.map_index_forward(0, 10, 10) == 0
        assert Route.map_index_forward(9, 10, 10) == 9

    def test_larger_new_collection(self):
        """Test mapping to a larger collection."""
        # 50% through (index 2 of 5), maps to 50% of 10 = index 5
        # progress = 2/4 = 0.5, ceil(0.5 * 9) = ceil(4.5) = 5
        assert Route.map_index_forward(2, 5, 10) == 5


class TestFindNearestIndex:
    """Tests for the find_nearest_index geographic proximity function."""

    def test_exact_match(self) -> None:
        """Target position exists in the collection."""
        points = [
            Position([-73.58, 45.49]),
            Position([-73.57, 45.50]),
            Position([-73.56, 45.51]),
        ]
        assert Route.find_nearest_index(points, Position([-73.57, 45.50])) == 1

    def test_nearest_to_middle(self) -> None:
        """Target between two points selects the closer one."""
        points = [
            Position([0.0, 0.0]),
            Position([1.0, 0.0]),
            Position([2.0, 0.0]),
            Position([3.0, 0.0]),
        ]
        # Closest to (1.1, 0.0) is index 1 at (1.0, 0.0)
        assert Route.find_nearest_index(points, Position([1.1, 0.0])) == 1

    def test_nearest_to_start(self) -> None:
        """Target near the start selects index 0."""
        points = [
            Position([0.0, 0.0]),
            Position([10.0, 0.0]),
            Position([20.0, 0.0]),
        ]
        assert Route.find_nearest_index(points, Position([0.1, 0.0])) == 0

    def test_nearest_to_end(self) -> None:
        """Target near the end selects last index."""
        points = [
            Position([0.0, 0.0]),
            Position([10.0, 0.0]),
            Position([20.0, 0.0]),
        ]
        assert Route.find_nearest_index(points, Position([19.9, 0.0])) == 2

    def test_single_point(self) -> None:
        """Single-point collection always returns 0."""
        points = [Position([5.0, 5.0])]
        assert Route.find_nearest_index(points, Position([99.0, 99.0])) == 0

    def test_non_uniform_distribution(self) -> None:
        """Non-uniform spacing (like traffic-affected roads) finds correct point.

        Simulates a road where the first half has sparse points (normal speed)
        and the second half has dense points (traffic zone). Geographic proximity
        correctly finds the nearest point instead of ratio-mapping to a wrong index.
        """
        # Normal zone: 3 points at 0m, 50m, 100m
        # Traffic zone: 5 dense points at 100m, 110m, 120m, 130m, 140m
        points = [
            Position([0.0, 0.0]),  # 0: 0m
            Position([50.0, 0.0]),  # 1: 50m
            Position([100.0, 0.0]),  # 2: 100m (traffic boundary)
            Position([110.0, 0.0]),  # 3: 110m
            Position([120.0, 0.0]),  # 4: 120m
            Position([130.0, 0.0]),  # 5: 130m
            Position([140.0, 0.0]),  # 6: 140m
        ]
        # Driver at ~50m — should get index 1, not a ratio-mapped index
        assert Route.find_nearest_index(points, Position([52.0, 0.0])) == 1
        # Driver at ~100m — should get index 2 (traffic boundary)
        assert Route.find_nearest_index(points, Position([99.0, 0.0])) == 2
        assert Route.map_index_forward(2, 5, 10) == 5


class TestRouteDistanceTraveled:
    """Tests for Route.get_distance_traveled()."""

    def test_distance_at_start_is_zero(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that distance at start of route is 0."""
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            speed=10.0,
        )
        route_result = RouteResult(
            coordinates=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        assert route.get_distance_traveled() == 0.0

    def test_distance_increases_during_traversal(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that distance increases monotonically during traversal."""
        points = [Position([i * 0.001, 0.0]) for i in range(11)]
        step = RouteStep(
            name="Test Road",
            distance=100.0,
            duration=10.0,
            geometry=points,
            speed=10.0,
        )
        route_result = RouteResult(
            coordinates=points,
            distance=100.0,
            duration=10.0,
            steps=[step],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        prev_distance = 0.0
        while not route.is_finished:
            route.next()
            d = route.get_distance_traveled()
            assert d >= prev_distance
            prev_distance = d

    def test_distance_across_multiple_roads(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test distance computation across multiple road segments."""
        step1 = RouteStep(
            name="Road 1",
            distance=100.0,
            duration=10.0,
            geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            speed=10.0,
        )
        step2 = RouteStep(
            name="Road 2",
            distance=150.0,
            duration=15.0,
            geometry=[Position([0.001, 0.0]), Position([0.002, 0.0])],
            speed=10.0,
        )
        route_result = RouteResult(
            coordinates=[
                Position([0.0, 0.0]),
                Position([0.001, 0.0]),
                Position([0.002, 0.0]),
            ],
            distance=250.0,
            duration=25.0,
            steps=[step1, step2],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Traverse past first road
        while route.current_road_index == 0 and not route.is_finished:
            route.next()

        # After completing first road, distance should be >= first road's length
        if not route.is_finished:
            d = route.get_distance_traveled()
            assert d >= 100.0

    def test_distance_when_route_finished(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test distance covers total route when fully traversed."""
        step1 = RouteStep(
            name="Road 1",
            distance=100.0,
            duration=10.0,
            geometry=[Position([0.0, 0.0]), Position([0.001, 0.0])],
            speed=10.0,
        )
        step2 = RouteStep(
            name="Road 2",
            distance=50.0,
            duration=5.0,
            geometry=[Position([0.001, 0.0]), Position([0.002, 0.0])],
            speed=10.0,
        )
        route_result = RouteResult(
            coordinates=[
                Position([0.0, 0.0]),
                Position([0.001, 0.0]),
                Position([0.002, 0.0]),
            ],
            distance=150.0,
            duration=15.0,
            steps=[step1, step2],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        # Traverse to end
        while route.next() is not None:
            pass

        assert route.is_finished
        d = route.get_distance_traveled()
        # Should be approximately the total route distance (sum of road lengths)
        total = sum(r.length for r in route.roads)
        assert d == pytest.approx(total)

    def test_distance_empty_route_is_zero(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that empty (finished) route reports 0 distance."""
        route_result = RouteResult(
            coordinates=[],
            distance=0,
            duration=0,
            steps=[],
            segments=[],
        )
        roads = build_roads_from_route_result(route_result)
        route = Route(route_result, mock_routing_provider, test_config, roads=roads)

        assert route.is_finished
        assert route.get_distance_traveled() == 0.0


class TestRouteEventIndex:
    def test_get_distance_to_next_event(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Test get_distance_to_next_event returns valid distance"""
        # road 0: 5 points, length 100
        road0 = Mock()
        road0.geometry = [None] * 5
        road0.pointcollection = [None] * 5
        road0.active_pointcollection = [None] * 5
        road0.length = 100.0
        # event at index 2 to 3
        road0.get_traffic_geometry_ranges.return_value = [
            (2, 3, CongestionLevel.MODERATE)
        ]

        # road 1: 3 points, length 50
        road1 = Mock()
        road1.geometry = [None] * 3
        road1.pointcollection = [None] * 3
        road1.active_pointcollection = [None] * 3
        road1.length = 50.0
        road1.get_traffic_geometry_ranges.return_value = []

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=[road0, road1],
        )
        route.current_road_index = 0
        route.current_point_index = 0

        # mock the distance traveled method
        route.get_distance_traveled = Mock(return_value=0.0)
        route._rebuild_global_event_indices()

        # check if the global index for the event was built correctly
        # road 0 event (2,3) + offset 0 = (2, 3)
        assert route._event_indices[0] == (2, 3)

        # check distance to that event
        # index 2 is halfway through road0 (indices 0,1,2,3,4)
        # dist = (2 / 4) * 100 = 50.0
        dist = route.get_distance_to_next_event()
        assert dist == pytest.approx(50.0)

    def test_get_distance_to_next_event_at_end_of_route(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Test when he driver is at the very last point of route"""
        road = Mock()
        road.geometry = [None] * 5
        road.pointcollection = [None] * 5
        road.active_pointcollection = [None] * 5
        road.length = 100

        road.get_traffic_geometry_ranges.return_value = []

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )
        route._event_indices = [(1, 2)]

        route.current_road_index - 0
        route.current_point_index = 4  # at the end
        route._next_event_idx = 0

        assert route.get_distance_to_next_event() is None

    def test_get_current_global_geometry_index(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Tests that the offset accumulates correctly across multiple roads."""
        road0 = Mock()
        road0.geometry = [None] * 5
        road0.pointcollection = [None] * 5
        road0.active_pointcollection = [None] * 5
        road0.length = 100
        road1 = Mock()
        road1.geometry = [None] * 3
        road1.pointcollection = [None] * 3
        road1.active_pointcollection = [None] * 3
        road1.length = 50.0

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=[road0, road1],
        )
        road0.get_traffic_geometry_ranges.return_value = []
        road1.get_traffic_geometry_ranges.return_value = []

        # when we are at the start of Road 1
        route.current_road_index = 1
        route.current_point_index = 0

        # offset should be (len(road0.geometry) - 1) = 4
        global_idx = route._get_current_global_geometry_index()
        assert global_idx == 4

    def test_get_current_global_geometry_index_with_no_geometry(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Tests that pointcollection is used if geometry is None"""
        road = Mock()
        road.geometry = None
        road.pointcollection = [None] * 10
        road.active_pointcollection = [None] * 10
        road.length = 90

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road]
        )
        route.roads = [road]
        route.current_road_index = 0
        route.current_point_index = 3

        assert route._get_current_global_geometry_index() == 3

    def test_get_current_global_geometry_index_route_finished(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """
        Tests that the index is clamped to the last global index
        when route is finished.
        """
        road0 = Mock()
        road0.geometry = [None] * 5

        road1 = Mock()
        road1.geometry = [None] * 3

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=[road0, road1],
        )
        route.current_road_index = 2

        # (5-1) + (3-1) = 6
        global_idx = route._get_current_global_geometry_index()
        assert global_idx == 6

    def test_event_at_exact_junction(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Tests an event that starts exactly where two roads meet"""
        road0 = Mock()
        road0.geometry = [None] * 5
        road0.pointcollection = [None] * 5
        road0.active_pointcollection = [None] * 5
        road0.length = 100
        road1 = Mock()
        road1.geometry = [None] * 3
        road1.pointcollection = [None] * 3
        road1.active_pointcollection = [None] * 3
        road1.length = 50.0

        road0.get_traffic_geometry_ranges.return_value = []
        road1.get_traffic_geometry_ranges.return_value = [
            (0, 2, CongestionLevel.MODERATE)
        ]

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=[road0, road1],
        )
        route._rebuild_global_event_indices()

        # road0 offset is 4. road1 starts at global index 4.
        # event should be at (4+0, 4+2) = (4, 6)
        assert route._event_indices[0] == (4, 6)

    def test_get_upcoming_traffic_multiplier(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Tests that the next event's multiplier is returned"""
        road0 = Mock()
        road0.geometry = [None] * 5
        road0.pointcollection = [None] * 5
        road0.active_pointcollection = [None] * 5
        road0.length = 100
        road0.get_multiplier_at_index = Mock(return_value=1.0)
        road1 = Mock()
        road1.geometry = [None] * 3
        road1.pointcollection = [None] * 3
        road1.active_pointcollection = [None] * 3
        road1.length = 50.0
        road1.get_multiplier_at_index = Mock(return_value=0.5)

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=[road0, road1],
        )

        route._event_indices = [(5, 6)]
        route._next_event_idx = 0

        multiplier = route._get_upcoming_traffic_multiplier()
        assert multiplier == 0.5
        road1.get_multiplier_at_index.assert_called_once_with(1)
        road0.get_multiplier_at_index.assert_not_called()

    def test_get_upcoming_traffic_multiplier_finished_route(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Tests that the free flow multiplier is returned if no more events"""
        road0 = Mock()
        road0.geometry = [None] * 5

        road1 = Mock()
        road1.geometry = [None] * 3

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=[road0, road1],
        )
        route.current_road_index = 2

        multiplier = route._get_upcoming_traffic_multiplier()

        assert multiplier == 1.0

    def test_sync_indices_after_transition(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Tests that the route indices sync to the closest road and point."""
        mock_final_pos = Mock()
        mock_final_pos.get_position.return_value = (10, 10)

        point_far = Mock()
        point_far.get_position.return_value = (0, 0)

        point_near = Mock()
        point_near.get_position.return_value = (10.1, 10.1)

        road0 = Mock()
        road0.active_pointcollection = [point_far]

        road1 = Mock()
        road1.active_pointcollection = [point_near]

        route = Route(
            sample_route_result,
            mock_routing_provider,
            test_config,
            roads=[road0, road1],
        )
        route.current_road_index = 0

        with patch.object(Route, "find_nearest_index", side_effect=[0, 0]):
            route._sync_indices_after_transition(mock_final_pos)

        assert route.current_road_index == 1
        assert route.current_point_index == 0
        assert route._last_point_count == 1

    def test_sync_indices_after_transition_on_same_road(
        self, test_config, mock_routing_provider, sample_route_result
    ):
        """Tests that the best point is selected within a single road."""
        mock_final_pos = Mock()
        mock_final_pos.get_position.return_value = (10, 10)

        point1 = Mock()
        point1.get_position.return_value = (9, 9)

        point2 = Mock()
        point2.get_position.return_value = (10.1, 10.1)

        road0 = Mock()
        road0.active_pointcollection = [point1, point2]

        route = Route(
            sample_route_result, mock_routing_provider, test_config, roads=[road0]
        )
        route.current_road_index = 0

        with patch.object(Route, "find_nearest_index", return_value=1):
            route._sync_indices_after_transition(mock_final_pos)

        assert route.current_road_index == 0
        assert route.current_point_index == 1
        assert route._last_point_count == 2
