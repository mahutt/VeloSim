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
from back.crud.sim_instance import sim_instance_crud
from back.schemas.sim_instance import SimInstanceCreate
from back.models.sim_instance import SimInstance
from back.models.user import User
from back.exceptions import VelosimPermissionError


@pytest.fixture
def test_user() -> User:
    """Create a normal test user (non-admin)."""
    return User(
        id=1,
        username="testuser",
        password_hash="hashedpassword",
        is_admin=False,
        is_enabled=True,
    )


@pytest.fixture
def admin_user() -> User:
    """Create an admin test user."""
    return User(
        id=2,
        username="adminuser",
        password_hash="hashedpassword2",
        is_admin=True,
        is_enabled=True,
    )


@pytest.fixture
def sim_instance(test_user: User) -> SimInstance:
    """Create a test simulation instance for the normal user."""
    from datetime import datetime

    return SimInstance(
        id=1,
        user_id=test_user.id,
        date_created=datetime.now(),
        date_updated=datetime.now(),
    )


class TestSimInstanceCRUD:
    """Tests for SimInstance CRUD operations with full permission coverage."""

    def test_create_sim_instance(self, mock_db: Mock, test_user: User) -> None:
        """Test creating a new simulation instance."""
        from datetime import datetime
        from typing import Any

        # Mock add to set ID and datetime fields
        def mock_add(obj: Any) -> None:
            obj.id = 1
            obj.date_created = datetime.now()
            obj.date_updated = datetime.now()

        mock_db.add.side_effect = mock_add
        mock_db.flush = Mock()
        mock_db.refresh = Mock()

        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        sim = sim_instance_crud.create(mock_db, sim_instance_data)

        # Verify core fields are set
        assert sim.id is not None
        assert sim.user_id == test_user.id
        assert sim.date_created is not None
        assert sim.date_updated is not None

    def test_get_sim_instance_by_id(
        self, mock_db: Mock, sim_instance: SimInstance
    ) -> None:
        """Test retrieving a simulation instance by its ID."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sim_instance
        mock_db.query.return_value = mock_query

        retrieved_sim = sim_instance_crud.get(mock_db, sim_instance.id)
        assert retrieved_sim is not None
        assert retrieved_sim.id == sim_instance.id
        assert retrieved_sim.user_id == sim_instance.user_id

    def test_get_sim_instance_by_id_not_found(self, mock_db: Mock) -> None:
        """Retrieving a non-existent simulation returns None."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        retrieved_sim = sim_instance_crud.get(mock_db, 99999)
        assert retrieved_sim is None

    def test_get_sim_instances_by_user(
        self, mock_db: Mock, test_user: User, sim_instance: SimInstance
    ) -> None:
        """Test retrieving all simulation instances for a specific user."""
        from datetime import datetime

        sim2 = SimInstance(
            id=2,
            user_id=test_user.id,
            date_created=datetime.now(),
            date_updated=datetime.now(),
        )

        # Mock requester check (test_user accessing themselves)
        mock_requester_query = Mock()
        mock_requester_query.filter.return_value.first.return_value = test_user

        # Mock sim instances query
        mock_sim_query = Mock()
        mock_filter = mock_sim_query.filter.return_value
        mock_filter.offset.return_value.limit.return_value.all.return_value = [
            sim_instance,
            sim2,
        ]

        mock_db.query.side_effect = [mock_requester_query, mock_sim_query]

        user_sims = sim_instance_crud.get_by_user(mock_db, test_user.id, test_user.id)
        assert len(user_sims) == 2
        assert all(sim.user_id == test_user.id for sim in user_sims)

    def test_get_sim_instances_by_user_empty(self, mock_db: Mock) -> None:
        """User with no simulations receives an empty list."""
        user = User(
            id=10,
            username="nosimsuser",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )

        # Mock requester check
        mock_requester_query = Mock()
        mock_requester_query.filter.return_value.first.return_value = user

        # Mock sim instances query returning empty
        mock_sim_query = Mock()
        mock_filter = mock_sim_query.filter.return_value
        mock_filter.offset.return_value.limit.return_value.all.return_value = []

        mock_db.query.side_effect = [mock_requester_query, mock_sim_query]

        user_sims = sim_instance_crud.get_by_user(mock_db, user.id, user.id)
        assert len(user_sims) == 0

    def test_non_admin_cannot_access_other_users_sims(
        self, mock_db: Mock, test_user: User
    ) -> None:
        """Test that a non-admin cannot access another user's simulations."""
        other_user = User(
            id=10,
            username="otheruser",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )

        # Mock requester check - test_user trying to access other_user's sims
        mock_requester_query = Mock()
        mock_requester_query.filter.return_value.first.return_value = test_user
        mock_db.query.return_value = mock_requester_query

        # Non-admin attempting to access other user's simulations should fail
        with pytest.raises(VelosimPermissionError) as excinfo:
            sim_instance_crud.get_by_user(mock_db, other_user.id, test_user.id)
        assert "cannot access" in str(excinfo.value)

    def test_admin_can_access_other_users_sims(
        self, mock_db: Mock, admin_user: User
    ) -> None:
        """Admin can access simulations of other users."""
        from datetime import datetime

        other_user = User(
            id=10,
            username="otheruser_admin_access",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )

        sim = SimInstance(
            id=1,
            user_id=other_user.id,
            date_created=datetime.now(),
            date_updated=datetime.now(),
        )

        # Mock requester check - admin accessing other user's sims
        mock_requester_query = Mock()
        mock_requester_query.filter.return_value.first.return_value = admin_user

        # Mock sim instances query
        mock_sim_query = Mock()
        mock_filter = mock_sim_query.filter.return_value
        mock_filter.offset.return_value.limit.return_value.all.return_value = [sim]

        mock_db.query.side_effect = [mock_requester_query, mock_sim_query]

        # Admin requests simulations for the other user
        user_sims = sim_instance_crud.get_by_user(mock_db, other_user.id, admin_user.id)
        assert len(user_sims) == 1
        assert user_sims[0].user_id == other_user.id

    def test_disabled_user_cannot_access_sims(self, mock_db: Mock) -> None:
        """Disabled users cannot access simulations."""
        user = User(
            id=10,
            username="disableduser",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=False,
        )

        # Mock requester check - disabled user
        mock_requester_query = Mock()
        mock_requester_query.filter.return_value.first.return_value = user
        mock_db.query.return_value = mock_requester_query

        with pytest.raises(VelosimPermissionError):
            sim_instance_crud.get_by_user(mock_db, user.id, user.id)

    def test_get_sim_instances_by_user_pagination(
        self, mock_db: Mock, test_user: User
    ) -> None:
        """Test pagination when retrieving simulation instances by user."""
        from datetime import datetime

        sims_page1 = [
            SimInstance(
                id=i,
                user_id=test_user.id,
                date_created=datetime.now(),
                date_updated=datetime.now(),
            )
            for i in range(1, 4)
        ]
        sims_page2 = [
            SimInstance(
                id=i,
                user_id=test_user.id,
                date_created=datetime.now(),
                date_updated=datetime.now(),
            )
            for i in range(4, 6)
        ]

        # Mock requester check for both calls
        mock_requester_query1 = Mock()
        mock_requester_query1.filter.return_value.first.return_value = test_user
        mock_requester_query2 = Mock()
        mock_requester_query2.filter.return_value.first.return_value = test_user

        # Mock sim queries for pagination
        mock_sim_query1 = Mock()
        mock_filter1 = mock_sim_query1.filter.return_value
        mock_filter1.offset.return_value.limit.return_value.all.return_value = (
            sims_page1
        )
        mock_sim_query2 = Mock()
        mock_filter2 = mock_sim_query2.filter.return_value
        mock_filter2.offset.return_value.limit.return_value.all.return_value = (
            sims_page2
        )

        mock_db.query.side_effect = [
            mock_requester_query1,
            mock_sim_query1,
            mock_requester_query2,
            mock_sim_query2,
        ]

        # First page: limit 3
        user_sims_page1 = sim_instance_crud.get_by_user(
            mock_db, test_user.id, test_user.id, skip=0, limit=3
        )
        assert len(user_sims_page1) == 3

        # Second page: remaining 2
        user_sims_page2 = sim_instance_crud.get_by_user(
            mock_db, test_user.id, test_user.id, skip=3, limit=3
        )
        assert len(user_sims_page2) == 2

    def test_get_by_user_skip_beyond_total(
        self, mock_db: Mock, test_user: User
    ) -> None:
        """Skip beyond total simulations returns an empty list."""
        # Mock requester check
        mock_requester_query = Mock()
        mock_requester_query.filter.return_value.first.return_value = test_user

        # Mock sim query returning empty (skip beyond total)
        mock_sim_query = Mock()
        mock_filter = mock_sim_query.filter.return_value
        mock_filter.offset.return_value.limit.return_value.all.return_value = []

        mock_db.query.side_effect = [mock_requester_query, mock_sim_query]

        sims = sim_instance_crud.get_by_user(
            mock_db, test_user.id, test_user.id, skip=5, limit=2
        )
        assert sims == []

    def test_multiple_users_simulation_isolation(
        self, mock_db: Mock, test_user: User
    ) -> None:
        """Simulations for different users are isolated."""
        from datetime import datetime

        other_user = User(
            id=10,
            username="otheruser2",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )

        sim1 = SimInstance(
            id=1,
            user_id=test_user.id,
            date_created=datetime.now(),
            date_updated=datetime.now(),
        )
        sim2 = SimInstance(
            id=2,
            user_id=other_user.id,
            date_created=datetime.now(),
            date_updated=datetime.now(),
        )

        # Mock for test_user getting their sims
        mock_requester_query1 = Mock()
        mock_requester_query1.filter.return_value.first.return_value = test_user
        mock_sim_query1 = Mock()
        mock_filter1 = mock_sim_query1.filter.return_value
        mock_filter1.offset.return_value.limit.return_value.all.return_value = [sim1]

        # Mock for other_user getting their sims
        mock_requester_query2 = Mock()
        mock_requester_query2.filter.return_value.first.return_value = other_user
        mock_sim_query2 = Mock()
        mock_filter2 = mock_sim_query2.filter.return_value
        mock_filter2.offset.return_value.limit.return_value.all.return_value = [sim2]

        mock_db.query.side_effect = [
            mock_requester_query1,
            mock_sim_query1,
            mock_requester_query2,
            mock_sim_query2,
        ]

        # Each user sees only their own simulations
        sims_user1 = sim_instance_crud.get_by_user(mock_db, test_user.id, test_user.id)
        sims_user2 = sim_instance_crud.get_by_user(
            mock_db, other_user.id, other_user.id
        )

        assert sims_user1 == [sim1]
        assert sims_user2 == [sim2]

    def test_get_all_sim_instances(
        self, mock_db: Mock, test_user: User, sim_instance: SimInstance
    ) -> None:
        """Test retrieving all simulation instances (admin function)."""
        from datetime import datetime

        user2 = User(
            id=10,
            username="testuser2",
            password_hash="hashedpassword2",
            is_admin=False,
            is_enabled=True,
        )

        sim2 = SimInstance(
            id=2,
            user_id=user2.id,
            date_created=datetime.now(),
            date_updated=datetime.now(),
        )

        mock_query = Mock()
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            sim_instance,
            sim2,
        ]
        mock_db.query.return_value = mock_query

        # Get all simulation instances
        all_sims = sim_instance_crud.get_all(mock_db)
        assert len(all_sims) >= 2
        user_ids = {sim.user_id for sim in all_sims}
        assert test_user.id in user_ids
        assert user2.id in user_ids

    def test_delete_sim_instance(
        self, mock_db: Mock, sim_instance: SimInstance
    ) -> None:
        """Test deleting a simulation instance."""
        sim_id = sim_instance.id

        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [sim_instance, None]
        mock_db.query.return_value = mock_query
        mock_db.delete = Mock()

        # Delete the simulation instance
        success = sim_instance_crud.delete(mock_db, sim_id)

        assert success is True

        # Verify deletion
        deleted_sim = sim_instance_crud.get(mock_db, sim_id)
        assert deleted_sim is None

    def test_delete_sim_instance_not_found(self, mock_db: Mock) -> None:
        """Deleting a non-existent simulation instance returns False."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        success = sim_instance_crud.delete(mock_db, 99999)
        assert success is False
