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

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_middleware_logs_successful_request(client: TestClient) -> None:
    """log_request is called for a normal request with correct method and status."""
    with patch("back.main.log_request") as mock_log:
        client.get("/")
        mock_log.assert_called_once()
        method, url, status_code, _ = mock_log.call_args[0]
        assert method == "GET"
        assert "/" in url
        assert status_code == 200


def test_middleware_logs_positive_duration(client: TestClient) -> None:
    """Duration passed to log_request is a positive float."""
    with patch("back.main.log_request") as mock_log:
        client.get("/")
        _, _, _, duration_ms = mock_log.call_args[0]
        assert isinstance(duration_ms, float)
        assert duration_ms > 0


def test_middleware_logs_4xx_status(client: TestClient) -> None:
    """log_request is called with the correct 4xx status code."""
    with patch("back.main.log_request") as mock_log:
        client.post(
            "/api/token",
            data={"username": "bad", "password": "bad"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        _, _, status_code, _ = mock_log.call_args[0]
        assert status_code == 400


def test_middleware_skips_metrics_endpoint(client: TestClient) -> None:
    """log_request is not called for the Prometheus metrics endpoint."""
    with patch("back.main.log_request") as mock_log:
        client.get("/api/v1/metric/metrics")
        mock_log.assert_not_called()


def test_middleware_skips_health_endpoint(client: TestClient) -> None:
    """log_request is not called for the health probe endpoint."""
    with patch("back.main.log_request") as mock_log:
        client.get("/health")
        mock_log.assert_not_called()


def test_middleware_includes_query_string_in_url(client: TestClient) -> None:
    """The full URL including query parameters is passed to log_request."""
    with patch("back.main.log_request") as mock_log:
        client.get("/?foo=bar")
        _, url, _, _ = mock_log.call_args[0]
        assert "foo=bar" in url
