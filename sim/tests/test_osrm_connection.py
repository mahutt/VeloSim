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
from requests.exceptions import RequestException, Timeout
import pandas as pd
from typing import Generator

from sim.osm.OSRMConnection import OSRMConnection, get_osrm_connection


@pytest.fixture(autouse=True)
def reset_singleton() -> Generator[None, None, None]:
    """Reset the OSRMConnection singleton before each test."""
    OSRMConnection._instance = None
    yield
    OSRMConnection._instance = None


@pytest.fixture
def mock_session() -> Mock:
    """Create a mock requests Session."""
    session = Mock()
    session.get = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_osrm_response() -> Mock:
    """Create a mock successful OSRM response."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "code": "Ok",
        "routes": [
            {
                "geometry": {
                    "coordinates": [
                        [-73.5673, 45.5017],
                        [-73.5600, 45.5050],
                        [-73.5533, 45.5017],
                    ]
                },
                "distance": 500.0,
                "duration": 300.0,
                "legs": [
                    {
                        "steps": [
                            {
                                "name": "Main Street",
                                "distance": 200.0,
                                "duration": 120.0,
                                "geometry": {
                                    "coordinates": [
                                        [-73.5673, 45.5017],
                                        [-73.5600, 45.5050],
                                    ]
                                },
                            },
                            {
                                "name": "Side Avenue",
                                "distance": 300.0,
                                "duration": 180.0,
                                "geometry": {
                                    "coordinates": [
                                        [-73.5600, 45.5050],
                                        [-73.5533, 45.5017],
                                    ]
                                },
                            },
                        ]
                    }
                ],
            }
        ],
    }
    return response


class TestOSRMConnectionInitialization:
    """Test OSRMConnection initialization and singleton pattern."""

    def test_initialization_with_explicit_url(self, mock_session: Mock) -> None:
        """Test initialization with explicit OSRM URL."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            assert osrm.osrm_base_url == "http://localhost:5000"
            assert osrm.blocked_roads == {}
            assert hasattr(osrm, "_session")

    def test_initialization_with_env_osrm_url(self, mock_session: Mock) -> None:
        """Test initialization with OSRM_URL environment variable."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            with patch.dict("os.environ", {"OSRM_URL": "http://env-osrm:5000"}):
                mock_session.get.return_value = Mock(status_code=200)

                osrm = OSRMConnection()

                assert osrm.osrm_base_url == "http://env-osrm:5000"

    def test_initialization_with_env_local_url(self, mock_session: Mock) -> None:
        """Test initialization with OSRM_LOCAL_URL environment variable."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            with patch.dict(
                "os.environ",
                {"OSRM_LOCAL_URL": "http://local-osrm:5000"},
                clear=True,
            ):
                mock_session.get.return_value = Mock(status_code=200)

                osrm = OSRMConnection()

                assert osrm.osrm_base_url == "http://local-osrm:5000"

    def test_initialization_with_env_public_url(self, mock_session: Mock) -> None:
        """Test initialization with OSRM_PUBLIC_URL environment variable."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            with patch.dict(
                "os.environ",
                {"OSRM_PUBLIC_URL": "http://router.project-osrm.org"},
                clear=True,
            ):
                mock_session.get.return_value = Mock(status_code=200)

                osrm = OSRMConnection()

                assert osrm.osrm_base_url == "http://router.project-osrm.org"

    def test_initialization_priority_explicit_over_env(
        self, mock_session: Mock
    ) -> None:
        """Test that explicit URL takes priority over environment variables."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            with patch.dict("os.environ", {"OSRM_URL": "http://env-osrm:5000"}):
                mock_session.get.return_value = Mock(status_code=200)

                osrm = OSRMConnection(osrm_url="http://explicit:5000")

                assert osrm.osrm_base_url == "http://explicit:5000"

    def test_initialization_no_url_raises_error(self) -> None:
        """Test that initialization without URL raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(
                ValueError,
                match="No OSRM server URL configured",
            ):
                OSRMConnection()

    def test_initialization_connection_failure_raises_error(
        self, mock_session: Mock
    ) -> None:
        """Test that connection failure raises ConnectionError."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(
                status_code=200, json=lambda: {"code": "Ok"}
            )

            # Initialize successfully first
            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Now test that _verify_osrm_connection returns False on error
            mock_session.get.side_effect = RequestException("Connection failed")
            assert osrm._verify_osrm_connection() is False

    def test_singleton_pattern(self, mock_session: Mock) -> None:
        """Test that OSRMConnection implements singleton pattern."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm1 = OSRMConnection(osrm_url="http://localhost:5000")
            osrm2 = OSRMConnection(osrm_url="http://different:5000")

            assert osrm1 is osrm2

    def test_singleton_initialization_only_once(self, mock_session: Mock) -> None:
        """Test that initialization only happens once for singleton."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm1 = OSRMConnection(osrm_url="http://localhost:5000")
            initial_url = osrm1.osrm_base_url

            osrm2 = OSRMConnection(osrm_url="http://different:5000")

            assert osrm1.osrm_base_url == initial_url
            assert osrm2.osrm_base_url == initial_url


