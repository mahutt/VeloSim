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
import os
import json
from pathlib import Path
from typing import Generator, List
from unittest.mock import Mock
from pandas import DataFrame
from shapely.geometry import LineString

from sim.entities.route import Route
from sim.entities.position import Position
from sim.entities.road import road
from sim.osm.OSMConnection import OSMConnection


@pytest.fixture
def setup_test_environment(tmp_path: Path) -> Generator[None, None, None]:
    """
    Creates a temporary config.json for road initialization.
    """
    original_cwd = Path.cwd()

    config_data = {
        "simulation": {
            "kmh_to_ms_factor": 3.6,
            "map_rules": {"roads": {"default_road_max_speed": 30}},
        }
    }

    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    os.chdir(tmp_path)
    yield
    os.chdir(original_cwd)


@pytest.fixture
def mock_osm_connection() -> Mock:
    """
    Creates a mock OSMConnection with sample edge data.
    """
    mock_osm = Mock(spec=OSMConnection)

    # Create sample edges DataFrame
    edges_data = {
        "id": [101, 102, 103],
        "u": [1, 2, 3],
        "v": [2, 3, 4],
        "name": ["Road A", "Road B", "Road C"],
        "length": [100.0, 150.0, 200.0],
        "maxspeed": [50, 40, 60],
        "geometry": [
            LineString([(0, 0), (0, 1)]),
            LineString([(0, 1), (1, 1)]),
            LineString([(1, 1), (1, 2)]),
        ],
    }
    mock_edges_df = DataFrame(edges_data)
    mock_osm.get_all_edges.return_value = mock_edges_df

    # Provide edge index mapping (u, v) -> DataFrame index as expected
    # by Route
    edge_index = {
        (int(row["u"]), int(row["v"])): int(idx)
        for idx, row in mock_edges_df.iterrows()
    }
    mock_osm.get_edge_index.return_value = edge_index

    return mock_osm


@pytest.fixture
def sample_route_node_ids() -> List[int]:
    """
    Returns a sample list of node IDs representing a route.
    """
    return [1, 2, 3, 4]


