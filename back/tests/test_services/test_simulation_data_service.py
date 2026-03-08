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
