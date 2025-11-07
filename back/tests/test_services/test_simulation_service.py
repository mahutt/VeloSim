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
from unittest.mock import patch
from typing import Generator
from sqlalchemy.orm import Session
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.models.user import User
from back.schemas import SimInstanceCreate
from back.schemas.playback_speed import (
    ALLOWED_SPEEDS,
    PlaybackSpeedBase,
    SimulationPlaybackStatus,
)
from back.services.simulation_service import SimulationService
from back.crud.sim_instance import sim_instance_crud

# Apply patches before any simulator code is imported
pytestmark = pytest.mark.usefixtures("mock_heavy_sim_operations")


@pytest.fixture(scope="session", autouse=True)
def mock_heavy_sim_operations() -> Generator[None, None, None]:
    """
    Mock heavy simulation operations at the session level to prevent
    OSM data loading and CH network building during tests.
    """
    with (
        patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file"),
        patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network"),
        patch("sim.DAO.OSMConnection.OSMConnection._set_projected_nodes"),
        patch("sim.DAO.OSMConnection.OSMConnection._build_edge_index"),
        patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph"),
        patch("sim.DAO.OSMConnection.OSMConnection.build_ch_network"),
        patch("sim.SimulatorController.SimulatorController.start") as mock_start,
    ):
        # Make start() a no-op that doesn't spawn threads or do heavy work
        mock_start.return_value = None
        yield


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
        with pytest.raises(ItemNotFoundError, match="Requesting user not found."):
            simulation_service._get_requesting_user(db, 99999)  # ID as int

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
        # Initialize simulation
        init_resp = simulation_service.initialize_simulation(db, test_user.id)
        sim_id = init_resp.sim_id
        db_id = init_resp.db_id

        # Start simulation
        start_resp = simulation_service.start_simulation(db, sim_id, test_user.id)
        assert start_resp.status == "running"
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
        # Initialize and start simulation
        init_resp = simulation_service.initialize_simulation(db, test_user.id)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        # User 2 tries to stop it
        with pytest.raises(VelosimPermissionError):
            simulation_service.stop_simulation(db, sim_id, test_user2.id)

        # Verify simulation is still running
        assert sim_id in simulation_service.active_simulations

    def test_get_active_user_simulations(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Retrieve only the requesting user's simulations."""
        # Start two simulations
        resp1 = simulation_service.initialize_simulation(db, test_user.id)
        resp2 = simulation_service.initialize_simulation(db, test_user.id)
        simulation_service.start_simulation(db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(db, resp2.sim_id, test_user.id)

        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert total == 2
        assert len(active_sims) == 2
        # Check that we got SimInstance objects
        assert all(hasattr(sim, "id") for sim in active_sims)
        assert all(hasattr(sim, "user_id") for sim in active_sims)
        db_ids = [sim.id for sim in active_sims]
        assert resp1.db_id in db_ids
        assert resp2.db_id in db_ids

    def test_get_all_active_simulations_admin(
        self,
        db: Session,
        test_user: User,
        admin_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Admin users can list all active simulations."""
        resp1 = simulation_service.initialize_simulation(db, test_user.id)
        resp2 = simulation_service.initialize_simulation(db, test_user.id)
        simulation_service.start_simulation(db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(db, resp2.sim_id, test_user.id)

        # Admin lists all active simulations
        sims, total = simulation_service.get_all_active_simulations(db, admin_user.id)
        assert total == 2
        assert len(sims) == 2
        db_ids = [sim.id for sim in sims]
        assert resp1.db_id in db_ids
        assert resp2.db_id in db_ids

    def test_get_all_active_simulations_non_admin(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Non-admin users cannot list all active simulations."""
        resp = simulation_service.initialize_simulation(db, test_user.id)
        simulation_service.start_simulation(db, resp.sim_id, test_user.id)

        # Attempt to list all active simulations as the same non-admin user
        with pytest.raises(VelosimPermissionError) as exc_info:
            simulation_service.get_all_active_simulations(db, test_user.id)

        assert "Admin privileges required" in str(exc_info.value)

        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert total == 1
        assert len(active_sims) == 1

    def test_get_simulation_status(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test getting status of a user's specific simulation."""
        resp = simulation_service.initialize_simulation(db, test_user.id)
        simulation_service.start_simulation(db, resp.sim_id, test_user.id)

        status = simulation_service.get_simulation_status(db, resp.sim_id, test_user.id)
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
        resp1 = simulation_service.initialize_simulation(db, test_user.id)
        resp2 = simulation_service.initialize_simulation(db, test_user.id)
        simulation_service.start_simulation(db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(db, resp2.sim_id, test_user.id)

        # Admin stops all simulations
        simulation_service.stop_all_simulations(db, admin_user.id)

        # Verify all simulations are stopped
        assert len(simulation_service.active_simulations) == 0

        # Verify database records are deleted
        assert sim_instance_crud.get(db, resp1.db_id) is None
        assert sim_instance_crud.get(db, resp2.db_id) is None

    def test_stop_all_simulations_non_admin(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Non-admin attempting to stop all simulations fails."""
        resp = simulation_service.initialize_simulation(db, test_user.id)
        simulation_service.start_simulation(db, resp.sim_id, test_user.id)

        with pytest.raises(VelosimPermissionError):
            simulation_service.stop_all_simulations(db, test_user.id)

    def test_simulation_lifecycle(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test complete simulation lifecycle: start -> check status -> stop."""
        # Initialize and start
        init_resp = simulation_service.initialize_simulation(db, test_user.id)
        sim_id = init_resp.sim_id
        db_id = init_resp.db_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        # Verify simulation is active
        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert any(sim.id == db_id for sim in active_sims)

        # Verify status
        status = simulation_service.get_simulation_status(db, sim_id, test_user.id)
        assert status == "running"

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

    def test_simulation_not_active(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Sim UUID not in active_simulations raises ItemNotFoundError."""
        with pytest.raises(
            ItemNotFoundError, match="Simulation .* is not currently active"
        ):
            simulation_service.verify_access(db, "nonexistent-sim-id", test_user.id)

    def test_simulation_db_record_not_found(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Sim record missing in DB raises ItemNotFoundError."""
        # Add active simulation with fake DB id
        simulation_service.active_simulations["sim-uuid-1"] = {
            "db_id": 99999,
            "status": "running",
        }

        with pytest.raises(
            ItemNotFoundError, match="Simulation instance record 99999 not found"
        ):
            simulation_service.verify_access(db, "sim-uuid-1", test_user.id)

    def test_user_is_admin(
        self, db: Session, admin_user: User, simulation_service: SimulationService
    ) -> None:
        """Admin user should have access regardless of ownership."""
        sim_instance_data = SimInstanceCreate(user_id=999)
        db_sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()
        simulation_service.active_simulations["sim-uuid-2"] = {
            "db_id": db_sim.id,
            "status": "running",
        }

        assert simulation_service.verify_access(db, "sim-uuid-2", admin_user.id) is True

    def test_user_owns_simulation(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Simulation owner should have access."""
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        db_sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()
        simulation_service.active_simulations["sim-uuid-3"] = {
            "db_id": db_sim.id,
            "status": "running",
        }

        assert simulation_service.verify_access(db, "sim-uuid-3", test_user.id) is True

    def test_user_does_not_own_simulation(
        self,
        db: Session,
        test_user2: User,
        simulation_service: SimulationService,
        test_user: User,
    ) -> None:
        """Non-admin, non-owner should not have access."""
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        db_sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()
        simulation_service.active_simulations["sim-uuid-4"] = {
            "db_id": db_sim.id,
            "status": "running",
        }

        assert (
            simulation_service.verify_access(db, "sim-uuid-4", test_user2.id) is False
        )

    def test_set_playback_speed_valid_values(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """User can set a valid playback speed."""
        # Initialize simulation and get the sim_id
        init_resp = simulation_service.initialize_simulation(db, test_user.id)
        sim_id = init_resp.sim_id

        # Start the simulation with the correct User object
        simulation_service.start_simulation(db, sim_id, test_user.id)

        # Pick a valid playback speed
        playback_speed = PlaybackSpeedBase(playback_speed=2.0)
        response = simulation_service.set_playback_speed(
            db, sim_id, playback_speed, test_user.id
        )

        # Verify playback speed
        assert response.playback_speed == playback_speed.playback_speed
        assert response.playback_speed in ALLOWED_SPEEDS
        assert response.status in [
            SimulationPlaybackStatus.RUNNING,
            SimulationPlaybackStatus.PAUSED,
        ]

    def test_set_playback_speed_invalid_value(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Invalid playback speeds should raise ValueError via schema validation."""
        # Schema itself should catch it before service is called
        with pytest.raises(ValueError, match="Playback speed must be one of"):
            PlaybackSpeedBase(playback_speed=3.0)

    def test_set_playback_speed_unauthorized_user(
        self,
        db: Session,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """A user cannot modify another user's simulation."""
        # Initialize and start simulation with the first user
        init_resp = simulation_service.initialize_simulation(db, test_user.id)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        playback_speed = PlaybackSpeedBase(playback_speed=1.0)

        # Attempting to set playback speed as a different user should raise error
        with pytest.raises(VelosimPermissionError):
            simulation_service.set_playback_speed(
                db, sim_id, playback_speed, test_user2.id
            )

    def test_get_playback_speed_valid(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Retrieve playback status for a simulation."""
        # Initialize and start simulation
        init_resp = simulation_service.initialize_simulation(db, test_user.id)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        # Retrieve playback speed/status
        response = simulation_service.get_playback_speed(db, sim_id, test_user.id)

        # Validate results
        assert response.simulation_id == sim_id
        assert response.playback_speed in ALLOWED_SPEEDS
        assert response.status in [
            SimulationPlaybackStatus.RUNNING,
            SimulationPlaybackStatus.PAUSED,
        ]

    def test_get_playback_speed_not_found(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Accessing playback status for nonexistent sim should raise error."""
        with pytest.raises(ItemNotFoundError):
            simulation_service.get_playback_speed(
                db, "nonexistent-sim-id", test_user.id
            )
