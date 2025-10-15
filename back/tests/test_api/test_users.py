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

    @patch("back.api.v1.users.user_crud.update_password")
    def test_update_password_success(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test updating a user's password successfully."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "test_user"
        mock_user.is_admin = False
        mock_update.return_value = mock_user

        password_data = {"password": "new_password"}

        response = authenticated_client.put(
            "/api/v1/users/1/password", json=password_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["username"] == "test_user"
        assert data["is_admin"] is False
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_password")
    def test_update_password_bad_request(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test updating password with bad request error."""
        mock_update.side_effect = BadRequestError("User not found")

        password_data = {"password": "new_password"}

        response = authenticated_client.put(
            "/api/v1/users/999/password", json=password_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "User not found" in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_password")
    def test_update_password_permission_error(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test updating password with permission error."""
        mock_update.side_effect = VelosimPermissionError(
            "Requesting user cannot update this password."
        )

        password_data = {"password": "new_password"}

        response = authenticated_client.put(
            "/api/v1/users/2/password", json=password_data
        )

        assert response.status_code == 401
        data = response.json()
        assert "Requesting user cannot update this password." in str(data["detail"])

    def test_update_password_invalid_data(
        self, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test updating password with missing data."""
        response = authenticated_client.put("/api/v1/users/1/password", json={})
        assert response.status_code == 422

    def test_update_password_no_authentication(
        self, client: TestClient, db: Session
    ) -> None:
        """Test that authentication is required for updating passwords."""
        password_data = {"password": "new_password"}

        # Use the base client without auth override
        response = client.put("/api/v1/users/1/password", json=password_data)

        # Should fail due to authentication
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.update_password")
    def test_update_password_non_admin_forbidden(
        self, mock_update: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        """Test non-admin user trying to update another user's password."""
        mock_update.side_effect = VelosimPermissionError(
            "Requesting user cannot update this password."
        )

        password_data = {"password": "new_password"}

        response = non_admin_client.put("/api/v1/users/1/password", json=password_data)

        assert response.status_code == 401
        data = response.json()
        assert "Requesting user cannot update this password." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_success(
        self, mock_get_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test getting users successfully."""
        # Mock the CRUD get_all method
        mock_user1 = MagicMock()
        mock_user1.id = 1
        mock_user1.username = "user1"
        mock_user1.is_admin = True

        mock_user2 = MagicMock()
        mock_user2.id = 2
        mock_user2.username = "user2"
        mock_user2.is_admin = False

        mock_get_all.return_value = ([mock_user1, mock_user2], 2)

        response = authenticated_client.get("/api/v1/users/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 1
        assert len(data["users"]) == 2
        assert data["users"][0]["id"] == 1
        assert data["users"][0]["username"] == "user1"
        assert data["users"][0]["is_admin"] is True
        mock_get_all.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_with_filters(
        self, mock_get_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test getting users with filters."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "admin_user"
        mock_user.is_admin = True

        mock_get_all.return_value = ([mock_user], 1)

        response = authenticated_client.get("/api/v1/users/?isAdmin=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["users"]) == 1
        assert data["users"][0]["is_admin"] is True
        mock_get_all.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_with_pagination(
        self, mock_get_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test getting users with pagination."""
        mock_users = []
        for i in range(3):
            mock_user = MagicMock()
            mock_user.id = i + 1
            mock_user.username = f"user{i + 1}"
            mock_user.is_admin = False
            mock_users.append(mock_user)

        mock_get_all.return_value = (mock_users, 10)  # 3 users returned, 10 total

        response = authenticated_client.get("/api/v1/users/?skip=5&limit=3")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["page"] == 2  # (5 // 3) + 1 = 2
        assert data["per_page"] == 3
        assert data["total_pages"] == 4  # ceil(10 / 3) = 4
        assert len(data["users"]) == 3
        mock_get_all.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_permission_error(
        self, mock_get_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test getting users with permission error."""
        mock_get_all.side_effect = VelosimPermissionError(
            "Requesting user cannot list users."
        )

        response = authenticated_client.get("/api/v1/users/")

        assert response.status_code == 401
        data = response.json()
        assert "Requesting user cannot list users." in str(data["detail"])

    def test_get_users_no_authentication(self, client: TestClient, db: Session) -> None:
        """Test that authentication is required for getting users."""
        # Use the base client without auth override
        response = client.get("/api/v1/users/")

        # Should fail due to authentication
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_non_admin_forbidden(
        self, mock_get_all: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        """Test non-admin user trying to get users."""
        mock_get_all.side_effect = VelosimPermissionError(
            "Requesting user cannot list users."
        )

        response = non_admin_client.get("/api/v1/users/")

        assert response.status_code == 401
        data = response.json()
        assert "Requesting user cannot list users." in str(data["detail"])
