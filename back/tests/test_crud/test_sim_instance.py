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


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        password_hash="hashedpassword",
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sim_instance(db: Session, test_user: User) -> SimInstance:
    """Create a test simulation instance."""
    sim_instance_data = SimInstanceCreate(user_id=test_user.id)
    sim = sim_instance_crud.create(db, sim_instance_data)
    db.commit()
    return sim


class TestSimInstanceCRUD:
    """Tests for SimInstance CRUD operations."""

    def test_create_sim_instance(self, db: Session, test_user: User) -> None:
        """Test creating a new simulation instance."""
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        assert sim.id is not None
        assert sim.user_id == test_user.id
        assert sim.date_created is not None
        assert sim.date_updated is not None

    def test_get_sim_instance_by_id(
        self, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test getting a simulation instance by ID."""
        retrieved_sim = sim_instance_crud.get(db, sim_instance.id)

        assert retrieved_sim is not None
        assert retrieved_sim.id == sim_instance.id
        assert retrieved_sim.user_id == sim_instance.user_id

    def test_get_sim_instance_by_id_not_found(self, db: Session) -> None:
        """Test getting a simulation instance by ID that doesn't exist."""
        retrieved_sim = sim_instance_crud.get(db, 99999)
        assert retrieved_sim is None

    def test_get_sim_instances_by_user(
        self, db: Session, test_user: User, sim_instance: SimInstance
    ) -> None:
        """Test getting all simulation instances for a specific user."""
        # Create another sim instance for the same user
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Get all sim instances for the user
        user_sims = sim_instance_crud.get_by_user(db, test_user.id)

        assert len(user_sims) == 2
        assert all(sim.user_id == test_user.id for sim in user_sims)

    def test_get_sim_instances_by_user_empty(self, db: Session) -> None:
        """Test getting simulation instances when user has none."""
        user_sims = sim_instance_crud.get_by_user(db, 99999)
        assert len(user_sims) == 0

    def test_get_sim_instances_by_user_pagination(
        self, db: Session, test_user: User
    ) -> None:
        """Test pagination when getting simulation instances by user."""
        # Create 5 sim instances for the user
        for _ in range(5):
            sim_instance_data = SimInstanceCreate(user_id=test_user.id)
            sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Get first 3
        user_sims_page1 = sim_instance_crud.get_by_user(
            db, test_user.id, skip=0, limit=3
        )
        assert len(user_sims_page1) == 3

        # Get next 2
        user_sims_page2 = sim_instance_crud.get_by_user(
            db, test_user.id, skip=3, limit=3
        )
        assert len(user_sims_page2) == 2

    def test_get_all_sim_instances(
        self, db: Session, test_user: User, sim_instance: SimInstance
    ) -> None:
        """Test getting all simulation instances (admin function)."""
        # Create another user and sim instance
        user2 = User(
            username="testuser2",
            password_hash="hashedpassword2",
            is_admin=False,
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)

        sim_instance_data = SimInstanceCreate(user_id=user2.id)
        sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        # Get all sim instances
        all_sims = sim_instance_crud.get_all(db)

        assert len(all_sims) == 2
        user_ids = {sim.user_id for sim in all_sims}
        assert user_ids == {test_user.id, user2.id}

    def test_delete_sim_instance(self, db: Session, sim_instance: SimInstance) -> None:
        """Test deleting a simulation instance."""
        sim_id = sim_instance.id

        # Delete the sim instance
        success = sim_instance_crud.delete(db, sim_id)
        db.commit()

        assert success is True

        # Verify it's deleted
        deleted_sim = sim_instance_crud.get(db, sim_id)
        assert deleted_sim is None

    def test_delete_sim_instance_not_found(self, db: Session) -> None:
        """Test deleting a simulation instance that doesn't exist."""
        success = sim_instance_crud.delete(db, 99999)
        assert success is False
