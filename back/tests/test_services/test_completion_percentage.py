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

import uuid
import pytest
from unittest.mock import Mock, patch
from typing import Generator

from back.models.sim_instance import SimInstance
from back.services.simulation_service import SimulationService


@pytest.fixture(scope="session", autouse=True)
def mock_heavy_sim_operations() -> Generator[None, None, None]:
    with (
        patch(
            "sim.osm.graphhopper_connection"
            ".GraphHopperConnection"
            "._verify_graphhopper_connection",
            return_value=True,
        ),
        patch("sim.core.simulator_controller.SimulatorController.start") as mock_start,
    ):
        mock_start.return_value = None
        yield


@pytest.fixture
def service() -> SimulationService:
    return SimulationService()


@pytest.fixture
def mock_db() -> Mock:
    return Mock()


def make_sim(
    *,
    completed: bool = False,
    scenario_payload: dict | None = None,
    sim_uuid: str | None = None,
) -> SimInstance:
    sim = Mock(spec=SimInstance)
    sim.id = 1
    sim.completed = completed
    sim.scenario_payload = scenario_payload
    sim.uuid = uuid.UUID(sim_uuid) if sim_uuid else uuid.uuid4()
    return sim


class TestComputeCompletionPercentage:
    """Unit tests for SimulationService.compute_completion_percentage."""

    def test_completed_sim_returns_100(
        self, service: SimulationService, mock_db: Mock
    ) -> None:
        sim = make_sim(completed=True)
        assert service.compute_completion_percentage(mock_db, sim) == 100

    @patch("back.services.simulation_service.sim_frame_crud")
    def test_no_frames_no_payload_returns_0(
        self, mock_frame_crud: Mock, service: SimulationService, mock_db: Mock
    ) -> None:
        mock_frame_crud.get_latest_sim_seconds.return_value = None
        sim = make_sim(scenario_payload=None)
        assert service.compute_completion_percentage(mock_db, sim) == 0

    @patch("back.services.simulation_service.sim_frame_crud")
    def test_no_end_time_in_payload_returns_0(
        self, mock_frame_crud: Mock, service: SimulationService, mock_db: Mock
    ) -> None:
        mock_frame_crud.get_latest_sim_seconds.return_value = 1000.0
        sim = make_sim(scenario_payload={"start_time": "day1:08:00"})
        assert service.compute_completion_percentage(mock_db, sim) == 0

    @patch("back.services.simulation_service.sim_frame_crud")
    def test_inactive_sim_halfway(
        self, mock_frame_crud: Mock, service: SimulationService, mock_db: Mock
    ) -> None:
        # _time_str_to_seconds("day1:17:00") = 17 * 3600 = 61200s
        # frame at 30600s = exactly 50% of 61200
        mock_frame_crud.get_latest_sim_seconds.return_value = 30600.0
        sim = make_sim(
            scenario_payload={"start_time": "day1:08:00", "end_time": "day1:17:00"}
        )
        result = service.compute_completion_percentage(mock_db, sim)
        assert result == 50

    @patch("back.services.simulation_service.sim_frame_crud")
    def test_inactive_sim_near_complete(
        self, mock_frame_crud: Mock, service: SimulationService, mock_db: Mock
    ) -> None:
        # _time_str_to_seconds("day1:17:00") = 61200s
        # frame at 58140s = 95% of 61200
        mock_frame_crud.get_latest_sim_seconds.return_value = 58140.0
        sim = make_sim(
            scenario_payload={"start_time": "day1:08:00", "end_time": "day1:17:00"}
        )
        result = service.compute_completion_percentage(mock_db, sim)
        assert result == 95

    @patch("back.services.simulation_service.sim_frame_crud")
    def test_result_clamped_to_100(
        self, mock_frame_crud: Mock, service: SimulationService, mock_db: Mock
    ) -> None:
        # Frame time exceeds end_time — should be clamped to 100
        mock_frame_crud.get_latest_sim_seconds.return_value = 99999.0
        sim = make_sim(
            scenario_payload={"start_time": "day1:08:00", "end_time": "day1:17:00"}
        )
        result = service.compute_completion_percentage(mock_db, sim)
        assert result == 100

    @patch("back.services.simulation_service.sim_frame_crud")
    def test_result_clamped_to_0(
        self, mock_frame_crud: Mock, service: SimulationService, mock_db: Mock
    ) -> None:
        mock_frame_crud.get_latest_sim_seconds.return_value = 0.0
        sim = make_sim(
            scenario_payload={"start_time": "day1:08:00", "end_time": "day1:17:00"}
        )
        result = service.compute_completion_percentage(mock_db, sim)
        assert result == 0

    @patch("back.services.simulation_service.sim_frame_crud")
    def test_active_sim_uses_clock_not_frames(
        self, mock_frame_crud: Mock, service: SimulationService, mock_db: Mock
    ) -> None:
        sim_uuid = str(uuid.uuid4())
        sim = make_sim(
            scenario_payload={"start_time": "day1:08:00", "end_time": "day1:17:00"},
            sim_uuid=sim_uuid,
        )

        # Set up active simulation with clock at 50% (30600s of 61200s)
        mock_clock = Mock()
        mock_clock.sim_time_seconds = 30600.0
        mock_sim_controller = Mock()
        mock_sim_controller.clock = mock_clock
        service.active_simulations[sim_uuid] = {
            "sim_time": 61200,
            "db_id": 1,
            "status": "initialized",
            "user_id": 1,
        }
        service.simulator.get_sim_by_id = Mock(  # type: ignore[method-assign]
            return_value={"sim_controller": mock_sim_controller}
        )

        # Frames should NOT be queried for active sims
        mock_frame_crud.get_latest_sim_seconds.return_value = 0.0

        result = service.compute_completion_percentage(mock_db, sim)
        assert result == 50
        mock_frame_crud.get_latest_sim_seconds.assert_not_called()

        # Cleanup
        del service.active_simulations[sim_uuid]
