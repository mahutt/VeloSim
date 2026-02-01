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
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

# Default log configuration
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOGGER_DIR = Path(__file__).parent
DEFAULT_LOG_FILE = os.getenv("LOG_FILE_PATH", str(_LOGGER_DIR / "logs.txt"))
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"
LOG_TO_CONSOLE = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"

# Log formats
# File format: With timestamp for production reliability
FILE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# Console format: With timestamp for local debugging
CONSOLE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class VeloSimLogger:
    """
    Centralized logging utility for VeloSim.

    Provides structured logging that can be collected by Promtail
    and visualized in Grafana via Loki.

    Usage:
        from grafana_logging.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
        logger.error("An error occurred", exc_info=True)
    """

    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False

    @classmethod
    def _ensure_log_file_exists(cls) -> None:
        """Ensure the log file and its directory exist."""
        if LOG_TO_FILE:
            log_path = Path(DEFAULT_LOG_FILE)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Create file if it doesn't exist
            if not log_path.exists():
                log_path.touch()

    @classmethod
    def _setup_handlers(cls) -> List[Union[logging.FileHandler, logging.StreamHandler]]:
        """Set up logging handlers for file and console output."""
        handlers: List[Union[logging.FileHandler, logging.StreamHandler]] = []

        # File handler - with timestamp for production reliability
        if LOG_TO_FILE:
            cls._ensure_log_file_exists()
            file_handler = logging.FileHandler(
                DEFAULT_LOG_FILE, mode="a", encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(FILE_LOG_FORMAT, DATE_FORMAT)
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)

        # Console handler - with timestamp for local debugging
        if LOG_TO_CONSOLE:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_formatter = logging.Formatter(CONSOLE_LOG_FORMAT, DATE_FORMAT)
            console_handler.setFormatter(console_formatter)
            handlers.append(console_handler)

        return handlers

    @classmethod
    def get_logger(cls, name: str, level: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance for the specified module.

        Args:
            name: Name of the logger (typically __name__ from the calling module)
            level: Optional log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Returns:
            A configured logger instance

        Example:
            >>> logger = VeloSimLogger.get_logger(__name__)
            >>> logger.info("Starting process")
            >>> logger.error("Error occurred", exc_info=True)
        """
        # Return existing logger if already created
        if name in cls._loggers:
            return cls._loggers[name]

        # Create new logger
        logger = logging.getLogger(name)

        # Set log level
        log_level = level or DEFAULT_LOG_LEVEL
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Add handlers only if not already added (avoid duplicate logs)
        if not logger.handlers:
            for handler in cls._setup_handlers():
                logger.addHandler(handler)

        # Prevent propagation to avoid duplicate logs
        logger.propagate = False

        # Cache the logger
        cls._loggers[name] = logger

        return logger

    @classmethod
    def log_request(
        cls,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        logger_name: str = "http",
    ) -> None:
        """
        Log an HTTP request in a structured format.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            logger_name: Name of the logger to use

        Returns:
            None

        Example:
            >>> VeloSimLogger.log_request("GET", "/api/v1/stations", 200, 45.2)
        """
        logger = cls.get_logger(logger_name)

        level = logging.INFO
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING

        logger.log(level, f"{method} {path} - {status_code} - {duration_ms:.2f}ms")

    @classmethod
    def log_simulation_event(
        cls,
        event_type: str,
        message: str,
        data: Optional[dict] = None,
        logger_name: str = "simulator",
    ) -> None:
        """
        Log a simulation event with optional structured data.

        Args:
            event_type: Type of event (START, STEP, COMPLETE, ERROR)
            message: Event message
            data: Optional dictionary of event data
            logger_name: Name of the logger to use

        Returns:
            None

        Example:
            >>> VeloSimLogger.log_simulation_event(
            ...     "STEP",
            ...     "Vehicle moved",
            ...     {"vehicle_id": 123, "position": (10, 20)}
            ... )
        """
        logger = cls.get_logger(logger_name)

        log_msg = f"[{event_type}] {message}"
        if data:
            # Format data for readability
            data_str = ", ".join([f"{k}={v}" for k, v in data.items()])
            log_msg += f" | {data_str}"

        logger.info(log_msg)


# Convenience function for easy importing
def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    This is the main entry point for getting loggers in the VeloSim application.

    Args:
        name: Name of the logger (use __name__ from your module)
        level: Optional log level override

    Returns:
        A configured logger instance

    Example:
        >>> from grafana_logging.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return VeloSimLogger.get_logger(name, level)


# Convenience functions for common logging patterns
def log_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    """Log an HTTP request. See VeloSimLogger.log_request for details.

    Args:
        method: HTTP method.
        path: Request path.
        status_code: HTTP status code.
        duration_ms: Request duration in milliseconds.

    Returns:
        None
    """
    VeloSimLogger.log_request(method, path, status_code, duration_ms)


def log_simulation_event(
    event_type: str, message: str, data: Optional[dict] = None
) -> None:
    """Log a simulation event. See VeloSimLogger.log_simulation_event for details.

    Args:
        event_type: Type of event.
        message: Event message.
        data: Optional dictionary of event data.

    Returns:
        None
    """
    VeloSimLogger.log_simulation_event(event_type, message, data)


# Initialize on import
if __name__ != "__main__":
    # Ensure log file exists when module is imported
    VeloSimLogger._ensure_log_file_exists()
