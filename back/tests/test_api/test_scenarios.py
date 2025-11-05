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
from typing import Generator

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
