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
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from typing import Generator, Dict, Any

from back.main import app
from back.auth.dependency import get_user_id
from back.schemas.scenario import ScenarioResponse, ScenarioListResponse
from back.exceptions import ItemNotFoundError, VelosimPermissionError, BadRequestError


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Authenticated user fixture."""

    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def non_admin_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Non-admin user fixture."""

    def mock_get_user_id() -> int:
        return 2

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_scenario() -> ScenarioResponse:
    """Return a test scenario that passes Pydantic validation."""
    now = datetime.now(timezone.utc)
    return ScenarioResponse(
        id=1,
        name="Test Scenario",
        content={"foo": "bar"},
        description="A test scenario",
        user_id=1,
        date_created=now,
        date_updated=now,
    )


class TestScenariosAPI:
    """Test the scenarios API endpoints."""

    @patch("back.crud.scenario.scenario_crud.get_by_user")
    def test_get_scenarios_empty(
        self, mock_get_by_user: MagicMock, authenticated_client: TestClient
    ) -> None:
        """Test getting scenarios when DB is empty."""
        mock_get_by_user.return_value = ([], 0)
        response = authenticated_client.get("/api/v1/scenarios/?skip=0&limit=10")
        assert response.status_code == 200
        data = ScenarioListResponse.model_validate(response.json())
        assert data.total == 0
        assert data.scenarios == []
        assert data.page == 1
        assert data.per_page == 10
        assert data.total_pages == 0

    @patch("back.crud.scenario.scenario_crud.get_by_user")
    def test_get_scenarios_pagination(
        self,
        mock_get_by_user: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test getting scenarios with pagination."""
        fake_scenarios = [test_scenario.model_copy() for _ in range(15)]
        mock_get_by_user.return_value = (fake_scenarios[:10], 15)  # simulate limit=10
        response = authenticated_client.get("/api/v1/scenarios/?skip=0&limit=10")
        assert response.status_code == 200
        data = ScenarioListResponse.model_validate(response.json())
        assert data.total == 15
        assert len(data.scenarios) == 10
        assert data.page == 1
        assert data.per_page == 10
        assert data.total_pages == 2

    @patch("back.crud.scenario.scenario_crud.get")
    def test_get_scenario_by_id_success(
        self,
        mock_get: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test getting scenario by ID successfully."""
        mock_get.return_value = test_scenario
        response = authenticated_client.get("/api/v1/scenarios/1")
        assert response.status_code == 200
        data = ScenarioResponse.model_validate(response.json())
        assert data.id == test_scenario.id
        assert data.name == test_scenario.name
        assert data.content == test_scenario.content
        assert data.description == test_scenario.description

    @patch("back.crud.scenario.scenario_crud.get")
    def test_get_scenario_not_found(
        self, mock_get: MagicMock, authenticated_client: TestClient
    ) -> None:
        """Test scenario not found returns 404."""
        mock_get.side_effect = ItemNotFoundError("Scenario not found")
        response = authenticated_client.get("/api/v1/scenarios/999")
        assert response.status_code == 404
        assert "Scenario not found" in response.json()["detail"]

    @patch("back.crud.scenario.scenario_crud.get_by_user")
    def test_get_scenarios_permission_error(
        self, mock_get_by_user: MagicMock, authenticated_client: TestClient
    ) -> None:
        """Test permission error returns 403."""
        mock_get_by_user.side_effect = VelosimPermissionError("Forbidden")
        response = authenticated_client.get("/api/v1/scenarios/")
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    @patch("back.crud.scenario.scenario_crud.get_by_user")
    def test_get_scenarios_bad_request(
        self, mock_get_by_user: MagicMock, authenticated_client: TestClient
    ) -> None:
        """Test bad request error returns 400."""
        mock_get_by_user.side_effect = BadRequestError("Bad request")
        response = authenticated_client.get("/api/v1/scenarios/")
        assert response.status_code == 400
        assert "Bad request" in response.json()["detail"]

    @patch("back.crud.scenario.scenario_crud.get")
    def test_get_scenario_permission_error(
        self, mock_get: MagicMock, authenticated_client: TestClient
    ) -> None:
        """Test getting scenario by ID with permission error returns 403."""
        mock_get.side_effect = VelosimPermissionError("Forbidden")
        response = authenticated_client.get("/api/v1/scenarios/1")
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    @patch("back.crud.scenario.scenario_crud.get")
    def test_get_scenario_bad_request(
        self, mock_get: MagicMock, authenticated_client: TestClient
    ) -> None:
        """Test getting scenario by ID with bad request error returns 400."""
        mock_get.side_effect = BadRequestError("Bad request")
        response = authenticated_client.get("/api/v1/scenarios/1")
        assert response.status_code == 400
        assert "Bad request" in response.json()["detail"]

    def test_get_scenario_requires_authentication(self, client: TestClient) -> None:
        """Test unauthenticated request returns 401."""
        response = client.get("/api/v1/scenarios/1")
        assert response.status_code == 401

    # ==================== CREATE SCENARIO TESTS ====================

    @patch("back.api.v1.scenarios.JsonParseStrategy")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    @patch("back.crud.scenario.scenario_crud.create")
    def test_create_scenario_success(
        self,
        mock_create: MagicMock,
        mock_get_by_name: MagicMock,
        mock_parser_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test creating a scenario successfully."""
        # Mock the parser to return no errors
        mock_parser = MagicMock()
        mock_parser.validate.return_value = []
        mock_parser_class.return_value = mock_parser

        mock_get_by_name.return_value = None  # No duplicate
        mock_create.return_value = test_scenario

        response = authenticated_client.post(
            "/api/v1/scenarios/",
            json={
                "name": "Test Scenario",
                "content": {"foo": "bar"},
                "description": "A test scenario",
            },
        )
        assert response.status_code == 201
        data = ScenarioResponse.model_validate(response.json())
        assert data.name == test_scenario.name
        assert data.content == test_scenario.content

    @patch("back.api.v1.scenarios.JsonParseStrategy")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    @patch("back.crud.scenario.scenario_crud.create")
    def test_create_scenario_duplicate_name_not_allowed(
        self,
        mock_create: MagicMock,
        mock_get_by_name: MagicMock,
        mock_parser_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test creating scenario with duplicate name raises 400."""
        # Mock the parser to return no errors
        mock_parser = MagicMock()
        mock_parser.validate.return_value = []
        mock_parser_class.return_value = mock_parser

        mock_get_by_name.return_value = test_scenario  # Duplicate exists

        response = authenticated_client.post(
            "/api/v1/scenarios/",
            json={
                "name": "Test Scenario",
                "content": {"foo": "bar"},
                "allow_duplicate_name": False,
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @patch("back.api.v1.scenarios.JsonParseStrategy")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    @patch("back.crud.scenario.scenario_crud.create")
    def test_create_scenario_duplicate_name_allowed(
        self,
        mock_create: MagicMock,
        mock_get_by_name: MagicMock,
        mock_parser_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test creating scenario with duplicate name when explicitly allowed."""
        # Mock the parser to return no errors
        mock_parser = MagicMock()
        mock_parser.validate.return_value = []
        mock_parser_class.return_value = mock_parser

        mock_get_by_name.return_value = test_scenario  # Duplicate exists
        mock_create.return_value = test_scenario

        response = authenticated_client.post(
            "/api/v1/scenarios/",
            json={
                "name": "Test Scenario",
                "content": {"foo": "bar"},
                "allow_duplicate_name": True,
            },
        )
        assert response.status_code == 201

    @patch("back.api.v1.scenarios.JsonParseStrategy")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    def test_create_scenario_validation_error(
        self,
        mock_get_by_name: MagicMock,
        mock_parser_class: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test creating scenario with invalid content triggers validation errors."""
        # Mock the parser to return validation errors
        mock_parser = MagicMock()
        mock_parser.validate.return_value = [
            {
                "field": "content.stations",
                "message": "At least one station is required",
                "line": 5,
            }
        ]
        mock_parser_class.return_value = mock_parser

        mock_get_by_name.return_value = None

        response = authenticated_client.post(
            "/api/v1/scenarios/",
            json={
                "name": "Test",
                "content": {"foo": "bar"},  # Invalid content
            },
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["message"] == "Invalid scenario content"
        assert len(detail["errors"]) == 1
        assert detail["errors"][0]["field"] == "content.stations"
        assert detail["errors"][0]["line"] == 5

    def test_create_scenario_requires_authentication(self, client: TestClient) -> None:
        """Test creating scenario without authentication returns 401."""
        response = client.post(
            "/api/v1/scenarios/",
            json={"name": "Test", "content": {"foo": "bar"}},
        )
        assert response.status_code == 401

    # ==================== UPDATE SCENARIO TESTS ====================

    @patch("back.api.v1.scenarios.JsonParseStrategy")
    @patch("back.crud.scenario.scenario_crud.update")
    def test_update_scenario_success(
        self,
        mock_update: MagicMock,
        mock_parser_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test updating a scenario successfully."""
        # Mock the parser (not called when only updating name)
        mock_parser = MagicMock()
        mock_parser.validate.return_value = []
        mock_parser_class.return_value = mock_parser

        updated_scenario = test_scenario.model_copy()
        updated_scenario.name = "Updated Name"
        mock_update.return_value = updated_scenario

        response = authenticated_client.put(
            "/api/v1/scenarios/1",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = ScenarioResponse.model_validate(response.json())
        assert data.name == "Updated Name"
        # Parser should not be called when content is not being updated
        mock_parser.validate.assert_not_called()

    @patch("back.crud.scenario.scenario_crud.update")
    def test_update_scenario_not_found(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test updating non-existent scenario returns 404."""
        mock_update.side_effect = ItemNotFoundError("Scenario not found")

        response = authenticated_client.put(
            "/api/v1/scenarios/999",
            json={"name": "Updated"},
        )
        assert response.status_code == 404

    @patch("back.crud.scenario.scenario_crud.update")
    def test_update_scenario_no_fields(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test updating scenario with no fields returns 400."""
        mock_update.side_effect = BadRequestError("No valid fields to update")

        response = authenticated_client.put("/api/v1/scenarios/1", json={})
        assert response.status_code == 400

    @patch("back.api.v1.scenarios.JsonParseStrategy")
    @patch("back.crud.scenario.scenario_crud.update")
    def test_update_scenario_with_content_validation(
        self,
        mock_update: MagicMock,
        mock_parser_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test updating scenario content triggers validation."""
        # Mock the parser to return no errors
        mock_parser = MagicMock()
        mock_parser.validate.return_value = []
        mock_parser_class.return_value = mock_parser

        updated_scenario = test_scenario.model_copy()
        updated_scenario.content = {"new": "content"}
        mock_update.return_value = updated_scenario

        response = authenticated_client.put(
            "/api/v1/scenarios/1",
            json={"content": {"new": "content"}},
        )
        assert response.status_code == 200
        # Parser should be called when content is being updated
        mock_parser.validate.assert_called_once()

    @patch("back.api.v1.scenarios.JsonParseStrategy")
    def test_update_scenario_validation_error(
        self,
        mock_parser_class: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test updating scenario with invalid content triggers validation errors."""
        # Mock the parser to return validation errors
        mock_parser = MagicMock()
        mock_parser.validate.return_value = [
            {
                "field": "content.resources",
                "message": "Invalid resource configuration",
                "line": 10,
            }
        ]
        mock_parser_class.return_value = mock_parser

        response = authenticated_client.put(
            "/api/v1/scenarios/1",
            json={"content": {"invalid": "data"}},
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["message"] == "Invalid scenario content"
        assert len(detail["errors"]) == 1
        assert detail["errors"][0]["field"] == "content.resources"
        assert detail["errors"][0]["line"] == 10

    def test_update_scenario_requires_authentication(self, client: TestClient) -> None:
        """Test updating scenario without authentication returns 401."""
        response = client.put(
            "/api/v1/scenarios/1",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    # ==================== DELETE SCENARIO TESTS ====================

    @patch("back.crud.scenario.scenario_crud.delete")
    def test_delete_scenario_success(
        self,
        mock_delete: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test deleting a scenario successfully."""
        mock_delete.return_value = None

        response = authenticated_client.delete("/api/v1/scenarios/1")
        assert response.status_code == 204
        assert response.content == b""

    @patch("back.crud.scenario.scenario_crud.delete")
    def test_delete_scenario_not_found(
        self,
        mock_delete: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test deleting non-existent scenario returns 404."""
        mock_delete.side_effect = ItemNotFoundError("Scenario not found")

        response = authenticated_client.delete("/api/v1/scenarios/999")
        assert response.status_code == 404

    @patch("back.crud.scenario.scenario_crud.delete")
    def test_delete_scenario_permission_error(
        self,
        mock_delete: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test deleting another user's scenario returns 403."""
        mock_delete.side_effect = VelosimPermissionError("Not authorized")

        response = authenticated_client.delete("/api/v1/scenarios/1")
        assert response.status_code == 403

    def test_delete_scenario_requires_authentication(self, client: TestClient) -> None:
        """Test deleting scenario without authentication returns 401."""
        response = client.delete("/api/v1/scenarios/1")
        assert response.status_code == 401


class TestScenarioValidation:
    """Test class for scenario validation endpoint."""

    def test_validate_valid_content(self, client: TestClient) -> None:
        """Test validating valid scenario content."""
        valid_content = {
            "content": {
                "start_time": "day1:08:00",
                "end_time": "day1:12:00",
                "stations": [
                    {
                        "station_id": 1,
                        "station_name": "Station 1",
                        "task_count": 2,
                        "station_position": [45.5, -73.5],
                    }
                ],
                "resources": [
                    {
                        "resource_id": 1,
                        "task_count": 2,
                        "resource_position": [45.5, -73.5],
                    }
                ],
                "initial_tasks": [{"station_id": "1"}],
                "scheduled_tasks": [{"station_id": "1"}],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=valid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_missing_required_fields(self, client: TestClient) -> None:
        """Test validation fails when required fields are missing."""
        invalid_content: Dict[str, Any] = {
            "content": {
                "stations": [],
                "resources": [],
                # Missing start_time and end_time
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        # Check that errors mention missing time fields
        error_fields = [err["field"] for err in data["errors"]]
        assert any("start_time" in field for field in error_fields)
        assert any("end_time" in field for field in error_fields)

    def test_validate_invalid_time_format(self, client: TestClient) -> None:
        """Test validation fails with invalid time format."""
        invalid_content = {
            "content": {
                "start_time": "8AM",  # Invalid format
                "end_time": "1200",  # Invalid format
                "stations": [],
                "resources": [],
                "initial_tasks": [],
                "scheduled_tasks": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_end_time_before_start_time(self, client: TestClient) -> None:
        """Test validation fails when end_time is before start_time."""
        invalid_content = {
            "content": {
                "start_time": "day1:12:00",
                "end_time": "day1:08:00",
                "stations": [],
                "resources": [],
                "initial_tasks": [],
                "scheduled_tasks": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any(
            "end_time" in err["field"] and "after" in err["message"]
            for err in data["errors"]
        )

    def test_validate_duplicate_station_id(self, client: TestClient) -> None:
        """Test validation fails with duplicate station IDs."""
        invalid_content = {
            "content": {
                "start_time": "day1:08:00",
                "end_time": "day1:12:00",
                "stations": [
                    {
                        "station_id": 1,
                        "station_name": "Station 1",
                        "task_count": 2,
                        "station_position": [45.5, -73.5],
                    },
                    {
                        "station_id": 1,  # Duplicate
                        "station_name": "Station 2",
                        "task_count": 2,
                        "station_position": [45.6, -73.6],
                    },
                ],
                "resources": [],
                "initial_tasks": [],
                "scheduled_tasks": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any("Duplicate station ID" in err["message"] for err in data["errors"])

    def test_validate_task_with_nonexistent_station(self, client: TestClient) -> None:
        """Test validation fails when task references non-existent station."""
        invalid_content = {
            "content": {
                "start_time": "day1:08:00",
                "end_time": "day1:12:00",
                "stations": [
                    {
                        "station_id": 1,
                        "station_name": "Station 1",
                        "task_count": 1,
                        "station_position": [45.5, -73.5],
                    }
                ],
                "resources": [],
                "initial_tasks": [{"station_id": "999"}],  # Non-existent station
                "scheduled_tasks": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any("does not exist" in err["message"] for err in data["errors"])

    def test_validate_no_authentication_required(self, client: TestClient) -> None:
        """Test validation endpoint does not require authentication."""
        valid_content = {
            "content": {
                "start_time": "day1:08:00",
                "end_time": "day1:12:00",
                "stations": [],
                "resources": [],
                "initial_tasks": [],
                "scheduled_tasks": [],
            }
        }

        # Should work without authentication
        response = client.post("/api/v1/scenarios/validate", json=valid_content)
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "errors" in data


class TestValidateScenario:
    """Test cases for POST /api/v1/scenarios/validate endpoint."""

    def test_validate_valid_scenario_content(self, client: TestClient) -> None:
        """Test validating valid scenario content returns success."""
        valid_content = {
            "content": {
                "start_time": "day1:08:00",
                "end_time": "day1:17:00",
                "stations": [
                    {
                        "station_id": 1,
                        "station_name": "Station Alpha",
                        "station_position": [45.5017, -73.5673],
                        "task_count": 2,
                    }
                ],
                "resources": [
                    {
                        "resource_id": 101,
                        "resource_position": [45.505, -73.56],
                        "task_count": 2,
                    }
                ],
                "initial_tasks": [{"station_id": "1"}],
                "scheduled_tasks": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=valid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_invalid_scenario_content(self, client: TestClient) -> None:
        """Test validating invalid scenario content returns errors."""
        invalid_content: Dict[str, Any] = {
            "content": {
                # Missing start_time and end_time
                "stations": [],
                "resources": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        # Should have errors for missing start_time and end_time
        error_fields = [err["field"] for err in data["errors"]]
        assert "start_time" in error_fields
        assert "end_time" in error_fields

    def test_validate_invalid_time_format(self, client: TestClient) -> None:
        """Test validating scenario with invalid time format."""
        invalid_content = {
            "content": {
                "start_time": "8AM",  # Invalid format
                "end_time": "5PM",  # Invalid format
                "stations": [],
                "resources": [],
                "initial_tasks": [],
                "scheduled_tasks": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_end_time_before_start_time(self, client: TestClient) -> None:
        """Test validating scenario where end_time is before start_time."""
        invalid_content = {
            "content": {
                "start_time": "day1:17:00",
                "end_time": "day1:08:00",  # Before start_time
                "stations": [],
                "resources": [],
                "initial_tasks": [],
                "scheduled_tasks": [],
            }
        }

        response = client.post("/api/v1/scenarios/validate", json=invalid_content)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any("after" in err["message"].lower() for err in data["errors"])

    def test_validate_no_authentication_required(self, client: TestClient) -> None:
        """Test that validation endpoint does not require authentication."""
        valid_content = {
            "content": {
                "start_time": "day1:08:00",
                "end_time": "day1:17:00",
                "stations": [],
                "resources": [],
                "initial_tasks": [],
                "scheduled_tasks": [],
            }
        }

        # Should work without authentication
        response = client.post("/api/v1/scenarios/validate", json=valid_content)
        assert response.status_code == 200

    def test_validate_invalid_utf8_encoding(self, client: TestClient) -> None:
        """Test that validation endpoint handles invalid UTF-8 encoding gracefully."""
        # Send raw bytes with invalid UTF-8 sequence
        invalid_utf8_bytes = b'{"content": {"start_time": "\xff\xfe"}}'

        response = client.post(
            "/api/v1/scenarios/validate",
            content=invalid_utf8_bytes,
            headers={"Content-Type": "application/json"},
        )

        # FastAPI/Starlette handles this before our endpoint
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_validate_unicode_decode_error_handling(self, client: TestClient) -> None:
        """Test that the endpoint handles UnicodeDecodeError in request body parsing."""
        from unittest.mock import AsyncMock
        from back.api.v1.scenarios import (
            validate_scenario_content,
            ValidationRequest,
        )
        import asyncio

        valid_content = {
            "content": {
                "start_time": "day1:08:00",
                "end_time": "day1:17:00",
                "stations": [],
                "resources": [],
            }
        }

        # Create a mock bytes object that raises UnicodeDecodeError on decode()
        class BadBytes:
            def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")

        # Mock request with body() returning our BadBytes
        mock_request = AsyncMock()
        mock_request.body = AsyncMock(return_value=BadBytes())

        # Call the endpoint directly
        result = asyncio.run(
            validate_scenario_content(mock_request, ValidationRequest(**valid_content))
        )

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0]["field"] == "content"
        assert "UTF-8 encoding" in result.errors[0]["message"]
