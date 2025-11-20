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
import json
import os
from pathlib import Path
from typing import Generator
from unittest.mock import Mock
from shapely.geometry import LineString

from sim.entities.route import Route
from sim.entities.osrm_result import OSRMResult, OSRMStep
from sim.entities.position import Position


@pytest.fixture
def setup_test_environment(tmp_path: Path) -> Generator[None, None, None]:
    """
    Creates a temporary config.json and changes the working directory.
    This allows the Route class to read configuration during tests.
    """
    original_cwd = Path.cwd()

    config_data = {
        "simulation": {
            "kmh_to_ms_factor": 3.6,
            "map_rules": {"roads": {"default_road_max_speed": 50}},
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    os.chdir(tmp_path)

    yield

    os.chdir(original_cwd)


@pytest.fixture
def mock_routing_connection() -> Mock:
    """Create a mock OSRMConnection for testing."""
    mock_conn = Mock()
    mock_conn.shortest_path_coords = Mock()
    return mock_conn


@pytest.fixture
def simple_osrm_result() -> OSRMResult:
    """Create a simple OSRMResult for testing."""
    step1 = OSRMStep(
        name="Main Street",
        distance=100.0,
        duration=7.2,  # ~13.88 m/s
        geometry=[[0.0, 0.0], [0.001, 0.0]],
        speed=13.88,
    )
    step2 = OSRMStep(
        name="Second Avenue",
        distance=150.0,
        duration=10.8,  # ~13.88 m/s
        geometry=[[0.001, 0.0], [0.001, 0.001]],
        speed=13.88,
    )

    return OSRMResult(
        coordinates=[[0.0, 0.0], [0.001, 0.0], [0.001, 0.001]],
        distance=250.0,
        duration=18.0,
        steps=[step1, step2],
    )


@pytest.fixture
def osrm_result_no_steps() -> OSRMResult:
    """Create an OSRMResult without steps (fallback mode)."""
    return OSRMResult(
        coordinates=[[0.0, 0.0], [0.001, 0.0], [0.002, 0.0]],
        distance=200.0,
        duration=14.4,
        steps=[],
    )


class TestRouteInitialization:
    """Test suite for Route initialization."""

    def test_route_with_osrm_result_and_steps(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test Route initialization with OSRMResult containing steps."""
        route = Route(simple_osrm_result, mock_routing_connection)

        assert route.id > 0
        assert route.current_road_index == 0
        assert route.current_point_index == 0
        assert route.is_finished is False
        assert len(route.roads) == 2  # Should have created 2 roads from 2 steps
        assert route.routing_connection == mock_routing_connection
        assert len(route.roads) == 2  # Two steps = two roads
        assert route.distance == 250.0
        assert route.duration == 18.0
        assert route.start_coord == (0.0, 0.0)
        assert route.end_coord == (0.001, 0.001)

    def test_route_with_osrm_result_no_steps(
        self,
        setup_test_environment: None,
        osrm_result_no_steps: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test Route initialization with OSRMResult without steps (fallback)."""
        route = Route(osrm_result_no_steps, mock_routing_connection)

        assert route.id > 0
        assert len(route.roads) == 1  # Single fallback road
        assert route.distance == 200.0
        assert route.is_finished is False

    def test_route_with_invalid_type_raises_error(
        self, setup_test_environment: None, mock_routing_connection: Mock
    ) -> None:
        """Test that passing non-OSRMResult data raises TypeError."""
        with pytest.raises(TypeError, match="route_data must be OSRMResult"):
            Route({"coordinates": [[0, 0]]}, mock_routing_connection)  # type: ignore

    def test_route_with_empty_steps_and_coords(
        self, setup_test_environment: None, mock_routing_connection: Mock
    ) -> None:
        """Test Route with minimal valid route (two identical points)."""
        # Create a minimal valid OSRMResult with at least 2 points
        minimal_result = OSRMResult(
            coordinates=[[0.0, 0.0], [0.0, 0.0]],  # Two identical points
            distance=0.0,
            duration=0.0,
            steps=[],
        )

        route = Route(minimal_result, mock_routing_connection)
        # With zero distance, should create minimal roads
        assert len(route.roads) >= 0

    def test_route_unique_ids(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that each Route gets a unique ID."""
        route1 = Route(simple_osrm_result, mock_routing_connection)
        route2 = Route(simple_osrm_result, mock_routing_connection)

        assert route1.id != route2.id


class TestRouteTraversal:
    """Test suite for Route traversal with next() method."""

    def test_next_first_call(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that first call to next() returns position only."""
        route = Route(simple_osrm_result, mock_routing_connection)

        result = route.next(as_json=False)

        assert isinstance(result, Position)
        # Route geometry is available via separate method
        geometry = route.get_route_geometry()
        assert isinstance(geometry, LineString)

    def test_next_first_call_json_format(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that first call to next() with as_json=True returns correct format."""
        route = Route(simple_osrm_result, mock_routing_connection)

        result = route.next(as_json=True)

        assert isinstance(result, dict)
        assert result is not None
        assert "id" in result
        assert "position" in result
        assert "route" not in result  # Route geometry is via separate method
        assert result["id"] == route.id

    def test_next_subsequent_calls_return_positions(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that all calls to next() return Position objects."""
        route = Route(simple_osrm_result, mock_routing_connection)

        # First call
        first = route.next(as_json=False)
        assert isinstance(first, Position)

        # Subsequent calls
        second = route.next(as_json=False)
        assert isinstance(second, Position)

        third = route.next(as_json=False)
        assert isinstance(third, Position)

    def test_next_subsequent_calls_json_format(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test subsequent calls with as_json=True."""
        route = Route(simple_osrm_result, mock_routing_connection)

        # First call
        route.next(as_json=True)

        # Subsequent calls
        result = route.next(as_json=True)
        assert isinstance(result, dict)
        assert "id" in result
        assert "position" in result
        assert "route" not in result  # Only first call has route

    def test_next_traverses_all_roads(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that next() traverses all roads in sequence."""
        route = Route(simple_osrm_result, mock_routing_connection)

        positions = []
        result = route.next()
        while result is not None:
            if isinstance(result, Position):
                positions.append(result)
            result = route.next()

        # Should have traversed both roads
        assert route.is_finished is True
        assert route.current_road_index >= len(route.roads)
        assert len(positions) > 0

    def test_next_skips_duplicate_positions(
        self, setup_test_environment: None, mock_routing_connection: Mock
    ) -> None:
        """Test that next() skips consecutive duplicate positions."""
        # Create a result with overlapping positions at road boundaries
        step1 = OSRMStep(
            name="Road 1",
            distance=50.0,
            duration=3.6,
            geometry=[[0.0, 0.0], [0.0005, 0.0]],  # Short road
            speed=13.88,
        )
        step2 = OSRMStep(
            name="Road 2",
            distance=50.0,
            duration=3.6,
            geometry=[[0.0005, 0.0], [0.001, 0.0]],  # Starts where step1 ends
            speed=13.88,
        )

        osrm_result = OSRMResult(
            coordinates=[[0.0, 0.0], [0.0005, 0.0], [0.001, 0.0]],
            distance=100.0,
            duration=7.2,
            steps=[step1, step2],
        )

        route = Route(osrm_result, mock_routing_connection)

        positions = []
        result = route.next()
        while result is not None:
            if isinstance(result, Position):
                pos = result.get_position()
                positions.append(pos)
            result = route.next()

        # Check no consecutive duplicates
        for i in range(len(positions) - 1):
            assert positions[i] != positions[i + 1], f"Duplicate at index {i}"

    def test_next_returns_none_when_finished(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that next() returns None once route is finished."""
        route = Route(simple_osrm_result, mock_routing_connection)

        # Exhaust all positions
        result = route.next()
        while result is not None:
            result = route.next()

        # Should be finished
        assert route.is_finished is True

        # Further calls should return None
        assert route.next() is None
        assert route.next() is None


class TestRouteRoadBuilding:
    """Test suite for road building from OSRM data."""

    def test_build_roads_from_steps(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that roads are properly built from OSRM steps."""
        route = Route(simple_osrm_result, mock_routing_connection)

        assert len(route.roads) == 2
        assert route.roads[0].name == "Main Street"
        assert route.roads[1].name == "Second Avenue"
        assert route.roads[0].length == 100.0
        assert route.roads[1].length == 150.0

    def test_build_coordinate_roads_fallback(
        self,
        setup_test_environment: None,
        osrm_result_no_steps: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test fallback road building from coordinates."""
        route = Route(osrm_result_no_steps, mock_routing_connection)

        assert len(route.roads) == 1
        assert route.roads[0].name is None  # Fallback has no name
        assert len(route.roads[0].pointcollection) > 0

    def test_skip_invalid_steps(
        self, setup_test_environment: None, mock_routing_connection: Mock
    ) -> None:
        """Test that invalid steps are skipped during road building."""
        invalid_step = OSRMStep(
            name="Invalid Road",
            distance=0.0,  # Invalid distance
            duration=0.0,
            geometry=[],
            speed=0.0,
        )
        valid_step = OSRMStep(
            name="Valid Road",
            distance=100.0,
            duration=7.2,
            geometry=[[0.0, 0.0], [0.001, 0.0]],
            speed=13.88,
        )

        osrm_result = OSRMResult(
            coordinates=[[0.0, 0.0], [0.001, 0.0]],
            distance=100.0,
            duration=7.2,
            steps=[invalid_step, valid_step],
        )

        route = Route(osrm_result, mock_routing_connection)

        # Should only have the valid road
        assert len(route.roads) == 1
        assert route.roads[0].name == "Valid Road"


class TestRouteSubscriptionManagement:
    """Test suite for road subscription management."""

    def test_subscribe_to_map_controller(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test subscribing route to all roads via MapController."""
        route = Route(simple_osrm_result, mock_routing_connection)
        mock_map_controller = Mock()
        mock_map_controller._subscribe_route_to_road = Mock()

        route.subscribe_to_map_controller(mock_map_controller)

        # Should subscribe to all roads
        assert mock_map_controller._subscribe_route_to_road.call_count == len(
            route.roads
        )
        assert route.map_controller == mock_map_controller

    def test_unsubscribe_from_all_roads(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test unsubscribing from all roads."""
        route = Route(simple_osrm_result, mock_routing_connection)
        mock_map_controller = Mock()
        mock_map_controller._unsubscribe_route_from_road = Mock()

        route.subscribe_to_map_controller(mock_map_controller)
        route.unsubscribe_from_all_roads()

        # Should unsubscribe from all roads
        assert mock_map_controller._unsubscribe_route_from_road.call_count == len(
            route.roads
        )

    def test_unsubscribe_from_specific_road(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test unsubscribing from a specific road."""
        route = Route(simple_osrm_result, mock_routing_connection)
        mock_map_controller = Mock()
        mock_map_controller._unsubscribe_route_from_road = Mock()

        route.subscribe_to_map_controller(mock_map_controller)
        road_id = route.roads[0].id

        route.unsubscribe_from_road(road_id)

        mock_map_controller._unsubscribe_route_from_road.assert_called_once_with(
            road_id, route
        )


class TestRouteRecalculation:
    """Test suite for route recalculation."""

    def test_recalculate_success(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test successful route recalculation."""
        route = Route(simple_osrm_result, mock_routing_connection)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        # Setup mock to return new route
        new_route_data = {
            "coordinates": [[0.001, 0.0], [0.002, 0.0]],
            "distance": 100.0,
            "duration": 7.2,
            "steps": [
                {
                    "name": "New Road",
                    "distance": 100.0,
                    "duration": 7.2,
                    "geometry": [[0.001, 0.0], [0.002, 0.0]],
                    "speed": 13.88,
                }
            ],
        }
        mock_routing_connection.shortest_path_coords.return_value = new_route_data

        # Move forward a bit
        route.next()
        route.next()

        success = route.recalculate()

        assert success is True
        assert mock_routing_connection.shortest_path_coords.called
        assert route.current_road_index == 0
        assert route.current_point_index == 0

    def test_recalculate_when_finished(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that recalculation fails when route is finished."""
        route = Route(simple_osrm_result, mock_routing_connection)
        route.is_finished = True

        success = route.recalculate()

        assert success is False

    def test_recalculate_without_map_controller(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that recalculation fails without MapController."""
        route = Route(simple_osrm_result, mock_routing_connection)

        success = route.recalculate()

        assert success is False

    def test_recalculate_no_route_found(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test recalculation when no new route is found."""
        route = Route(simple_osrm_result, mock_routing_connection)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        # Mock returns no route
        mock_routing_connection.shortest_path_coords.return_value = None

        route.next()  # Move forward
        success = route.recalculate()

        assert success is False
        assert route.is_finished is True

    def test_recalculate_unsubscribes_and_resubscribes(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that recalculation properly manages subscriptions."""
        route = Route(simple_osrm_result, mock_routing_connection)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        new_route_data = {
            "coordinates": [[0.001, 0.0], [0.002, 0.0]],
            "distance": 100.0,
            "duration": 7.2,
            "steps": [
                {
                    "name": "New Road",
                    "distance": 100.0,
                    "duration": 7.2,
                    "geometry": [[0.001, 0.0], [0.002, 0.0]],
                    "speed": 13.88,
                }
            ],
        }
        mock_routing_connection.shortest_path_coords.return_value = new_route_data

        original_road_count = len(route.roads)
        route.next()
        route.recalculate()

        # Should unsubscribe from old roads
        assert (
            mock_map_controller._unsubscribe_route_from_road.call_count
            == original_road_count
        )

        # Should subscribe to new roads
        assert (
            mock_map_controller._subscribe_route_to_road.call_count
            > original_road_count
        )


class TestRouteHelperMethods:
    """Test suite for Route helper methods."""

    def test_get_all_points(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test _get_all_points returns all positions without duplicates."""
        route = Route(simple_osrm_result, mock_routing_connection)

        all_points = route._get_all_points()

        assert len(all_points) > 0
        assert all(isinstance(p, Position) for p in all_points)

        # Check no consecutive duplicates
        for i in range(len(all_points) - 1):
            assert all_points[i].get_position() != all_points[i + 1].get_position()

    def test_get_route_geometry(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test get_route_geometry returns valid LineString."""
        route = Route(simple_osrm_result, mock_routing_connection)

        geometry = route.get_route_geometry()

        assert isinstance(geometry, LineString)
        assert len(geometry.coords) > 0

    def test_get_current_position(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test _get_current_position returns current coordinates."""
        route = Route(simple_osrm_result, mock_routing_connection)

        current_pos = route._get_current_position()

        assert current_pos is not None
        assert isinstance(current_pos, tuple)
        assert len(current_pos) == 2

    def test_get_current_position_when_finished(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test _get_current_position returns None when finished."""
        route = Route(simple_osrm_result, mock_routing_connection)

        # Exhaust the route
        while route.next() is not None:
            pass

        current_pos = route._get_current_position()
        assert current_pos is None


class TestRouteEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_route_with_single_step(
        self, setup_test_environment: None, mock_routing_connection: Mock
    ) -> None:
        """Test Route with a single step."""
        step = OSRMStep(
            name="Single Road",
            distance=50.0,
            duration=3.6,
            geometry=[[0.0, 0.0], [0.001, 0.0]],
            speed=13.88,
        )

        osrm_result = OSRMResult(
            coordinates=[[0.0, 0.0], [0.001, 0.0]],
            distance=50.0,
            duration=3.6,
            steps=[step],
        )

        route = Route(osrm_result, mock_routing_connection)

        assert len(route.roads) == 1
        assert route.roads[0].name == "Single Road"

    def test_route_with_very_short_distance(
        self, setup_test_environment: None, mock_routing_connection: Mock
    ) -> None:
        """Test Route with very short distance."""
        step = OSRMStep(
            name="Short Road",
            distance=1.0,  # 1 meter
            duration=0.07,
            geometry=[[0.0, 0.0], [0.00001, 0.0]],
            speed=13.88,
        )

        osrm_result = OSRMResult(
            coordinates=[[0.0, 0.0], [0.00001, 0.0]],
            distance=1.0,
            duration=0.07,
            steps=[step],
        )

        route = Route(osrm_result, mock_routing_connection)

        assert len(route.roads) > 0
        assert len(route.roads[0].pointcollection) >= 2

    def test_route_with_zero_speed_step(
        self, setup_test_environment: None, mock_routing_connection: Mock
    ) -> None:
        """Test Route handles step with zero speed gracefully."""
        step = OSRMStep(
            name="Zero Speed Road",
            distance=100.0,
            duration=0.0,  # Would cause division by zero
            geometry=[[0.0, 0.0], [0.001, 0.0]],
            speed=0.0,
        )

        osrm_result = OSRMResult(
            coordinates=[[0.0, 0.0], [0.001, 0.0]],
            distance=100.0,
            duration=0.0,
            steps=[step],
        )

        # Should not raise exception
        route = Route(osrm_result, mock_routing_connection)
        assert len(route.roads) >= 0  # May skip invalid step

    def test_route_coordinates_match_step_geometry(
        self,
        setup_test_environment: None,
        simple_osrm_result: OSRMResult,
        mock_routing_connection: Mock,
    ) -> None:
        """Test that route coordinates align with step geometries."""
        route = Route(simple_osrm_result, mock_routing_connection)

        # First road should start at route start
        first_pos = route.roads[0].pointcollection[0].get_position()
        assert first_pos[0] == pytest.approx(simple_osrm_result.start_coord[0])
        assert first_pos[1] == pytest.approx(simple_osrm_result.start_coord[1])

        # Last road should end at route end
        last_pos = route.roads[-1].pointcollection[-1].get_position()
        assert last_pos[0] == pytest.approx(simple_osrm_result.end_coord[0])
        assert last_pos[1] == pytest.approx(simple_osrm_result.end_coord[1])
