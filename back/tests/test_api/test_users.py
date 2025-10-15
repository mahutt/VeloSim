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
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Generator
from back.main import app
from back.auth.dependency import get_user_id
from back.exceptions.bad_request_error import BadRequestError
from back.exceptions.velosim_permission_error import VelosimPermissionError


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Create test client with authenticated user."""

    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def non_admin_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Create test client with non-admin user."""

    def mock_get_user_id() -> int:
        return 2

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


class TestUsersAPI:
    """Test the users API endpoints."""

    @patch("back.api.v1.users.user_crud.create")
    def test_create_user_success(
        self, mock_create: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test creating a user successfully."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "test_user"
        mock_user.email = "test@example.com"
        mock_user.is_admin = False
        mock_create.return_value = mock_user

        user_data = {
            "username": "test_user",
            "password": "test_password",
            "is_admin": False,
        }

        response = authenticated_client.post("/api/v1/users/create", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["username"] == "test_user"
        assert data["is_admin"] is False
        mock_create.assert_called_once()

    @patch("back.api.v1.users.user_crud.create")
    def test_create_user_bad_request(
        self, mock_create: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test creating a user with bad request error."""
        mock_create.side_effect = BadRequestError("Username already exists")

        user_data = {
            "username": "existing_user",
            "password": "test_password",
            "is_admin": False,
        }

        response = authenticated_client.post("/api/v1/users/create", json=user_data)

        assert response.status_code == 400
        data = response.json()
        assert "Username already exists" in str(data["detail"])

    @patch("back.api.v1.users.user_crud.create")
    def test_create_user_permission_error(
        self, mock_create: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test creating a user with permission error."""
        mock_create.side_effect = VelosimPermissionError(
            "Requesting user cannot create users."
        )

        user_data = {
            "username": "test_user",
            "password": "test_password",
            "is_admin": False,
        }

        response = authenticated_client.post("/api/v1/users/create", json=user_data)

        assert response.status_code == 401
        data = response.json()
        assert "Requesting user cannot create users." in str(data["detail"])

    def test_create_user_invalid_data(
        self, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test creating a user with missing data."""
        response = authenticated_client.post(
            "/api/v1/users/create", json={"username": "test_user"}
        )
        assert response.status_code == 422

    def test_create_user_no_authentication(
        self, client: TestClient, db: Session
    ) -> None:
        """Test that authentication is required for creating users."""
        user_data = {
            "username": "test_user",
            "password": "test_password",
            "is_admin": False,
        }

        # Use the base client without auth override
        response = client.post("/api/v1/users/create", json=user_data)

        # Should fail due to authentication
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.create")
    def test_create_user_non_admin_forbidden(
        self, mock_create: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        """Test non-admin user trying to create users raises permission error."""
        mock_create.side_effect = VelosimPermissionError(
            "Requesting user cannot create users."
        )

        user_data = {
            "username": "test_user",
            "password": "test_password",
            "is_admin": True,
        }

        response = non_admin_client.post("/api/v1/users/create", json=user_data)

        assert response.status_code == 401
        data = response.json()
        assert "Requesting user cannot create users." in str(data["detail"])
