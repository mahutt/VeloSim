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

from pathlib import Path
from unittest.mock import patch

import pytest

from back.grafana_logging.examples import (
    example_backend_api_logging,
    example_basic_logging,
    example_conditional_logging,
    example_error_logging_with_context,
    example_frontend_api_logging,
    example_http_request_logging,
    example_simulator_logging,
    example_structured_logging,
)
from back.grafana_logging.logger import VeloSimLogger


@pytest.fixture
def temp_log_file(tmp_path: Path) -> Path:
    """Create a temporary log file for testing."""
    log_file = tmp_path / "test_examples_logs.txt"
    log_file.touch()
    return log_file


def test_example_basic_logging(temp_log_file: Path) -> None:
    """Test that basic logging example works and logs all levels."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                with patch("back.grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
                    VeloSimLogger._loggers.clear()

                    example_basic_logging()

                    content = temp_log_file.read_text()

                    # Check all log levels are present
                    assert "DEBUG" in content
                    assert "INFO" in content
                    assert "WARNING" in content
                    assert "ERROR" in content
                    assert "CRITICAL" in content
                    assert "debug message" in content
                    assert "info message" in content


def test_example_backend_api_logging(temp_log_file: Path) -> None:
    """Test backend API logging example."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                VeloSimLogger._loggers.clear()

                result = example_backend_api_logging()

                # Check return value
                assert result == ["Station A", "Station B"]

                # Check logging
                content = temp_log_file.read_text()
                assert "Fetching all stations from database" in content
                assert "Successfully retrieved 2 stations" in content
                assert "api.stations" in content


def test_example_http_request_logging(temp_log_file: Path) -> None:
    """Test HTTP request logging example."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                VeloSimLogger._loggers.clear()

                example_http_request_logging()

                content = temp_log_file.read_text()
                assert "GET /api/v1/stations" in content
                assert "200" in content
                assert "ms" in content


def test_example_simulator_logging(temp_log_file: Path) -> None:
    """Test simulator logging example."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                VeloSimLogger._loggers.clear()

                example_simulator_logging()

                content = temp_log_file.read_text()

                # Check simulation start
                assert "Starting new simulation run" in content

                # Check simulation step event
                assert "[STEP] Vehicle moved to new position" in content
                assert "vehicle_id=123" in content
                assert "position=(10.5, 20.3)" in content
                assert "speed=15.2" in content

                # Check completion event
                assert "[COMPLETE] Simulation finished successfully" in content
                assert "total_steps=1000" in content
                assert "duration_seconds=45.2" in content


def test_example_error_logging_with_context(temp_log_file: Path) -> None:
    """Test error logging with context example."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                VeloSimLogger._loggers.clear()

                example_error_logging_with_context()

                content = temp_log_file.read_text()

                # Check error was logged
                assert "Database operation failed" in content
                assert "division by zero" in content
                assert "ERROR" in content


def test_example_conditional_logging_development(temp_log_file: Path) -> None:
    """Test conditional logging in development environment."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                with patch("back.grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
                    with patch.dict(
                        "os.environ", {"ENVIRONMENT": "development"}, clear=False
                    ):
                        VeloSimLogger._loggers.clear()

                        # Just verify it runs without errors
                        example_conditional_logging()
                        # The function ran successfully


def test_example_conditional_logging_production(temp_log_file: Path) -> None:
    """Test conditional logging in production environment."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                with patch("back.grafana_logging.logger.DEFAULT_LOG_LEVEL", "INFO"):
                    with patch.dict(
                        "os.environ", {"ENVIRONMENT": "production"}, clear=False
                    ):
                        VeloSimLogger._loggers.clear()

                        # Just verify it runs without errors
                        example_conditional_logging()
                        # The function ran successfully


def test_example_structured_logging(temp_log_file: Path) -> None:
    """Test structured logging example."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                VeloSimLogger._loggers.clear()

                example_structured_logging()

                content = temp_log_file.read_text()

                # Check structured format
                assert "User action completed" in content
                assert "user_id=12345" in content
                assert "action=login" in content
                assert "status=success" in content


def test_example_frontend_api_logging() -> None:
    """Test that frontend API logging example doesn't raise errors."""
    # This example just defines a function, doesn't execute anything
    # We just verify it can be called without errors
    example_frontend_api_logging()
    # If we get here without exceptions, the test passes


def test_all_examples_run_without_errors(temp_log_file: Path) -> None:
    """Integration test: run all examples to ensure none raise exceptions."""
    with patch("back.grafana_logging.logger.DEFAULT_LOG_FILE", str(temp_log_file)):
        with patch("back.grafana_logging.logger.LOG_TO_FILE", True):
            with patch("back.grafana_logging.logger.LOG_TO_CONSOLE", False):
                with patch("back.grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
                    VeloSimLogger._loggers.clear()

                    # Run all examples - should not raise any exceptions
                    example_basic_logging()
                    result = example_backend_api_logging()
                    assert result == ["Station A", "Station B"]
                    example_http_request_logging()
                    example_simulator_logging()
                    example_error_logging_with_context()
                    example_conditional_logging()
                    example_structured_logging()
                    example_frontend_api_logging()

                    # If we got here without exceptions, the test passes
