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
from unittest.mock import patch, Mock
from typing import Generator, cast

from sqlalchemy.orm import Session
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.models.user import User
from back.schemas.playback_speed import (
    ALLOWED_SPEEDS,
    PlaybackSpeedBase,
    SimulationPlaybackStatus,
)
from back.services.simulation_service import ActiveSimulationData, SimulationService
from sim.entities.inputParameters import InputParameter

# Apply patches before any simulator code is imported
pytestmark = pytest.mark.usefixtures("mock_heavy_sim_operations")


@pytest.fixture(scope="session", autouse=True)
def mock_heavy_sim_operations() -> Generator[None, None, None]:
    """
    Mock heavy simulation operations at the session level to prevent
    OSRM connection checks during tests.
    """
    with (
        patch(
            "sim.osm.OSRMConnection.OSRMConnection._verify_osrm_connection",
            return_value=True,
        ),
        patch("sim.core.SimulatorController.SimulatorController.start") as mock_start,
    ):
        # Make start() a no-op that doesn't spawn threads or do heavy work
        mock_start.return_value = None
        yield


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
def test_user2() -> User:
    """Create a second normal test user (non-admin)."""
    return User(
        id=2,
        username="testuser2",
        password_hash="hashedpassword2",
        is_admin=False,
        is_enabled=True,
    )


@pytest.fixture
def admin_user() -> User:
    """Create an admin test user."""
    return User(
        id=3,
        username="adminuser",
        password_hash="hashedpassword3",
        is_admin=True,
        is_enabled=True,
    )


@pytest.fixture
def simulation_service() -> SimulationService:
    """Create a fresh simulation service instance for each test."""
    return SimulationService()


@pytest.fixture
def mock_db() -> Mock:
    """Create a mock database session."""
    mock = Mock()
    mock.commit = Mock()
    return mock


