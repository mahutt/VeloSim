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

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from typing import Generator
from back.main import app
from back.auth.dependency import get_user_id
from back.schemas.frontend_log import FrontendLogEntry
from back.services.frontend_log_service import frontend_log_service
from back.api.v1.logs import _rate_limit_store, MAX_LOGS_PER_MINUTE


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Create test client with authenticated user."""

    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


class TestFrontendLogSchema:
    """Test FrontendLogEntry schema validation."""

    def test_valid_log_entry(self) -> None:
        """Test creating a valid log entry matching frontend format."""
        entry = FrontendLogEntry.model_validate(
            {
                "message": "station with ID 123 not found in state",
                "timestamp": datetime.now().isoformat(),
                "context": "Missing station data",
                "entityType": "station",
                "entityId": 123,
                "errorType": "MISSING_ENTITY_DATA",
            }
        )
        assert entry.message == "station with ID 123 not found in state"
        assert entry.entityType == "station"
        assert entry.entityId == 123

    def test_message_max_length(self) -> None:
        """Test message exceeds max length."""
        with pytest.raises(ValueError):
            FrontendLogEntry.model_validate(
                {"message": "x" * 2001, "timestamp": datetime.now().isoformat()}
            )

    def test_with_stack_trace(self) -> None:
        """Test log entry with stack trace."""
        entry = FrontendLogEntry.model_validate(
            {
                "message": "Test error message",
                "timestamp": datetime.now().isoformat(),
                "stack": "Error: Test error\n  at Component.tsx:42",
                "userAgent": "Mozilla/5.0",
                "url": "https://app.velosim.com/simulation/123",
            }
        )
        assert entry.stack is not None
        assert "Component.tsx:42" in entry.stack
        assert entry.userAgent == "Mozilla/5.0"

    def test_optional_fields(self) -> None:
        """Test log entry with minimal required fields."""
        entry = FrontendLogEntry.model_validate(
            {"message": "Simple log message", "timestamp": datetime.now().isoformat()}
        )
        assert entry.message == "Simple log message"
        assert entry.stack is None
        assert entry.context is None
        assert entry.entityType is None

    def test_extra_fields_allowed(self) -> None:
        """Test that extra fields from frontend are allowed."""
        entry = FrontendLogEntry.model_validate(
            {
                "message": "Test",
                "timestamp": datetime.now().isoformat(),
                "customField": "custom value",
            }
        )
        assert entry.message == "Test"


class TestFrontendLogService:
    """Test FrontendLogService functionality."""

    def test_log_entry(self) -> None:
        """Test logging a single entry."""
        entry = FrontendLogEntry.model_validate(
            {
                "message": "Test error message",
                "timestamp": datetime.now().isoformat(),
                "context": "Test context",
                "entityType": "station",
                "entityId": 123,
            }
        )
        # Should not raise exception
        frontend_log_service.log_entry(entry, user_id=1)

    def test_log_batch(self) -> None:
        """Test logging a batch of entries."""
        entries = [
            FrontendLogEntry.model_validate(
                {
                    "message": f"Error message {i}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            for i in range(5)
        ]
        # Should not raise exception
        frontend_log_service.log_batch(entries, user_id=1)


class TestFrontendLogEndpoint:
    """Test frontend logging API endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Clear rate limit store before each test."""
        _rate_limit_store.clear()

    def test_log_entry_requires_auth(self, client: TestClient) -> None:
        """Test that logging requires authentication."""
        response = client.post(
            "/api/v1/logs/frontend",
            json={
                "level": "info",
                "message": "Test message",
                "timestamp": datetime.now().isoformat(),
            },
        )
        assert response.status_code == 401  # Unauthorized

    def test_log_entry_success(self, authenticated_client: TestClient) -> None:
        """Test successful log entry matching frontend format."""
        response = authenticated_client.post(
            "/api/v1/logs/frontend",
            json={
                "message": "station with ID 123 not found in state",
                "timestamp": datetime.now().isoformat(),
                "context": "Missing station data",
                "entityType": "station",
                "entityId": 123,
                "errorType": "MISSING_ENTITY_DATA",
                "userAgent": "Mozilla/5.0",
                "url": "https://app.velosim.com",
            },
        )
        assert response.status_code == 201
        assert response.json()["success"] is True

    def test_rate_limit_enforcement(self, authenticated_client: TestClient) -> None:
        """Test that rate limiting is enforced."""
        # Send MAX_LOGS_PER_MINUTE + 1 requests
        for i in range(MAX_LOGS_PER_MINUTE + 1):
            response = authenticated_client.post(
                "/api/v1/logs/frontend",
                json={
                    "message": f"Message {i}",
                    "timestamp": datetime.now().isoformat(),
                },
            )
            if i < MAX_LOGS_PER_MINUTE:
                assert response.status_code == 201
            else:
                # Last request should be rate limited
                assert response.status_code == 429
                assert "Rate limit exceeded" in response.json()["detail"]

    def test_batch_logging(self, authenticated_client: TestClient) -> None:
        """Test batch logging endpoint."""
        batch = [
            {
                "message": f"Batch message {i}",
                "timestamp": datetime.now().isoformat(),
            }
            for i in range(10)
        ]
        response = authenticated_client.post("/api/v1/logs/frontend/batch", json=batch)
        assert response.status_code == 201
        assert "10 entries" in response.json()["message"]

    def test_batch_size_limit(self, authenticated_client: TestClient) -> None:
        """Test batch size is limited to 50."""
        batch = [
            {
                "message": f"Message {i}",
                "timestamp": datetime.now().isoformat(),
            }
            for i in range(51)  # Exceeds limit
        ]
        response = authenticated_client.post("/api/v1/logs/frontend/batch", json=batch)
        assert response.status_code == 400
        assert "Batch size too large" in response.json()["detail"]

    def test_missing_required_fields(self, authenticated_client: TestClient) -> None:
        """Test that missing required fields are rejected."""
        response = authenticated_client.post(
            "/api/v1/logs/frontend",
            json={
                "timestamp": datetime.now().isoformat(),
                # Missing 'message' field
            },
        )
        assert response.status_code == 422  # Validation error

    def test_log_levels(self, authenticated_client: TestClient) -> None:
        """Test different log levels are accepted and defaults to error."""
        # Test explicit levels
        for level in ["debug", "info", "warn", "error"]:
            response = authenticated_client.post(
                "/api/v1/logs/frontend",
                json={
                    "message": f"Test {level} message",
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                },
            )
            assert response.status_code == 201
            assert response.json()["success"] is True

        # Test default level (should be error when not specified)
        response = authenticated_client.post(
            "/api/v1/logs/frontend",
            json={
                "message": "Test default level",
                "timestamp": datetime.now().isoformat(),
                # No level field
            },
        )
        assert response.status_code == 201
        assert response.json()["success"] is True
