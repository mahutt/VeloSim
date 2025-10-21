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
from back.models.user import User
from back.services.simulation_service import SimulationService
from back.crud.sim_instance import sim_instance_crud


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
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
    """Create a second test user."""
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
def simulation_service() -> SimulationService:
    """Create a fresh simulation service instance for each test."""
    return SimulationService()


class TestSimulationService:
    """Tests for SimulationService."""

    def test_start_simulation(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test starting a simulation creates database record."""
        sim_id, db_id = simulation_service.start_simulation(db, test_user.id)

        # Verify sim_id is returned
        assert sim_id is not None
        assert isinstance(sim_id, str)
        assert db_id > 0

        # Verify database record was created
        sim_instance = sim_instance_crud.get(db, db_id)
        assert sim_instance is not None
        assert sim_instance.user_id == test_user.id

        # Verify simulation is tracked in service
        assert sim_id in simulation_service.active_simulations
        assert simulation_service.active_simulations[sim_id]["db_id"] == db_id
        assert simulation_service.active_simulations[sim_id]["status"] == "running"

    def test_start_multiple_simulations(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test starting multiple simulations."""
        sim_id1, db_id1 = simulation_service.start_simulation(db, test_user.id)
        sim_id2, db_id2 = simulation_service.start_simulation(db, test_user.id)

        assert sim_id1 != sim_id2
        assert db_id1 != db_id2

        # Verify both are tracked
        assert len(simulation_service.active_simulations) == 2
        assert sim_id1 in simulation_service.active_simulations
        assert sim_id2 in simulation_service.active_simulations

        # Verify both have database records
        assert sim_instance_crud.get(db, db_id1) is not None
        assert sim_instance_crud.get(db, db_id2) is not None

    def test_stop_simulation(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test stopping a simulation removes database record."""
        sim_id, db_id = simulation_service.start_simulation(db, test_user.id)

        # Stop the simulation
        success = simulation_service.stop_simulation(db, sim_id, test_user.id)

        assert success is True
        assert sim_id not in simulation_service.active_simulations

        # Verify database record was deleted
        sim_instance = sim_instance_crud.get(db, db_id)
        assert sim_instance is None

    def test_stop_simulation_not_found(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test stopping a simulation that doesn't exist."""
        success = simulation_service.stop_simulation(
            db, "nonexistent-sim-id", test_user.id
        )
        assert success is False

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
        success = simulation_service.stop_simulation(db, sim_id, test_user2.id)

        assert success is False
        # Verify simulation is still running
        assert sim_id in simulation_service.active_simulations
        assert sim_instance_crud.get(db, db_id) is not None

    def test_get_active_simulations(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test getting list of active simulation IDs."""
        # Start two simulations
        sim_id1, _ = simulation_service.start_simulation(db, test_user.id)
        sim_id2, _ = simulation_service.start_simulation(db, test_user.id)

        active_sims = simulation_service.get_active_simulations()

        assert len(active_sims) == 2
        assert sim_id1 in active_sims
        assert sim_id2 in active_sims

    def test_get_simulation_status(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test getting status of a specific simulation."""
        sim_id, _ = simulation_service.start_simulation(db, test_user.id)

        status = simulation_service.get_simulation_status(sim_id)
        assert status == "running"

    def test_get_simulation_status_not_found(
        self, simulation_service: SimulationService
    ) -> None:
        """Test getting status of a simulation that doesn't exist."""
        status = simulation_service.get_simulation_status("nonexistent-sim-id")
        assert status == "not_found"

    def test_stop_all_simulations(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test stopping all simulations."""
        # Start two simulations
        sim_id1, db_id1 = simulation_service.start_simulation(db, test_user.id)
        sim_id2, db_id2 = simulation_service.start_simulation(db, test_user.id)

        # Stop all
        simulation_service.stop_all_simulations(db)

        # Verify all simulations are stopped
        assert len(simulation_service.active_simulations) == 0

        # Verify database records are deleted
        assert sim_instance_crud.get(db, db_id1) is None
        assert sim_instance_crud.get(db, db_id2) is None

    def test_simulation_lifecycle(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test complete simulation lifecycle: start -> check status -> stop."""
        # Start
        sim_id, db_id = simulation_service.start_simulation(db, test_user.id)
        assert sim_id in simulation_service.get_active_simulations()
        assert simulation_service.get_simulation_status(sim_id) == "running"
        assert sim_instance_crud.get(db, db_id) is not None

        # Stop
        success = simulation_service.stop_simulation(db, sim_id, test_user.id)
        assert success is True
        assert sim_id not in simulation_service.get_active_simulations()
        assert simulation_service.get_simulation_status(sim_id) == "not_found"
        assert sim_instance_crud.get(db, db_id) is None
