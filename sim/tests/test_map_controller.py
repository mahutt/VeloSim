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

from sim.map.MapController import MapController
from sim.entities.position import Position
from sim.entities.route import Route


@pytest.fixture
def mock_osrm() -> Mock:
    """Create a mock OSRM connection."""
    osrm = Mock()
    osrm.shortest_path_coords.return_value = {
        "coordinates": [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]],
        "distance": 300.0,
        "duration": 180.0,
    }
    return osrm


@pytest.fixture
def mock_route() -> Mock:
    """Create a mock Route object."""
    route = Mock(spec=Route)
    route.id = 1
    route.is_finished = False
    route.recalculate.return_value = True
    route.subscribe_to_map_controller = Mock()
    return route


class TestMapControllerSingleton:
    """Test MapController singleton pattern."""

    def test_singleton_returns_same_instance(self) -> None:
        """Test that MapController returns the same instance."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection") as mock_osrm_class:
            mock_osrm_class.return_value = Mock()

            mc1 = MapController()
            mc2 = MapController()

            assert mc1 is mc2
            assert mock_osrm_class.call_count == 1

    def test_singleton_initialization_once(self) -> None:
        """Test that initialization only happens once."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection") as mock_osrm_class:
            mock_osrm_class.return_value = Mock()

            MapController()
            MapController()

            assert mock_osrm_class.call_count == 1


class TestMapControllerInitialization:
    """Test MapController initialization."""

    def test_initialization_creates_osrm_connection(self) -> None:
        """Test that initialization creates an OSRM connection."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection") as mock_osrm_class:
            mock_osrm_class.return_value = Mock()

            mc = MapController()

            mock_osrm_class.assert_called_once_with(osrm_url=None)
            assert hasattr(mc, "osrm")
            assert hasattr(mc, "road_subscriptions")

    def test_initialization_with_custom_osrm_url(self) -> None:
        """Test initialization with custom OSRM URL."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection") as mock_osrm_class:
            mock_osrm_class.return_value = Mock()

            MapController(osrm_url="http://custom-osrm:5000")

            mock_osrm_class.assert_called_once_with(osrm_url="http://custom-osrm:5000")


class TestMapControllerGetRoute:
    """Test MapController.getRoute() functionality."""

    def test_get_route_creates_route(self, mock_osrm: Mock) -> None:
        """Test that getRoute creates a Route object."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            with patch("sim.map.MapController.Route") as mock_route_class:
                mock_route = Mock(spec=Route)
                mock_route_class.return_value = mock_route

                mc = MapController()
                pos_a = Mock(spec=Position)
                pos_a.get_position.return_value = (0.0, 0.0)
                pos_b = Mock(spec=Position)
                pos_b.get_position.return_value = (2.0, 2.0)

                route = mc.getRoute(pos_a, pos_b)

                mock_osrm.shortest_path_coords.assert_called_once_with(
                    0.0, 0.0, 2.0, 2.0
                )

                mock_route_class.assert_called_once()
                assert route == mock_route

    def test_get_route_subscribes_route(self, mock_osrm: Mock) -> None:
        """Test that getRoute subscribes the route to MapController."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            with patch("sim.map.MapController.Route") as mock_route_class:
                mock_route = Mock(spec=Route)
                mock_route_class.return_value = mock_route

                mc = MapController()
                pos_a = Mock(spec=Position)
                pos_a.get_position.return_value = (0.0, 0.0)
                pos_b = Mock(spec=Position)
                pos_b.get_position.return_value = (2.0, 2.0)

                mc.getRoute(pos_a, pos_b)

                mock_route.subscribe_to_map_controller.assert_called_once_with(mc)

    def test_get_route_no_route_found_raises_error(self, mock_osrm: Mock) -> None:
        """Test that getRoute raises error when no route is found."""
        MapController._instance = None
        mock_osrm.shortest_path_coords.return_value = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            pos_a = Mock(spec=Position)
            pos_a.get_position.return_value = (0.0, 0.0)
            pos_b = Mock(spec=Position)
            pos_b.get_position.return_value = (2.0, 2.0)

            with pytest.raises(ValueError, match="No route found"):
                mc.getRoute(pos_a, pos_b)