class TestVerifyOSRMConnection:
    """Test OSRM connection verification."""

    def test_verify_connection_success(self, mock_session: Mock) -> None:
        """Test successful connection verification."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            assert osrm._verify_osrm_connection() is True

    def test_verify_connection_failure_bad_status(self, mock_session: Mock) -> None:
        """Test connection verification with bad status code."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            # Initialize first
            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Now test bad status code
            mock_session.get.return_value = Mock(status_code=500)
            assert osrm._verify_osrm_connection() is False

    def test_verify_connection_timeout(self, mock_session: Mock) -> None:
        """Test connection verification with timeout."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            # Initialize first
            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Now test timeout
            mock_session.get.side_effect = Timeout("Request timed out")
            assert osrm._verify_osrm_connection() is False

    def test_verify_connection_request_exception(self, mock_session: Mock) -> None:
        """Test connection verification with request exception."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            # Initialize first
            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Now test request exception
            mock_session.get.side_effect = RequestException("Network error")
            assert osrm._verify_osrm_connection() is False


class TestShortestPathCoords:
    """Test coordinate-based shortest path routing."""

    def test_shortest_path_coords_success(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test successful shortest path query."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            result = osrm.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert result is not None
            assert "coordinates" in result
            assert "distance" in result
            assert "duration" in result
            assert "steps" in result
            assert result["distance"] == 500.0
            assert result["duration"] == 300.0
            assert len(result["coordinates"]) == 3
            assert len(result["steps"]) == 2

    def test_shortest_path_coords_no_route(self, mock_session: Mock) -> None:
        """Test shortest path when no route is found."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            no_route_response = Mock()
            no_route_response.status_code = 200
            no_route_response.json.return_value = {"code": "NoRoute", "routes": []}
            mock_session.get.return_value = no_route_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            result = osrm.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert result is None

    def test_shortest_path_coords_blocked_road(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test shortest path with blocked road."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050)

            result = osrm.shortest_path_coords(
                -73.5673, 45.5017, -73.5533, 45.5017, check_blocked=True
            )

            assert result is None

    def test_shortest_path_coords_skip_blocked_check(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test shortest path skipping blocked road check."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050)

            result = osrm.shortest_path_coords(
                -73.5673, 45.5017, -73.5533, 45.5017, check_blocked=False
            )

            assert result is not None

    def test_shortest_path_coords_request_exception(self, mock_session: Mock) -> None:
        """Test shortest path with request exception."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            mock_session.get.return_value = init_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            mock_session.get.side_effect = RequestException("Network error")

            result = osrm.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert result is None

    def test_shortest_path_coords_no_legs(self, mock_session: Mock) -> None:
        """Test shortest path response with no legs."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            response_no_legs = Mock()
            response_no_legs.status_code = 200
            response_no_legs.json.return_value = {
                "code": "Ok",
                "routes": [
                    {
                        "geometry": {"coordinates": [[-73.5673, 45.5017]]},
                        "distance": 100.0,
                        "duration": 60.0,
                    }
                ],
            }
            mock_session.get.return_value = response_no_legs

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            result = osrm.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert result is not None
            assert result["steps"] == []


class TestGetDistanceCoords:
    """Test coordinate-based distance calculation."""

    def test_get_distance_coords_success(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test successful distance calculation."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            distance = osrm.get_distance_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert distance == 500.0

    def test_get_distance_coords_no_route(self, mock_session: Mock) -> None:
        """Test distance calculation when no route found."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            no_route_response = Mock()
            no_route_response.status_code = 200
            no_route_response.json.return_value = {"code": "NoRoute", "routes": []}
            mock_session.get.return_value = no_route_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            distance = osrm.get_distance_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert distance is None


class TestSnapToRoad:
    """Test road snapping functionality."""

    def test_snap_to_road_success(self, mock_session: Mock) -> None:
        """Test successful coordinate snapping."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            snap_response = Mock()
            snap_response.status_code = 200
            snap_response.json.return_value = {
                "code": "Ok",
                "waypoints": [{"location": [-73.5670, 45.5020]}],
            }

            mock_session.get.side_effect = [init_response, snap_response]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            snapped = osrm.snap_to_road(-73.5673, 45.5017)

            assert snapped == (-73.5670, 45.5020)

    def test_snap_to_road_failure(self, mock_session: Mock) -> None:
        """Test coordinate snapping failure."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            snap_response = Mock()
            snap_response.status_code = 200
            snap_response.json.return_value = {"code": "NoSegment", "waypoints": []}

            mock_session.get.side_effect = [init_response, snap_response]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            snapped = osrm.snap_to_road(-73.5673, 45.5017)

            assert snapped == (-73.5673, 45.5017)

    def test_snap_to_road_request_exception(self, mock_session: Mock) -> None:
        """Test coordinate snapping with request exception."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            mock_session.get.side_effect = [init_response, RequestException("Error")]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            snapped = osrm.snap_to_road(-73.5673, 45.5017)

            assert snapped == (-73.5673, 45.5017)


class TestRoadBlocking:
    """Test road blocking functionality."""

    def test_block_road_area(self, mock_session: Mock) -> None:
        """Test blocking a road area."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050)

            assert (-73.5600, 45.5050) in osrm.blocked_roads

    def test_unblock_road_area(self, mock_session: Mock) -> None:
        """Test unblocking a road area."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050)
            osrm.unblock_road_area(-73.5600, 45.5050)

            assert (-73.5600, 45.5050) not in osrm.blocked_roads

    def test_unblock_nonexistent_road(self, mock_session: Mock) -> None:
        """Test unblocking a road that wasn't blocked."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.unblock_road_area(-73.5600, 45.5050)

            assert len(osrm.blocked_roads) == 0

    def test_clear_blocked_roads(self, mock_session: Mock) -> None:
        """Test clearing all blocked roads."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050)
            osrm.block_road_area(-73.5700, 45.5100)
            osrm.clear_blocked_roads()

            assert len(osrm.blocked_roads) == 0

    def test_route_intersects_blocked(self, mock_session: Mock) -> None:
        """Test checking if route intersects blocked roads."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050)

            coordinates = [
                [-73.5673, 45.5017],
                [-73.5600, 45.5050],
                [-73.5533, 45.5017],
            ]

            result = osrm._route_intersects_blocked(coordinates)

            assert result is True

    def test_route_does_not_intersect_blocked(self, mock_session: Mock) -> None:
        """Test route that doesn't intersect blocked roads."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.9999, 45.9999)

            coordinates = [
                [-73.5673, 45.5017],
                [-73.5600, 45.5050],
                [-73.5533, 45.5017],
            ]

            result = osrm._route_intersects_blocked(coordinates)

            assert result is False

    def test_route_intersects_blocked_empty_set(self, mock_session: Mock) -> None:
        """Test route intersection with no blocked roads."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            coordinates = [[-73.5673, 45.5017], [-73.5600, 45.5050]]

            result = osrm._route_intersects_blocked(coordinates)

            assert result is False


class TestCompatibilityWrappers:
    """Test compatibility wrappers for node-based interface."""

    def test_coord_to_virtual_node(self) -> None:
        """Test coordinate to virtual node conversion."""
        node_id = OSRMConnection._coord_to_virtual_node(-73.5673, 45.5017)

        assert isinstance(node_id, int)
        assert node_id > 0

    def test_coord_to_virtual_node_stable(self) -> None:
        """Test that same coordinates produce same node ID."""
        node_id1 = OSRMConnection._coord_to_virtual_node(-73.5673, 45.5017)
        node_id2 = OSRMConnection._coord_to_virtual_node(-73.5673, 45.5017)

        assert node_id1 == node_id2

    def test_coord_to_virtual_node_different(self) -> None:
        """Test that different coordinates produce different node IDs."""
        node_id1 = OSRMConnection._coord_to_virtual_node(-73.5673, 45.5017)
        node_id2 = OSRMConnection._coord_to_virtual_node(-73.5674, 45.5018)

        assert node_id1 != node_id2

    def test_virtual_node_to_coord_success(self) -> None:
        """Test virtual node to coordinate conversion."""
        coord_lookup: dict[int, tuple[float, float]] = {12345: (-73.5673, 45.5017)}

        coord = OSRMConnection._virtual_node_to_coord(12345, coord_lookup)

        assert coord == (-73.5673, 45.5017)

    def test_virtual_node_to_coord_not_found(self) -> None:
        """Test virtual node to coordinate with missing node."""
        coord_lookup: dict[int, tuple[float, float]] = {}

        coord = OSRMConnection._virtual_node_to_coord(12345, coord_lookup)

        assert coord == (0.0, 0.0)

    def test_shortest_path_node_based(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test node-based shortest path."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            coord_lookup = {1: (-73.5673, 45.5017), 2: (-73.5533, 45.5017)}

            path = osrm.shortest_path(1, 2, coord_lookup)

            assert path is not None
            assert isinstance(path, list)
            assert all(isinstance(node, int) for node in path)

    def test_shortest_path_node_based_no_lookup(self, mock_session: Mock) -> None:
        """Test node-based shortest path without coord lookup."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            with pytest.raises(ValueError, match="coord_lookup dictionary required"):
                osrm.shortest_path(1, 2)

    def test_shortest_path_node_based_missing_coords(self, mock_session: Mock) -> None:
        """Test node-based shortest path with missing coordinates."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            coord_lookup = {1: (-73.5673, 45.5017)}

            path = osrm.shortest_path(1, 2, coord_lookup)

            assert path is None

    def test_shortest_path_node_based_no_route(self, mock_session: Mock) -> None:
        """Test node-based shortest path when no route found."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            no_route_response = Mock()
            no_route_response.status_code = 200
            no_route_response.json.return_value = {"code": "NoRoute", "routes": []}

            mock_session.get.side_effect = [init_response, no_route_response]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            coord_lookup = {1: (-73.5673, 45.5017), 2: (-73.5533, 45.5017)}

            path = osrm.shortest_path(1, 2, coord_lookup)

            assert path is None

    def test_coordinates_to_nearest_node(self, mock_session: Mock) -> None:
        """Test coordinate to nearest node conversion."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            snap_response = Mock()
            snap_response.status_code = 200
            snap_response.json.return_value = {
                "code": "Ok",
                "waypoints": [{"location": [-73.5670, 45.5020]}],
            }

            mock_session.get.side_effect = [init_response, snap_response]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            node_id = osrm.coordinates_to_nearest_node(-73.5673, 45.5017)

            assert isinstance(node_id, int)

    def test_get_node_coordinates(self, mock_session: Mock) -> None:
        """Test getting node coordinates (returns None for virtual nodes)."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            result = osrm.get_node_coordinates(12345)

            assert result is None


class TestGetRouteDetails:
    """Test detailed route information retrieval."""

    def test_get_route_details_success(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test successful route details retrieval."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            details = osrm.get_route_details(-73.5673, 45.5017, -73.5533, 45.5017)

            assert details is not None
            assert "geometry" in details
            assert "distance" in details
            assert "duration" in details

    def test_get_route_details_no_route(self, mock_session: Mock) -> None:
        """Test route details when no route found."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            no_route_response = Mock()
            no_route_response.status_code = 200
            no_route_response.json.return_value = {"code": "NoRoute", "routes": []}

            mock_session.get.side_effect = [init_response, no_route_response]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            details = osrm.get_route_details(-73.5673, 45.5017, -73.5533, 45.5017)

            assert details is None

    def test_get_route_details_request_exception(self, mock_session: Mock) -> None:
        """Test route details with request exception."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            mock_session.get.side_effect = [init_response, RequestException("Error")]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            details = osrm.get_route_details(-73.5673, 45.5017, -73.5533, 45.5017)

            assert details is None


class TestCompatibilityEdgeMethods:
    """Test compatibility methods for edge-based operations."""

    def test_get_all_edges(self, mock_session: Mock) -> None:
        """Test get_all_edges returns empty DataFrame."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            edges = osrm.get_all_edges()

            assert isinstance(edges, pd.DataFrame)
            assert len(edges) == 0

    def test_set_edges(self, mock_session: Mock) -> None:
        """Test set_edges is a no-op."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Should not raise any errors
            osrm.set_edges(pd.DataFrame())


class TestSessionManagement:
    """Test session management and cleanup."""

    def test_close_session(self, mock_session: Mock) -> None:
        """Test closing the session."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.close()

            mock_session.close.assert_called_once()

    def test_del_closes_session(self, mock_session: Mock) -> None:
        """Test that __del__ closes the session."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.__del__()

            mock_session.close.assert_called()


class TestGetOSRMConnection:
    """Test convenience singleton getter function."""

    def test_get_osrm_connection(self, mock_session: Mock) -> None:
        """Test get_osrm_connection function."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = get_osrm_connection(osrm_url="http://localhost:5000")

            assert isinstance(osrm, OSRMConnection)

    def test_get_osrm_connection_returns_singleton(self, mock_session: Mock) -> None:
        """Test that get_osrm_connection returns singleton instance."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm1 = get_osrm_connection(osrm_url="http://localhost:5000")
            osrm2 = get_osrm_connection()

            assert osrm1 is osrm2


class TestRouteIntersectsBlockedWithSegmentDistance:
    """Test route intersection detection using point-to-segment distance."""

    def test_route_intersects_blocked_segment_midpoint(
        self, mock_session: Mock
    ) -> None:
        """
        Test that blocked area near segment midpoint is detected.
        This tests the improvement over point-only checking.
        """
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Block an area with small radius
            osrm.block_road_area(-73.5600, 45.5050, radius=0.005)

            # Route segment passes near but not through the blocked point
            # Segment endpoints are away from blocked area, but segment passes close
            coordinates = [
                [-73.5673, 45.5017],  # Start point far from blocked area
                [-73.5533, 45.5017],  # End point far from blocked area
            ]
            # But the segment at x=-73.5600 is only 0.0033 degrees away
            # from blocked point

            result = osrm._route_intersects_blocked(coordinates, tolerance=0.001)

            # Should detect intersection because segment passes near blocked area
            assert result is True

    def test_route_does_not_intersect_distant_blocked_area(
        self, mock_session: Mock
    ) -> None:
        """
        Test that blocked area far from all segments is not detected.
        """
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Block an area far from route
            osrm.block_road_area(-73.9999, 45.9999, radius=0.001)

            coordinates = [
                [-73.5673, 45.5017],
                [-73.5533, 45.5017],
            ]

            result = osrm._route_intersects_blocked(coordinates, tolerance=0.001)

            # Should not detect intersection
            assert result is False

    def test_route_intersects_multiple_segments_one_blocked(
        self, mock_session: Mock
    ) -> None:
        """
        Test route with multiple segments where only one intersects blocked area.
        """
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Block area near second segment
            osrm.block_road_area(-73.5550, 45.5100, radius=0.005)

            coordinates = [
                [-73.5673, 45.5017],  # Segment 1 start
                [-73.5600, 45.5050],  # Segment 1 end / Segment 2 start
                [-73.5533, 45.5150],  # Segment 2 end
            ]

            result = osrm._route_intersects_blocked(coordinates, tolerance=0.001)

            # Should detect intersection on second segment
            assert result is True

    def test_route_segment_parallel_to_blocked_area(self, mock_session: Mock) -> None:
        """
        Test that segment parallel but close to blocked area is detected.
        """
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Block area parallel to route segment
            osrm.block_road_area(5.0, 1.0, radius=0.5)

            # Route segment parallel to blocked area, 1 unit away
            coordinates = [
                [0.0, 0.0],
                [10.0, 0.0],
            ]

            result = osrm._route_intersects_blocked(coordinates, tolerance=0.001)

            # Should detect intersection
            # (distance 1.0 < radius 0.5 + tolerance 0.001 is False)
            # Actually, 1.0 > 0.501, so should NOT intersect
            assert result is False

    def test_route_segment_crosses_blocked_area(self, mock_session: Mock) -> None:
        """
        Test that segment crossing through blocked area is detected.
        """
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Block area at origin
            osrm.block_road_area(5.0, 0.0, radius=2.0)

            # Route segment passes directly through blocked area
            coordinates = [
                [0.0, 0.0],
                [10.0, 0.0],
            ]

            result = osrm._route_intersects_blocked(coordinates, tolerance=0.001)

            # Should definitely detect intersection
            assert result is True


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_shortest_path_coords_with_custom_tolerance(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test route intersection checking with custom tolerance."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050, radius=0.0001)

            coordinates = [[-73.5673, 45.5017], [-73.5601, 45.5051]]

            # Should still intersect because tolerance is added to radius
            # (0.0001 + 0.001 = 0.0011, and distance is ~0.0014)
            result = osrm._route_intersects_blocked(coordinates, tolerance=0.001)
            assert result is True

    def test_empty_coordinates_list(self, mock_session: Mock) -> None:
        """Test route intersection with empty coordinates."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050)

            result = osrm._route_intersects_blocked([])

            assert result is False

    def test_block_road_area_with_custom_radius(self, mock_session: Mock) -> None:
        """Test blocking road area with custom radius."""
        with patch(
            "sim.osm.OSRMConnection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.block_road_area(-73.5600, 45.5050, radius=0.01)

            assert (-73.5600, 45.5050) in osrm.blocked_roads
