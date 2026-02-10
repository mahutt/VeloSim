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


from grafana_logging.examples import (
    example_backend_api_logging,
    example_basic_logging,
    example_conditional_logging,
    example_error_logging_with_context,
    example_frontend_api_logging,
    example_http_request_logging,
    example_simulator_logging,
    example_structured_logging,
)
from grafana_logging.logger import VeloSimLogger


def test_example_basic_logging() -> None:
    """Test that basic logging example works and logs all levels."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            with patch("grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
                VeloSimLogger._loggers.clear()

                # Should run without errors
                example_basic_logging()


def test_example_backend_api_logging() -> None:
    """Test backend API logging example."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            VeloSimLogger._loggers.clear()

            result = example_backend_api_logging()

            # Check return value
            assert result == ["Station A", "Station B"]


def test_example_http_request_logging() -> None:
    """Test HTTP request logging example."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            VeloSimLogger._loggers.clear()

            # Should run without errors
            example_http_request_logging()


def test_example_simulator_logging() -> None:
    """Test simulator logging example."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            VeloSimLogger._loggers.clear()

            # Should run without errors
            example_simulator_logging()


def test_example_error_logging_with_context() -> None:
    """Test error logging with context example."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            VeloSimLogger._loggers.clear()

            # Should run without errors
            example_error_logging_with_context()


def test_example_conditional_logging_development() -> None:
    """Test conditional logging in development environment."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            with patch("grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
                with patch.dict(
                    "os.environ", {"ENVIRONMENT": "development"}, clear=False
                ):
                    VeloSimLogger._loggers.clear()

                    # Just verify it runs without errors
                    example_conditional_logging()


def test_example_conditional_logging_production() -> None:
    """Test conditional logging in production environment."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            with patch("grafana_logging.logger.DEFAULT_LOG_LEVEL", "INFO"):
                with patch.dict(
                    "os.environ", {"ENVIRONMENT": "production"}, clear=False
                ):
                    VeloSimLogger._loggers.clear()

                    # Just verify it runs without errors
                    example_conditional_logging()


def test_example_structured_logging() -> None:
    """Test structured logging example."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            VeloSimLogger._loggers.clear()

            # Should run without errors
            example_structured_logging()


def test_example_frontend_api_logging() -> None:
    """Test that frontend API logging example doesn't raise errors."""
    # This example just defines a function, doesn't execute anything
    # We just verify it can be called without errors
    example_frontend_api_logging()
    # If we get here without exceptions, the test passes


def test_all_examples_run_without_errors() -> None:
    """Integration test: run all examples to ensure none raise exceptions."""
    with patch("grafana_logging.logger.LOG_TO_LOKI", False):
        with patch("grafana_logging.logger.LOG_TO_CONSOLE", False):
            with patch("grafana_logging.logger.DEFAULT_LOG_LEVEL", "DEBUG"):
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