class TestRouteCreation:
    """Tests for Route object initialization."""

    def test_route_creation_with_valid_nodes(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that a route can be created with valid node IDs."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        assert route is not None
        assert route.id > 0
        assert route.current_road_index == 0
        assert route.current_point_index == 0
        assert route.is_finished is False
        assert len(route.roads) == 3  # 4 nodes = 3 road segments

    def test_route_creation_with_empty_nodes(
        self, setup_test_environment, mock_osm_connection
    ) -> None:
        """Test that a route with no nodes is marked as finished."""
        route = Route([], mock_osm_connection)

        assert route.is_finished is True
        assert len(route.roads) == 0

    def test_route_unique_ids(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that each route gets a unique ID."""
        route1 = Route(sample_route_node_ids, mock_osm_connection)
        route2 = Route(sample_route_node_ids, mock_osm_connection)

        assert route1.id != route2.id

    def test_route_stores_start_and_end_nodes(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that route stores start and end node IDs for recalculation."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        assert route.start_node_id == 1
        assert route.end_node_id == 4

    def test_route_builds_road_segments(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that road segments are correctly built from node IDs."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        # Should create 3 road segments: (1->2), (2->3), (3->4)
        assert len(route.roads) == 3
        assert all(isinstance(r, road) for r in route.roads)
        assert route.roads[0].id == 101
        assert route.roads[1].id == 102
        assert route.roads[2].id == 103


class TestRouteSubscription:
    """Tests for route subscription to MapController."""

    def test_subscribe_to_map_controller(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that route can subscribe to a MapController."""
        route = Route(sample_route_node_ids, mock_osm_connection)
        mock_map_controller = Mock()

        route.subscribe_to_map_controller(mock_map_controller)

        assert route.map_controller == mock_map_controller
        # Should call _subscribe_route_to_road for each road segment
        assert mock_map_controller._subscribe_route_to_road.call_count == 3

    def test_unsubscribe_from_all_roads(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that route can unsubscribe from all roads."""
        route = Route(sample_route_node_ids, mock_osm_connection)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        route.unsubscribe_from_all_roads()

        # Should call _unsubscribe_route_from_road for each road segment
        assert mock_map_controller._unsubscribe_route_from_road.call_count == 3

    def test_unsubscribe_from_specific_road(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that route can unsubscribe from a specific road."""
        route = Route(sample_route_node_ids, mock_osm_connection)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        route.unsubscribe_from_road(101)

        mock_map_controller._unsubscribe_route_from_road.assert_called_with(101, route)

    def test_unsubscribe_without_map_controller(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that unsubscribe operations handle missing map_controller gracefully."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        # Should not raise an exception
        route.unsubscribe_from_all_roads()
        route.unsubscribe_from_road(101)


class TestRouteTraversal:
    """Tests for route traversal using next()."""

    def test_first_call_returns_current_and_full_route(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that first call to next() returns current position and full route."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        result = route.next(as_json=False)

        assert isinstance(result, tuple)
        current_position, full_route = result
        assert isinstance(current_position, Position)
        assert isinstance(full_route, list)
        assert all(isinstance(p, Position) for p in full_route)

    def test_subsequent_calls_return_only_position(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that subsequent calls to next() return only the position."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        # First call
        route.next(as_json=False)

        # Second call
        result = route.next(as_json=False)

        assert isinstance(result, Position)

    def test_next_json_format_first_call(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that first call with as_json=True returns proper format."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        result = route.next(as_json=True)

        assert isinstance(result, dict)
        assert "id" in result
        assert "position" in result
        assert "route" in result
        assert "coordinates" in result["route"]
        assert result["id"] == route.id

    def test_next_json_format_subsequent_calls(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that subsequent calls with as_json=True return proper format."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        # First call
        route.next(as_json=True)

        # Second call
        result = route.next(as_json=True)

        assert isinstance(result, dict)
        assert "id" in result
        assert "position" in result
        assert "route" not in result  # Only first call includes full route

    def test_traversal_moves_through_roads(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that traversal correctly moves through road segments."""
        route = Route(sample_route_node_ids, mock_osm_connection)
        initial_road_index = route.current_road_index

        # Move through all points in first road
        first_road = route.roads[0]
        num_points = len(first_road.pointcollection)

        for _ in range(num_points):
            route.next(as_json=False)

        # Should have moved to the next road
        assert route.current_road_index > initial_road_index

    def test_route_finishes_when_complete(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that route is marked as finished when all points are consumed."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        # Count total points
        total_points = sum(len(r.pointcollection) for r in route.roads)

        # Traverse all points
        for _ in range(total_points):
            _ = route.next(as_json=False)
            if route.is_finished:
                break

        assert route.is_finished is True

        # Next call should return None
        assert route.next(as_json=False) is None

    def test_route_unsubscribes_from_completed_roads(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that route unsubscribes from roads as they are completed."""
        route = Route(sample_route_node_ids, mock_osm_connection)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        # Reset mock to clear subscription calls
        mock_map_controller.reset_mock()

        # Move through all points in first road
        first_road = route.roads[0]
        num_points = len(first_road.pointcollection)

        for _ in range(num_points):
            route.next(as_json=False)

        # Should have unsubscribed from the first road
        mock_map_controller._unsubscribe_route_from_road.assert_called_with(
            first_road.id, route
        )


class TestRouteRecalculation:
    """Tests for route recalculation when roads are disabled."""

    def test_recalculate_with_valid_map_controller(
        self, setup_test_environment, sample_route_node_ids
    ) -> None:
        """Test that recalculate works with a valid map map."""
        # Create a more sophisticated mock OSM connection
        mock_osm = Mock(spec=OSMConnection)

        # Initial edges
        initial_edges_data = {
            "id": [101, 102, 103],
            "u": [1, 2, 3],
            "v": [2, 3, 4],
            "name": ["Road A", "Road B", "Road C"],
            "length": [100.0, 150.0, 200.0],
            "maxspeed": [50, 40, 60],
            "geometry": [
                LineString([(0, 0), (0, 1)]),
                LineString([(0, 1), (1, 1)]),
                LineString([(1, 1), (1, 2)]),
            ],
        }
        mock_osm.get_all_edges.return_value = DataFrame(initial_edges_data)
        # Provide edge index mapping for (u, v) -> row index
        _df = DataFrame(initial_edges_data)
        mock_osm.get_edge_index.return_value = {
            (int(row["u"]), int(row["v"])): int(idx) for idx, row in _df.iterrows()
        }

        # Mock pathfinding to return alternative route
        mock_osm.coordinates_to_nearest_node.return_value = 1
        mock_osm.get_node_by_id.return_value = {"id": 4, "x": 1, "y": 2}
        mock_osm.shortest_path.return_value = [1, 2, 4]  # Skips node 3

        route = Route(sample_route_node_ids, mock_osm)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        # Recalculate the route
        success = route.recalculate()

        assert success is True
        # Should have called shortest_path
        assert mock_osm.shortest_path.called

    def test_recalculate_unsubscribes_and_resubscribes(
        self, setup_test_environment, sample_route_node_ids
    ) -> None:
        """
        Test that recalculation unsubscribes from old roads and
        subscribes to new ones.
        """
        mock_osm = Mock(spec=OSMConnection)

        # Initial edges
        initial_edges_data = {
            "id": [101, 102, 103, 104],
            "u": [1, 2, 3, 1],
            "v": [2, 3, 4, 4],
            "name": ["Road A", "Road B", "Road C", "Road D"],
            "length": [100.0, 150.0, 200.0, 250.0],
            "maxspeed": [50, 40, 60, 50],
            "geometry": [
                LineString([(0, 0), (0, 1)]),
                LineString([(0, 1), (1, 1)]),
                LineString([(1, 1), (1, 2)]),
                LineString([(0, 0), (1, 2)]),
            ],
        }
        mock_osm.get_all_edges.return_value = DataFrame(initial_edges_data)
        _df = DataFrame(initial_edges_data)
        mock_osm.get_edge_index.return_value = {
            (int(row["u"]), int(row["v"])): int(idx) for idx, row in _df.iterrows()
        }
        mock_osm.coordinates_to_nearest_node.return_value = 1
        mock_osm.get_node_by_id.return_value = {"id": 4, "x": 1, "y": 2}
        mock_osm.shortest_path.return_value = [1, 4]  # Direct route

        route = Route(sample_route_node_ids, mock_osm)
        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        # Reset to clear initial subscription calls
        mock_map_controller.reset_mock()

        # Recalculate
        route.recalculate()

        # Should unsubscribe from all old roads (3 roads in original route)
        assert mock_map_controller._unsubscribe_route_from_road.call_count == 3
        # Should subscribe to new roads (1 road in new route)
        assert mock_map_controller._subscribe_route_to_road.call_count == 1

    def test_recalculate_preserves_route_id(
        self, setup_test_environment, sample_route_node_ids
    ) -> None:
        """Test that route ID remains the same after recalculation."""
        mock_osm = Mock(spec=OSMConnection)

        initial_edges_data = {
            "id": [101, 102, 103],
            "u": [1, 2, 3],
            "v": [2, 3, 4],
            "name": ["Road A", "Road B", "Road C"],
            "length": [100.0, 150.0, 200.0],
            "maxspeed": [50, 40, 60],
            "geometry": [
                LineString([(0, 0), (0, 1)]),
                LineString([(0, 1), (1, 1)]),
                LineString([(1, 1), (1, 2)]),
            ],
        }
        mock_osm.get_all_edges.return_value = DataFrame(initial_edges_data)
        _df = DataFrame(initial_edges_data)
        mock_osm.get_edge_index.return_value = {
            (int(row["u"]), int(row["v"])): int(idx) for idx, row in _df.iterrows()
        }
        mock_osm.coordinates_to_nearest_node.return_value = 1
        mock_osm.get_node_by_id.return_value = {"id": 4, "x": 1, "y": 2}
        mock_osm.shortest_path.return_value = [1, 2, 4]

        route = Route(sample_route_node_ids, mock_osm)
        original_id = route.id

        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        route.recalculate()
        assert route.id == original_id

    def test_recalculate_resets_traversal_state(
        self, setup_test_environment, sample_route_node_ids
    ) -> None:
        """Test that recalculation resets the traversal state."""
        mock_osm = Mock(spec=OSMConnection)

        initial_edges_data = {
            "id": [101, 102, 103],
            "u": [1, 2, 3],
            "v": [2, 3, 4],
            "name": ["Road A", "Road B", "Road C"],
            "length": [100.0, 150.0, 200.0],
            "maxspeed": [50, 40, 60],
            "geometry": [
                LineString([(0, 0), (0, 1)]),
                LineString([(0, 1), (1, 1)]),
                LineString([(1, 1), (1, 2)]),
            ],
        }
        mock_osm.get_all_edges.return_value = DataFrame(initial_edges_data)
        _df = DataFrame(initial_edges_data)
        mock_osm.get_edge_index.return_value = {
            (int(row["u"]), int(row["v"])): int(idx) for idx, row in _df.iterrows()
        }
        mock_osm.coordinates_to_nearest_node.return_value = 1
        mock_osm.get_node_by_id.return_value = {"id": 4, "x": 1, "y": 2}
        mock_osm.shortest_path.return_value = [1, 2, 4]
        route = Route(sample_route_node_ids, mock_osm)

        # Advance the route
        route.next()
        route.next()

        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        # Recalculate
        route.recalculate()

        # Traversal state should be reset
        assert route.current_road_index == 0
        assert route.current_point_index == 0

    def test_recalculate_returns_false_if_finished(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that recalculate returns False if route is already finished."""
        route = Route(sample_route_node_ids, mock_osm_connection)
        route.is_finished = True

        mock_map_controller = Mock()
        route.subscribe_to_map_controller(mock_map_controller)

        success = route.recalculate()

        assert success is False

    def test_recalculate_returns_false_without_map_controller(
        self, setup_test_environment, mock_osm_connection, sample_route_node_ids
    ) -> None:
        """Test that recalculate returns False if no map map is set."""
        route = Route(sample_route_node_ids, mock_osm_connection)

        success = route.recalculate()

        assert success is False


class TestRouteEdgeCases:
    """Tests for edge cases and error handling."""

    def test_route_with_single_node(
        self, setup_test_environment, mock_osm_connection
    ) -> None:
        """Test route creation with a single node (no edges)."""
        route = Route([1], mock_osm_connection)

        assert len(route.roads) == 0
        assert route.is_finished is True

    def test_route_with_missing_edge(
        self, setup_test_environment, sample_route_node_ids
    ) -> None:
        """Test route creation when an edge is missing from OSM data."""
        mock_osm = Mock(spec=OSMConnection)

        # Only provide edges for first two segments
        edges_data = {
            "id": [101, 102],
            "u": [1, 2],
            "v": [2, 3],
            "name": ["Road A", "Road B"],
            "length": [100.0, 150.0],
            "maxspeed": [50, 40],
            "geometry": [LineString([(0, 0), (0, 1)]), LineString([(0, 1), (1, 1)])],
        }
        mock_osm.get_all_edges.return_value = DataFrame(edges_data)
        _df = DataFrame(edges_data)
        mock_osm.get_edge_index.return_value = {
            (int(row["u"]), int(row["v"])): int(idx) for idx, row in _df.iterrows()
        }

        # This should print a warning but not crash
        route = Route(sample_route_node_ids, mock_osm)

        # Should only have 2 road segments instead of 3
        assert len(route.roads) == 2
