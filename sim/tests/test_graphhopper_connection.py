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
from requests.exceptions import RequestException
from requests import HTTPError

from sim.osm.graphhopper_connection import GraphHopperConnection


@pytest.fixture
def mock_session() -> Mock:
    session = Mock()
    session.get = Mock()
    session.post = Mock()
    session.close = Mock()
    return session


def _health_response(ok: bool = True) -> Mock:
    """Mock a healthy /health response."""
    r = Mock()
    r.ok = ok
    r.status_code = 200 if ok else 503
    r.raise_for_status = Mock()
    return r


def _route_response(distance_m: float = 5000.0, time_ms: float = 600000.0) -> Mock:
    """Mock a successful /route response."""
    r = Mock()
    r.status_code = 200
    r.raise_for_status = Mock()
    r.json.return_value = {
        "paths": [
            {
                "distance": distance_m,
                "time": time_ms,
                "points": {
                    "coordinates": [
                        [-73.5673, 45.5017],
                        [-73.5600, 45.5050],
                        [-73.5533, 45.5017],
                    ]
                },
                "instructions": [
                    {
                        "text": "Continue",
                        "distance": 1000.0,
                        "time": 120000.0,
                        "interval": [0, 1],
                        "street_name": "Main Street",
                    }
                ],
            }
        ]
    }
    return r


def _nearest_response() -> Mock:
    """Mock a successful /nearest response."""
    r = Mock()
    r.status_code = 200
    r.raise_for_status = Mock()
    r.json.return_value = {"coordinates": [-73.5673, 45.5017]}
    return r


class TestDetermineGraphHopperUrl:
    """URL resolution priority."""

    def test_uses_env_graphhopper_url_when_no_explicit_url(
        self, mock_session: Mock
    ) -> None:
        """GRAPHHOPPER_URL env var is used when no explicit URL given."""
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            with patch.dict("os.environ", {"GRAPHHOPPER_URL": "http://env-host:8989"}):
                conn = GraphHopperConnection()
            assert conn._base_url == "http://env-host:8989"

    def test_env_graphhopper_url_strips_trailing_slash(
        self, mock_session: Mock
    ) -> None:
        """Trailing slash is stripped from GRAPHHOPPER_URL."""
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            with patch.dict("os.environ", {"GRAPHHOPPER_URL": "http://env-host:8989/"}):
                conn = GraphHopperConnection()
            assert conn._base_url == "http://env-host:8989"

    def test_uses_default_localhost_when_no_env_set(self, mock_session: Mock) -> None:
        """Falls back to http://localhost:8989 when no env var is set."""
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            with patch.dict("os.environ", {}, clear=True):
                conn = GraphHopperConnection()
            assert conn._base_url == "http://localhost:8989"

    def test_explicit_url_takes_priority_over_env(self, mock_session: Mock) -> None:
        """Explicitly provided URL takes priority over the GRAPHHOPPER_URL env var."""
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            with patch.dict("os.environ", {"GRAPHHOPPER_URL": "http://env-host:8989"}):
                conn = GraphHopperConnection(graphhopper_url="http://explicit:9999")
            assert conn._base_url == "http://explicit:9999"


class TestVerifyGraphHopperConnection:
    """Startup health check against /health or /status endpoints."""

    def test_accepts_ok_response(self, mock_session: Mock) -> None:
        """Any ok response from /health or /status succeeds."""
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            conn = GraphHopperConnection(graphhopper_url="http://localhost:8989")
        assert conn._base_url == "http://localhost:8989"

    def test_raises_connection_error_on_request_exception(
        self, mock_session: Mock
    ) -> None:
        """RequestException during health check is raised as ConnectionError."""
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.side_effect = RequestException("timeout")
            with pytest.raises(ConnectionError, match="Cannot connect to GraphHopper"):
                GraphHopperConnection(graphhopper_url="http://localhost:8989")

    def test_connection_error_message_includes_url(self, mock_session: Mock) -> None:
        """ConnectionError message includes the configured URL for diagnostics."""
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.side_effect = RequestException("refused")
            with pytest.raises(ConnectionError) as exc_info:
                GraphHopperConnection(graphhopper_url="http://bad-host:9999")
        assert "http://bad-host:9999" in str(exc_info.value)


