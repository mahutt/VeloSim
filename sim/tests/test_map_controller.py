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
def mock_routing_provider() -> Mock:
    """Create a mock routing provider."""
    provider = Mock()
    provider.get_route.return_value = Mock(
        coordinates=[[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]],
        distance=300.0,
        duration=180.0,
    )
    return provider


@pytest.fixture
def mock_route() -> Mock:
    """Create a mock Route object."""
    route = Mock(spec=Route)
    route.id = 1
    route.is_finished = False
    route.recalculate.return_value = True
    return route


class TestMapControllerInitialization:
    """Test MapController initialization."""

    def test_initialization_creates_routing_provider(self) -> None:
        """Test that initialization creates a routing provider."""
        with patch("sim.map.MapController.OSRMAdapter") as mock_adapter_class:
            mock_adapter_class.return_value = Mock()

            mc = MapController()

            mock_adapter_class.assert_called_once_with()
            assert hasattr(mc, "routing_provider")
            assert hasattr(mc, "route_controller")


class TestMapControllerGetRoute:
    """Test MapController.get_route() functionality."""

    def test_get_route_delegates_to_route_controller(
        self, mock_routing_provider: Mock
    ) -> None:
        """Test that get_route delegates entirely to RouteController."""
        with patch(
            "sim.map.MapController.OSRMAdapter", return_value=mock_routing_provider
        ):
            with patch("sim.map.MapController.RouteController") as mock_rc_class:
                mock_route = Mock(spec=Route)
                mock_route_controller = Mock()
                mock_route_controller.get_route_from_positions.return_value = mock_route
                mock_rc_class.return_value = mock_route_controller

                mc = MapController()
                pos_a = Mock(spec=Position)
                pos_b = Mock(spec=Position)

                route = mc.get_route(pos_a, pos_b)

                # Verify pure delegation - MapController just passes through
                mock_route_controller.get_route_from_positions.assert_called_once_with(
                    pos_a, pos_b, mc.routing_provider, mc.config
                )
                assert route == mock_route

    def test_get_route_returns_route_controller_result(
        self, mock_routing_provider: Mock
    ) -> None:
        """Test that get_route returns exactly what RouteController returns."""
        with patch(
            "sim.map.MapController.OSRMAdapter", return_value=mock_routing_provider
        ):
            with patch("sim.map.MapController.RouteController") as mock_rc_class:
                mock_route = Mock(spec=Route)
                mock_route.id = 42
                mock_route_controller = Mock()
                mock_route_controller.get_route_from_positions.return_value = mock_route
                mock_rc_class.return_value = mock_route_controller

                mc = MapController()
                pos_a = Mock(spec=Position)
                pos_b = Mock(spec=Position)

                result = mc.get_route(pos_a, pos_b)

                assert result is mock_route
                assert result.id == 42

    def test_get_route_propagates_value_error(
        self, mock_routing_provider: Mock
    ) -> None:
        """Test that get_route propagates ValueError from RouteController."""
        with patch(
            "sim.map.MapController.OSRMAdapter", return_value=mock_routing_provider
        ):
            with patch("sim.map.MapController.RouteController") as mock_rc_class:
                mock_route_controller = Mock()
                mock_route_controller.get_route_from_positions.side_effect = ValueError(
                    "No route found"
                )
                mock_rc_class.return_value = mock_route_controller

                mc = MapController()
                pos_a = Mock(spec=Position)
                pos_b = Mock(spec=Position)

                with pytest.raises(ValueError, match="No route found"):
                    mc.get_route(pos_a, pos_b)


class TestMapControllerRouteController:
    """Test MapController integration with RouteController."""

    def test_route_controller_initialized(self, mock_routing_provider: Mock) -> None:
        """Test that RouteController is initialized with MapController."""
        with patch(
            "sim.map.MapController.OSRMAdapter", return_value=mock_routing_provider
        ):
            with patch("sim.map.MapController.RouteController") as mock_rc_class:
                mock_rc = Mock()
                mock_rc_class.return_value = mock_rc

                mc = MapController()

                mock_rc_class.assert_called_once_with(mc)
                assert mc.route_controller == mock_rc
