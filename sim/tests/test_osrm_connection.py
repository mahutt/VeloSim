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

from sim.osm.osrm_connection import OSRMConnection, get_osrm_connection


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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            assert osrm.osrm_base_url == "http://localhost:5000"
            assert hasattr(osrm, "_session")

    def test_initialization_with_env_osrm_url(self, mock_session: Mock) -> None:
        """Test initialization with OSRM_URL environment variable."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            with patch.dict("os.environ", {"OSRM_URL": "http://env-osrm:5000"}):
                mock_session.get.return_value = Mock(status_code=200)

                osrm = OSRMConnection()

                assert osrm.osrm_base_url == "http://env-osrm:5000"

    def test_initialization_with_env_local_url(self, mock_session: Mock) -> None:
        """Test initialization with OSRM_LOCAL_URL environment variable."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            with patch.dict("os.environ", {"OSRM_URL": "http://env-osrm:5000"}):
                mock_session.get.return_value = Mock(status_code=200)

                osrm = OSRMConnection(osrm_url="http://explicit:5000")

                assert osrm.osrm_base_url == "http://explicit:5000"

    def test_initialization_no_url_raises_error(self, mock_session: Mock) -> None:
        """Test that initialization without URL uses default localhost:5001."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            with patch.dict("os.environ", {}, clear=True):
                mock_session.get.return_value = Mock(status_code=200)

                osrm = OSRMConnection()

                # Should use default localhost:5001
                assert osrm.osrm_base_url == "http://localhost:5001"

    def test_initialization_connection_failure_raises_error(
        self, mock_session: Mock
    ) -> None:
        """Test that connection failure raises ConnectionError."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(
                status_code=200, json=lambda: {"code": "Ok"}
            )

            # Initialize successfully first
            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            # Now test that _verify_osrm_connection returns False on error
            mock_session.get.side_effect = RequestException("Connection failed")
            assert osrm._verify_osrm_connection() is False


class TestVerifyOSRMConnection:
    """Test OSRM connection verification."""

    def test_verify_connection_success(self, mock_session: Mock) -> None:
        """Test successful connection verification."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")

            assert osrm._verify_osrm_connection() is True

    def test_verify_connection_failure_bad_status(self, mock_session: Mock) -> None:
        """Test connection verification with bad status code."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            result = osrm.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert result is not None
            assert result.coordinates is not None
            assert result.distance == 500.0
            assert result.duration == 300.0
            assert len(result.coordinates) == 3
            assert len(result.steps) == 2

    def test_shortest_path_coords_no_route(self, mock_session: Mock) -> None:
        """Test shortest path when no route is found."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            no_route_response = Mock()
            no_route_response.status_code = 200
            no_route_response.json.return_value = {"code": "NoRoute", "routes": []}
            mock_session.get.return_value = no_route_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            result = osrm.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert result is None

    def test_shortest_path_coords_request_exception(self, mock_session: Mock) -> None:
        """Test shortest path with request exception."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            assert result.steps == []


class TestGetDistanceCoords:
    """Test coordinate-based distance calculation."""

    def test_get_distance_coords_success(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test successful distance calculation."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            distance = osrm.get_distance_coords(-73.5673, 45.5017, -73.5533, 45.5017)

            assert distance == 500.0

    def test_get_distance_coords_no_route(self, mock_session: Mock) -> None:
        """Test distance calculation when no route found."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            mock_session.get.side_effect = [init_response, RequestException("Error")]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            snapped = osrm.snap_to_road(-73.5673, 45.5017)

            assert snapped == (-73.5673, 45.5017)


class TestGetRouteDetails:
    """Test detailed route information retrieval."""

    def test_get_route_details_success(
        self, mock_session: Mock, mock_osrm_response: Mock
    ) -> None:
        """Test successful route details retrieval."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = mock_osrm_response

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            details = osrm.get_route_details(-73.5673, 45.5017, -73.5533, 45.5017)

            assert details is not None
            assert details.coordinates is not None
            assert details.distance == 500.0
            assert details.duration == 300.0

    def test_get_route_details_no_route(self, mock_session: Mock) -> None:
        """Test route details when no route found."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
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
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            init_response = Mock(status_code=200)
            mock_session.get.side_effect = [init_response, RequestException("Error")]

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            details = osrm.get_route_details(-73.5673, 45.5017, -73.5533, 45.5017)

            assert details is None


class TestSessionManagement:
    """Test session management and cleanup."""

    def test_close_session(self, mock_session: Mock) -> None:
        """Test closing the session."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.close()

            mock_session.close.assert_called_once()

    def test_del_closes_session(self, mock_session: Mock) -> None:
        """Test that __del__ closes the session."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = OSRMConnection(osrm_url="http://localhost:5000")
            osrm.__del__()

            mock_session.close.assert_called()


class TestGetOSRMConnection:
    """Test convenience getter function."""

    def test_get_osrm_connection(self, mock_session: Mock) -> None:
        """Test get_osrm_connection function."""
        with patch(
            "sim.osm.osrm_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = Mock(status_code=200)

            osrm = get_osrm_connection(osrm_url="http://localhost:5000")

            assert isinstance(osrm, OSRMConnection)