class TestShortestPathCoords:
    """Route calculation via /route."""

    @pytest.fixture
    def conn(self, mock_session: Mock) -> GraphHopperConnection:
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            return GraphHopperConnection(graphhopper_url="http://localhost:8989")

    def test_builds_route_request_body(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """Request body contains correct points and profile."""
        mock_session.post.return_value = _route_response()

        conn.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017, profile="car")

        body = mock_session.post.call_args[1]["json"]
        assert body["profile"] == "car"
        assert body["points"][0] == [-73.5673, 45.5017]
        assert body["points"][1] == [-73.5533, 45.5017]

    def test_includes_custom_model_when_provided(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """custom_model is included in the /route request body when provided."""
        mock_session.post.return_value = _route_response()
        custom_model = {"speed": [{"if": "true", "multiply_by": 0.5}]}

        conn.shortest_path_coords(
            -73.5673,
            45.5017,
            -73.5533,
            45.5017,
            profile="car",
            custom_model=custom_model,
        )

        body = mock_session.post.call_args[1]["json"]
        assert body["custom_model"] == custom_model

    def test_returns_result_on_success(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """Successful /route response is parsed into a GraphHopperResult."""
        mock_session.post.return_value = _route_response(
            distance_m=5000.0, time_ms=600000.0
        )

        result = conn.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

        assert result is not None
        assert result.distance == pytest.approx(5000.0, rel=0.01)

    def test_returns_none_on_request_exception(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """RequestException returns None."""
        mock_session.post.side_effect = RequestException("400 Bad Request")

        result = conn.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

        assert result is None

    def test_returns_none_on_value_error_parsing(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """ValueError during response parsing returns None."""
        r = Mock()
        r.raise_for_status = Mock()
        r.json.return_value = {"paths": []}
        mock_session.post.return_value = r

        result = conn.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

        assert result is None

    def test_returns_none_on_http_error_with_response_body(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """HTTPError with response payload is handled and returns None."""
        response = Mock()
        response.raise_for_status.side_effect = HTTPError(
            "bad request",
            response=Mock(text="x" * 1200),
        )
        mock_session.post.return_value = response

        result = conn.shortest_path_coords(-73.5673, 45.5017, -73.5533, 45.5017)

        assert result is None


class TestGetDistanceCoords:
    """Distance lookups via /route."""

    @pytest.fixture
    def conn(self, mock_session: Mock) -> GraphHopperConnection:
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            return GraphHopperConnection(graphhopper_url="http://localhost:8989")

    def test_returns_distance_on_success(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """Distance in meters is returned when route succeeds."""
        mock_session.post.return_value = _route_response(
            distance_m=1234.0, time_ms=60000.0
        )

        distance = conn.get_distance_coords(-73.5673, 45.5017, -73.5533, 45.5017)

        assert distance == pytest.approx(1234.0, rel=0.01)

    def test_returns_none_when_route_fails(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """None is returned when the route request fails."""
        mock_session.post.side_effect = RequestException("connection refused")

        distance = conn.get_distance_coords(-73.5673, 45.5017, -73.5533, 45.5017)

        assert distance is None


class TestSnapToRoad:
    """Nearest snapping via /nearest."""

    @pytest.fixture
    def conn(self, mock_session: Mock) -> GraphHopperConnection:
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            return GraphHopperConnection(graphhopper_url="http://localhost:8989")

    def test_returns_coordinates_on_success(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """Coordinates from /nearest response are returned."""
        mock_session.get.return_value = _nearest_response()

        lon, lat = conn.snap_to_road(-73.5673, 45.5017)

        assert (lon, lat) == (-73.5673, 45.5017)

    def test_returns_original_coordinates_on_request_exception(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """RequestException returns the original coordinates."""
        mock_session.get.side_effect = RequestException("timeout")

        lon, lat = conn.snap_to_road(-73.5673, 45.5017)

        assert (lon, lat) == (-73.5673, 45.5017)

    def test_returns_original_coordinates_when_nearest_payload_has_no_point(
        self, conn: GraphHopperConnection, mock_session: Mock
    ) -> None:
        """Malformed /nearest payload falls back to original coordinates."""
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"point": {"coordinates": "invalid"}}
        mock_session.get.return_value = response

        lon, lat = conn.snap_to_road(-73.5673, 45.5017)

        assert (lon, lat) == (-73.5673, 45.5017)


class TestClose:
    """Session lifecycle cleanup."""

    def test_close_calls_underlying_session_close(self, mock_session: Mock) -> None:
        with patch(
            "sim.osm.graphhopper_connection.requests.Session", return_value=mock_session
        ):
            mock_session.get.return_value = _health_response()
            conn = GraphHopperConnection(graphhopper_url="http://localhost:8989")

        conn.close()

        mock_session.close.assert_called_once()
