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

import json
import logging
from unittest.mock import MagicMock, patch


from grafana_logging.logger import LokiHandler, VeloSimLogger, get_logger


def test_get_logger_creates_logger() -> None:
    """Test that get_logger creates a logger instance."""
    logger = get_logger("test_module")

    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_get_logger_returns_same_instance() -> None:
    """Test that get_logger returns the same instance for the same name."""
    logger1 = get_logger("test_module_cached")
    logger2 = get_logger("test_module_cached")

    assert logger1 is logger2


def test_logger_different_levels() -> None:
    """Test logging at different levels."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            with patch("grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
                VeloSimLogger._loggers.clear()

                logger = get_logger("test_levels")

                # These should not raise any exceptions
                logger.debug("Debug message")
                logger.info("Info message")
                logger.warning("Warning message")
                logger.error("Error message")
                logger.critical("Critical message")


def test_log_request_function() -> None:
    """Test the log_request convenience function."""
    # Instead of actually logging to file, just verify the function is called correctly
    with patch("grafana_logging.logger.VeloSimLogger.get_logger") as mock_get_logger:
        mock_logger = mock_get_logger.return_value

        VeloSimLogger.log_request("GET", "/api/v1/stations", 200, 45.2)

        # Verify get_logger was called
        mock_get_logger.assert_called_once_with("http")

        # Verify logger.log was called with correct level and message
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == logging.INFO  # level
        assert "GET /api/v1/stations" in call_args[0][1]  # message
        assert "200" in call_args[0][1]
        assert "45.20ms" in call_args[0][1]


def test_log_simulation_event() -> None:
    """Test the log_simulation_event function."""
    # Instead of actually logging to file, just verify the function is called correctly
    with patch("grafana_logging.logger.VeloSimLogger.get_logger") as mock_get_logger:
        mock_logger = mock_get_logger.return_value

        VeloSimLogger.log_simulation_event(
            "STEP", "Vehicle moved", {"vehicle_id": 123, "position": (10, 20)}
        )

        # Verify get_logger was called
        mock_get_logger.assert_called_once_with("simulator")

        # Verify logger.info was called with correct message
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        message = call_args[0][0]
        assert "[STEP] Vehicle moved" in message
        assert "vehicle_id=123" in message
        assert "position=(10, 20)" in message


def test_logger_custom_level() -> None:
    """Test creating logger with custom log level."""
    logger = get_logger("test_custom_level", level="WARNING")

    assert logger.level == logging.WARNING


def test_logger_no_propagation() -> None:
    """Test that logger doesn't propagate to avoid duplicate logs."""
    logger = get_logger("test_no_propagate")

    assert logger.propagate is False


# =============================================================================
# LokiHandler Tests
# =============================================================================


def test_loki_handler_init_default_values() -> None:
    """Test LokiHandler initialization with default values."""
    handler = LokiHandler()

    assert handler.url == "http://velosim-loki:3100/loki/api/v1/push"
    assert handler.labels == {"job": "python_app"}
    assert handler.timeout == 2.0


def test_loki_handler_init_custom_values() -> None:
    """Test LokiHandler initialization with custom values."""
    handler = LokiHandler(
        url="http://custom-loki:3100/loki/api/v1/push",
        labels={"job": "custom_job", "env": "test"},
        timeout=5.0,
    )

    assert handler.url == "http://custom-loki:3100/loki/api/v1/push"
    assert handler.labels == {"job": "custom_job", "env": "test"}
    assert handler.timeout == 5.0


def test_loki_handler_emit_builds_correct_payload() -> None:
    """Test that emit builds the correct Loki payload structure."""
    handler = LokiHandler(url="http://test-loki:3100/loki/api/v1/push")
    handler.setFormatter(logging.Formatter("%(message)s"))

    with patch.object(handler, "_send_to_loki") as mock_send:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        # Verify _send_to_loki was called
        mock_send.assert_called_once()

        # Get the payload that was sent
        payload = mock_send.call_args[0][0]

        # Verify payload structure
        assert "streams" in payload
        assert len(payload["streams"]) == 1

        stream = payload["streams"][0]
        assert "stream" in stream
        assert "values" in stream

        # Verify labels
        labels = stream["stream"]
        assert labels["job"] == "python_app"
        assert labels["logger"] == "test_logger"
        assert labels["level"] == "INFO"

        # Verify values (timestamp, message)
        values = stream["values"]
        assert len(values) == 1
        assert len(values[0]) == 2  # [timestamp_ns, message]
        assert values[0][1] == "Test message"


def test_loki_handler_emit_includes_extra_labels() -> None:
    """Test that emit includes extra labels from log record."""
    handler = LokiHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))

    with patch.object(handler, "_send_to_loki") as mock_send:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Add extra attributes that LokiHandler looks for
        record.source = "frontend"
        record.user_id = 123
        record.context = "login"

        handler.emit(record)

        payload = mock_send.call_args[0][0]
        labels = payload["streams"][0]["stream"]

        assert labels["source"] == "frontend"
        assert labels["user_id"] == "123"
        assert labels["context"] == "login"


def test_loki_handler_emit_handles_errors_gracefully() -> None:
    """Test that emit doesn't raise exceptions on errors."""
    handler = LokiHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))

    with patch.object(handler, "_send_to_loki", side_effect=Exception("Network error")):
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # This should not raise an exception
        handler.emit(record)


def test_loki_handler_send_makes_http_request() -> None:
    """Test that _send_to_loki makes correct HTTP request."""
    handler = LokiHandler(url="http://test-loki:3100/loki/api/v1/push")

    payload = {
        "streams": [
            {
                "stream": {"job": "test"},
                "values": [["1234567890000000000", "Test message"]],
            }
        ]
    }

    with patch("grafana_logging.logger.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = MagicMock()
        mock_urlopen.return_value.__exit__ = MagicMock()

        handler._send_to_loki(payload)

        # Verify urlopen was called
        mock_urlopen.assert_called_once()

        # Get the request object
        request = mock_urlopen.call_args[0][0]

        assert request.full_url == "http://test-loki:3100/loki/api/v1/push"
        assert request.get_header("Content-type") == "application/json"
        assert request.method == "POST"

        # Verify the data
        data = json.loads(request.data.decode("utf-8"))
        assert data == payload


def test_loki_handler_send_handles_network_errors() -> None:
    """Test that _send_to_loki handles network errors silently."""
    handler = LokiHandler()

    with patch(
        "grafana_logging.logger.urllib.request.urlopen",
        side_effect=Exception("Connection refused"),
    ):
        # This should not raise an exception
        handler._send_to_loki({"streams": []})