@patch("back.services.simulation_service.sim_instance_crud")
@patch("back.services.simulation_service.user_crud")
class TestSimulationService:
    """Tests for SimulationService."""

    def test_start_and_stop_simulation(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Normal user starts and stops a simulation."""
        # Setup mocks
        mock_user_crud.get.side_effect = [test_user, test_user, test_user]
        mock_sim_instance = Mock()
        mock_sim_instance.id = 1
        mock_sim_instance.user_id = test_user.id
        mock_sim_crud.create.return_value = mock_sim_instance
        mock_sim_crud.get.side_effect = [
            mock_sim_instance,
            mock_sim_instance,
            mock_sim_instance,
            None,
        ]
        mock_sim_crud.delete.return_value = True

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )

        start_resp = simulation_service.start_simulation(
            mock_db, init_resp.sim_id, test_user.id
        )
        assert start_resp.status == "running"
        assert init_resp.sim_id in simulation_service.active_simulations

        success = simulation_service.stop_simulation(
            mock_db, init_resp.sim_id, test_user.id
        )
        assert success is True
        assert init_resp.sim_id not in simulation_service.active_simulations

    def test_stop_simulation_unauthorized(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """User cannot stop another user's simulation."""
        # Setup mocks for test_user
        mock_user_crud.get.side_effect = [test_user, test_user, test_user2]
        mock_sim_instance = Mock()
        mock_sim_instance.id = 1
        mock_sim_instance.user_id = test_user.id
        mock_sim_crud.create.return_value = mock_sim_instance
        mock_sim_crud.get.return_value = mock_sim_instance

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        with pytest.raises(VelosimPermissionError):
            simulation_service.stop_simulation(mock_db, sim_id, test_user2.id)
        assert sim_id in simulation_service.active_simulations

    def test_get_active_user_simulations(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Retrieve only the requesting user's simulations."""
        # Setup mocks
        mock_user_crud.get.side_effect = [
            test_user,
            test_user,
            test_user,
            test_user,
            test_user,
        ]
        mock_sim1 = Mock(id=1, user_id=test_user.id)
        mock_sim2 = Mock(id=2, user_id=test_user.id)
        mock_sim_crud.create.side_effect = [mock_sim1, mock_sim2]
        mock_sim_crud.get.side_effect = [mock_sim1, mock_sim1, mock_sim2, mock_sim2]

        # Mock db.query() chain for get_active_user_simulations
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_sim1, mock_sim2]
        mock_db.query.return_value = mock_query

        resp1 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(mock_db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(mock_db, resp2.sim_id, test_user.id)

        active_sims, total = simulation_service.get_active_user_simulations(
            mock_db, test_user.id
        )
        assert total == 2
        assert len(active_sims) == 2
        db_ids = [sim.id for sim in active_sims]
        assert resp1.db_id in db_ids
        assert resp2.db_id in db_ids

    def test_get_all_active_simulations_admin(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        admin_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Admin users can list all active simulations."""
        # Setup mocks
        mock_user_crud.get.side_effect = [
            test_user,
            test_user,
            test_user,
            test_user,
            admin_user,
        ]
        mock_sim1 = Mock(id=1, user_id=test_user.id)
        mock_sim2 = Mock(id=2, user_id=test_user.id)
        mock_sim_crud.create.side_effect = [mock_sim1, mock_sim2]
        mock_sim_crud.get.side_effect = [mock_sim1, mock_sim1, mock_sim2, mock_sim2]

        # Mock db.query() chain for get_all_active_simulations
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_sim1, mock_sim2]
        mock_db.query.return_value = mock_query

        resp1 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(mock_db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(mock_db, resp2.sim_id, test_user.id)

        sims, total = simulation_service.get_all_active_simulations(
            mock_db, admin_user.id
        )
        assert total == 2
        db_ids = [sim.id for sim in sims]
        assert resp1.db_id in db_ids
        assert resp2.db_id in db_ids

    def test_get_all_active_simulations_non_admin(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Non-admin users cannot list all active simulations."""
        # Setup mocks
        mock_user_crud.get.side_effect = [
            test_user,
            test_user,
            test_user,
            test_user,
            test_user,
        ]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.side_effect = [mock_sim, mock_sim]

        # Mock db.query() chain for get_active_user_simulations
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [mock_sim]
        mock_db.query.return_value = mock_query

        resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(mock_db, resp.sim_id, test_user.id)

        with pytest.raises(VelosimPermissionError):
            simulation_service.get_all_active_simulations(mock_db, test_user.id)

        active_sims, total = simulation_service.get_active_user_simulations(
            mock_db, test_user.id
        )
        assert total == 1
        assert len(active_sims) == 1

    def test_initialize_simulation_with_scenario_payload(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that scenario_payload is persisted when creating a sim instance."""
        from back.schemas.sim_instance import SimInstanceCreate

        # Setup mocks
        mock_user_crud.get.return_value = test_user
        mock_sim_instance = Mock()
        mock_sim_instance.id = 1
        mock_sim_instance.user_id = test_user.id
        mock_sim_instance.scenario_payload = None
        mock_sim_crud.create.return_value = mock_sim_instance

        # Create scenario payload
        scenario_payload = {
            "start_time": "08:00",
            "end_time": "12:00",
            "stations": [{"station_id": 1, "station_name": "Test"}],
            "resources": [{"resource_id": 101}],
        }

        params = InputParameter()
        simulation_service.initialize_simulation(
            mock_db, test_user.id, params, scenario_payload=scenario_payload
        )

        # Verify that create was called with scenario_payload
        mock_sim_crud.create.assert_called_once()
        create_call_args = mock_sim_crud.create.call_args[0]
        sim_instance_create = create_call_args[1]
        assert isinstance(sim_instance_create, SimInstanceCreate)
        assert sim_instance_create.scenario_payload == scenario_payload

    def test_initialize_simulation_without_scenario_payload(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that initialization works when scenario_payload is not provided."""
        from back.schemas.sim_instance import SimInstanceCreate

        # Setup mocks
        mock_user_crud.get.return_value = test_user
        mock_sim_instance = Mock()
        mock_sim_instance.id = 1
        mock_sim_instance.user_id = test_user.id
        mock_sim_instance.scenario_payload = None
        mock_sim_crud.create.return_value = mock_sim_instance

        params = InputParameter()
        simulation_service.initialize_simulation(mock_db, test_user.id, params)

        # Verify that create was called with None scenario_payload
        mock_sim_crud.create.assert_called_once()
        create_call_args = mock_sim_crud.create.call_args[0]
        sim_instance_create = create_call_args[1]
        assert isinstance(sim_instance_create, SimInstanceCreate)
        assert sim_instance_create.scenario_payload is None

    def test_simulation_not_active(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Inactive simulation attempts restore and fails authorization."""

        mock_user_crud.get.return_value = test_user

        # Sim exists in DB but belongs to another user
        foreign_sim = Mock()
        foreign_sim.user_id = 999
        mock_sim_crud.get_by_uuid.return_value = foreign_sim

        with pytest.raises(
            VelosimPermissionError,
            match="Unauthorized to restore simulation",
        ):
            simulation_service.verify_access(
                mock_db, "nonexistent-sim-id", test_user.id
            )

    def test_simulation_db_record_not_found(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Sim record missing in DB raises ItemNotFoundError."""
        mock_user_crud.get.return_value = test_user
        mock_sim_crud.get.return_value = None

        simulation_service.active_simulations["sim-uuid-1"] = {
            "db_id": 99999,
            "status": "running",
            "sim_time": 3600,
            "user_id": test_user.id,
        }
        with pytest.raises(
            ItemNotFoundError, match="Simulation instance record 99999 not found"
        ):
            simulation_service.verify_access(mock_db, "sim-uuid-1", test_user.id)

    def test_user_is_admin(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        admin_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Admin user should have access regardless of ownership."""
        mock_user_crud.get.return_value = admin_user
        mock_sim = Mock(id=1, user_id=999)
        mock_sim_crud.get.return_value = mock_sim

        simulation_service.active_simulations["sim-uuid-2"] = {
            "db_id": 1,
            "status": "running",
            "sim_time": 3600,
            "user_id": 999,
        }
        assert (
            simulation_service.verify_access(mock_db, "sim-uuid-2", admin_user.id)
            is True
        )

    def test_user_owns_simulation(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Simulation owner should have access."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.get.return_value = mock_sim

        simulation_service.active_simulations["sim-uuid-3"] = {
            "db_id": 1,
            "status": "running",
            "sim_time": 3600,
            "user_id": test_user.id,
        }
        assert (
            simulation_service.verify_access(mock_db, "sim-uuid-3", test_user.id)
            is True
        )

    def test_user_does_not_own_simulation(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user2: User,
        simulation_service: SimulationService,
        test_user: User,
    ) -> None:
        """Non-admin, non-owner should not have access."""
        mock_user_crud.get.return_value = test_user2
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.get.return_value = mock_sim

        simulation_service.active_simulations["sim-uuid-4"] = {
            "db_id": 1,
            "status": "running",
            "sim_time": 3600,
            "user_id": test_user.id,
        }
        assert (
            simulation_service.verify_access(mock_db, "sim-uuid-4", test_user2.id)
            is False
        )

    def test_set_playback_speed_valid_values(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """User can set a valid playback speed."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        playback_speed = PlaybackSpeedBase(playback_speed=2.0)
        response = simulation_service.set_playback_speed(
            mock_db, sim_id, playback_speed, test_user.id
        )

        assert response.playback_speed == playback_speed.playback_speed
        assert response.playback_speed in ALLOWED_SPEEDS
        assert response.status in [
            SimulationPlaybackStatus.RUNNING,
            SimulationPlaybackStatus.PAUSED,
        ]

    def test_set_playback_speed_unauthorized_user(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """A user cannot modify another user's simulation."""
        mock_user_crud.get.side_effect = [test_user, test_user, test_user2]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        playback_speed = PlaybackSpeedBase(playback_speed=1.0)
        with pytest.raises(VelosimPermissionError):
            simulation_service.set_playback_speed(
                mock_db, sim_id, playback_speed, test_user2.id
            )

    def test_get_playback_speed_not_found(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Accessing playback status for nonexistent sim should raise error."""
        mock_user_crud.get.return_value = test_user

        with pytest.raises(ItemNotFoundError):
            simulation_service.get_playback_speed(
                mock_db, "nonexistent-sim-id", test_user.id
            )

    def test_get_requesting_user_not_found(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        simulation_service: SimulationService,
    ) -> None:
        """Test that non-existent user raises ItemNotFoundError."""
        mock_user_crud.get.return_value = None

        with pytest.raises(ItemNotFoundError, match="Requesting user not found"):
            simulation_service._get_requesting_user(mock_db, 99999)

    def test_get_requesting_user_disabled(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        simulation_service: SimulationService,
    ) -> None:
        """Test that disabled user raises VelosimPermissionError."""
        disabled_user = User(
            id=10,
            username="disableduser",
            password_hash="hash",
            is_admin=False,
            is_enabled=False,
        )
        mock_user_crud.get.return_value = disabled_user

        with pytest.raises(VelosimPermissionError, match="Requesting user is disabled"):
            simulation_service._get_requesting_user(mock_db, disabled_user.id)

    def test_start_simulation_verify_access_fails(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that start_simulation fails if verify_access returns False."""
        mock_user_crud.get.side_effect = [test_user, test_user2]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id

        # test_user2 doesn't have access to test_user's simulation
        with pytest.raises(VelosimPermissionError, match="Unauthorized to start"):
            simulation_service.start_simulation(mock_db, sim_id, test_user2.id)

    def test_start_simulation_not_in_active_simulations(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Starting an inactive simulation triggers restore authorization failure."""

        mock_user_crud.get.return_value = test_user

        foreign_sim = Mock()
        foreign_sim.user_id = 999
        mock_sim_crud.get_by_uuid.return_value = foreign_sim

        with pytest.raises(
            VelosimPermissionError,
            match="Unauthorized to restore simulation",
        ):
            simulation_service.start_simulation(
                mock_db, "nonexistent-sim", test_user.id
            )

    def test_start_simulation_db_record_not_found(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test error when DB record doesn't exist."""
        mock_user_crud.get.return_value = test_user
        mock_sim_crud.get.return_value = None

        simulation_service.active_simulations["test-sim"] = {
            "db_id": 99999,
            "status": "initialized",
            "sim_time": 3600,
            "user_id": test_user.id,
        }
        with pytest.raises(ItemNotFoundError, match="Simulation instance record"):
            simulation_service.start_simulation(mock_db, "test-sim", test_user.id)

    def test_start_simulation_missing_simulator(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test error when simulator is None."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.get.return_value = mock_sim

        simulation_service.active_simulations["test-sim"] = {
            "db_id": mock_sim.id,
            "status": "initialized",
            "sim_time": 3600,
            "user_id": test_user.id,
        }

        with patch.object(simulation_service, "simulator", None):
            with pytest.raises(
                RuntimeError, match="Simulator for simulation .* not found"
            ):
                simulation_service.start_simulation(mock_db, "test-sim", test_user.id)

    def test_start_simulation_sim_not_in_simulator(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test error when sim_id not found in Simulator."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id

        # Mock the simulator to return None for get_sim_by_id
        with patch.object(
            simulation_service.simulator, "get_sim_by_id", return_value=None
        ):
            with pytest.raises(
                RuntimeError, match="Simulation .* not found in its Simulator"
            ):
                simulation_service.start_simulation(mock_db, sim_id, test_user.id)

    def test_start_simulation_missing_sim_time(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test error when sim_time is None."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id

        # Remove sim_time from active_simulations
        simulation_service.active_simulations[sim_id]["sim_time"] = None

        with pytest.raises(ValueError, match="does not have a valid sim_time"):
            simulation_service.start_simulation(mock_db, sim_id, test_user.id)

    def test_get_simulation_status_success(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test getting simulation status."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id

        status = simulation_service.get_simulation_status(mock_db, sim_id, test_user.id)
        assert status == "initialized"

    def test_get_simulation_status_unauthorized(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that unauthorized user cannot get status."""
        mock_user_crud.get.side_effect = [test_user, test_user2]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id

        with pytest.raises(VelosimPermissionError, match="Unauthorized to access"):
            simulation_service.get_simulation_status(mock_db, sim_id, test_user2.id)

    def test_stop_all_simulations_admin(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        admin_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that admin can stop all simulations."""
        mock_user_crud.get.side_effect = [
            test_user,
            test_user,
            test_user,
            test_user,
            admin_user,
        ]
        mock_sim1 = Mock(id=1, user_id=test_user.id)
        mock_sim2 = Mock(id=2, user_id=test_user.id)
        mock_sim_crud.create.side_effect = [mock_sim1, mock_sim2]
        mock_sim_crud.get.side_effect = [mock_sim1, mock_sim2, mock_sim1, mock_sim2]

        resp1 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(mock_db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(mock_db, resp2.sim_id, test_user.id)

        assert len(simulation_service.active_simulations) == 2

        simulation_service.stop_all_simulations(mock_db, admin_user.id)

        assert len(simulation_service.active_simulations) == 0

    def test_stop_all_simulations_non_admin(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that non-admin cannot stop all simulations."""
        mock_user_crud.get.return_value = test_user

        with pytest.raises(VelosimPermissionError, match="Only admins can stop"):
            simulation_service.stop_all_simulations(mock_db, test_user.id)

    def test_stop_all_simulations_system(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test system stop all simulations (no permission check)."""
        mock_user_crud.get.side_effect = [test_user, test_user, test_user, test_user]
        mock_sim1 = Mock(id=1, user_id=test_user.id)
        mock_sim2 = Mock(id=2, user_id=test_user.id)
        mock_sim_crud.create.side_effect = [mock_sim1, mock_sim2]
        mock_sim_crud.get.side_effect = [mock_sim1, mock_sim2, mock_sim1, mock_sim2]

        resp1 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        resp2 = simulation_service.initialize_simulation(
            mock_db, test_user.id, InputParameter()
        )
        simulation_service.start_simulation(mock_db, resp1.sim_id, test_user.id)
        simulation_service.start_simulation(mock_db, resp2.sim_id, test_user.id)

        assert len(simulation_service.active_simulations) == 2

        simulation_service.stop_all_simulations_system(mock_db)

        assert len(simulation_service.active_simulations) == 0

    def test_stop_all_simulations_core_with_exception(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test _stop_all_simulations_core handles exceptions."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        # Mock the simulator stop to raise an exception
        with patch.object(
            simulation_service.simulator, "stop", side_effect=Exception("Stop failed")
        ):
            # Should not raise, but print error
            simulation_service._stop_all_simulations_core(mock_db)

        assert len(simulation_service.active_simulations) == 0

    def test_set_playback_speed_pause(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test setting playback speed to 0 (pause)."""
        mock_user_crud.get.side_effect = [test_user, test_user, test_user]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.side_effect = [mock_sim, mock_sim, mock_sim]

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        playback_speed = PlaybackSpeedBase(playback_speed=0.0)
        response = simulation_service.set_playback_speed(
            mock_db, sim_id, playback_speed, test_user.id
        )

        assert response.playback_speed == 0.0
        assert response.status == SimulationPlaybackStatus.PAUSED

    def test_set_playback_speed_pause_emits_keyframe(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test setting playback speed to 0 emits keyframe with paused_by_user=True."""
        mock_user_crud.get.side_effect = [test_user, test_user, test_user]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.side_effect = [mock_sim, mock_sim, mock_sim]

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        # Get the sim_info and mock the controller
        sim_info = simulation_service.simulator.get_sim_by_id(sim_id)
        assert sim_info is not None
        mock_controller = Mock()
        mock_frame = Mock()
        mock_controller.create_frame.return_value = mock_frame

        # Mock the driver to update running state when paused
        mock_driver = Mock()
        mock_driver.running = True  # Initially running

        def pause_side_effect() -> None:
            mock_driver.running = False

        mock_driver.pause.side_effect = pause_side_effect
        mock_controller.realTimeDriver = mock_driver

        sim_info["simController"] = mock_controller

        # Mock the keyframe subscriber
        mock_keyframe_subscriber = Mock()
        simulation_service.active_simulations[sim_id][
            "keyframe_subscriber"
        ] = mock_keyframe_subscriber

        playback_speed = PlaybackSpeedBase(playback_speed=0.0)
        response = simulation_service.set_playback_speed(
            mock_db, sim_id, playback_speed, test_user.id
        )

        assert response.playback_speed == 0.0
        assert response.status == SimulationPlaybackStatus.PAUSED

        # Should create keyframe with paused_by_user=True
        mock_controller.create_frame.assert_called_with(
            is_key=True, paused_by_user=True
        )
        mock_controller.emit_frame.assert_called_once_with(mock_frame)

        # Should force-persist the keyframe
        mock_keyframe_subscriber.force_persist_keyframe.assert_called_once_with(
            mock_frame
        )

    def test_set_playback_speed_missing_simulator(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test error when simulator is None."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.get.return_value = mock_sim

        simulation_service.active_simulations["test-sim"] = {
            "db_id": mock_sim.id,
            "status": "running",
            "sim_time": 3600,
            "user_id": test_user.id,
        }

        playback_speed = PlaybackSpeedBase(playback_speed=1.0)
        with patch.object(simulation_service, "simulator", None):
            with pytest.raises(
                RuntimeError, match="Simulator for simulation .* not found"
            ):
                simulation_service.set_playback_speed(
                    mock_db, "test-sim", playback_speed, test_user.id
                )

    def test_set_playback_speed_sim_not_in_simulator(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test error when sim not found in simulator."""
        mock_user_crud.get.side_effect = [test_user, test_user, test_user]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.side_effect = [mock_sim, mock_sim, mock_sim]

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        with patch.object(
            simulation_service.simulator, "get_sim_by_id", return_value=None
        ):
            playback_speed = PlaybackSpeedBase(playback_speed=2.0)
            with pytest.raises(
                RuntimeError, match="Simulation .* not found in simulator"
            ):
                simulation_service.set_playback_speed(
                    mock_db, sim_id, playback_speed, test_user.id
                )

    def test_get_playback_speed_success(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test getting playback speed successfully."""
        mock_user_crud.get.side_effect = [test_user, test_user, test_user]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        response = simulation_service.get_playback_speed(mock_db, sim_id, test_user.id)

        assert response.simulation_id == sim_id
        assert isinstance(response.playback_speed, float)
        assert response.status in [
            SimulationPlaybackStatus.RUNNING,
            SimulationPlaybackStatus.PAUSED,
        ]

    def test_get_playback_speed_unauthorized(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        test_user2: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that unauthorized user cannot get playback speed."""
        mock_user_crud.get.side_effect = [test_user, test_user, test_user2]
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.create.return_value = mock_sim
        mock_sim_crud.get.return_value = mock_sim

        params = InputParameter()
        init_resp = simulation_service.initialize_simulation(
            mock_db, test_user.id, params
        )
        sim_id = init_resp.sim_id
        simulation_service.start_simulation(mock_db, sim_id, test_user.id)

        with pytest.raises(VelosimPermissionError, match="Unauthorized to access"):
            simulation_service.get_playback_speed(mock_db, sim_id, test_user2.id)

    def test_get_playback_speed_missing_simulator(
        self,
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test error when simulator is None."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(id=1, user_id=test_user.id)
        mock_sim_crud.get.return_value = mock_sim

        simulation_service.active_simulations["test-sim"] = {
            "db_id": mock_sim.id,
            "status": "running",
            "sim_time": 3600,
            "user_id": test_user.id,
        }

        with patch.object(simulation_service, "simulator", None):
            with pytest.raises(
                RuntimeError, match="Simulator for simulation .* not found"
            ):
                simulation_service.get_playback_speed(mock_db, "test-sim", test_user.id)

    def test_ensure_active_simulation_returns_existing(
        self: "TestSimulationService",
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        mock_user_crud.get.return_value = test_user

        existing_sim_data: ActiveSimulationData = {
            "db_id": 1,
            "status": "running",
            "sim_time": 123,
            "user_id": test_user.id,
        }

        simulation_service.active_simulations["sim-123"] = existing_sim_data

        result = simulation_service.ensure_active_simulation(
            sim_id="sim-123",
            db=cast(Session, mock_db),
            requesting_user=test_user.id,
        )

        assert result is existing_sim_data

    def test_restore_user_paused_simulation_preserves_paused_by_user_flag(
        self: "TestSimulationService",
        mock_user_crud: Mock,
        mock_sim_crud: Mock,
        mock_db: Mock,
        test_user: User,
        simulation_service: SimulationService,
    ) -> None:
        """Test that restoring a user-paused simulation preserves paused_by_user
        flag."""
        mock_user_crud.get.return_value = test_user
        mock_sim = Mock(
            id=1,
            user_id=test_user.id,
            scenario_payload='{"start_time": "08:00", "end_time": "10:00"}',
        )
        mock_sim_crud.get_by_uuid.return_value = mock_sim

        # Mock keyframe with pausedByUser=True
        keyframe_with_user_pause = {
            "clock": {
                "simSecondsPassed": 1800,
                "startTime": 0,
                "running": False,
                "realTimeFactor": 1.0,
                "pausedByUser": True,  # User had paused it
            },
            "stations": [],
            "vehicles": [],
            "drivers": [],
            "tasks": [],
        }

        scenario_data = {"start_time": "08:00", "end_time": "10:00"}

        # Mock simulation_data_service
        mock_data_service = Mock()
        mock_data_service.get_scenario.return_value = scenario_data
        mock_data_service.get_last_persisted_keyframe.return_value = (
            keyframe_with_user_pause
        )
        simulation_service.simulation_data_service = mock_data_service

        # Restore simulation
        restored = simulation_service.ensure_active_simulation(
            sim_id="test-sim-id", db=mock_db, requesting_user=test_user.id
        )

        # Verify paused_by_user flag is preserved in active_simulations
        assert restored.get("paused_by_user") is True
        assert (
            simulation_service.active_simulations["test-sim-id"].get("paused_by_user")
            is True
        )

        # Verify simulator was initialized with correct params by checking driver state
        sim_info = simulation_service.simulator.get_sim_by_id("test-sim-id")
        assert sim_info is not None
        assert sim_info["simController"].realTimeDriver.running is False  # Paused