class TestMapControllerSubscription:
    """Test MapController subscription management."""

    def test_subscribe_route_to_road(self, mock_osrm: Mock, mock_route: Mock) -> None:
        """Test subscribing a route to a road."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            mc._subscribe_route_to_road(101, mock_route)

            assert 101 in mc.road_subscriptions
            assert mock_route in mc.road_subscriptions[101]

    def test_subscribe_multiple_routes_to_same_road(self, mock_osrm: Mock) -> None:
        """Test subscribing multiple routes to the same road."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route1 = Mock(spec=Route)
            route2 = Mock(spec=Route)

            mc._subscribe_route_to_road(101, route1)
            mc._subscribe_route_to_road(101, route2)

            assert len(mc.road_subscriptions[101]) == 2
            assert route1 in mc.road_subscriptions[101]
            assert route2 in mc.road_subscriptions[101]

    def test_unsubscribe_route_from_road(
        self, mock_osrm: Mock, mock_route: Mock
    ) -> None:
        """Test unsubscribing a route from a road."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            mc._subscribe_route_to_road(101, mock_route)
            mc._unsubscribe_route_from_road(101, mock_route)

            assert 101 not in mc.road_subscriptions

    def test_unsubscribe_cleans_up_empty_sets(self, mock_osrm: Mock) -> None:
        """Test that unsubscribing removes empty road subscription sets."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route1 = Mock(spec=Route)
            route2 = Mock(spec=Route)

            mc._subscribe_route_to_road(101, route1)
            mc._subscribe_route_to_road(101, route2)
            mc._unsubscribe_route_from_road(101, route1)

            assert 101 in mc.road_subscriptions
            assert route2 in mc.road_subscriptions[101]

            mc._unsubscribe_route_from_road(101, route2)

            assert 101 not in mc.road_subscriptions


