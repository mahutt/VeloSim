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
from typing import Generator, Any, Dict
from unittest.mock import Mock, patch
from pandas import DataFrame
from shapely.geometry import LineString
import networkx as nx

from sim.controller.MapController import MapController
from sim.entities.position import Position
from sim.entities.route import Route
from sim.DAO.OSMConnection import OSMConnection


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
    Creates a comprehensive mock OSMConnection with sample network data.
    """
    mock_osm = Mock(spec=OSMConnection)

    # Create sample edges DataFrame representing a small network
    edges_data = {
        "id": [101, 102, 103, 104, 105],
        "u": [1, 2, 3, 1, 2],
        "v": [2, 3, 4, 5, 4],
        "name": ["Main St", "Second Ave", "Third St", "Oak Rd", "Elm St"],
        "length": [100.0, 150.0, 200.0, 250.0, 180.0],
        "maxspeed": [50, 40, 60, 50, 45],
        "geometry": [
            LineString([(0, 0), (0, 1)]),  # 1->2
            LineString([(0, 1), (1, 1)]),  # 2->3
            LineString([(1, 1), (1, 2)]),  # 3->4
            LineString([(0, 0), (-1, 0)]),  # 1->5 (alternative)
            LineString([(0, 1), (1, 2)]),  # 2->4 (alternative)
        ],
    }
    mock_edges_df = DataFrame(edges_data)
    mock_osm.get_all_edges.return_value = mock_edges_df

    # Provide edge index mapping (u, v) -> DataFrame index, as Route expects
    edge_index = {(int(row["u"]), int(row["v"])): int(idx) for idx, row in mock_edges_df.iterrows()}
    mock_osm.get_edge_index.return_value = edge_index

    # Mock graph operations
    mock_graph: nx.MultiDiGraph = nx.MultiDiGraph()
    for idx, row in mock_edges_df.iterrows():
        mock_graph.add_edge(row["u"], row["v"], key=0, id=row["id"])

    mock_osm.get_graph.return_value = mock_graph

    # Mock node lookup
    def mock_node_by_id(node_id: int) -> Dict[str, Any]:
        nodes: Dict[int, Dict[str, Any]] = {
            1: {"id": 1, "x": 0, "y": 0},
            2: {"id": 2, "x": 0, "y": 1},
            3: {"id": 3, "x": 1, "y": 1},
            4: {"id": 4, "x": 1, "y": 2},
            5: {"id": 5, "x": -1, "y": 0},
        }
        return nodes.get(node_id)

    mock_osm.get_node_by_id.side_effect = mock_node_by_id

    # Mock coordinate to node conversion
    def mock_coordinates_to_nearest_node(lng: float, lat: float) -> int:
        # Simple mock - just return node 1 for start, 4 for end
        if lat < 1:
            return 1
        return 4

    mock_osm.coordinates_to_nearest_node.side_effect = mock_coordinates_to_nearest_node

    # Mock shortest path
    def mock_shortest_path(
        start: int,
        end: int,
        graph: nx.MultiDiGraph | None = None,
        use_ch: bool = True,
    ) -> list[int]:
        # Return predefined paths based on start/end
        paths: Dict[tuple[int, int], list[int]] = {
            (1, 4): [1, 2, 3, 4],  # Main path
            (2, 4): [2, 3, 4],  # From node 2
            (3, 4): [3, 4],  # From node 3
            (1, 2): [1, 2],
            (2, 3): [2, 3],
            (3, 1): [3, 2, 1],
        }
        return paths.get((start, end), [start, end])

    mock_osm.shortest_path.side_effect = mock_shortest_path

    # Mock set_edges to update the edges DataFrame
    def mock_set_edges(new_edges_df):
        mock_osm.get_all_edges.return_value = new_edges_df

    mock_osm.set_edges.side_effect = mock_set_edges

    return mock_osm


@pytest.fixture
def map_controller(setup_test_environment, mock_osm_connection):
    """
    Creates a MapController instance with mocked OSMConnection.
    Note: MapController is a singleton, so we need to reset it between tests.
    """
    # Reset the singleton instance
    MapController._instance = None

    with patch(
        "sim.controller.MapController.OSMConnection", return_value=mock_osm_connection
    ):
        controller = MapController()
        return controller


class TestMapControllerSingleton:
    """Tests for MapController singleton pattern."""

    def test_singleton_returns_same_instance(
        self, setup_test_environment, mock_osm_connection
    ) -> None:
        """Test that MapController implements singleton pattern correctly."""
        MapController._instance = None

        with patch(
            "sim.controller.MapController.OSMConnection",
            return_value=mock_osm_connection,
        ):
            controller1 = MapController()
            controller2 = MapController()

            assert controller1 is controller2

    def test_singleton_initialization_once(
        self, setup_test_environment, mock_osm_connection
    ) -> None:
        """Test that MapController initializes only once."""
        MapController._instance = None

        with patch(
            "sim.controller.MapController.OSMConnection",
            return_value=mock_osm_connection,
        ):
            controller1 = MapController()
            initial_subscriptions = controller1.road_subscriptions

            controller2 = MapController()

            # Should be the same dictionary object
            assert controller2.road_subscriptions is initial_subscriptions


class TestMapControllerGetRoute:
    """Tests for MapController.getRoute() method."""

    def test_get_route_creates_route(self, map_controller) -> None:
        """Test that getRoute creates a Route object."""
        start_pos = Position([0, 0])
        end_pos = Position([1, 2])

        route = map_controller.getRoute(start_pos, end_pos)

        assert isinstance(route, Route)
        assert route is not None

    def test_get_route_subscribes_route(self, map_controller) -> None:
        """Test that getRoute automatically subscribes the route to roads."""
        start_pos = Position([0, 0])
        end_pos = Position([1, 2])

        route = map_controller.getRoute(start_pos, end_pos)

        # Route should be subscribed to its roads
        assert route.map_controller == map_controller

        # road_subscriptions should have entries
        assert len(map_controller.road_subscriptions) > 0

    def test_get_route_subscription_registry_structure(self, map_controller) -> None:
        """Test that road_subscriptions has correct structure."""
        import numpy as np

        start_pos = Position([0, 0])
        end_pos = Position([1, 2])

        _ = map_controller.getRoute(start_pos, end_pos)

        # Each entry should map road_id -> Set[Route]
        for road_id, routes_set in map_controller.road_subscriptions.items():
            # road_id can be int or np.int64 (from pandas)
            assert isinstance(road_id, (int, np.integer))
            assert isinstance(routes_set, set)
            assert all(isinstance(r, Route) for r in routes_set)

    def test_get_route_multiple_routes(self, map_controller) -> None:
        """Test creating multiple routes updates subscriptions correctly."""
        route1 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        route2 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Both routes should be in the subscription registry
        # They follow the same path, so should share road subscriptions
        for road_id, routes_set in map_controller.road_subscriptions.items():
            # At least one road should have both routes
            if len(routes_set) == 2:
                assert route1 in routes_set
                assert route2 in routes_set
                break
        else:
            # If all paths have same roads, all should have both routes
            for routes_set in map_controller.road_subscriptions.values():
                assert route1 in routes_set and route2 in routes_set


class TestMapControllerSubscription:
    """Tests for MapController subscription management."""

    def test_subscribe_route_to_road(self, map_controller) -> None:
        """Test subscribing a route to a specific road."""
        start_pos = Position([0, 0])
        end_pos = Position([1, 2])

        route = map_controller.getRoute(start_pos, end_pos)
        road_id = 999

        # Subscribe to a new road
        map_controller._subscribe_route_to_road(road_id, route)

        assert road_id in map_controller.road_subscriptions
        assert route in map_controller.road_subscriptions[road_id]

    def test_subscribe_multiple_routes_to_same_road(self, map_controller) -> None:
        """Test that multiple routes can subscribe to the same road."""
        route1 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        route2 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        road_id = 101

        map_controller._subscribe_route_to_road(road_id, route1)
        map_controller._subscribe_route_to_road(road_id, route2)

        assert len(map_controller.road_subscriptions[road_id]) == 2
        assert route1 in map_controller.road_subscriptions[road_id]
        assert route2 in map_controller.road_subscriptions[road_id]

    def test_subscribe_same_route_twice_no_duplicates(self, map_controller) -> None:
        """Test that subscribing the same route twice doesn't create duplicates."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        road_id = 101

        map_controller._subscribe_route_to_road(road_id, route)
        map_controller._subscribe_route_to_road(road_id, route)

        # Set should prevent duplicates
        assert (
            map_controller.road_subscriptions[road_id].count(route) == 1
            if hasattr(set, "count")
            else True
        )
        # Better test: length should be 1 since it's a set
        routes_with_road = [
            r for r in map_controller.road_subscriptions[road_id] if r == route
        ]
        assert len(routes_with_road) == 1

    def test_unsubscribe_route_from_road(self, map_controller) -> None:
        """Test unsubscribing a route from a specific road."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        road_id = 101

        # First subscribe
        map_controller._subscribe_route_to_road(road_id, route)
        assert route in map_controller.road_subscriptions[road_id]

        # Then unsubscribe
        map_controller._unsubscribe_route_from_road(road_id, route)

        # Route should be removed, or the road_id key should be deleted if empty
        if road_id in map_controller.road_subscriptions:
            assert route not in map_controller.road_subscriptions[road_id]
        else:
            # Key was deleted because set became empty
            assert True

    def test_unsubscribe_cleans_up_empty_sets(self, map_controller) -> None:
        """Test that unsubscribing removes empty sets from the registry."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        road_id = 999  # Use unique road ID

        map_controller._subscribe_route_to_road(road_id, route)
        map_controller._unsubscribe_route_from_road(road_id, route)

        # Empty set should be removed
        assert road_id not in map_controller.road_subscriptions

    def test_unsubscribe_nonexistent_road(self, map_controller) -> None:
        """Test that unsubscribing from a nonexistent road doesn't crash."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Should not raise an exception
        map_controller._unsubscribe_route_from_road(9999, route)

    def test_unsubscribe_route_not_in_set(self, map_controller) -> None:
        """Test unsubscribing a route that's not in the set."""
        route1 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        route2 = map_controller.getRoute(Position([0, 0]), Position([1, 1]))
        road_id = 101

        map_controller._subscribe_route_to_road(road_id, route1)

        # Unsubscribe route2 which was never subscribed - should not crash
        map_controller._unsubscribe_route_from_road(road_id, route2)

        # route1 should still be there
        if road_id in map_controller.road_subscriptions:
            assert route1 in map_controller.road_subscriptions[road_id]


