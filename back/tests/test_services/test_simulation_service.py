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
from sim.entities.inputParameters import InputParameter

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

    def test_start_and_stop_simulation(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Normal user starts and stops a simulation."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        db_id = init_resp.db_id

        start_resp = simulation_service.start_simulation(db, sim_id, test_user.id)
        assert start_resp.status == "running"
        assert sim_id in simulation_service.active_simulations
        assert sim_instance_crud.get(db, db_id) is not None

        success = simulation_service.stop_simulation(db, sim_id, test_user.id)
        assert success is True
        assert sim_id not in simulation_service.active_simulations
        assert sim_instance_crud.get(db, db_id) is None

    def test_stop_simulation_unauthorized(
        self,
        db: Session,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """User cannot stop another user's simulation."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        with pytest.raises(VelosimPermissionError):
            simulation_service.stop_simulation(db, sim_id, test_user2.id)
        assert sim_id in simulation_service.active_simulations

    def test_get_active_user_simulations(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Retrieve only the requesting user's simulations."""
        resp1 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(db, resp2.sim_id, test_user.id)

        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert total == 2
        assert len(active_sims) == 2
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
        resp1 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(db, resp2.sim_id, test_user.id)

        sims, total = simulation_service.get_all_active_simulations(db, admin_user.id)
        assert total == 2
        db_ids = [sim.id for sim in sims]
        assert resp1.db_id in db_ids
        assert resp2.db_id in db_ids

    def test_get_all_active_simulations_non_admin(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Non-admin users cannot list all active simulations."""
        resp = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(db, resp.sim_id, test_user.id)

        with pytest.raises(VelosimPermissionError):
            simulation_service.get_all_active_simulations(db, test_user.id)

        active_sims, total = simulation_service.get_active_user_simulations(
            db, test_user.id
        )
        assert total == 1
        assert len(active_sims) == 1

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
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        playback_speed = PlaybackSpeedBase(playback_speed=2.0)
        response = simulation_service.set_playback_speed(
            db, sim_id, playback_speed, test_user.id
        )

        assert response.playback_speed == playback_speed.playback_speed
        assert response.playback_speed in ALLOWED_SPEEDS
        assert response.status in [
            SimulationPlaybackStatus.RUNNING,
            SimulationPlaybackStatus.PAUSED,
        ]

    def test_set_playback_speed_unauthorized_user(
        self,
        db: Session,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """A user cannot modify another user's simulation."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        playback_speed = PlaybackSpeedBase(playback_speed=1.0)
        with pytest.raises(VelosimPermissionError):
            simulation_service.set_playback_speed(
                db, sim_id, playback_speed, test_user2.id
            )

    def test_get_playback_speed_not_found(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Accessing playback status for nonexistent sim should raise error."""
        with pytest.raises(ItemNotFoundError):
            simulation_service.get_playback_speed(
                db, "nonexistent-sim-id", test_user.id
            )

    def test_get_requesting_user_not_found(
        self, db: Session, simulation_service: SimulationService
    ) -> None:
        """Test that non-existent user raises ItemNotFoundError."""
        with pytest.raises(ItemNotFoundError, match="Requesting user not found"):
            simulation_service._get_requesting_user(db, 99999)

    def test_get_requesting_user_disabled(
        self, db: Session, simulation_service: SimulationService
    ) -> None:
        """Test that disabled user raises VelosimPermissionError."""
        disabled_user = User(
            username="disableduser",
            password_hash="hash",
            is_admin=False,
            is_enabled=False,
        )
        db.add(disabled_user)
        db.commit()
        db.refresh(disabled_user)

        with pytest.raises(VelosimPermissionError, match="Requesting user is disabled"):
            simulation_service._get_requesting_user(db, disabled_user.id)

    def test_start_simulation_verify_access_fails(
        self,
        db: Session,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that start_simulation fails if verify_access returns False."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id

        # test_user2 doesn't have access to test_user's simulation
        with pytest.raises(VelosimPermissionError, match="Unauthorized to start"):
            simulation_service.start_simulation(db, sim_id, test_user2.id)

    def test_start_simulation_not_in_active_simulations(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when sim_id not in active_simulations."""
        with pytest.raises(ItemNotFoundError):
            simulation_service.start_simulation(db, "nonexistent-sim", test_user.id)

    def test_start_simulation_db_record_not_found(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when DB record doesn't exist."""
        simulation_service.active_simulations["test-sim"] = {
            "db_id": 99999,
            "status": "initialized",
        }
        with pytest.raises(ItemNotFoundError, match="Simulation instance record"):
            simulation_service.start_simulation(db, "test-sim", test_user.id)

    def test_start_simulation_missing_simulator(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when simulator is None."""
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        db_sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        simulation_service.active_simulations["test-sim"] = {
            "db_id": db_sim.id,
            "status": "initialized",
            "simulator": None,
        }

        with pytest.raises(RuntimeError, match="Simulator for simulation .* not found"):
            simulation_service.start_simulation(db, "test-sim", test_user.id)

    def test_start_simulation_sim_not_in_simulator(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when sim_id not found in Simulator."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id

        # Mock the simulator to return None for get_sim_by_id
        sim_data = simulation_service.active_simulations[sim_id]
        mock_sim = sim_data["simulator"]
        with patch.object(mock_sim, "get_sim_by_id", return_value=None):
            with pytest.raises(
                RuntimeError, match="Simulation .* not found in its Simulator"
            ):
                simulation_service.start_simulation(db, sim_id, test_user.id)

    def test_start_simulation_missing_sim_time(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when sim_time is None."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id

        # Remove sim_time from active_simulations
        simulation_service.active_simulations[sim_id]["sim_time"] = None

        with pytest.raises(ValueError, match="does not have a valid sim_time"):
            simulation_service.start_simulation(db, sim_id, test_user.id)

    def test_get_simulation_status_success(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test getting simulation status."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id

        status = simulation_service.get_simulation_status(db, sim_id, test_user.id)
        assert status == "initialized"

    def test_get_simulation_status_unauthorized(
        self,
        db: Session,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that unauthorized user cannot get status."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id

        with pytest.raises(VelosimPermissionError, match="Unauthorized to access"):
            simulation_service.get_simulation_status(db, sim_id, test_user2.id)

    def test_stop_all_simulations_admin(
        self,
        db: Session,
        test_user: User,
        admin_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that admin can stop all simulations."""
        resp1 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(db, resp2.sim_id, test_user.id)

        assert len(simulation_service.active_simulations) == 2

        simulation_service.stop_all_simulations(db, admin_user.id)

        assert len(simulation_service.active_simulations) == 0

    def test_stop_all_simulations_non_admin(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test that non-admin cannot stop all simulations."""
        with pytest.raises(VelosimPermissionError, match="Only admins can stop"):
            simulation_service.stop_all_simulations(db, test_user.id)

    def test_stop_all_simulations_system(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test system stop all simulations (no permission check)."""
        resp1 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(db, resp2.sim_id, test_user.id)

        assert len(simulation_service.active_simulations) == 2

        simulation_service.stop_all_simulations_system(db)

        assert len(simulation_service.active_simulations) == 0

    def test_stop_all_simulations_core_with_exception(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test _stop_all_simulations_core handles exceptions."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        # Mock the simulator stop to raise an exception
        sim_data = simulation_service.active_simulations[sim_id]
        mock_sim = sim_data["simulator"]
        with patch.object(mock_sim, "stop", side_effect=Exception("Stop failed")):
            # Should not raise, but print error
            simulation_service._stop_all_simulations_core(db)

        assert len(simulation_service.active_simulations) == 0

    def test_set_playback_speed_pause(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test setting playback speed to 0 (pause)."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        playback_speed = PlaybackSpeedBase(playback_speed=0.0)
        response = simulation_service.set_playback_speed(
            db, sim_id, playback_speed, test_user.id
        )

        assert response.playback_speed == 0.0
        assert response.status == SimulationPlaybackStatus.PAUSED

    def test_set_playback_speed_missing_simulator(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when simulator is None."""
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        db_sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        simulation_service.active_simulations["test-sim"] = {
            "db_id": db_sim.id,
            "status": "running",
            "simulator": None,
        }

        playback_speed = PlaybackSpeedBase(playback_speed=1.0)
        with pytest.raises(RuntimeError, match="Simulator for simulation .* not found"):
            simulation_service.set_playback_speed(
                db, "test-sim", playback_speed, test_user.id
            )

    def test_set_playback_speed_sim_not_in_simulator(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when sim not found in simulator."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        sim_data = simulation_service.active_simulations[sim_id]
        mock_sim = sim_data["simulator"]
        with patch.object(mock_sim, "get_sim_by_id", return_value=None):
            playback_speed = PlaybackSpeedBase(playback_speed=2.0)
            with pytest.raises(
                RuntimeError, match="Simulation .* not found in simulator"
            ):
                simulation_service.set_playback_speed(
                    db, sim_id, playback_speed, test_user.id
                )

    def test_get_playback_speed_success(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test getting playback speed successfully."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        response = simulation_service.get_playback_speed(db, sim_id, test_user.id)

        assert response.simulation_id == sim_id
        assert isinstance(response.playback_speed, float)
        assert response.status in [
            SimulationPlaybackStatus.RUNNING,
            SimulationPlaybackStatus.PAUSED,
        ]

    def test_get_playback_speed_unauthorized(
        self,
        db: Session,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that unauthorized user cannot get playback speed."""
        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(db, test_user.id, params)
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(db, sim_id, test_user.id)

        with pytest.raises(VelosimPermissionError, match="Unauthorized to access"):
            simulation_service.get_playback_speed(db, sim_id, test_user2.id)

    def test_get_playback_speed_missing_simulator(
        self, db: Session, test_user: User, simulation_service: SimulationService
    ) -> None:
        """Test error when simulator is None."""
        sim_instance_data = SimInstanceCreate(user_id=test_user.id)
        db_sim = sim_instance_crud.create(db, sim_instance_data)
        db.commit()

        simulation_service.active_simulations["test-sim"] = {
            "db_id": db_sim.id,
            "status": "running",
            "simulator": None,
        }

        with pytest.raises(RuntimeError, match="Simulator for simulation .* not found"):
            simulation_service.get_playback_speed(db, "test-sim", test_user.id)
