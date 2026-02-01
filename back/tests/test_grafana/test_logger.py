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

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from grafana_logging.logger import VeloSimLogger, get_logger


@pytest.fixture
def temp_log_file(tmp_path: Path) -> Path:
    """Create a temporary log file for testing."""
    log_file = tmp_path / "test_logs.txt"
    return log_file


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


def test_logger_logs_to_file(temp_log_file: Path) -> None:
    """Test that logger writes to file with timestamps."""
    import re

    with patch("grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("grafana_logging.logger.LOG_TO_FILE", True):
            with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
                # Clear cached loggers
                VeloSimLogger._loggers.clear()

                logger = get_logger("test_file_logging")
                logger.info("Test message")

                # Read the log file
                assert temp_log_file.exists()
                content = temp_log_file.read_text()
                assert "Test message" in content
                assert "test_file_logging" in content
                assert "INFO" in content

                # Verify timestamp is included
                timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
                assert re.search(
                    timestamp_pattern, content
                ), "Timestamp should be present in file logs"


def test_logger_different_levels(temp_log_file: Path) -> None:
    """Test logging at different levels."""
    with patch("grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("grafana_logging.logger.LOG_TO_FILE", True):
            with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
                with patch("grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
                    VeloSimLogger._loggers.clear()

                    logger = get_logger("test_levels")

                    logger.debug("Debug message")
                    logger.info("Info message")
                    logger.warning("Warning message")
                    logger.error("Error message")
                    logger.critical("Critical message")

                    content = temp_log_file.read_text()

                    # All levels should be in the file
                    assert "Debug message" in content
                    assert "Info message" in content
                    assert "Warning message" in content
                    assert "Error message" in content
                    assert "Critical message" in content


def test_log_request_function(temp_log_file: Path) -> None:
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


def test_log_simulation_event(temp_log_file: Path) -> None:
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


def test_log_file_creation(tmp_path: Path) -> None:
    """Test that log file is created if it doesn't exist."""
    log_file = tmp_path / "new_logs.txt"

    with patch("grafana_logging.logger.DEFAULT_LOG_FILE", str(log_file)):
        with patch("grafana_logging.logger.LOG_TO_FILE", True):
            VeloSimLogger._ensure_log_file_exists()

            assert log_file.exists()


def test_logger_no_propagation() -> None:
    """Test that logger doesn't propagate to avoid duplicate logs."""
    logger = get_logger("test_no_propagate")

    assert logger.propagate is False


def test_logger_includes_timestamp_in_file(temp_log_file: Path) -> None:
    """Test that file logs include timestamps."""
    import re

    with patch("grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("grafana_logging.logger.LOG_TO_FILE", True):
            with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
                VeloSimLogger._loggers.clear()

                logger = get_logger("test_timestamp")
                logger.info("Timestamp test message")

                content = temp_log_file.read_text()

                # Verify timestamp is present (format: YYYY-MM-DD HH:MM:SS)
                timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
                assert re.search(timestamp_pattern, content), (
                    "Timestamp not found in log file. " f"Content: {content}"
                )

                # Verify full log format
                assert "test_timestamp" in content
                assert "INFO" in content
                assert "Timestamp test message" in content