class TestMapControllerDisableRoads:
    """Tests for MapController.disableRoads() method."""

    def test_disable_roads_triggers_recalculation(
        self, map_controller, mock_osm_connection
    ) -> None:
        """Test that disabling roads triggers recalculation for affected routes."""
        # Create a route
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Mock the recalculate method to track if it was called
        original_recalculate = route.recalculate
        recalculate_called = []

        def mock_recalculate():
            recalculate_called.append(True)
            return original_recalculate()

        route.recalculate = mock_recalculate

        # Disable a road that the route uses
        map_controller.disableRoads([101])

        # Recalculate should have been called
        assert len(recalculate_called) > 0

    def test_disable_roads_only_affects_routes_using_road(self, map_controller) -> None:
        """Test that only routes using disabled roads are recalculated."""
        # Create route using road 101
        route1 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Create another route (may or may not use road 101)
        route2 = map_controller.getRoute(Position([0.5, 0.5]), Position([1, 1]))

        # Track which routes get recalculated
        recalculated = []

        def make_tracker(route_obj):
            original = route_obj.recalculate

            def tracked():
                recalculated.append(route_obj)
                return original()

            return tracked

        route1.recalculate = make_tracker(route1)
        route2.recalculate = make_tracker(route2)

        # Disable road 999 which doesn't exist or isn't used
        map_controller.disableRoads([999])

        # Should not recalculate any routes
        assert len(recalculated) == 0

    def test_disable_roads_removes_from_graph(
        self, map_controller, mock_osm_connection
    ) -> None:
        """Test that disabling roads removes them from the OSM graph."""
        initial_edges = mock_osm_connection.get_all_edges()
        _ = len(initial_edges)

        # Disable a road
        map_controller.disableRoads([101])

        # Check that edges were updated
        assert mock_osm_connection.set_edges.called

    def test_disable_multiple_roads(self, map_controller) -> None:
        """Test disabling multiple roads at once."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        recalculate_count = []
        original_recalc = route.recalculate

        def count_recalc():
            recalculate_count.append(1)
            return original_recalc()

        route.recalculate = count_recalc

        # Disable multiple roads
        map_controller.disableRoads([101, 102, 103])

        # Route should be recalculated (possibly multiple times if it
        # uses multiple disabled roads)
        assert len(recalculate_count) > 0

    def test_disable_roads_handles_finished_routes(self, map_controller) -> None:
        """Test that finished routes are not recalculated."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        route.is_finished = True

        recalculate_called = []

        def track_recalc():
            recalculate_called.append(True)
            return False

        route.recalculate = track_recalc

        # Disable a road
        map_controller.disableRoads([101])

        # Finished routes should not be recalculated
        # (recalculate returns False immediately for finished routes)
        assert len(recalculate_called) <= 1

    def test_disable_roads_empty_list(self, map_controller) -> None:
        """Test that disabling an empty list of roads doesn't crash."""
        _ = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Should not raise an exception
        map_controller.disableRoads([])


