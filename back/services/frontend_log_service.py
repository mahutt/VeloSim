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
from typing import Optional
from back.schemas.frontend_log import FrontendLogEntry
from grafana_logging.logger import VeloSimLogger
from opentelemetry import metrics

meter = metrics.get_meter("velosim.frontend")

frontend_action_counter = meter.create_counter(
    name="frontend.action.total",
    description="Count of frontend actions by type",
)


class FrontendLogService:
    """Service for handling frontend log entries."""

    def __init__(self) -> None:
        """Initialize the frontend logging service."""
        self.logger = VeloSimLogger.get_logger("frontend")

    def log_entry(
        self, log_entry: FrontendLogEntry, user_id: Optional[int] = None
    ) -> None:
        """
        Process and log a frontend log entry.

        Args:
            log_entry: The frontend log entry to process
            user_id: Optional user ID from authentication

        Returns:
            None
        """
        # Build structured log message matching frontend's format
        log_data = {
            "source": "frontend",
            "level": log_entry.level.value if log_entry.level else "error",
            "message": log_entry.message,
            "timestamp": log_entry.timestamp,
            "user_id": user_id,
        }

        # Add optional fields if present
        if log_entry.stack:
            log_data["stack"] = log_entry.stack
        if log_entry.context:
            log_data["context"] = log_entry.context
        if log_entry.userAgent:
            log_data["userAgent"] = log_entry.userAgent
        if log_entry.url:
            log_data["url"] = log_entry.url
        if log_entry.entityType:
            log_data["entityType"] = log_entry.entityType
        if log_entry.entityId is not None:
            log_data["entityId"] = log_entry.entityId
        if log_entry.errorType:
            log_data["errorType"] = log_entry.errorType

        # Add any extra fields frontend might have sent
        if hasattr(log_entry, "__pydantic_extra__") and log_entry.__pydantic_extra__:
            log_data.update(log_entry.__pydantic_extra__)

        # Format as JSON for structured logging
        log_message = json.dumps(log_data)

        # Build extra labels to be added as Loki stream labels (queryable in Grafana)
        extra: dict = {"source": "frontend"}
        if user_id is not None:
            extra["user_id"] = user_id
        if log_entry.context:
            extra["context"] = log_entry.context
        if log_entry.entityType:
            extra["entity_type"] = log_entry.entityType
        if log_entry.errorType:
            extra["error_type"] = log_entry.errorType

        # Log at the appropriate level based on frontend's level field
        # Defaults to ERROR if not specified (backward compatible)
        level_map = {
            "debug": self.logger.debug,
            "info": self.logger.info,
            "warn": self.logger.warning,
            "error": self.logger.error,
        }
        log_func = level_map.get(
            log_entry.level.value if log_entry.level else "error", self.logger.error
        )
        log_func(log_message, extra=extra)

        if log_entry.context:
            frontend_action_counter.add(
                1,
                {
                    "action": log_entry.context,
                    "user_id": str(user_id) if user_id is not None else "unknown",
                },
            )

    def log_batch(
        self, log_entries: list[FrontendLogEntry], user_id: Optional[int] = None
    ) -> None:
        """
        Process and log multiple frontend log entries.

        Args:
            log_entries: List of frontend log entries to process
            user_id: Optional user ID from authentication

        Returns:
            None
        """
        for entry in log_entries:
            self.log_entry(entry, user_id)


# Singleton instance
frontend_log_service = FrontendLogService()
