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


@pytest.fixture
def disabled_admin_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Create test client with disabled admin user."""

    def mock_get_user_id() -> int:
        return 3  # Assume user ID 3 is a disabled admin

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

        assert response.status_code == 403
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

        assert response.status_code == 403
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

        assert response.status_code == 403
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

        assert response.status_code == 403
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

        assert response.status_code == 403
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

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot list users." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_success(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test updating a user's role successfully."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "test_user"
        mock_user.is_admin = True
        mock_update.return_value = mock_user

        role_data = {"is_admin": True}

        response = authenticated_client.put("/api/v1/users/2/role", json=role_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "test_user"
        assert data["is_admin"] is True
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_demote_admin(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test demoting an admin user successfully."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "admin_user"
        mock_user.is_admin = False
        mock_update.return_value = mock_user

        role_data = {"is_admin": False}

        response = authenticated_client.put("/api/v1/users/2/role", json=role_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "admin_user"
        assert data["is_admin"] is False
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_bad_request(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test updating role with bad request error."""
        mock_update.side_effect = BadRequestError("User not found")

        role_data = {"is_admin": True}

        response = authenticated_client.put("/api/v1/users/999/role", json=role_data)

        assert response.status_code == 400
        data = response.json()
        assert "User not found" in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_permission_error_self(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test admin trying to update their own role."""
        mock_update.side_effect = VelosimPermissionError(
            "Requesting user cannot update this role."
        )

        role_data = {"is_admin": False}

        response = authenticated_client.put("/api/v1/users/1/role", json=role_data)

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot update this role." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_permission_error_non_admin(
        self, mock_update: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        """Test non-admin user trying to update role."""
        mock_update.side_effect = VelosimPermissionError(
            "Requesting user cannot update this role."
        )

        role_data = {"is_admin": True}

        response = non_admin_client.put("/api/v1/users/2/role", json=role_data)

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot update this role." in str(data["detail"])

    def test_update_role_invalid_data(
        self, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test updating role with invalid data. Empty object is ok because both fields
        are optional."""
        response = authenticated_client.put(
            "/api/v1/users/1/role", json={"is_admin": "non_boolean"}
        )
        assert response.status_code == 422

    def test_update_role_no_authentication(
        self, client: TestClient, db: Session
    ) -> None:
        """Test that authentication is required for updating roles."""
        role_data = {"is_admin": True}

        # Use the base client without auth override
        response = client.put("/api/v1/users/1/role", json=role_data)

        # Should fail due to authentication
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_with_enabled_filter(
        self, mock_get_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test getting users with enabled filter."""
        # Mock enabled users only
        mock_user1 = MagicMock()
        mock_user1.id = 1
        mock_user1.username = "enabled_user1"
        mock_user1.is_admin = False
        mock_user1.is_enabled = True

        mock_user2 = MagicMock()
        mock_user2.id = 2
        mock_user2.username = "enabled_user2"
        mock_user2.is_admin = True
        mock_user2.is_enabled = True

        mock_get_all.return_value = ([mock_user1, mock_user2], 2)

        response = authenticated_client.get("/api/v1/users/?isEnabled=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["users"]) == 2
        for user in data["users"]:
            assert user["is_enabled"] is True
        mock_get_all.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_with_disabled_filter(
        self, mock_get_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test getting disabled users only."""
        # Mock disabled users only
        mock_user1 = MagicMock()
        mock_user1.id = 3
        mock_user1.username = "disabled_user1"
        mock_user1.is_admin = False
        mock_user1.is_enabled = False

        mock_get_all.return_value = ([mock_user1], 1)

        response = authenticated_client.get("/api/v1/users/?isEnabled=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["users"]) == 1
        assert data["users"][0]["is_enabled"] is False
        mock_get_all.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_disable_user(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test disabling a user successfully."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "test_user"
        mock_user.is_admin = False
        mock_user.is_enabled = False
        mock_update.return_value = mock_user

        role_data = {"is_enabled": False}

        response = authenticated_client.put("/api/v1/users/2/role", json=role_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "test_user"
        assert data["is_enabled"] is False
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_enable_user(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test enabling a disabled user successfully."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "test_user"
        mock_user.is_admin = False
        mock_user.is_enabled = True
        mock_update.return_value = mock_user

        role_data = {"is_enabled": True}

        response = authenticated_client.put("/api/v1/users/2/role", json=role_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "test_user"
        assert data["is_enabled"] is True
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_promote_and_enable(
        self, mock_update: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test promoting and enabling a user simultaneously."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "test_user"
        mock_user.is_admin = True
        mock_user.is_enabled = True
        mock_update.return_value = mock_user

        role_data = {"is_admin": True, "is_enabled": True}

        response = authenticated_client.put("/api/v1/users/2/role", json=role_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "test_user"
        assert data["is_admin"] is True
        assert data["is_enabled"] is True
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.create")
    def test_create_user_disabled_admin_forbidden(
        self, mock_create: MagicMock, disabled_admin_client: TestClient, db: Session
    ) -> None:
        """Test disabled admin trying to create users."""
        mock_create.side_effect = VelosimPermissionError(
            "Requesting user cannot create users."
        )

        user_data = {
            "username": "test_user",
            "password": "test_password",
            "is_admin": False,
        }

        response = disabled_admin_client.post("/api/v1/users/create", json=user_data)

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot create users." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_password")
    def test_update_password_disabled_admin_forbidden(
        self, mock_update: MagicMock, disabled_admin_client: TestClient, db: Session
    ) -> None:
        """Test disabled admin trying to update passwords."""
        mock_update.side_effect = VelosimPermissionError(
            "Requesting user cannot update this password."
        )

        password_data = {"password": "new_password"}

        response = disabled_admin_client.put(
            "/api/v1/users/1/password", json=password_data
        )

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot update this password." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_role")
    def test_update_role_disabled_admin_forbidden(
        self, mock_update: MagicMock, disabled_admin_client: TestClient, db: Session
    ) -> None:
        """Test disabled admin trying to update roles."""
        mock_update.side_effect = VelosimPermissionError(
            "Requesting user cannot update this role."
        )

        role_data = {"is_admin": True}

        response = disabled_admin_client.put("/api/v1/users/2/role", json=role_data)

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot update this role." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.get_all")
    def test_get_users_disabled_admin_forbidden(
        self, mock_get_all: MagicMock, disabled_admin_client: TestClient, db: Session
    ) -> None:
        """Test disabled admin trying to get users."""
        mock_get_all.side_effect = VelosimPermissionError(
            "Requesting user cannot list users."
        )

        response = disabled_admin_client.get("/api/v1/users/")

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot list users." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.create")
    def test_create_user_with_disabled_status(
        self, mock_create: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test creating a user with disabled status."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "disabled_user"
        mock_user.is_admin = False
        mock_user.is_enabled = False
        mock_create.return_value = mock_user

        user_data = {
            "username": "disabled_user",
            "password": "test_password",
            "is_admin": False,
            "is_enabled": False,
        }

        response = authenticated_client.post("/api/v1/users/create", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["username"] == "disabled_user"
        assert data["is_admin"] is False
        assert data["is_enabled"] is False
        mock_create.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_me_success(
        self,
        mock_get_if_permission: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Test getting current user info successfully."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "current_user"
        mock_user.is_admin = True
        mock_user.is_enabled = True
        mock_get_if_permission.return_value = mock_user

        response = authenticated_client.get("/api/v1/users/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["username"] == "current_user"
        assert data["is_admin"] is True
        assert data["is_enabled"] is True
        # The function is called with (db, requesting_user, requesting_user) for /me
        mock_get_if_permission.assert_called_once()

    def test_get_me_no_authentication(self, client: TestClient, db: Session) -> None:
        """Test that authentication is required for getting current user info."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_by_id_success_admin(
        self,
        mock_get_if_permission: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Test admin getting user by ID successfully."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "target_user"
        mock_user.is_admin = False
        mock_user.is_enabled = True
        mock_get_if_permission.return_value = mock_user

        response = authenticated_client.get("/api/v1/users/2")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "target_user"
        assert data["is_admin"] is False
        assert data["is_enabled"] is True
        mock_get_if_permission.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_by_id_success_self(
        self,
        mock_get_if_permission: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Test user getting their own info by ID successfully."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "current_user"
        mock_user.is_admin = False
        mock_user.is_enabled = True
        mock_get_if_permission.return_value = mock_user

        response = authenticated_client.get("/api/v1/users/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["username"] == "current_user"
        assert data["is_admin"] is False
        assert data["is_enabled"] is True
        mock_get_if_permission.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_by_id_not_found(
        self,
        mock_get_if_permission: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Test getting user by ID that doesn't exist."""
        mock_get_if_permission.return_value = None

        response = authenticated_client.get("/api/v1/users/999")

        assert response.status_code == 404
        data = response.json()
        assert "User not found" in str(data["detail"])
        mock_get_if_permission.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_by_id_permission_error(
        self,
        mock_get_if_permission: MagicMock,
        non_admin_client: TestClient,
        db: Session,
    ) -> None:
        """Test non-admin user trying to access another user's info."""
        mock_get_if_permission.side_effect = VelosimPermissionError(
            "Requesting user cannot access this user."
        )

        response = non_admin_client.get("/api/v1/users/1")

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot access this user." in str(data["detail"])
        mock_get_if_permission.assert_called_once()

    def test_get_by_id_no_authentication(self, client: TestClient, db: Session) -> None:
        """Test that authentication is required for getting user by ID."""
        response = client.get("/api/v1/users/1")
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_by_id_disabled_admin_forbidden(
        self,
        mock_get_if_permission: MagicMock,
        disabled_admin_client: TestClient,
        db: Session,
    ) -> None:
        """Test disabled admin trying to get user by ID."""
        mock_get_if_permission.side_effect = VelosimPermissionError(
            "Requesting user cannot access this user."
        )

        response = disabled_admin_client.get("/api/v1/users/1")

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot access this user." in str(data["detail"])
        mock_get_if_permission.assert_called_once()


class TestPreferencesAPI:
    """Test the user preferences endpoints."""

    # ------------------------------------------------------------------
    # GET /users/{user_id}/preferences  (canonical implementation)
    # ------------------------------------------------------------------

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_user_preferences_success_admin(
        self,
        mock_get: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Admin can read another user's preferences."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "fr", "front_theme": "dark"}
        mock_get.return_value = mock_user

        response = authenticated_client.get("/api/v1/users/2/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "fr"
        assert data["front_theme"] == "dark"
        mock_get.assert_called_once()

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_user_preferences_success_self(
        self,
        mock_get: MagicMock,
        non_admin_client: TestClient,
        db: Session,
    ) -> None:
        """A non-admin user can read their own preferences via the /{id} endpoint."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "en"}
        mock_get.return_value = mock_user

        # non_admin_client authenticates as user 2
        response = non_admin_client.get("/api/v1/users/2/preferences")

        assert response.status_code == 200
        assert response.json()["language"] == "en"

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_user_preferences_none_stored(
        self,
        mock_get: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """When preferences is null in DB, returns an object with language: null."""
        mock_user = MagicMock()
        mock_user.preferences = None
        mock_get.return_value = mock_user

        response = authenticated_client.get("/api/v1/users/1/preferences")

        assert response.status_code == 200
        assert response.json()["language"] is None

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_user_preferences_not_found(
        self,
        mock_get: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Returns 404 when the target user does not exist."""
        mock_get.return_value = None

        response = authenticated_client.get("/api/v1/users/999/preferences")

        assert response.status_code == 404

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_user_preferences_permission_error(
        self,
        mock_get: MagicMock,
        non_admin_client: TestClient,
        db: Session,
    ) -> None:
        """A non-admin cannot read another user's preferences."""
        mock_get.side_effect = VelosimPermissionError(
            "Requesting user cannot access this user."
        )

        response = non_admin_client.get("/api/v1/users/1/preferences")

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot access this user." in str(data["detail"])

    def test_get_user_preferences_no_authentication(
        self, client: TestClient, db: Session
    ) -> None:
        """Unauthenticated request is rejected."""
        response = client.get("/api/v1/users/1/preferences")
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # GET /users/me/preferences  (wrapper → /{user_id}/preferences)
    # ------------------------------------------------------------------

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_my_preferences_no_prefs(
        self,
        mock_get: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Preferences is null in DB → response contains language: null."""
        mock_user = MagicMock()
        mock_user.preferences = None
        mock_get.return_value = mock_user

        response = authenticated_client.get("/api/v1/users/me/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["language"] is None

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_my_preferences_with_language(
        self,
        mock_get: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Stored language preference is returned correctly."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "fr", "front_theme": "dark"}
        mock_get.return_value = mock_user

        response = authenticated_client.get("/api/v1/users/me/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "fr"
        assert data["front_theme"] == "dark"

    def test_get_my_preferences_no_authentication(
        self, client: TestClient, db: Session
    ) -> None:
        """Unauthenticated request is rejected."""
        response = client.get("/api/v1/users/me/preferences")
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.get_if_permission")
    def test_get_my_preferences_user_not_found(
        self,
        mock_get: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Returns 404 when the user cannot be found."""
        mock_get.return_value = None

        response = authenticated_client.get("/api/v1/users/me/preferences")

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # PATCH /{user_id}/preferences
    # ------------------------------------------------------------------

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_set_language(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Setting language to 'fr' succeeds and returns the merged blob."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "fr"}
        mock_update.return_value = mock_user

        response = authenticated_client.patch(
            "/api/v1/users/1/preferences", json={"language": "fr"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "fr"
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_clear_language(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Setting language to null clears the preference."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": None}
        mock_update.return_value = mock_user

        response = authenticated_client.patch(
            "/api/v1/users/1/preferences", json={"language": None}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] is None
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_front_only_key(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Front-end-only keys (front_*) are stored transparently."""
        mock_user = MagicMock()
        mock_user.preferences = {"front_theme": "dark", "front_sidebar": False}
        mock_update.return_value = mock_user

        response = authenticated_client.patch(
            "/api/v1/users/1/preferences",
            json={"front_theme": "dark", "front_sidebar": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["front_theme"] == "dark"
        assert data["front_sidebar"] is False
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_mixed_keys(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """A mix of back-end and front-end keys is accepted."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "en", "front_theme": "light"}
        mock_update.return_value = mock_user

        response = authenticated_client.patch(
            "/api/v1/users/1/preferences",
            json={"language": "en", "front_theme": "light"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"
        assert data["front_theme"] == "light"

    def test_update_preferences_invalid_language(
        self,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """An unrecognised language value is rejected by Pydantic validation."""
        response = authenticated_client.patch(
            "/api/v1/users/1/preferences", json={"language": "de"}
        )
        assert response.status_code == 422

    def test_update_preferences_unknown_key_rejected(
        self,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """An unknown key without the front_ prefix is rejected with 400."""
        response = authenticated_client.patch(
            "/api/v1/users/1/preferences", json={"theme": "dark"}
        )

        assert response.status_code == 400

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_permission_error(
        self,
        mock_update: MagicMock,
        non_admin_client: TestClient,
        db: Session,
    ) -> None:
        """A non-admin cannot update another user's preferences."""
        mock_update.side_effect = VelosimPermissionError(
            "Requesting user cannot update these preferences."
        )

        response = non_admin_client.patch(
            "/api/v1/users/1/preferences", json={"language": "en"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "Requesting user cannot update these preferences." in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_admin_can_update_other_user(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """An admin can update another user's preferences."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "fr"}
        mock_update.return_value = mock_user

        response = authenticated_client.patch(
            "/api/v1/users/2/preferences", json={"language": "fr"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "fr"
        mock_update.assert_called_once()

    def test_update_preferences_no_authentication(
        self, client: TestClient, db: Session
    ) -> None:
        """Unauthenticated request is rejected."""
        response = client.patch("/api/v1/users/1/preferences", json={"language": "en"})
        assert response.status_code == 401

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_user_not_found(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Returns 400 when target user does not exist."""
        mock_update.side_effect = BadRequestError("User not found")

        response = authenticated_client.patch(
            "/api/v1/users/999/preferences", json={"language": "en"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "User not found" in str(data["detail"])

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_preferences_self_non_admin(
        self,
        mock_update: MagicMock,
        non_admin_client: TestClient,
        db: Session,
    ) -> None:
        """A non-admin user can update their own preferences via the /{id} endpoint."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "fr"}
        mock_update.return_value = mock_user

        # non_admin_client authenticates as user 2
        response = non_admin_client.patch(
            "/api/v1/users/2/preferences", json={"language": "fr"}
        )

        assert response.status_code == 200
        assert response.json()["language"] == "fr"
        mock_update.assert_called_once()

    # ------------------------------------------------------------------
    # PATCH /users/me/preferences  (wrapper → /{user_id}/preferences)
    # ------------------------------------------------------------------

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_my_preferences_success(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """PATCH /me/preferences delegates to the /{id} handler."""
        mock_user = MagicMock()
        mock_user.preferences = {"language": "fr", "front_theme": "dark"}
        mock_update.return_value = mock_user

        response = authenticated_client.patch(
            "/api/v1/users/me/preferences",
            json={"language": "fr", "front_theme": "dark"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "fr"
        assert data["front_theme"] == "dark"
        mock_update.assert_called_once()

    @patch("back.api.v1.users.user_crud.update_preferences")
    def test_update_my_preferences_invalid_language(
        self,
        mock_update: MagicMock,
        authenticated_client: TestClient,
        db: Session,
    ) -> None:
        """Invalid language is rejected by Pydantic before hitting CRUD."""
        response = authenticated_client.patch(
            "/api/v1/users/me/preferences", json={"language": "de"}
        )

        assert response.status_code == 422
        mock_update.assert_not_called()

    def test_update_my_preferences_no_authentication(
        self, client: TestClient, db: Session
    ) -> None:
        """Unauthenticated request to /me/preferences is rejected."""
        response = client.patch("/api/v1/users/me/preferences", json={"language": "en"})
        assert response.status_code == 401