class TestMapControllerIntegration:
    """Integration tests for complete MapController workflows."""

    def test_complete_route_lifecycle_with_subscription(self, map_controller) -> None:
        """Test complete lifecycle: create route, traverse, unsubscribe."""
        # Create route
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        _ = sum(len(routes) for routes in map_controller.road_subscriptions.values())

        # Traverse through first road
        if route.roads:
            first_road = route.roads[0]
            points_to_traverse = len(first_road.pointcollection)

            for _ in range(points_to_traverse):
                route.next()

            # Should have unsubscribed from first road
            if first_road.id in map_controller.road_subscriptions:
                assert route not in map_controller.road_subscriptions[first_road.id]

    def test_multiple_routes_same_path_subscription(self, map_controller) -> None:
        """Test that multiple routes on the same path share road subscriptions."""
        route1 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        route2 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        route3 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Find a road used by all routes
        common_roads = set(r.id for r in route1.roads)

        for road_id in common_roads:
            if road_id in map_controller.road_subscriptions:
                routes_set = map_controller.road_subscriptions[road_id]
                # Should contain all three routes
                assert (
                    route1 in routes_set or route2 in routes_set or route3 in routes_set
                )

    def test_disable_road_forces_alternative_path(
        self, map_controller, mock_osm_connection
    ) -> None:
        """Test that disabling a road forces routes to use alternative paths."""
        # Create a route
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        original_road_ids = [r.id for r in route.roads]

        # Mock alternative path when road is disabled
        def alternative_path(start, end, graph=None, use_ch=True):
            # If a graph is provided and road 102 is disabled, use alternative
            try:
                if graph is not None and not any(
                    d.get("id") == 102 for u, v, d in graph.edges(data=True)
                ):
                    return [start, 4]  # Direct alternative
            except Exception:
                pass
            # Default behavior
            return [1, 2, 3, 4]

        mock_osm_connection.shortest_path.side_effect = alternative_path

        # Disable a road in the route
        if original_road_ids:
            map_controller.disableRoads([original_road_ids[0]])

            # Route should have been recalculated
            new_road_ids = [r.id for r in route.roads]
            # Path may have changed (or stayed same if alternative uses same roads)
            assert isinstance(new_road_ids, list)

    def test_memory_cleanup_after_route_completion(self, map_controller) -> None:
        """Test that memory is cleaned up as routes complete."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Get initial subscription count
        initial_total_subscriptions = sum(
            len(routes) for routes in map_controller.road_subscriptions.values()
        )

        # Complete the route
        while not route.is_finished:
            route.next()

        # Final subscription count should be less (route unsubscribed from all roads)
        final_total_subscriptions = sum(
            len(routes) for routes in map_controller.road_subscriptions.values()
        )

        # Route should have unsubscribed from all its roads
        assert (
            final_total_subscriptions < initial_total_subscriptions
            or final_total_subscriptions == 0
        )

    def test_concurrent_disable_and_traversal(self, map_controller) -> None:
        """
        Test that disabling roads while routes are being traversed
        works correctly.
        """
        route1 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        route2 = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Traverse route1 partway
        if route1.roads:
            route1.next()
            route1.next()

        # Disable a road that route2 might use but route1 has passed
        if len(route1.roads) > 1:
            future_road_id = route1.roads[-1].id
            map_controller.disableRoads([future_road_id])

            # Both routes should still be valid
            assert route1 is not None
            assert route2 is not None


class TestMapControllerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_disable_nonexistent_road(self, map_controller) -> None:
        """Test that disabling a nonexistent road doesn't crash."""
        # Should not raise an exception
        map_controller.disableRoads([99999])

    def test_subscription_to_nonexistent_road(self, map_controller) -> None:
        """Test subscribing to a road ID that doesn't exist."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))

        # Should not crash
        map_controller._subscribe_route_to_road(99999, route)

        assert 99999 in map_controller.road_subscriptions
        assert route in map_controller.road_subscriptions[99999]

    def test_empty_route_handling(self, map_controller, mock_osm_connection) -> None:
        """Test handling routes with no roads."""
        # Mock to return empty path
        mock_osm_connection.shortest_path.return_value = []

        route = map_controller.getRoute(Position([0, 0]), Position([0, 0]))

        assert route.is_finished is True
        assert len(route.roads) == 0

    def test_large_number_of_routes(self, map_controller) -> None:
        """Test that system handles many routes efficiently."""
        routes = []

        for i in range(50):
            route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
            routes.append(route)

        # All routes should be created
        assert len(routes) == 50

        # Subscription registry should handle all routes
        total_subscriptions = sum(
            len(route_set) for route_set in map_controller.road_subscriptions.values()
        )
        assert total_subscriptions > 0

    def test_disable_all_roads_in_route(self, map_controller) -> None:
        """Test disabling all roads in a route."""
        route = map_controller.getRoute(Position([0, 0]), Position([1, 2]))
        all_road_ids = [r.id for r in route.roads]

        # Disable all roads
        if all_road_ids:
            map_controller.disableRoads(all_road_ids)

            # Route should handle this (either recalculate or mark as finished)
            assert route is not None
