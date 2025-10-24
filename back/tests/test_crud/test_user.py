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
from back.schemas import UserCreate, UserPasswordUpdate, UserRoleUpdate
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
        is_enabled=True,
    )
    db.add(admin)
    db.flush()
    db.refresh(admin)
    return admin


class TestUserCRUD:
    def test_create_user_success(self, db: Session, admin_user: User) -> None:
        """Test creating a user successfully."""
        user_data = UserCreate(
            username="test_user",
            password="test_password",
            is_admin=False,
            is_enabled=True,
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
            is_enabled=True,
        )
        db.add(non_admin)
        db.flush()
        db.refresh(non_admin)

        user_data = UserCreate(
            username="new_user", password="password", is_admin=False, is_enabled=True
        )

        with pytest.raises(VelosimPermissionError):
            user_crud.create(db, user_data, non_admin.id)

    def test_create_user_nonexistent_requester(self, db: Session) -> None:
        """Test creating a user with nonexistent requester raises permission error."""
        user_data = UserCreate(
            username="new_user", password="password", is_admin=False, is_enabled=True
        )

        with pytest.raises(VelosimPermissionError):
            user_crud.create(db, user_data, 99999)

    def test_create_user_duplicate_username(
        self, db: Session, admin_user: User
    ) -> None:
        """Test creating a user with duplicate username raises bad request error."""
        # Create first user
        user_data = UserCreate(
            username="duplicate_user",
            password="password1",
            is_admin=False,
            is_enabled=True,
        )
        user_crud.create(db, user_data, admin_user.id)

        # Try to create second user with same username
        user_data2 = UserCreate(
            username="duplicate_user",
            password="password2",
            is_admin=False,
            is_enabled=True,
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
            is_enabled=True,
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
            is_enabled=True,
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
            is_enabled=True,
        )
        user2 = User(
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
            is_enabled=True,
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
            is_enabled=True,
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

    def test_update_role_success_admin(self, db: Session, admin_user: User) -> None:
        """Test admin updating another user's role successfully."""
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(regular_user)
        db.flush()
        db.refresh(regular_user)

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)
        updated_user = user_crud.update_role(
            db, regular_user.id, role_data, admin_user.id
        )

        assert updated_user.id == regular_user.id
        assert updated_user.is_admin is True

    def test_update_role_demote_admin(self, db: Session, admin_user: User) -> None:
        """Test admin demoting another admin user successfully."""
        # Create another admin user
        admin_user2 = User(
            username="admin_user2",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=True,
        )
        db.add(admin_user2)
        db.flush()
        db.refresh(admin_user2)

        role_data = UserRoleUpdate(is_admin=False, is_enabled=True)
        updated_user = user_crud.update_role(
            db, admin_user2.id, role_data, admin_user.id
        )

        assert updated_user.id == admin_user2.id
        assert updated_user.is_admin is False

    def test_update_role_permission_error_self(
        self, db: Session, admin_user: User
    ) -> None:
        """Test admin trying to update their own role raises permission error."""
        role_data = UserRoleUpdate(is_admin=False, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(db, admin_user.id, role_data, admin_user.id)

    def test_update_role_permission_error_non_admin(self, db: Session) -> None:
        """Test non-admin trying to update role raises permission error."""
        # Create two regular users
        user1 = User(
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(user1)
        db.add(user2)
        db.flush()
        db.refresh(user1)
        db.refresh(user2)

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(db, user2.id, role_data, user1.id)

    def test_update_role_nonexistent_requester(self, db: Session) -> None:
        """Test updating role with nonexistent requester raises permission error."""
        # Create a user
        user = User(
            username="test_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(user)
        db.flush()
        db.refresh(user)

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(db, user.id, role_data, 99999)

    def test_update_role_user_not_found(self, db: Session, admin_user: User) -> None:
        """Test updating role for nonexistent user raises bad request error."""
        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(BadRequestError):
            user_crud.update_role(db, 99999, role_data, admin_user.id)

    def test_get_all_users_success_admin(self, db: Session, admin_user: User) -> None:
        """Test admin getting all users successfully."""
        # Create some additional users
        user1 = User(
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=True,
            is_enabled=True,
        )
        db.add(user1)
        db.add(user2)
        db.flush()

        users, total = user_crud.get_all(db, None, None, admin_user.id)

        assert total == 3  # admin_user + user1 + user2
        assert len(users) == 3
        usernames = [user.username for user in users]
        assert "admin_user" in usernames
        assert "user1" in usernames
        assert "user2" in usernames

    def test_get_all_users_with_admin_filter(
        self, db: Session, admin_user: User
    ) -> None:
        """Test getting users with admin filter."""
        # Create some additional users
        user1 = User(
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=True,
            is_enabled=True,
        )
        db.add(user1)
        db.add(user2)
        db.flush()

        # Filter for admin users only
        users, total = user_crud.get_all(db, None, True, admin_user.id)

        assert total == 2  # admin_user + user2 (both admin)
        assert len(users) == 2
        for user in users:
            assert user.is_admin is True

    def test_get_all_users_with_pagination(self, db: Session, admin_user: User) -> None:
        """Test getting users with pagination."""
        # Create additional users
        for i in range(5):
            user = User(
                username=f"user{i}",
                password_hash=user_crud.hash_password(f"password{i}"),
                is_admin=False,
                is_enabled=True,
            )
            db.add(user)
        db.flush()

        # Test pagination: skip 2, limit 3
        users, total = user_crud.get_all(db, None, None, admin_user.id, skip=2, limit=3)

        assert total == 6  # admin_user + 5 created users
        assert len(users) == 3  # Limited to 3

    def test_get_all_users_permission_error_non_admin(self, db: Session) -> None:
        """Test non-admin trying to get all users raises permission error."""
        # Create a non-admin user
        non_admin = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(non_admin)
        db.flush()
        db.refresh(non_admin)

        with pytest.raises(VelosimPermissionError):
            user_crud.get_all(db, None, None, non_admin.id)

    def test_get_all_users_permission_error_nonexistent_requester(
        self, db: Session
    ) -> None:
        """Test nonexistent requester trying to get all users raises permission
        error."""
        with pytest.raises(VelosimPermissionError):
            user_crud.get_all(db, None, None, 99999)

    def test_get_all_users_with_enabled_filter(
        self, db: Session, admin_user: User
    ) -> None:
        """Test getting users with enabled filter."""
        # Create some additional users - mix of enabled and disabled
        user1 = User(
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
            is_enabled=False,  # Disabled user
        )
        user3 = User(
            username="user3",
            password_hash=user_crud.hash_password("password3"),
            is_admin=True,
            is_enabled=False,  # Disabled admin
        )
        db.add(user1)
        db.add(user2)
        db.add(user3)
        db.flush()

        # Filter for enabled users only
        users, total = user_crud.get_all(db, True, None, admin_user.id)

        assert total == 2  # admin_user + user1 (both enabled)
        assert len(users) == 2
        for user in users:
            assert user.is_enabled is True

        # Filter for disabled users only
        users, total = user_crud.get_all(db, False, None, admin_user.id)

        assert total == 2  # user2 + user3 (both disabled)
        assert len(users) == 2
        for user in users:
            assert user.is_enabled is False

    def test_create_user_disabled_admin_requester(self, db: Session) -> None:
        """Test creating a user with disabled admin requester raises permission
        error."""
        # Create a disabled admin user
        disabled_admin = User(
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        db.add(disabled_admin)
        db.flush()
        db.refresh(disabled_admin)

        user_data = UserCreate(
            username="new_user",
            password="password",
            is_admin=False,
            is_enabled=True,
        )

        with pytest.raises(VelosimPermissionError):
            user_crud.create(db, user_data, disabled_admin.id)

    def test_update_password_disabled_admin_requester(self, db: Session) -> None:
        """Test disabled admin trying to update password raises permission error."""
        # Create a disabled admin user
        disabled_admin = User(
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("old_password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(disabled_admin)
        db.add(regular_user)
        db.flush()
        db.refresh(disabled_admin)
        db.refresh(regular_user)

        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(VelosimPermissionError):
            user_crud.update_password(
                db, regular_user.id, password_data, disabled_admin.id
            )

    def test_update_role_disabled_admin_requester(self, db: Session) -> None:
        """Test disabled admin trying to update role raises permission error."""
        # Create a disabled admin user
        disabled_admin = User(
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(disabled_admin)
        db.add(regular_user)
        db.flush()
        db.refresh(disabled_admin)
        db.refresh(regular_user)

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(db, regular_user.id, role_data, disabled_admin.id)

    def test_get_all_users_disabled_admin_requester(self, db: Session) -> None:
        """Test disabled admin trying to get all users raises permission error."""
        # Create a disabled admin user
        disabled_admin = User(
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        db.add(disabled_admin)
        db.flush()
        db.refresh(disabled_admin)

        with pytest.raises(VelosimPermissionError):
            user_crud.get_all(db, None, None, disabled_admin.id)

    def test_update_role_disable_user(self, db: Session, admin_user: User) -> None:
        """Test admin disabling a user successfully."""
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(regular_user)
        db.flush()
        db.refresh(regular_user)

        role_data = UserRoleUpdate(is_admin=False, is_enabled=False)
        updated_user = user_crud.update_role(
            db, regular_user.id, role_data, admin_user.id
        )

        assert updated_user.id == regular_user.id
        assert updated_user.is_enabled is False

    def test_update_role_enable_user(self, db: Session, admin_user: User) -> None:
        """Test admin enabling a disabled user successfully."""
        # Create a disabled user
        disabled_user = User(
            username="disabled_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=False,
        )
        db.add(disabled_user)
        db.flush()
        db.refresh(disabled_user)

        role_data = UserRoleUpdate(is_admin=False, is_enabled=True)
        updated_user = user_crud.update_role(
            db, disabled_user.id, role_data, admin_user.id
        )

        assert updated_user.id == disabled_user.id
        assert updated_user.is_enabled is True

    def test_get_if_permission_admin_access_any_user(
        self, db: Session, admin_user: User
    ) -> None:
        """Test admin can access any user through get_if_permission."""
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(regular_user)
        db.flush()
        db.refresh(regular_user)

        # Admin should be able to access regular user
        retrieved_user = user_crud.get_if_permission(db, regular_user.id, admin_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == regular_user.id
        assert retrieved_user.username == regular_user.username

    def test_get_if_permission_user_access_self(self, db: Session) -> None:
        """Test user can access themselves through get_if_permission."""
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(regular_user)
        db.flush()
        db.refresh(regular_user)

        # User should be able to access themselves
        retrieved_user = user_crud.get_if_permission(
            db, regular_user.id, regular_user.id
        )
        assert retrieved_user is not None
        assert retrieved_user.id == regular_user.id
        assert retrieved_user.username == regular_user.username

    def test_get_if_permission_user_access_other_forbidden(self, db: Session) -> None:
        """Test regular user cannot access other users through get_if_permission."""
        # Create two regular users
        user1 = User(
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(user1)
        db.add(user2)
        db.flush()
        db.refresh(user1)
        db.refresh(user2)

        # User1 should not be able to access user2
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(db, user2.id, user1.id)

    def test_get_if_permission_disabled_admin_forbidden(self, db: Session) -> None:
        """Test disabled admin cannot access users through get_if_permission."""
        # Create a disabled admin user
        disabled_admin = User(
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(disabled_admin)
        db.add(regular_user)
        db.flush()
        db.refresh(disabled_admin)
        db.refresh(regular_user)

        # Disabled admin should not be able to access regular user
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(db, regular_user.id, disabled_admin.id)

    def test_get_if_permission_nonexistent_requester(self, db: Session) -> None:
        """Test nonexistent requester cannot access users through get_if_permission."""
        # Create a regular user
        regular_user = User(
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )
        db.add(regular_user)
        db.flush()
        db.refresh(regular_user)

        # Nonexistent requester should not be able to access user
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(db, regular_user.id, 99999)

    def test_get_if_permission_nonexistent_target_user(
        self, db: Session, admin_user: User
    ) -> None:
        """Test get_if_permission returns None for nonexistent target user."""
        # Admin trying to access nonexistent user should return None
        retrieved_user = user_crud.get_if_permission(db, 99999, admin_user.id)
        assert retrieved_user is None

    def test_get_if_permission_disabled_user_access_self_forbidden(
        self, db: Session
    ) -> None:
        """Test disabled user cannot access themselves through get_if_permission."""
        # Create a disabled user
        disabled_user = User(
            username="disabled_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=False,
        )
        db.add(disabled_user)
        db.flush()
        db.refresh(disabled_user)

        # Disabled user should not be able to access themselves either
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(db, disabled_user.id, disabled_user.id)
