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
import logging.handlers
import os
import sys
import time
import urllib.request
import atexit
import threading
from queue import Full, Queue
from typing import Any, Dict, List, Optional

# Configuration
DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_TO_CONSOLE = os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"
LOG_TO_LOKI = os.getenv("LOG_TO_LOKI", "true").lower() == "true"
LOG_TO_LOKI_ASYNC = os.getenv("LOG_TO_LOKI_ASYNC", "true").lower() == "true"
LOKI_URL = os.getenv("LOKI_URL", "http://velosim-loki:3100/loki/api/v1/push")
LOKI_QUEUE_SIZE = int(os.getenv("LOKI_QUEUE_SIZE", "10000"))

# Console log format
CONSOLE_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LokiHandler(logging.Handler):
    """
    Custom logging handler that sends logs directly to Loki via HTTP.

    This handler pushes logs to Loki's push API endpoint, eliminating the need
    for file-based log collection via Alloy/Promtail.
    """

    def __init__(
        self,
        url: str = LOKI_URL,
        labels: Optional[Dict[str, str]] = None,
        timeout: float = 2.0,
    ):
        """
        Initialize the Loki handler.

        Args:
            url: Loki push API URL
            labels: Static labels to add to all log entries
            timeout: HTTP request timeout in seconds
        """
        super().__init__()
        self.url = url
        self.labels = labels or {"job": "python_app"}
        self.timeout = timeout

    def emit(self, record: logging.LogRecord) -> None:
        """
        Send a log record to Loki.

        Args:
            record: The log record to send
        """
        try:
            # Build labels for this log entry
            labels = {
                **self.labels,
                "logger": record.name,
                "level": record.levelname,
            }

            # Add extra labels if present on the record
            if hasattr(record, "source"):
                labels["source"] = record.source
            if hasattr(record, "user_id"):
                labels["user_id"] = str(record.user_id)
            if hasattr(record, "context"):
                labels["context"] = record.context
            if hasattr(record, "entity_type"):
                labels["entity_type"] = record.entity_type
            if hasattr(record, "error_type"):
                labels["error_type"] = record.error_type

            # Format the log message
            message = self.format(record)

            # Loki expects timestamps in nanoseconds
            timestamp_ns = str(int(time.time() * 1_000_000_000))

            # Build the Loki push payload
            payload = {
                "streams": [
                    {
                        "stream": labels,
                        "values": [[timestamp_ns, message]],
                    }
                ]
            }

            # Send to Loki
            self._send_to_loki(payload)

        except Exception:
            # Don't let logging errors crash the application
            self.handleError(record)

    def _send_to_loki(self, payload: Dict[str, Any]) -> None:
        """
        Send payload to Loki via HTTP POST.

        Args:
            payload: The JSON payload to send
        """
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout):
                pass  # Success - Loki returns 204 No Content
        except Exception:
            # Silently ignore errors to avoid disrupting the application
            pass


class NonBlockingQueueHandler(logging.handlers.QueueHandler):
    """Queue handler that never blocks application threads."""

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except Full:
            # Drop records when queue is saturated to protect request latency.
            pass


class VeloSimLogger:
    """
    Centralized logging utility for VeloSim.

    Provides structured logging that is sent directly to Loki via HTTP
    and visualized in Grafana.

    Usage:
        from grafana_logging.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Application started")
        logger.error("An error occurred", exc_info=True)

    Environment variables:
        LOG_TO_LOKI: Enable Loki HTTP push (default: true)
        LOG_TO_LOKI_ASYNC: Enable asynchronous Loki push queue (default: true)
        LOKI_QUEUE_SIZE: Max buffered records in async mode (default: 10000)
        LOG_TO_CONSOLE: Enable console logging (default: true)
        LOKI_URL: Loki push API URL (default: http://velosim-loki:3100/loki/api/v1/push)
    """

    _loggers: Dict[str, logging.Logger] = {}
    _loki_queue: Optional[Queue[Any]] = None
    _loki_queue_handler: Optional[logging.Handler] = None
    _loki_queue_listener: Optional[logging.handlers.QueueListener] = None
    _loki_lock = threading.Lock()

    @classmethod
    def _build_loki_handler(cls) -> LokiHandler:
        loki_handler = LokiHandler(url=LOKI_URL)
        loki_handler.setLevel(logging.DEBUG)
        loki_formatter = logging.Formatter("%(asctime)s - %(message)s", DATE_FORMAT)
        loki_handler.setFormatter(loki_formatter)
        return loki_handler

    @classmethod
    def _stop_loki_listener(cls) -> None:
        if cls._loki_queue_listener is None:
            return
        try:
            cls._loki_queue_listener.stop()
        except Exception:
            pass

    @classmethod
    def _get_async_loki_handler(cls) -> logging.Handler:
        with cls._loki_lock:
            if cls._loki_queue_handler is not None:
                return cls._loki_queue_handler

            cls._loki_queue = Queue(maxsize=max(1, LOKI_QUEUE_SIZE))
            loki_handler = cls._build_loki_handler()

            cls._loki_queue_listener = logging.handlers.QueueListener(
                cls._loki_queue,
                loki_handler,
                respect_handler_level=True,
            )
            cls._loki_queue_listener.start()
            atexit.register(cls._stop_loki_listener)

            queue_handler = NonBlockingQueueHandler(cls._loki_queue)
            queue_handler.setLevel(logging.DEBUG)
            cls._loki_queue_handler = queue_handler
            return cls._loki_queue_handler

    @classmethod
    def _setup_handlers(cls) -> List[logging.Handler]:
        """Set up logging handlers for Loki and console output."""
        handlers: List[logging.Handler] = []

        # Loki handler - send logs directly to Loki via HTTP
        if LOG_TO_LOKI:
            if LOG_TO_LOKI_ASYNC:
                handlers.append(cls._get_async_loki_handler())
            else:
                handlers.append(cls._build_loki_handler())

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
