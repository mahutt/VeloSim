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
from sqlalchemy.orm import Session
from back.crud.user import user_crud
from back.schemas.user import UserCreate
from back.models.user import User
from back.exceptions.bad_request_error import BadRequestError
from back.exceptions.velosim_permission_error import VelosimPermissionError


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing."""
    admin = User(
        username="admin_user",
        password_hash=user_crud.hash_password("admin_password"),
        is_admin=True,
    )
    db.add(admin)
    db.flush()
    db.refresh(admin)
    return admin


class TestUserCRUD:
    def test_create_user_success(self, db: Session, admin_user: User) -> None:
        """Test creating a user successfully."""
        user_data = UserCreate(
            username="test_user", password="test_password", is_admin=False
        )
        user = user_crud.create(db, user_data, admin_user.id)
        assert user.id is not None
        assert user.username == "test_user"
        assert user.is_admin is False
        assert user.password_hash != "test_password"  # Should be hashed

    def test_create_user_non_admin_requester(self, db: Session) -> None:
        """Test creating a user with non-admin requester raises permission error."""
        # Create a non-admin user
        non_admin = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
        )
        db.add(non_admin)
        db.flush()
        db.refresh(non_admin)

        user_data = UserCreate(username="new_user", password="password", is_admin=False)

        with pytest.raises(VelosimPermissionError):
            user_crud.create(db, user_data, non_admin.id)

    def test_create_user_nonexistent_requester(self, db: Session) -> None:
        """Test creating a user with nonexistent requester raises permission error."""
        user_data = UserCreate(username="new_user", password="password", is_admin=False)

        with pytest.raises(VelosimPermissionError):
            user_crud.create(db, user_data, 99999)

    def test_create_user_duplicate_username(
        self, db: Session, admin_user: User
    ) -> None:
        """Test creating a user with duplicate username raises bad request error."""
        # Create first user
        user_data = UserCreate(
            username="duplicate_user", password="password1", is_admin=False
        )
        user_crud.create(db, user_data, admin_user.id)

        # Try to create second user with same username
        user_data2 = UserCreate(
            username="duplicate_user", password="password2", is_admin=False
        )

        with pytest.raises(BadRequestError):
            user_crud.create(db, user_data2, admin_user.id)

    def test_get_user_by_id(self, db: Session, admin_user: User) -> None:
        """Test getting a user by ID."""
        retrieved_user = user_crud.get(db, admin_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == admin_user.id
        assert retrieved_user.username == admin_user.username

    def test_get_user_by_id_not_found(self, db: Session) -> None:
        """Test getting a user by ID that doesn't exist."""
        user = user_crud.get(db, 99999)
        assert user is None

    def test_get_user_by_username(self, db: Session, admin_user: User) -> None:
        """Test getting a user by username."""
        retrieved_user = user_crud.get_by_username(db, admin_user.username)
        assert retrieved_user is not None
        assert retrieved_user.id == admin_user.id
        assert retrieved_user.username == admin_user.username

    def test_get_user_by_username_not_found(self, db: Session) -> None:
        """Test getting a user by username that doesn't exist."""
        user = user_crud.get_by_username(db, "nonexistent_user")
        assert user is None

    def test_hash_password(self, db: Session) -> None:
        """Test password hashing."""
        password = "test_password"
        hashed = user_crud.hash_password(password)
        assert hashed != password
        assert hashed.startswith("$argon2")
