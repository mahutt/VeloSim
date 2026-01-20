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
from unittest.mock import Mock
from shapely.geometry import LineString

from sim.entities.route import Route, map_index_forward
from sim.entities.road import Road
from sim.entities.position import Position
from sim.map.routing_provider import RoutingProvider, RouteResult, RouteStep


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
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.5,
            congestion_level=CongestionLevel.MODERATE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

        # Call next() - should clamp index to 2 (max valid) and return that point
        point = route.next()

        # Should return the last valid point (index 2)
        assert point is not None
        assert point.get_position() == traffic_points[2].get_position()

    def test_route_transitions_after_clamping(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that route transitions to next road after clamping."""
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.3,
            congestion_level=CongestionLevel.SEVERE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

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
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.2,
            congestion_level=CongestionLevel.SEVERE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

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
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.5,
            congestion_level=CongestionLevel.MODERATE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

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
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.4,
            congestion_level=CongestionLevel.MODERATE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

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

    def test_empty_traffic_points_falls_back_to_original(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that empty traffic_pointcollection falls back to original points.

        When traffic_pointcollection is empty, active_pointcollection returns
        the original pointcollection (empty list is falsy).
        """
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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

        # Set traffic with empty points (should fall back to original)
        traffic_state = RoadTrafficState(
            multiplier=0.1,
            congestion_level=CongestionLevel.SEVERE,
            traffic_pointcollection=[],  # Empty falls back to original
        )
        roads[0].set_traffic_state(traffic_state)

        # active_pointcollection should still return original points
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
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.5,
            congestion_level=CongestionLevel.MODERATE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

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
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.4,
            congestion_level=CongestionLevel.MODERATE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

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

    def test_ratio_mapping_at_various_positions(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test ratio mapping at various progress percentages."""
        import math
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

        test_cases = [
            # (original_count, traffic_count, current_idx, expected_idx)
            (10, 4, 4, math.ceil((4 / 9) * 3)),  # 44% -> ceil(1.33) = 2
            (10, 4, 6, math.ceil((6 / 9) * 3)),  # 67% -> ceil(2.0) = 2
            (10, 4, 8, math.ceil((8 / 9) * 3)),  # 89% -> ceil(2.67) = 3
            (10, 2, 5, math.ceil((5 / 9) * 1)),  # 56% -> ceil(0.56) = 1
        ]

        for orig_count, traffic_count, curr_idx, expected_idx in test_cases:
            # Create road
            original_points = [Position([0.0, i * 0.001]) for i in range(orig_count)]
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

            # Advance to target index
            for _ in range(curr_idx):
                route.next()

            # Apply traffic
            traffic_points = [Position([0.0, i * 0.001]) for i in range(traffic_count)]
            traffic_state = RoadTrafficState(
                multiplier=0.5,
                congestion_level=CongestionLevel.MODERATE,
                traffic_pointcollection=traffic_points,
            )
            roads[0].set_traffic_state(traffic_state)

            # Get mapped point
            point = route.next()

            assert (
                point is not None
            ), f"Failed for {orig_count}->{traffic_count} at {curr_idx}"
            assert (
                point.get_position() == traffic_points[expected_idx].get_position()
            ), f"Expected index {expected_idx} for {orig_count}->{traffic_count}"

    def test_ratio_mapping_single_point_fallback(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that single-point edge cases fall back to simple clamping."""
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

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
        traffic_state = RoadTrafficState(
            multiplier=0.1,
            congestion_level=CongestionLevel.SEVERE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

        # Should fallback to clamping (index 0, the only valid index)
        point = route.next()

        assert point is not None
        assert point.get_position() == traffic_points[0].get_position()

    def test_ratio_mapping_when_traffic_increases_points(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that ratio mapping works when traffic INCREASES point count.

        When traffic gives MORE points than default, the driver's progress
        percentage should be preserved. Without this fix, the driver would
        stay at the same index (going backward in progress).
        """
        import math
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

        # Create road with 5 points
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

        # Advance to index 2 (50% through: 2/4 = 0.5)
        for _ in range(2):
            route.next()

        assert route.current_point_index == 2

        # Traffic INCREASES to 10 points
        traffic_points = [Position([0.0, i * 0.001]) for i in range(10)]
        traffic_state = RoadTrafficState(
            multiplier=0.5,
            congestion_level=CongestionLevel.MODERATE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

        # Expected mapping with ceil():
        # progress = 2 / (5-1) = 0.5
        # new_index = ceil(0.5 * (10-1)) = ceil(4.5) = 5
        expected_index = math.ceil((2 / 4) * 9)
        assert expected_index == 5  # Sanity check

        # Call next() to trigger the mapping
        point = route.next()

        # Should map to index 5 (50% - ceil gives 56%), not stay at index 2 (22%)
        assert point is not None
        assert point.get_position() == traffic_points[5].get_position()

    def test_ratio_mapping_when_traffic_clears(
        self, mock_routing_provider: Mock, test_config: dict
    ) -> None:
        """Test that ratio mapping works when traffic is cleared.

        When traffic is cleared, the point count changes back to original.
        The driver's progress should be preserved using ratio mapping.
        """
        import math
        from sim.entities.traffic_data import RoadTrafficState, CongestionLevel

        # Create road with 10 original points
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

        # Start traversal (establishes initial point count tracking)
        route.next()  # Returns point 0, index becomes 1, stores count 10

        # Apply traffic with 4 points
        traffic_points = [Position([0.0, i * 0.003]) for i in range(4)]
        traffic_state = RoadTrafficState(
            multiplier=0.5,
            congestion_level=CongestionLevel.MODERATE,
            traffic_pointcollection=traffic_points,
        )
        roads[0].set_traffic_state(traffic_state)

        # This next() call detects traffic change (10 -> 4)
        # Maps index 1 -> ceil(1/9 * 3) = ceil(0.33) = 1
        # Returns point 1, index becomes 2, stores count 4
        route.next()

        # Now current_point_index = 2 in a 4-point collection (2/3 = 67% progress)

        # Clear traffic (back to 10 points)
        roads[0].clear_traffic()

        # Expected mapping with ceil():
        # progress = 2 / (4-1) = 0.67
        # new_index = ceil(0.67 * (10-1)) = ceil(6.0) = 6
        expected_index = math.ceil((2 / 3) * 9)
        assert expected_index == 6  # Sanity check

        # Call next() to trigger the mapping
        point = route.next()

        # Should map to index 6 (67%), not stay at index 2 (22%)
        assert point is not None
        assert point.get_position() == original_points[6].get_position()

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
        assert map_index_forward(7, 10, 4) == 3

    def test_exact_progress_mapping(self):
        """Test mapping when progress is exactly representable."""
        # 50% through (index 4 of 9), maps to index 2 of 5 (50% exactly)
        # progress = 4/8 = 0.5, ceil(0.5 * 4) = ceil(2.0) = 2
        assert map_index_forward(4, 9, 5) == 2

    def test_uses_ceil_for_forward_only(self):
        """Test that ceil() is used to ensure forward-only progress."""
        # 33% through (index 3 of 10), would round to 1 but ceil gives 2
        # progress = 3/9 = 0.333, ceil(0.333 * 3) = ceil(1.0) = 1
        assert map_index_forward(3, 10, 4) == 1

        # 44% through (index 4 of 10), round would give 1, ceil gives 2
        # progress = 4/9 = 0.444, ceil(0.444 * 3) = ceil(1.33) = 2
        assert map_index_forward(4, 10, 4) == 2

    def test_at_start(self):
        """Test mapping at the start of the route."""
        assert map_index_forward(0, 10, 4) == 0

    def test_at_end(self):
        """Test mapping at the end of the route."""
        assert map_index_forward(9, 10, 4) == 3

    def test_beyond_bounds_clamps_to_max(self):
        """Test that index beyond bounds is clamped to max."""
        # Index 15 in a 10-point collection, mapping to 4 points
        # progress = 15/9 = 1.67, ceil(1.67 * 3) = ceil(5.0) = 5
        # But clamped to max valid index 3
        assert map_index_forward(15, 10, 4) == 3

    def test_single_point_old_collection(self):
        """Test fallback when old collection has single point."""
        assert map_index_forward(0, 1, 4) == 0
        assert map_index_forward(5, 1, 4) == 3  # Clamps to max

    def test_single_point_new_collection(self):
        """Test fallback when new collection has single point."""
        assert map_index_forward(5, 10, 1) == 0
        assert map_index_forward(0, 10, 1) == 0

    def test_same_size_collections(self):
        """Test mapping between same-sized collections."""
        assert map_index_forward(5, 10, 10) == 5
        assert map_index_forward(0, 10, 10) == 0
        assert map_index_forward(9, 10, 10) == 9

    def test_larger_new_collection(self):
        """Test mapping to a larger collection."""
        # 50% through (index 2 of 5), maps to 50% of 10 = index 5
        # progress = 2/4 = 0.5, ceil(0.5 * 9) = ceil(4.5) = 5
        assert map_index_forward(2, 5, 10) == 5
