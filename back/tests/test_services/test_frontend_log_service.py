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
from back.services.frontend_log_service import frontend_log_service
from back.schemas.frontend_log import FrontendLogEntry, LogLevel


def test_log_entry_increments_metrics_with_context() -> None:
    """Test that metrics counter is incremented when context is provided."""
    with patch(
        "back.services.frontend_log_service.frontend_action_counter"
    ) as mock_counter:
        log_entry = FrontendLogEntry(
            message="Test action",
            timestamp="2026-01-02T10:00:00Z",
            level=LogLevel.INFO,
            stack=None,
            context="scenario_export",
            userAgent=None,
            url=None,
            entityType=None,
            entityId=None,
            errorType=None,
        )

        frontend_log_service.log_entry(log_entry, user_id=123)

        # Verify counter was incremented with correct labels
        mock_counter.add.assert_called_once_with(
            1,
            {
                "action": "scenario_export",
                "user_id": "123",
            },
        )


def test_log_entry_without_context_does_not_increment_metrics() -> None:
    """Test that metrics counter is NOT incremented when context is missing."""
    with patch(
        "back.services.frontend_log_service.frontend_action_counter"
    ) as mock_counter:
        log_entry = FrontendLogEntry(
            message="Test error",
            timestamp="2026-01-02T10:00:00Z",
            level=LogLevel.ERROR,
            stack=None,
            context=None,
            userAgent=None,
            url=None,
            entityType=None,
            entityId=None,
            errorType=None,
        )

        frontend_log_service.log_entry(log_entry, user_id=123)

        # Verify counter was NOT called
        mock_counter.add.assert_not_called()


def test_log_entry_with_different_actions() -> None:
    """Test that different action contexts are tracked correctly."""
    with patch(
        "back.services.frontend_log_service.frontend_action_counter"
    ) as mock_counter:
        actions = [
            ("scenario_export", LogLevel.INFO),
            ("scenario_import", LogLevel.INFO),
            ("simulation_initialize", LogLevel.INFO),
            ("user_login", LogLevel.INFO),
        ]

        for action, level in actions:
            log_entry = FrontendLogEntry(
                message=f"Test {action}",
                timestamp="2026-01-02T10:00:00Z",
                level=level,
                stack=None,
                context=action,
                userAgent=None,
                url=None,
                entityType=None,
                entityId=None,
                errorType=None,
            )
            frontend_log_service.log_entry(log_entry, user_id=456)

        # Verify counter was called for each action
        assert mock_counter.add.call_count == len(actions)


def test_log_entry_passes_loki_labels_via_extra() -> None:
    """Test that log_entry passes frontend labels as Loki stream labels via extra."""
    with patch.object(frontend_log_service.logger, "error") as mock_log:
        log_entry = FrontendLogEntry(
            message="Station not found",
            timestamp="2026-01-02T10:00:00Z",
            level=LogLevel.ERROR,
            stack=None,
            context="Missing station data",
            userAgent=None,
            url=None,
            entityType="station",
            entityId=42,
            errorType="MISSING_ENTITY_DATA",
        )

        frontend_log_service.log_entry(log_entry, user_id=99)

        mock_log.assert_called_once()
        _, kwargs = mock_log.call_args
        extra = kwargs["extra"]

        assert extra["source"] == "frontend"
        assert extra["user_id"] == 99
        assert extra["context"] == "Missing station data"
        assert extra["entity_type"] == "station"
        assert extra["error_type"] == "MISSING_ENTITY_DATA"


def test_log_entry_with_no_user_id() -> None:
    """Test that metrics work when user_id is None."""
    with patch(
        "back.services.frontend_log_service.frontend_action_counter"
    ) as mock_counter:
        log_entry = FrontendLogEntry(
            message="Test action",
            timestamp="2026-01-02T10:00:00Z",
            level=LogLevel.INFO,
            stack=None,
            context="scenario_delete",
            userAgent=None,
            url=None,
            entityType=None,
            entityId=None,
            errorType=None,
        )

        frontend_log_service.log_entry(log_entry, user_id=None)

        # Verify counter uses "unknown" for missing user_id
        mock_counter.add.assert_called_once_with(
            1,
            {
                "action": "scenario_delete",
                "user_id": "unknown",
            },
        )
