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
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.models.user import User
from back.services.simulation_service import SimulationService
from back.crud.sim_instance import sim_instance_crud


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a normal test user (non-admin)."""
    user = db.query(User).filter(User.username == "testuser").first()
    if user:
        return user
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
def test_user2(db: Session) -> User:
    """Create a second normal test user (non-admin)."""
    user = db.query(User).filter(User.username == "testuser2").first()
    if user:
        return user
    user = User(
        username="testuser2",
        password_hash="hashedpassword2",
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
    user = db.query(User).filter(User.username == "adminuser").first()
    if user:
        return user
    user = User(
        username="adminuser",
        password_hash="hashedpassword3",
        is_admin=True,
        is_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def simulation_service() -> SimulationService:
    """Create a fresh simulation service instance for each test."""
    return SimulationService()


class TestSimulationService:
    """Tests for SimulationService."""

    def test_get_requesting_user_not_found(
        self, db: Session, simulation_service: SimulationService
    ) -> None:
        """Fetching a non-existent user should raise VelosimPermissionError."""
        with pytest.raises(VelosimPermissionError, match="Requesting user not found."):
            simulation_service._get_requesting_user(db, 99999)  # ID does not exist

    def test_get_requesting_user_disabled(
        self, db: Session, simulation_service: SimulationService, test_user: User
    ) -> None:
        """Fetching a disabled user should raise VelosimPermissionError."""
        # Disable the user
        test_user.is_enabled = False
        db.commit()

        with pytest.raises(
            VelosimPermissionError, match="Requesting user is disabled."
        ):
            simulation_service._get_requesting_user(db, test_user.id)

        # Re-enable for other tests
        test_user.is_enabled = True
        db.commit()

    def test_start_and_stop_simulation(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Normal user starts and stops a simulation."""
        # Start simulation
        sim_id, db_id = simulation_service.start_simulation(db, test_user.id)
        assert sim_id in simulation_service.active_simulations

        # Verify database record was created
        assert sim_instance_crud.get(db, db_id) is not None

        # Stop the simulation
        success = simulation_service.stop_simulation(db, sim_id, test_user.id)
        assert success is True
        assert sim_id not in simulation_service.active_simulations

        # Verify database record was deleted
        assert sim_instance_crud.get(db, db_id) is None

    def test_stop_simulation_not_found(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Stopping a non-existent simulation raises ItemNotFoundError."""
        with pytest.raises(ItemNotFoundError):
            simulation_service.stop_simulation(db, "nonexistent-sim-id", test_user.id)

    def test_stop_simulation_unauthorized(
        self,
        db: Session,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that a user cannot stop another user's simulation."""
        # User 1 starts a simulation
        sim_id, db_id = simulation_service.start_simulation(db, test_user.id)

        # User 2 tries to stop it
        with pytest.raises(VelosimPermissionError):
            simulation_service.stop_simulation(db, sim_id, test_user2.id)

        # Verify simulation is still running
        assert sim_id in simulation_service.active_simulations
        assert sim_instance_crud.get(db, db_id) is not None

    def test_get_active_user_simulations(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Retrieve only the requesting user's simulations."""
        # Start two simulations
        sim_id1, db_id1 = simulation_service.start_simulation(db, test_user.id)
        sim_id2, db_id2 = simulation_service.start_simulation(db, test_user.id)

        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert total == 2
        assert len(active_sims) == 2
        # Check that we got SimInstance objects
        assert all(hasattr(sim, "id") for sim in active_sims)
        assert all(hasattr(sim, "user_id") for sim in active_sims)
        # Check db_ids are in the results
        db_ids = [sim.id for sim in active_sims]
        assert db_id1 in db_ids
        assert db_id2 in db_ids

    def test_get_all_active_simulations_admin(
        self,
        db: Session,
        test_user: User,
        admin_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Admin users can list all active simulations."""
        # Start two simulations
        sim_id1, db_id1 = simulation_service.start_simulation(db, test_user.id)
        sim_id2, db_id2 = simulation_service.start_simulation(db, test_user.id)

        # Admin lists all active simulations
        sims, total = simulation_service.get_all_active_simulations(db, admin_user.id)
        assert total == 2
        assert len(sims) == 2
        # Check that we got SimInstance objects
        assert all(hasattr(sim, "id") for sim in sims)
        # Check db_ids are in the results
        db_ids = [sim.id for sim in sims]
        assert db_id1 in db_ids
        assert db_id2 in db_ids

    def test_get_all_active_simulations_non_admin(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Non-admin users cannot list all active simulations."""
        # Start a simulation as a normal user
        sim_id, _ = simulation_service.start_simulation(db, test_user.id)

        # Attempt to list all active simulations as the same non-admin user
        with pytest.raises(VelosimPermissionError) as exc_info:
            simulation_service.get_all_active_simulations(db, test_user.id)

        assert "Admin privileges required" in str(exc_info.value)

        # Verify simulation is still active
        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert total == 1
        assert len(active_sims) == 1

    def test_get_simulation_status(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test getting status of a user's specific simulation."""
        sim_id, _ = simulation_service.start_simulation(db, test_user.id)

        status = simulation_service.get_simulation_status(db, sim_id, test_user.id)
        assert status == "running"

    def test_get_simulation_status_not_found(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Non-existent simulation status raises error."""
        with pytest.raises(ItemNotFoundError):
            simulation_service.get_simulation_status(
                db, "nonexistent-sim-id", test_user.id
            )

    def test_stop_all_simulations_admin(
        self,
        db: Session,
        test_user: User,
        admin_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that an admin can stop all running simulations."""
        # Start two simulations as a non-admin user
        sim_id1, db_id1 = simulation_service.start_simulation(db, test_user.id)
        sim_id2, db_id2 = simulation_service.start_simulation(db, test_user.id)

        # Admin stops all simulations
        simulation_service.stop_all_simulations(db, admin_user.id)

        # Verify all simulations are stopped
        assert len(simulation_service.active_simulations) == 0

        # Verify database records are deleted
        assert sim_instance_crud.get(db, db_id1) is None
        assert sim_instance_crud.get(db, db_id2) is None

    def test_stop_all_simulations_non_admin(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Non-admin attempting to stop all simulations fails."""
        # Start a simulation
        sim_id, _ = simulation_service.start_simulation(db, test_user.id)

        # Non-admin cannot stop all simulations
        with pytest.raises(VelosimPermissionError):
            simulation_service.stop_all_simulations(db, test_user.id)

    def test_simulation_lifecycle(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test complete simulation lifecycle: start -> check status -> stop."""
        # Start
        sim_id, db_id = simulation_service.start_simulation(db, test_user.id)

        # Verify simulation is active
        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert any(sim.id == db_id for sim in active_sims)

        # Verify status
        assert (
            simulation_service.get_simulation_status(db, sim_id, test_user.id)
            == "running"
        )

        # Stop
        simulation_service.stop_simulation(db, sim_id, test_user.id)

        # Verify simulation no longer active
        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert not any(sim.id == db_id for sim in active_sims)

        # Verify status now raises error
        with pytest.raises(ItemNotFoundError):
            simulation_service.get_simulation_status(db, sim_id, test_user.id)
