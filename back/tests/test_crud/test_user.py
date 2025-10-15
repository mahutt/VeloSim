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
from back.schemas import UserCreate, UserPasswordUpdate
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

    def test_update_password_success_admin(self, db: Session, admin_user: User) -> None:
        """Test admin updating another user's password successfully."""
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("old_password"),
            is_admin=False,
        )
        db.add(regular_user)
        db.flush()
        db.refresh(regular_user)

        # Store the old hash before updating
        old_password_hash = regular_user.password_hash

        password_data = UserPasswordUpdate(password="new_password")
        updated_user = user_crud.update_password(
            db, regular_user.id, password_data, admin_user.id
        )

        assert updated_user.id == regular_user.id
        assert updated_user.password_hash != "new_password"  # Should be hashed
        assert (
            updated_user.password_hash != old_password_hash
        )  # Should be different from old hash

    def test_update_password_success_self(self, db: Session) -> None:
        """Test user updating their own password successfully."""
        # Create a user
        user = User(
            username="self_user",
            password_hash=user_crud.hash_password("old_password"),
            is_admin=False,
        )
        db.add(user)
        db.flush()
        db.refresh(user)

        # Store the old hash before updating
        old_hash = user.password_hash

        password_data = UserPasswordUpdate(password="new_password")
        updated_user = user_crud.update_password(db, user.id, password_data, user.id)

        assert updated_user.id == user.id
        assert updated_user.password_hash != "new_password"  # Should be hashed
        assert (
            updated_user.password_hash != old_hash
        )  # Should be different from old hash

    def test_update_password_permission_error_non_admin(self, db: Session) -> None:
        """Test non-admin trying to update another user's password raises permission
        error."""
        # Create two regular users
        user1 = User(
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
        )
        user2 = User(
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
        )
        db.add(user1)
        db.add(user2)
        db.flush()
        db.refresh(user1)
        db.refresh(user2)

        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(VelosimPermissionError):
            user_crud.update_password(db, user2.id, password_data, user1.id)

    def test_update_password_nonexistent_requester(self, db: Session) -> None:
        """Test updating password with nonexistent requester raises permission error."""
        # Create a user
        user = User(
            username="test_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
        )
        db.add(user)
        db.flush()
        db.refresh(user)

        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(VelosimPermissionError):
            user_crud.update_password(db, user.id, password_data, 99999)

    def test_update_password_user_not_found(
        self, db: Session, admin_user: User
    ) -> None:
        """Test updating password for nonexistent user raises bad request error."""
        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(BadRequestError):
            user_crud.update_password(db, 99999, password_data, admin_user.id)
