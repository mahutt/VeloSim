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
from unittest.mock import Mock
from back.crud.user import user_crud
from back.schemas import UserCreate, UserPasswordUpdate, UserRoleUpdate
from back.models.user import User
from back.exceptions.bad_request_error import BadRequestError
from back.exceptions.velosim_permission_error import VelosimPermissionError
from back.tests.mock_utils import (
    create_mock_db_session,
    setup_mock_db_add_with_id,
)


@pytest.fixture
def mock_db() -> Mock:
    """Create a mock database session for testing."""
    return create_mock_db_session()


@pytest.fixture
def admin_user() -> User:
    """Create an admin user for testing."""
    admin = User(
        id=1,
        username="admin_user",
        password_hash=user_crud.hash_password("admin_password"),
        is_admin=True,
        is_enabled=True,
    )
    return admin


class TestUserCRUD:
    def test_create_user_success(self, mock_db: Mock, admin_user: User) -> None:
        """Test creating a user successfully."""
        # Mock the requester check
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            admin_user,  # For get(requesting_user_id)
            None,  # For get_by_username (no existing user)
        ]

        # Setup mock to assign ID on refresh
        setup_mock_db_add_with_id(mock_db, id_value=2)

        user_data = UserCreate(
            username="test_user",
            password="test_password",
            is_admin=False,
            is_enabled=True,
        )
        user = user_crud.create(mock_db, user_data, admin_user.id)
        assert user.id is not None
        assert user.username == "test_user"
        assert user.is_admin is False
        assert user.password_hash != "test_password"  # Should be hashed

    def test_create_user_non_admin_requester(self, mock_db: Mock) -> None:
        """Test creating a user with non-admin requester raises permission error."""
        # Create a non-admin user
        non_admin = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get() to return non_admin user
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = non_admin
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        user_data = UserCreate(
            username="new_user", password="password", is_admin=False, is_enabled=True
        )

        with pytest.raises(VelosimPermissionError):
            user_crud.create(mock_db, user_data, non_admin.id)

    def test_create_user_nonexistent_requester(self, mock_db: Mock) -> None:
        """Test creating a user with nonexistent requester raises permission error."""
        # Mock get() to return None (user not found)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        user_data = UserCreate(
            username="new_user", password="password", is_admin=False, is_enabled=True
        )

        with pytest.raises(VelosimPermissionError):
            user_crud.create(mock_db, user_data, 99999)

    def test_create_user_duplicate_username(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test creating a user with duplicate username raises bad request error."""
        existing_user = User(
            id=2,
            username="duplicate_user",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get() to return admin_user
        # then get_by_username() to return existing user
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [
            admin_user,
            existing_user,
        ]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        user_data2 = UserCreate(
            username="duplicate_user",
            password="password2",
            is_admin=False,
            is_enabled=True,
        )

        with pytest.raises(BadRequestError):
            user_crud.create(mock_db, user_data2, admin_user.id)

    def test_get_user_by_id(self, mock_db: Mock, admin_user: User) -> None:
        """Test getting a user by ID."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = admin_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        retrieved_user = user_crud.get(mock_db, admin_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == admin_user.id
        assert retrieved_user.username == admin_user.username

    def test_get_user_by_id_not_found(self, mock_db: Mock) -> None:
        """Test getting a user by ID that doesn't exist."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        user = user_crud.get(mock_db, 99999)
        assert user is None

    def test_get_user_by_username(self, mock_db: Mock, admin_user: User) -> None:
        """Test getting a user by username."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = admin_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        retrieved_user = user_crud.get_by_username(mock_db, admin_user.username)
        assert retrieved_user is not None
        assert retrieved_user.id == admin_user.id
        assert retrieved_user.username == admin_user.username

    def test_get_user_by_username_not_found(self, mock_db: Mock) -> None:
        """Test getting a user by username that doesn't exist."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        user = user_crud.get_by_username(mock_db, "nonexistent_user")
        assert user is None

    def test_hash_password(self) -> None:
        """Test password hashing."""
        password = "test_password"
        hashed = user_crud.hash_password(password)
        assert hashed != password
        assert hashed.startswith("$argon2")

    def test_update_password_success_admin(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test admin updating another user's password successfully."""
        # Create a regular user
        regular_user = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("old_password"),
            is_admin=False,
            is_enabled=True,
        )
        old_password_hash = regular_user.password_hash

        # Mock get() calls: first for admin_user, then for regular_user
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [admin_user, regular_user]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        password_data = UserPasswordUpdate(password="new_password")
        updated_user = user_crud.update_password(
            mock_db, regular_user.id, password_data, admin_user.id
        )

        assert updated_user.id == regular_user.id
        assert updated_user.password_hash != "new_password"  # Should be hashed
        assert updated_user.password_hash != old_password_hash
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_update_password_success_self(self, mock_db: Mock) -> None:
        """Test user updating their own password successfully."""
        # Create a user
        user = User(
            id=1,
            username="self_user",
            password_hash=user_crud.hash_password("old_password"),
            is_admin=False,
            is_enabled=True,
        )
        old_hash = user.password_hash

        # Mock get() calls: same user for both requester and target
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [user, user]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        password_data = UserPasswordUpdate(password="new_password")
        updated_user = user_crud.update_password(
            mock_db, user.id, password_data, user.id
        )

        assert updated_user.id == user.id
        assert updated_user.password_hash != "new_password"  # Should be hashed
        assert updated_user.password_hash != old_hash
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_update_password_permission_error_non_admin(self, mock_db: Mock) -> None:
        """Test non-admin trying to update another user's password raises permission
        error."""
        # Create two regular users
        user1 = User(
            id=1,
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            id=2,
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get() to return user1 (non-admin requester)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = user1
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(VelosimPermissionError):
            user_crud.update_password(mock_db, user2.id, password_data, user1.id)

    def test_update_password_nonexistent_requester(self, mock_db: Mock) -> None:
        """Test updating password with nonexistent requester raises permission error."""
        user = User(
            id=1,
            username="test_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get() to return None (requester not found)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(VelosimPermissionError):
            user_crud.update_password(mock_db, user.id, password_data, 99999)

    def test_update_password_user_not_found(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test updating password for nonexistent user raises bad request error."""
        # Mock get() calls: return admin_user for requester, None for target user
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [admin_user, None]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(BadRequestError):
            user_crud.update_password(mock_db, 99999, password_data, admin_user.id)

    def test_update_role_success_admin(self, mock_db: Mock, admin_user: User) -> None:
        """Test admin updating another user's role successfully."""
        regular_user = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get() calls: return admin_user for requester, regular_user for target
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [admin_user, regular_user]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)
        updated_user = user_crud.update_role(
            mock_db, regular_user.id, role_data, admin_user.id
        )

        assert updated_user.id == regular_user.id
        assert updated_user.is_admin is True
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_update_role_demote_admin(self, mock_db: Mock, admin_user: User) -> None:
        """Test admin demoting another admin user successfully."""
        admin_user2 = User(
            id=2,
            username="admin_user2",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=True,
        )

        # Mock get() calls
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [admin_user, admin_user2]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=False, is_enabled=True)
        updated_user = user_crud.update_role(
            mock_db, admin_user2.id, role_data, admin_user.id
        )

        assert updated_user.id == admin_user2.id
        assert updated_user.is_admin is False
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_update_role_permission_error_self(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test admin trying to update their own role raises permission error."""
        # Mock get() to return admin_user
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = admin_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=False, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(mock_db, admin_user.id, role_data, admin_user.id)

    def test_update_role_permission_error_non_admin(self, mock_db: Mock) -> None:
        """Test non-admin trying to update role raises permission error."""
        user1 = User(
            id=1,
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = user1
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(mock_db, 2, role_data, user1.id)

    def test_update_role_nonexistent_requester(self, mock_db: Mock) -> None:
        """Test updating role with nonexistent requester raises permission error."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(mock_db, 1, role_data, 99999)

    def test_update_role_user_not_found(self, mock_db: Mock, admin_user: User) -> None:
        """Test updating role for nonexistent user raises bad request error."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.side_effect = [admin_user, None]
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(BadRequestError):
            user_crud.update_role(mock_db, 99999, role_data, admin_user.id)

    def test_get_all_users_success_admin(self, mock_db: Mock, admin_user: User) -> None:
        """Test admin getting all users successfully."""
        user1 = User(
            id=2,
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            id=3,
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=True,
            is_enabled=True,
        )

        # Mock get() for admin check
        mock_get_query = Mock()
        mock_get_filter = Mock()
        mock_get_filter.first.return_value = admin_user
        mock_get_query.filter.return_value = mock_get_filter

        # Mock query for get_all
        # - needs to support both count() and offset().limit().all()
        mock_query = Mock()
        mock_query.count.return_value = 3
        mock_limit = Mock()
        mock_limit.all.return_value = [
            admin_user,
            user1,
            user2,
        ]
        mock_offset = Mock()
        mock_offset.limit.return_value = mock_limit
        mock_query.offset.return_value = mock_offset

        mock_db.query.side_effect = [mock_get_query, mock_query]

        users, total = user_crud.get_all(mock_db, None, None, admin_user.id)

        assert total == 3
        assert len(users) == 3
        usernames = [user.username for user in users]
        assert "admin_user" in usernames
        assert "user1" in usernames
        assert "user2" in usernames

    def test_get_all_users_with_admin_filter(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test getting users with admin filter."""
        user2 = User(
            id=2,
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=True,
            is_enabled=True,
        )

        mock_get_query = Mock()
        mock_get_filter = Mock()
        mock_get_filter.first.return_value = admin_user
        mock_get_query.filter.return_value = mock_get_filter

        # Mock query that supports filter().count() and filter().offset().limit().all()
        mock_query = Mock()
        mock_filtered = Mock()
        mock_filtered.count.return_value = 2
        mock_limit = Mock()
        mock_limit.all.return_value = [admin_user, user2]
        mock_offset = Mock()
        mock_offset.limit.return_value = mock_limit
        mock_filtered.offset.return_value = mock_offset
        mock_query.filter.return_value = mock_filtered

        mock_db.query.side_effect = [mock_get_query, mock_query]

        users, total = user_crud.get_all(mock_db, None, True, admin_user.id)

        assert total == 2
        assert len(users) == 2
        for user in users:
            assert user.is_admin is True

    def test_get_all_users_with_pagination(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test getting users with pagination."""
        users_list = [
            User(
                id=i + 2,
                username=f"user{i}",
                password_hash=user_crud.hash_password(f"password{i}"),
                is_admin=False,
                is_enabled=True,
            )
            for i in range(5)
        ]

        mock_get_query = Mock()
        mock_get_filter = Mock()
        mock_get_filter.first.return_value = admin_user
        mock_get_query.filter.return_value = mock_get_filter

        # Mock query for get_all
        mock_query = Mock()
        mock_query.count.return_value = 6
        mock_limit = Mock()
        mock_limit.all.return_value = users_list[2:5]
        mock_offset = Mock()
        mock_offset.limit.return_value = mock_limit
        mock_query.offset.return_value = mock_offset

        mock_db.query.side_effect = [mock_get_query, mock_query]

        users, total = user_crud.get_all(
            mock_db, None, None, admin_user.id, skip=2, limit=3
        )

        assert total == 6
        assert len(users) == 3

    def test_get_all_users_permission_error_non_admin(self, mock_db: Mock) -> None:
        """Test non-admin trying to get all users raises permission error."""
        non_admin = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = non_admin
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        with pytest.raises(VelosimPermissionError):
            user_crud.get_all(mock_db, None, None, non_admin.id)

    def test_get_all_users_permission_error_nonexistent_requester(
        self, mock_db: Mock
    ) -> None:
        """Test nonexistent requester trying to get all users raises permission
        error."""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        with pytest.raises(VelosimPermissionError):
            user_crud.get_all(mock_db, None, None, 99999)

    def test_get_all_users_with_enabled_filter(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test getting users with enabled filter."""
        # Create some additional users - mix of enabled and disabled
        user1 = User(
            id=2,
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            id=3,
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
            is_enabled=False,  # Disabled user
        )
        user3 = User(
            id=4,
            username="user3",
            password_hash=user_crud.hash_password("password3"),
            is_admin=True,
            is_enabled=False,  # Disabled admin
        )

        # Mock for enabled users filter (first call)
        mock_get_query = Mock()
        mock_get_query.filter.return_value.first.return_value = admin_user

        mock_query = Mock()
        mock_filtered = Mock()
        mock_filtered.count.return_value = 2
        mock_limit = Mock()
        mock_limit.all.return_value = [admin_user, user1]
        mock_offset = Mock()
        mock_offset.limit.return_value = mock_limit
        mock_filtered.offset.return_value = mock_offset
        mock_query.filter.return_value = mock_filtered

        mock_db.query.side_effect = [mock_get_query, mock_query]

        # Filter for enabled users only
        users, total = user_crud.get_all(mock_db, True, None, admin_user.id)

        assert total == 2  # admin_user + user1 (both enabled)
        assert len(users) == 2
        for user in users:
            assert user.is_enabled is True

        # Reset mocks for disabled users filter (second call)
        mock_get_query2 = Mock()
        mock_get_query2.filter.return_value.first.return_value = admin_user

        mock_query2 = Mock()
        mock_filtered2 = Mock()
        mock_filtered2.count.return_value = 2
        mock_limit2 = Mock()
        mock_limit2.all.return_value = [user2, user3]
        mock_offset2 = Mock()
        mock_offset2.limit.return_value = mock_limit2
        mock_filtered2.offset.return_value = mock_offset2
        mock_query2.filter.return_value = mock_filtered2

        mock_db.query.side_effect = [mock_get_query2, mock_query2]

        # Filter for disabled users only
        users, total = user_crud.get_all(mock_db, False, None, admin_user.id)

        assert total == 2  # user2 + user3 (both disabled)
        assert len(users) == 2
        for user in users:
            assert user.is_enabled is False

    def test_create_user_disabled_admin_requester(self, mock_db: Mock) -> None:
        """Test creating a user with disabled admin requester raises permission
        error."""
        # Create a disabled admin user
        disabled_admin = User(
            id=1,
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )

        # Mock get requester (disabled admin) and get_by_username (None)
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [disabled_admin, None]
        mock_db.query.return_value = mock_query

        user_data = UserCreate(
            username="new_user",
            password="password",
            is_admin=False,
            is_enabled=True,
        )

        with pytest.raises(VelosimPermissionError):
            user_crud.create(mock_db, user_data, disabled_admin.id)

    def test_update_password_disabled_admin_requester(self, mock_db: Mock) -> None:
        """Test disabled admin trying to update password raises permission error."""
        # Create a disabled admin user
        disabled_admin = User(
            id=1,
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        # Create a regular user
        regular_user = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("old_password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester (disabled admin) - error raised before target user check
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = disabled_admin
        mock_db.query.return_value = mock_query

        password_data = UserPasswordUpdate(password="new_password")

        with pytest.raises(VelosimPermissionError):
            user_crud.update_password(
                mock_db, regular_user.id, password_data, disabled_admin.id
            )

    def test_update_role_disabled_admin_requester(self, mock_db: Mock) -> None:
        """Test disabled admin trying to update role raises permission error."""
        # Create a disabled admin user
        disabled_admin = User(
            id=1,
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        # Create a regular user
        regular_user = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester (disabled admin) - error raised before target user check
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = disabled_admin
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=True, is_enabled=True)

        with pytest.raises(VelosimPermissionError):
            user_crud.update_role(
                mock_db, regular_user.id, role_data, disabled_admin.id
            )

    def test_get_all_users_disabled_admin_requester(self, mock_db: Mock) -> None:
        """Test disabled admin trying to get all users raises permission error."""
        # Create a disabled admin user
        disabled_admin = User(
            id=1,
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )

        # Mock get requester (disabled admin)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = disabled_admin
        mock_db.query.return_value = mock_query

        with pytest.raises(VelosimPermissionError):
            user_crud.get_all(mock_db, None, None, disabled_admin.id)

    def test_update_role_disable_user(self, mock_db: Mock, admin_user: User) -> None:
        """Test admin disabling a user successfully."""
        # Create a regular user
        regular_user = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester (admin) and target user
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [admin_user, regular_user]
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=False, is_enabled=False)
        updated_user = user_crud.update_role(
            mock_db, regular_user.id, role_data, admin_user.id
        )

        assert updated_user.id == regular_user.id
        assert updated_user.is_enabled is False

    def test_update_role_enable_user(self, mock_db: Mock, admin_user: User) -> None:
        """Test admin enabling a disabled user successfully."""
        # Create a disabled user
        disabled_user = User(
            id=2,
            username="disabled_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=False,
        )

        # Mock get requester (admin) and target user
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [admin_user, disabled_user]
        mock_db.query.return_value = mock_query

        role_data = UserRoleUpdate(is_admin=False, is_enabled=True)
        updated_user = user_crud.update_role(
            mock_db, disabled_user.id, role_data, admin_user.id
        )

        assert updated_user.id == disabled_user.id
        assert updated_user.is_enabled is True

    def test_get_if_permission_admin_access_any_user(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test admin can access any user through get_if_permission."""
        # Create a regular user
        regular_user = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester (admin) and target user
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [admin_user, regular_user]
        mock_db.query.return_value = mock_query

        # Admin should be able to access regular user
        retrieved_user = user_crud.get_if_permission(
            mock_db, regular_user.id, admin_user.id
        )
        assert retrieved_user is not None
        assert retrieved_user.id == regular_user.id
        assert retrieved_user.username == regular_user.username

    def test_get_if_permission_user_access_self(self, mock_db: Mock) -> None:
        """Test user can access themselves through get_if_permission."""
        # Create a regular user
        regular_user = User(
            id=1,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester and target (same user)
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [regular_user, regular_user]
        mock_db.query.return_value = mock_query

        # User should be able to access themselves
        retrieved_user = user_crud.get_if_permission(
            mock_db, regular_user.id, regular_user.id
        )
        assert retrieved_user is not None
        assert retrieved_user.id == regular_user.id
        assert retrieved_user.username == regular_user.username

    def test_get_if_permission_user_access_other_forbidden(self, mock_db: Mock) -> None:
        """Test regular user cannot access other users through get_if_permission."""
        # Create two regular users
        user1 = User(
            id=1,
            username="user1",
            password_hash=user_crud.hash_password("password1"),
            is_admin=False,
            is_enabled=True,
        )
        user2 = User(
            id=2,
            username="user2",
            password_hash=user_crud.hash_password("password2"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester (user1) - error raised before getting target
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = user1
        mock_db.query.return_value = mock_query

        # User1 should not be able to access user2
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(mock_db, user2.id, user1.id)

    def test_get_if_permission_disabled_admin_forbidden(self, mock_db: Mock) -> None:
        """Test disabled admin cannot access users through get_if_permission."""
        # Create a disabled admin user
        disabled_admin = User(
            id=1,
            username="disabled_admin",
            password_hash=user_crud.hash_password("password"),
            is_admin=True,
            is_enabled=False,
        )
        # Create a regular user
        regular_user = User(
            id=2,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester (disabled admin) - error raised before getting target
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = disabled_admin
        mock_db.query.return_value = mock_query

        # Disabled admin should not be able to access regular user
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(mock_db, regular_user.id, disabled_admin.id)

    def test_get_if_permission_nonexistent_requester(self, mock_db: Mock) -> None:
        """Test nonexistent requester cannot access users through get_if_permission."""
        # Create a regular user
        regular_user = User(
            id=1,
            username="regular_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=True,
        )

        # Mock get requester (None - not found)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Nonexistent requester should not be able to access user
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(mock_db, regular_user.id, 99999)

    def test_get_if_permission_nonexistent_target_user(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Test get_if_permission returns None for nonexistent target user."""
        # Mock get requester (admin) and target user (None - not found)
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [admin_user, None]
        mock_db.query.return_value = mock_query

        # Admin trying to access nonexistent user should return None
        retrieved_user = user_crud.get_if_permission(mock_db, 99999, admin_user.id)
        assert retrieved_user is None

    def test_get_if_permission_disabled_user_access_self_forbidden(
        self, mock_db: Mock
    ) -> None:
        """Test disabled user cannot access themselves through get_if_permission."""
        # Create a disabled user
        disabled_user = User(
            id=1,
            username="disabled_user",
            password_hash=user_crud.hash_password("password"),
            is_admin=False,
            is_enabled=False,
        )

        # Mock get requester (disabled user) - error raised immediately
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = disabled_user
        mock_db.query.return_value = mock_query

        # Disabled user should not be able to access themselves either
        with pytest.raises(VelosimPermissionError):
            user_crud.get_if_permission(mock_db, disabled_user.id, disabled_user.id)
