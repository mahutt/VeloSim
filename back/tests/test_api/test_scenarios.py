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
from typing import Any, Generator

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

    @patch("back.api.v1.scenarios.ScenarioValidator")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    @patch("back.crud.scenario.scenario_crud.create")
    def test_create_scenario_success(
        self,
        mock_create: MagicMock,
        mock_get_by_name: MagicMock,
        mock_validator_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test creating a scenario successfully."""
        # Mock the validator to return no errors
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = []
        mock_validator_class.return_value = mock_validator

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

    @patch("back.api.v1.scenarios.ScenarioValidator")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    @patch("back.crud.scenario.scenario_crud.create")
    def test_create_scenario_duplicate_name_not_allowed(
        self,
        mock_create: MagicMock,
        mock_get_by_name: MagicMock,
        mock_validator_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test creating scenario with duplicate name raises 400."""
        # Mock the validator to return no errors
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = []
        mock_validator_class.return_value = mock_validator

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

    @patch("back.api.v1.scenarios.ScenarioValidator")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    @patch("back.crud.scenario.scenario_crud.create")
    def test_create_scenario_duplicate_name_allowed(
        self,
        mock_create: MagicMock,
        mock_get_by_name: MagicMock,
        mock_validator_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test creating scenario with duplicate name when explicitly allowed."""
        # Mock the validator to return no errors
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = []
        mock_validator_class.return_value = mock_validator

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

    @patch("back.api.v1.scenarios.ScenarioValidator")
    @patch("back.crud.scenario.scenario_crud.get_by_name_and_user")
    def test_create_scenario_validation_error(
        self,
        mock_get_by_name: MagicMock,
        mock_validator_class: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test creating scenario with invalid content triggers validation errors."""
        # Mock the validator to return validation errors
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [
            {"field": "content.stations", "message": "At least one station is required"}
        ]
        mock_validator_class.return_value = mock_validator

        mock_get_by_name.return_value = None

        response = authenticated_client.post(
            "/api/v1/scenarios/",
            json={
                "name": "Test",
                "content": {"foo": "bar"},  # Invalid content
            },
        )
        assert response.status_code == 400
        assert "Invalid scenario content" in response.json()["detail"]

    def test_create_scenario_requires_authentication(self, client: TestClient) -> None:
        """Test creating scenario without authentication returns 401."""
        response = client.post(
            "/api/v1/scenarios/",
            json={"name": "Test", "content": {"foo": "bar"}},
        )
        assert response.status_code == 401

    # ==================== UPDATE SCENARIO TESTS ====================

    @patch("back.api.v1.scenarios.ScenarioValidator")
    @patch("back.crud.scenario.scenario_crud.update")
    def test_update_scenario_success(
        self,
        mock_update: MagicMock,
        mock_validator_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test updating a scenario successfully."""
        # Mock the validator (not called when only updating name)
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = []
        mock_validator_class.return_value = mock_validator

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
        # Validator should not be called when content is not being updated
        mock_validator.validate_all.assert_not_called()

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

    @patch("back.api.v1.scenarios.ScenarioValidator")
    @patch("back.crud.scenario.scenario_crud.update")
    def test_update_scenario_with_content_validation(
        self,
        mock_update: MagicMock,
        mock_validator_class: MagicMock,
        authenticated_client: TestClient,
        test_scenario: ScenarioResponse,
    ) -> None:
        """Test updating scenario content triggers validation."""
        # Mock the validator to return no errors
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = []
        mock_validator_class.return_value = mock_validator

        updated_scenario = test_scenario.model_copy()
        updated_scenario.content = {"new": "content"}
        mock_update.return_value = updated_scenario

        response = authenticated_client.put(
            "/api/v1/scenarios/1",
            json={"content": {"new": "content"}},
        )
        assert response.status_code == 200
        # Validator should be called when content is being updated
        mock_validator.validate_all.assert_called_once_with({"new": "content"})

    @patch("back.api.v1.scenarios.ScenarioValidator")
    def test_update_scenario_validation_error(
        self,
        mock_validator_class: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test updating scenario with invalid content triggers validation errors."""
        # Mock the validator to return validation errors
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = [
            {"field": "content.resources", "message": "Invalid resource configuration"}
        ]
        mock_validator_class.return_value = mock_validator

        response = authenticated_client.put(
            "/api/v1/scenarios/1",
            json={"content": {"invalid": "data"}},
        )
        assert response.status_code == 400
        assert "Invalid scenario content" in response.json()["detail"]

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

    # ============= Template Endpoint Tests =============

    def test_get_scenario_template_success(
        self, authenticated_client: TestClient
    ) -> None:
        """Test getting scenario template returns valid structure."""
        response = authenticated_client.get("/api/v1/scenarios/template")

        assert response.status_code == 200
        data = response.json()

        # Verify response has content and description
        assert "content" in data
        assert "description" in data

        # Verify template has all required fields
        content = data["content"]
        assert "scenario_title" in content
        assert "start_time" in content
        assert "end_time" in content
        assert "stations" in content
        assert "resources" in content
        assert "initial_tasks" in content

        # Verify stations structure
        assert isinstance(content["stations"], list)
        assert len(content["stations"]) > 0
        station = content["stations"][0]
        assert "station_id" in station
        assert "station_name" in station
        assert "task_count" in station
        assert "station_position" in station
        assert isinstance(station["station_position"], list)
        assert len(station["station_position"]) == 2

        # Verify resources structure
        assert isinstance(content["resources"], list)
        assert len(content["resources"]) > 0
        resource = content["resources"][0]
        assert "resource_id" in resource
        assert "task_count" in resource
        assert "resource_position" in resource
        assert isinstance(resource["resource_position"], list)
        assert len(resource["resource_position"]) == 2

        # Verify initial_tasks structure
        assert isinstance(content["initial_tasks"], list)
        assert len(content["initial_tasks"]) > 0
        task = content["initial_tasks"][0]
        assert "id" in task
        assert "station_id" in task
        assert "time" in task

    def test_get_scenario_template_requires_authentication(
        self, client: TestClient
    ) -> None:
        """Test template endpoint requires authentication."""
        response = client.get("/api/v1/scenarios/template")
        assert response.status_code == 401

    # ============= Validate Endpoint Tests =============

    @patch("back.services.scenario_validation_service.ScenarioValidator.validate_all")
    def test_validate_scenario_success(
        self,
        mock_validate: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test validating valid scenario returns no errors."""
        mock_validate.return_value = []

        request_data = {
            "content": {
                "scenario_title": "Test Scenario",
                "start_time": "08:00",
                "end_time": "17:00",
                "stations": [
                    {
                        "station_id": 1,
                        "station_name": "Station 1",
                        "task_count": 5,
                        "station_position": [40.7128, -74.0060],
                    }
                ],
                "resources": [
                    {
                        "resource_id": 1,
                        "task_count": 10,
                        "resource_position": [40.7128, -74.0060],
                    }
                ],
                "initial_tasks": [{"id": "task_1", "station_id": "1", "time": "08:30"}],
            }
        }

        response = authenticated_client.post(
            "/api/v1/scenarios/validate", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []
        assert isinstance(data["warnings"], list)

    @patch("back.services.scenario_validation_service.ScenarioValidator.validate_all")
    def test_validate_scenario_with_errors(
        self,
        mock_validate: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test validating invalid scenario returns errors."""
        mock_validate.return_value = [
            {"message": "Invalid latitude/longitude range"},
            {"message": "Duplicate station ID"},
        ]

        request_data = {
            "content": {
                "scenario_title": "Invalid Scenario",
                "start_time": "08:00",
                "end_time": "17:00",
                "stations": [],
                "resources": [],
                "initial_tasks": [],
            }
        }

        response = authenticated_client.post(
            "/api/v1/scenarios/validate", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) == 2
        assert "Invalid latitude/longitude range" in data["errors"]
        assert "Duplicate station ID" in data["errors"]

    @patch("back.services.scenario_validation_service.ScenarioValidator.validate_all")
    def test_validate_scenario_with_warnings(
        self,
        mock_validate: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test validation includes warnings for missing optional data."""
        mock_validate.return_value = []

        request_data = {
            "content": {
                "scenario_title": "Test Scenario",
                "start_time": "08:00",
                "end_time": "17:00",
                "stations": [],  # No stations
                "resources": [],  # No resources
                "initial_tasks": [],
            }
        }

        response = authenticated_client.post(
            "/api/v1/scenarios/validate", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["warnings"]) == 2
        assert any("resources" in w.lower() for w in data["warnings"])
        assert any("stations" in w.lower() for w in data["warnings"])

    @patch("back.services.scenario_validation_service.ScenarioValidator.validate_all")
    def test_validate_scenario_rfc3339_datetime(
        self,
        mock_validate: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test validation works with RFC 3339 datetime format."""
        mock_validate.return_value = []

        request_data = {
            "content": {
                "scenario_title": "Full Day Scenario",
                "start_time": "2025-11-06T08:00:00Z",
                "end_time": "2025-11-07T08:00:00Z",  # Exactly 24 hours
                "stations": [
                    {
                        "station_id": 1,
                        "station_name": "Station 1",
                        "task_count": 5,
                        "station_position": [40.7128, -74.0060],
                    }
                ],
                "resources": [
                    {
                        "resource_id": 1,
                        "task_count": 10,
                        "resource_position": [40.7128, -74.0060],
                    }
                ],
                "initial_tasks": [],
            }
        }

        response = authenticated_client.post(
            "/api/v1/scenarios/validate", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_scenario_requires_authentication(
        self, authenticated_client: TestClient
    ) -> None:
        """Test validate endpoint requires authentication."""
        request_data = {
            "content": {
                "scenario_title": "Test",
                "start_time": "08:00",
                "end_time": "17:00",
                "stations": [],
                "resources": [],
                "initial_tasks": [],
            }
        }

        # Should work with authentication
        response = authenticated_client.post(
            "/api/v1/scenarios/validate", json=request_data
        )
        assert response.status_code == 200

    def test_validate_scenario_missing_content(
        self, authenticated_client: TestClient
    ) -> None:
        """Test validation fails with missing content field."""
        request_data: dict[str, Any] = {}  # Missing content

        response = authenticated_client.post(
            "/api/v1/scenarios/validate", json=request_data
        )

        # Should return 422 for validation error (missing required field)
        assert response.status_code == 422

    @patch("back.services.scenario_validation_service.ScenarioValidator.validate_all")
    def test_validate_scenario_empty_content(
        self,
        mock_validate: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test validation with minimal empty content."""
        mock_validate.return_value = [
            {"message": "Missing required field 'scenario_title'"},
            {"message": "Missing required field 'start_time'"},
            {"message": "Missing required field 'end_time'"},
        ]

        request_data: dict[str, Any] = {"content": {}}

        response = authenticated_client.post(
            "/api/v1/scenarios/validate", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) >= 3
