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
from back.crud.sim_instance import sim_instance_crud
from back.schemas.sim_instance import SimInstanceCreate
from back.models.sim_instance import SimInstance
from back.models.user import User
from back.exceptions import VelosimPermissionError


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a normal test user (non-admin)."""
    user = User(
        username="testuser",
        password_hash="hashedpassword",
        is_admin=False,
        is_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin test user."""
    user = User(
        username="adminuser",
        password_hash="hashedpassword2",
        is_admin=True,
        is_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sim_instance(db: Session, test_user: User) -> SimInstance:
    """Create a test simulation instance for the normal user."""
    sim_instance_data = SimInstanceCreate(user_id=test_user.id)
    sim = sim_instance_crud.create(db, sim_instance_data)
    db.commit()
    return sim


class TestSimInstanceCRUD:
    """Tests for SimInstance CRUD operations with full permission coverage."""

    def test_create_sim_instance(self, db: Session, test_user: User) -> None:
        """Test creating a new simulation instance."""
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Verify core fields are set
        assert sim.id is not None
        assert sim.user_id == test_user.id
        assert sim.date_created is not None
        assert sim.date_updated is not None

    def test_get_sim_instance_by_id(
        self, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test retrieving a simulation instance by its ID."""
        retrieved_sim = sim_instance_crud.get(db, sim_instance.id)
        assert retrieved_sim is not None
        assert retrieved_sim.id == sim_instance.id
        assert retrieved_sim.user_id == sim_instance.user_id

    def test_get_sim_instance_by_id_not_found(self, db: Session) -> None:
        """Retrieving a non-existent simulation returns None."""
        retrieved_sim = sim_instance_crud.get(db, 99999)
        assert retrieved_sim is None

    def test_get_sim_instances_by_user(
        self, db: Session, test_user: User, sim_instance: SimInstance
    ) -> None:
        """Test retrieving all simulation instances for a specific user."""
        # Create another sim instance for the same user
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        user_sims = sim_instance_crud.get_by_user(db, test_user.id, test_user.id)
        assert len(user_sims) == 2
        assert all(sim.user_id == test_user.id for sim in user_sims)

    def test_get_sim_instances_by_user_empty(self, db: Session) -> None:
        """User with no simulations receives an empty list."""
        user = User(
            username="nosimsuser",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        user_sims = sim_instance_crud.get_by_user(db, user.id, user.id)
        assert len(user_sims) == 0

    def test_non_admin_cannot_access_other_users_sims(
        self, db: Session, test_user: User
    ) -> None:
        """Test that a non-admin cannot access another user's simulations."""
        # Create another user with a simulation
        other_user = User(
            username="otheruser",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        sim_instance_data = SimInstanceCreate(user_id=other_user.id)
        sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Non-admin attempting to access other user's simulations should fail
        with pytest.raises(VelosimPermissionError) as excinfo:
            sim_instance_crud.get_by_user(db, other_user.id, test_user.id)
        assert "cannot access" in str(excinfo.value)

    def test_admin_can_access_other_users_sims(
        self, db: Session, admin_user: User
    ) -> None:
        """Admin can access simulations of other users."""
        # Create another normal user with a simulation
        other_user = User(
            username="otheruser_admin_access",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        sim_instance_data = SimInstanceCreate(user_id=other_user.id)
        sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Admin requests simulations for the other user
        user_sims = sim_instance_crud.get_by_user(db, other_user.id, admin_user.id)
        assert len(user_sims) == 1
        assert user_sims[0].user_id == other_user.id

    def test_disabled_user_cannot_access_sims(self, db: Session) -> None:
        """Disabled users cannot access simulations."""
        user = User(
            username="disableduser",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        with pytest.raises(VelosimPermissionError):
            sim_instance_crud.get_by_user(db, user.id, user.id)

    def test_get_sim_instances_by_user_pagination(
        self, db: Session, test_user: User
    ) -> None:
        """Test pagination when retrieving simulation instances by user."""
        # Create 5 simulation instances
        for _ in range(5):
            sim_instance_data = SimInstanceCreate(user_id=test_user.id)
            sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # First page: limit 3
        user_sims_page1 = sim_instance_crud.get_by_user(
            db, test_user.id, test_user.id, skip=0, limit=3
        )
        assert len(user_sims_page1) == 3

        # Second page: remaining 2
        user_sims_page2 = sim_instance_crud.get_by_user(
            db, test_user.id, test_user.id, skip=3, limit=3
        )
        assert len(user_sims_page2) == 2

    def test_get_by_user_skip_beyond_total(self, db: Session, test_user: User) -> None:
        """Skip beyond total simulations returns an empty list."""
        # Create 2 simulations
        for _ in range(2):
            sim_instance_data = SimInstanceCreate(user_id=test_user.id)
            sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        sims = sim_instance_crud.get_by_user(
            db, test_user.id, test_user.id, skip=5, limit=2
        )
        assert sims == []

    def test_multiple_users_simulation_isolation(
        self, db: Session, test_user: User
    ) -> None:
        """Simulations for different users are isolated."""
        # Create another user
        other_user = User(
            username="otheruser2",
            password_hash="hashedpassword",
            is_admin=False,
            is_enabled=True,
        )
        db.add(other_user)
        db.commit()
        db.refresh(other_user)

        # Create simulations for both users
        sim1 = sim_instance_crud.create(db, SimInstanceCreate(user_id=test_user.id))
        sim2 = sim_instance_crud.create(db, SimInstanceCreate(user_id=other_user.id))
        db.commit()

        # Each user sees only their own simulations
        sims_user1 = sim_instance_crud.get_by_user(db, test_user.id, test_user.id)
        sims_user2 = sim_instance_crud.get_by_user(db, other_user.id, other_user.id)

        assert sims_user1 == [sim1]
        assert sims_user2 == [sim2]

    def test_get_all_sim_instances(
        self, db: Session, test_user: User, sim_instance: SimInstance
    ) -> None:
        """Test retrieving all simulation instances (admin function)."""
        # Create another user and sim instance
        user2 = User(
            username="testuser2",
            password_hash="hashedpassword2",
            is_admin=False,
            is_enabled=True,
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)

        sim_instance_data = SimInstanceCreate(user_id=user2.id)
        sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Get all simulation instances
        all_sims = sim_instance_crud.get_all(db)
        assert len(all_sims) >= 2
        user_ids = {sim.user_id for sim in all_sims}
        assert test_user.id in user_ids
        assert user2.id in user_ids

    def test_delete_sim_instance(self, db: Session, sim_instance: SimInstance) -> None:
        """Test deleting a simulation instance."""
        sim_id = sim_instance.id

        # Delete the simulation instance
        success = sim_instance_crud.delete(db, sim_id)
        db.commit()

        assert success is True

        # Verify deletion
        deleted_sim = sim_instance_crud.get(db, sim_id)
        assert deleted_sim is None

    def test_delete_sim_instance_not_found(self, db: Session) -> None:
        """Deleting a non-existent simulation instance returns False."""
        success = sim_instance_crud.delete(db, 99999)
        assert success is False