class TestMapControllerDisableRoads:
    """Test MapController.disableRoads() functionality."""

    def test_disable_roads_triggers_recalculation(self, mock_osrm: Mock) -> None:
        """Test that disabling roads triggers route recalculation."""
        MapController._instance = None
        mock_osrm.get_all_edges.return_value = Mock()

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route = Mock(spec=Route)
            route.is_finished = False
            route.recalculate.return_value = True

            mc._subscribe_route_to_road(101, route)

            mc.disableRoads([101])

            route.recalculate.assert_called_once()

    def test_disable_roads_does_not_recalculate_finished_routes(
        self, mock_osrm: Mock
    ) -> None:
        """Test that finished routes are not recalculated."""
        MapController._instance = None
        mock_osrm.get_all_edges.return_value = Mock()

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route = Mock(spec=Route)
            route.is_finished = True

            mc._subscribe_route_to_road(101, route)
            mc.disableRoads([101])

            route.recalculate.assert_not_called()

    def test_disable_roads_only_affects_subscribed_routes(
        self, mock_osrm: Mock
    ) -> None:
        """Test that only routes using the disabled road are affected."""
        MapController._instance = None
        mock_osrm.get_all_edges.return_value = Mock()

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route1 = Mock(spec=Route)
            route1.is_finished = False
            route1.recalculate.return_value = True

            route2 = Mock(spec=Route)
            route2.is_finished = False
            route2.recalculate.return_value = True

            mc._subscribe_route_to_road(101, route1)
            mc._subscribe_route_to_road(102, route2)

            mc.disableRoads([101])

            route1.recalculate.assert_called_once()
            route2.recalculate.assert_not_called()

    def test_disable_multiple_roads(self, mock_osrm: Mock) -> None:
        """Test disabling multiple roads at once."""
        MapController._instance = None
        mock_osrm.get_all_edges.return_value = Mock()

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route1 = Mock(spec=Route)
            route1.is_finished = False
            route1.recalculate.return_value = True

            route2 = Mock(spec=Route)
            route2.is_finished = False
            route2.recalculate.return_value = True

            mc._subscribe_route_to_road(101, route1)
            mc._subscribe_route_to_road(102, route2)

            mc.disableRoads([101, 102])

            route1.recalculate.assert_called_once()
            route2.recalculate.assert_called_once()

    def test_disable_roads_empty_list(self, mock_osrm: Mock) -> None:
        """Test that disabling empty list doesn't cause errors."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()

            mc.disableRoads([])

    def test_disable_roads_recalculation_fails(self, mock_osrm: Mock) -> None:
        """Test that failing recalculation is handled gracefully."""
        MapController._instance = None

        import pandas as pd

        edges_df = pd.DataFrame({"id": [100, 101], "name": ["Road A", "Road B"]})
        mock_osrm.get_all_edges.return_value = edges_df
        mock_osrm.set_edges = Mock()

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            with patch("builtins.print") as mock_print:
                mc = MapController()
                route = Mock(spec=Route)
                route.id = 42
                route.is_finished = False
                route.recalculate.return_value = False

                mc._subscribe_route_to_road(101, route)

                mc.disableRoads([101])

                route.recalculate.assert_called_once()
                mock_print.assert_called()
                call_args = str(mock_print.call_args_list)
                assert "Warning" in call_args
                assert "42" in call_args

    def test_disable_roads_handles_edges_dataframe(self, mock_osrm: Mock) -> None:
        """Test that disableRoads handles edges dataframe operations."""
        MapController._instance = None

        import pandas as pd

        edges_df = pd.DataFrame(
            {"id": [100, 101, 102], "name": ["Road A", "Road B", "Road C"]}
        )
        mock_osrm.get_all_edges.return_value = edges_df
        mock_osrm.set_edges = Mock()

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            with patch("builtins.print") as mock_print:
                mc = MapController()

                mc.disableRoads([101])

                mock_osrm.set_edges.assert_called_once()
                mock_print.assert_called()

    def test_disable_roads_road_not_in_edges(self, mock_osrm: Mock) -> None:
        """Test warning when road is not found in edges dataframe."""
        MapController._instance = None

        import pandas as pd

        edges_df = pd.DataFrame({"id": [100, 102], "name": ["Road A", "Road C"]})
        mock_osrm.get_all_edges.return_value = edges_df

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            with patch("builtins.print") as mock_print:
                mc = MapController()

                mc.disableRoads([101])

                mock_print.assert_called()
                call_args = str(mock_print.call_args)
                assert "not found" in call_args

    def test_disable_roads_handles_exception(self, mock_osrm: Mock) -> None:
        """Test that exceptions during road disabling are caught."""
        MapController._instance = None

        class FailingDataFrame:
            """Mock DataFrame that raises exception on __getitem__."""

            def __getitem__(self, key):  # type: ignore
                raise Exception("Test error")

        failing_df = FailingDataFrame()
        mock_osrm.get_all_edges.return_value = failing_df

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            with patch("builtins.print") as mock_print:
                mc = MapController()

                mc.disableRoads([101])

                mock_print.assert_called()
                call_args = str(mock_print.call_args_list)
                assert "Error" in call_args or "error" in call_args


class TestMapControllerEdgeCases:
    """Test edge cases and error handling."""

    def test_disable_nonexistent_road(self, mock_osrm: Mock) -> None:
        """Test disabling a road that doesn't exist in subscriptions."""
        MapController._instance = None
        mock_osrm.get_all_edges.return_value = Mock()

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()

            mc.disableRoads([999])

    def test_unsubscribe_nonexistent_road(self, mock_osrm: Mock) -> None:
        """Test unsubscribing from a road that doesn't exist."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route = Mock(spec=Route)

            mc._unsubscribe_route_from_road(999, route)

    def test_unsubscribe_route_not_in_set(self, mock_osrm: Mock) -> None:
        """Test unsubscribing a route that isn't in the subscription set."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route1 = Mock(spec=Route)
            route2 = Mock(spec=Route)

            mc._subscribe_route_to_road(101, route1)

            mc._unsubscribe_route_from_road(101, route2)

            assert route1 in mc.road_subscriptions[101]


class TestMapControllerIntegration:
    """Integration tests for MapController."""

    def test_road_subscriptions_are_sets(self, mock_osrm: Mock) -> None:
        """Test that road subscriptions use sets for O(1) operations."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route = Mock(spec=Route)

            mc._subscribe_route_to_road(101, route)

            assert isinstance(mc.road_subscriptions[101], set)

    def test_multiple_subscriptions_same_route(self, mock_osrm: Mock) -> None:
        """Test that subscribing the same route twice doesn't duplicate."""
        MapController._instance = None

        with patch("sim.map.MapController.OSRMConnection", return_value=mock_osrm):
            mc = MapController()
            route = Mock(spec=Route)

            mc._subscribe_route_to_road(101, route)
            mc._subscribe_route_to_road(101, route)

            assert len(mc.road_subscriptions[101]) == 1
            assert route in mc.road_subscriptions[101]
