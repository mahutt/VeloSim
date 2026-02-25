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

from unittest.mock import patch, MagicMock
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from back.auth.dependency import get_user_id
from back.exceptions import BadRequestError, ItemNotFoundError, VelosimPermissionError
from back.main import app


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Create test client with authenticated user."""

    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


class TestCentralizedExceptionHandlers:
    """Validate centralized FastAPI handlers for domain exceptions."""

    @patch("back.crud.scenario.scenario_crud.get")
    def test_bad_request_error_maps_to_400(
        self, mock_get: MagicMock, authenticated_client: TestClient
    ) -> None:
        """BadRequestError should be converted to HTTP 400 by central handler."""
        mock_get.side_effect = BadRequestError("Bad scenario request")

        response = authenticated_client.get("/api/v1/scenarios/1")

        assert response.status_code == 400
        assert response.json()["detail"] == "Bad scenario request"

    @patch("back.crud.scenario.scenario_crud.get")
    def test_item_not_found_error_maps_to_404(
        self, mock_get: MagicMock, authenticated_client: TestClient
    ) -> None:
        """ItemNotFoundError should be converted to HTTP 404 by central handler."""
        mock_get.side_effect = ItemNotFoundError("Scenario not found")

        response = authenticated_client.get("/api/v1/scenarios/999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Scenario not found"

    @patch("back.crud.scenario.scenario_crud.get")
    def test_permission_error_maps_to_403(
        self, mock_get: MagicMock, authenticated_client: TestClient
    ) -> None:
        """VelosimPermissionError should be converted to HTTP 403 by central handler."""
        mock_get.side_effect = VelosimPermissionError("Forbidden scenario access")

        response = authenticated_client.get("/api/v1/scenarios/1")

        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden scenario access"
