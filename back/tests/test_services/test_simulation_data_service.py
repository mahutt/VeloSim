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

from typing import Any
from unittest.mock import Mock
from types import SimpleNamespace

import pytest

from back.services.simulation_data_service import SimulationDataService
from back.models.sim_instance import SimInstance
from back.exceptions import ItemNotFoundError


class TestSimulationDataService:
    """Tests for SimulationDataService."""

    @pytest.fixture
    def service(self) -> SimulationDataService:
        """Create a SimulationDataService instance."""
        return SimulationDataService()

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    def test_get_traffic_csv_data_returns_data_when_present(
        self, service: SimulationDataService, mock_db: Mock
    ) -> None:
        """Test get_traffic_csv_data returns CSV data when it exists."""
        traffic_csv = (
            "TYPE,start_time,segment_key,name,duration,weight\n"
            'local_traffic,"08:00","((-73.5,45.5),(-73.6,45.6))",event,10,0.5\n'
        )
        mock_sim = Mock(spec=SimInstance)
        mock_sim.traffic_csv_data = traffic_csv

        mock_db.query.return_value.filter.return_value.first.return_value = mock_sim

        result = service.get_traffic_csv_data(mock_db, "sim-123")

        assert result == traffic_csv
        mock_db.query.assert_called_once_with(SimInstance)
        mock_db.query.return_value.filter.assert_called_once()

    def test_get_traffic_csv_data_returns_none_when_not_present(
        self, service: SimulationDataService, mock_db: Mock
    ) -> None:
        """Test get_traffic_csv_data returns None when no traffic data exists."""
        mock_sim = Mock(spec=SimInstance)
        mock_sim.traffic_csv_data = None

        mock_db.query.return_value.filter.return_value.first.return_value = mock_sim

        result = service.get_traffic_csv_data(mock_db, "sim-123")

        assert result is None

    def test_get_traffic_csv_data_raises_when_sim_not_found(
        self, service: SimulationDataService, mock_db: Mock
    ) -> None:
        """Test get_traffic_csv_data raises ItemNotFoundError when sim doesn't exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(
            ItemNotFoundError, match="Simulation instance sim-123 not found"
        ):
            service.get_traffic_csv_data(mock_db, "sim-123")

    def test_get_scenario_returns_payload(
        self, service: SimulationDataService, mock_db: Mock
    ) -> None:
        payload: dict[str, Any] = {"stations": [], "drivers": []}
        mock_sim = Mock(spec=SimInstance)
        mock_sim.scenario_payload = payload
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sim

        result = service.get_scenario(mock_db, "sim-1")

        assert result == payload

    def test_get_scenario_raises_when_sim_missing(
        self, service: SimulationDataService, mock_db: Mock
    ) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(
            ItemNotFoundError, match="Simulation instance sim-1 not found"
        ):
            service.get_scenario(mock_db, "sim-1")

    def test_get_scenario_raises_when_payload_missing(
        self, service: SimulationDataService, mock_db: Mock
    ) -> None:
        mock_sim = Mock(spec=SimInstance)
        mock_sim.scenario_payload = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sim

        with pytest.raises(
            ItemNotFoundError, match="No scenario payload found for simulation sim-1"
        ):
            service.get_scenario(mock_db, "sim-1")

    def test_get_keyframes_from_tick_returns_frame_data(
        self,
        service: SimulationDataService,
        mock_db: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        keyframe = SimpleNamespace(frame_data={"seq": 5})
        monkeypatch.setattr(
            (
                "back.services.simulation_data_service."
                "sim_keyframe_crud.get_keyframe_at_tick"
            ),
            lambda db, sim_id, tick: keyframe,
        )

        result = service.get_keyframes_from_tick(mock_db, "sim-1", 12.0)

        assert result == {"seq": 5}

    def test_get_keyframes_from_tick_raises_when_missing(
        self,
        service: SimulationDataService,
        mock_db: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            (
                "back.services.simulation_data_service."
                "sim_keyframe_crud.get_keyframe_at_tick"
            ),
            lambda db, sim_id, tick: None,
        )

        with pytest.raises(
            ItemNotFoundError, match="No keyframe found at or before tick"
        ):
            service.get_keyframes_from_tick(mock_db, "sim-1", 9.0)

    def test_get_last_persisted_keyframe_returns_frame_data(
        self,
        service: SimulationDataService,
        mock_db: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_sim = Mock(spec=SimInstance)
        mock_sim.id = 101
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sim
        monkeypatch.setattr(
            "back.services.simulation_data_service.sim_keyframe_crud.get_last_keyframe",
            lambda db, sim_instance_id: SimpleNamespace(frame_data={"last": True}),
        )

        result = service.get_last_persisted_keyframe(mock_db, "sim-1")

        assert result == {"last": True}

    def test_get_last_persisted_keyframe_raises_when_sim_missing(
        self, service: SimulationDataService, mock_db: Mock
    ) -> None:
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(
            ItemNotFoundError, match="Simulation instance with UUID sim-1 not found"
        ):
            service.get_last_persisted_keyframe(mock_db, "sim-1")

    def test_get_last_persisted_keyframe_raises_when_keyframe_missing(
        self,
        service: SimulationDataService,
        mock_db: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_sim = Mock(spec=SimInstance)
        mock_sim.id = 101
        mock_db.query.return_value.filter.return_value.first.return_value = mock_sim
        monkeypatch.setattr(
            "back.services.simulation_data_service.sim_keyframe_crud.get_last_keyframe",
            lambda db, sim_instance_id: None,
        )

        with pytest.raises(
            ItemNotFoundError, match="No keyframe found for simulation sim-1"
        ):
            service.get_last_persisted_keyframe(mock_db, "sim-1")

    def test_get_last_persisted_keyframe_by_id_returns_frame_data(
        self,
        service: SimulationDataService,
        mock_db: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "back.services.simulation_data_service.sim_keyframe_crud.get_last_keyframe",
            lambda db, sim_instance_id: SimpleNamespace(
                frame_data={"id": sim_instance_id}
            ),
        )

        result = service.get_last_persisted_keyframe_by_id(mock_db, 77)

        assert result == {"id": 77}

    def test_get_last_persisted_keyframe_by_id_raises_when_missing(
        self,
        service: SimulationDataService,
        mock_db: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "back.services.simulation_data_service.sim_keyframe_crud.get_last_keyframe",
            lambda db, sim_instance_id: None,
        )

        with pytest.raises(
            ItemNotFoundError,
            match="No keyframe found for simulation instance 77",
        ):
            service.get_last_persisted_keyframe_by_id(mock_db, 77)
