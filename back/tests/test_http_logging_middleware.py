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

from types import SimpleNamespace
from unittest.mock import patch
from typing import Any, Awaitable, Callable, Literal, MutableMapping

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

from back.core import simulation_callbacks as cb
from back.core.telemetry import initialize_global_telemetry
from back.middleware.metrics_middleware import MetricsMiddleware


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


@pytest.mark.asyncio
async def test_http_logging_middleware_logs_500_on_exception() -> None:
    from back.main import http_logging_middleware

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    request = Request(scope)

    async def failing_call_next(_request: Request) -> Response:
        raise RuntimeError("boom")

    with patch("back.main.log_request") as mock_log:
        with pytest.raises(RuntimeError, match="boom"):
            await http_logging_middleware(request, failing_call_next)

    _, _, status_code, duration_ms = mock_log.call_args[0]
    assert status_code == 500
    assert duration_ms > 0


def test_initialize_global_telemetry_noop_when_provider_already_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMeterProvider:
        pass

    monkeypatch.setattr("back.core.telemetry.MeterProvider", FakeMeterProvider)
    monkeypatch.setattr(
        "back.core.telemetry.metrics.get_meter_provider", lambda: FakeMeterProvider()
    )

    called = {"set": 0}
    monkeypatch.setattr(
        "back.core.telemetry.metrics.set_meter_provider",
        lambda provider: called.__setitem__("set", called["set"] + 1),
    )

    initialize_global_telemetry()

    assert called["set"] == 0


def test_initialize_global_telemetry_sets_provider_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMeterProvider:
        def __init__(self, resource: Any = None, metric_readers: Any = None):
            self.resource = resource
            self.metric_readers = metric_readers

    monkeypatch.setattr("back.core.telemetry.MeterProvider", FakeMeterProvider)
    monkeypatch.setattr(
        "back.core.telemetry.metrics.get_meter_provider", lambda: object()
    )

    set_calls = []
    monkeypatch.setattr(
        "back.core.telemetry.metrics.set_meter_provider",
        lambda provider: set_calls.append(provider),
    )

    initialize_global_telemetry()

    assert len(set_calls) == 1


def test_on_simulation_completed_marks_completed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyDb:
        committed = False

        def commit(self) -> None:
            self.committed = True

    db = DummyDb()
    sim_instance = SimpleNamespace(id=12, completed=False)

    class Ctx:
        def __enter__(self) -> DummyDb:
            return db

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
            return False

    monkeypatch.setattr(cb, "SessionLocal", lambda: Ctx())
    monkeypatch.setattr(
        cb.sim_instance_crud, "get_by_uuid", lambda _db, _id: sim_instance
    )

    cb.on_simulation_completed("sim-a")

    assert sim_instance.completed is True
    assert db.committed is True


def test_on_simulation_completed_missing_sim_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyDb:
        def commit(self) -> None:
            raise AssertionError("commit should not be called")

    class Ctx:
        def __enter__(self) -> DummyDb:
            return DummyDb()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
            return False

    monkeypatch.setattr(cb, "SessionLocal", lambda: Ctx())
    monkeypatch.setattr(cb.sim_instance_crud, "get_by_uuid", lambda _db, _id: None)

    warnings = []
    monkeypatch.setattr(
        cb.logger, "warning", lambda *args, **kwargs: warnings.append((args, kwargs))
    )

    cb.on_simulation_completed("sim-missing")

    assert warnings


def test_on_simulation_completed_exception_logs_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Ctx:
        def __enter__(self) -> Any:
            raise RuntimeError("db unavailable")

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
            return False

    monkeypatch.setattr(cb, "SessionLocal", lambda: Ctx())

    exceptions = []
    monkeypatch.setattr(
        cb.logger,
        "exception",
        lambda *args, **kwargs: exceptions.append((args, kwargs)),
    )

    cb.on_simulation_completed("sim-error")

    assert exceptions


def test_report_simulation_lag_records_histogram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = []
    monkeypatch.setattr(
        cb.simulation_lag_histogram, "record", lambda lag: recorded.append(lag)
    )

    cb.report_simulation_lag(2.75)

    assert recorded == [2.75]


@pytest.mark.asyncio
async def test_metrics_middleware_records_counter_and_histogram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counter_calls = []
    histogram_calls = []

    monkeypatch.setattr(
        "back.middleware.metrics_middleware.http_requests_total",
        SimpleNamespace(
            add=lambda value, labels: counter_calls.append((value, labels))
        ),
    )
    monkeypatch.setattr(
        "back.middleware.metrics_middleware.http_request_duration_seconds",
        SimpleNamespace(
            record=lambda value, labels: histogram_calls.append((value, labels))
        ),
    )

    async def app(
        scope: MutableMapping[str, Any],
        receive: Callable[[], Awaitable[MutableMapping[str, Any]]],
        send: Callable[[MutableMapping[str, Any]], Awaitable[None]],
    ) -> None:
        return None

    middleware = MetricsMiddleware(app=app)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    request = Request(scope)

    async def call_next(_request: Request) -> Response:
        return Response(status_code=204)

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 204
    assert counter_calls and histogram_calls
    assert counter_calls[0][0] == 1
    assert counter_calls[0][1]["status"] == "204"
