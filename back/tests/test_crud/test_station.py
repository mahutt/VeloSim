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
from back.crud.station import station_crud
from back.crud.user import user_crud
from back.schemas import StationCreate, StationUpdate
from back.models import User, SimInstance


@pytest.fixture
def test_user() -> User:
    """Create a non-admin user for testing."""
    return User(
        id=1,
        username="test_user",
        password_hash=user_crud.hash_password("test_password"),
        is_admin=False,
        is_enabled=True,
    )


@pytest.fixture
def sim_instance(test_user: User) -> SimInstance:
    """Create a test simulation instance for the normal user."""
    return SimInstance(id=1, user_id=test_user.id)


class TestStationCRUD:
    """Test the station CRUD operations."""

    def test_create_station(self, mock_db: Mock, sim_instance: SimInstance) -> None:
        """Test creating a station."""
        from back.tests.mock_utils import setup_mock_db_add_with_id

        setup_mock_db_add_with_id(mock_db, 1)

        station_data = StationCreate(
            name="Test Station",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )
        station = station_crud.create(mock_db, station_data)

        assert station.id is not None
        assert station.name == "Test Station"
        assert station.longitude == -73.5
        assert station.latitude == 45.5

    def test_get_station_by_id(self, mock_db: Mock, sim_instance: SimInstance) -> None:
        """Test getting a station by ID."""
        from back.models import Station

        created_station = Station(
            id=1,
            name="Get Test Station",
            longitude=-73.6,
            latitude=45.6,
            sim_instance_id=sim_instance.id,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = created_station
        mock_db.query.return_value = mock_query

        # Get the station by ID
        retrieved_station = station_crud.get(mock_db, created_station.id)
        assert retrieved_station is not None
        assert retrieved_station.id == created_station.id
        assert retrieved_station.name == "Get Test Station"

    def test_get_station_by_id_not_found(self, mock_db: Mock) -> None:
        """Test getting a station by ID that doesn't exist."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        station = station_crud.get(mock_db, 999)
        assert station is None

    def test_get_station_by_name(
        self, mock_db: Mock, sim_instance: SimInstance
    ) -> None:
        """Test getting a station by name."""
        from back.models import Station

        created_station = Station(
            id=1,
            name="Named Station",
            longitude=-73.7,
            latitude=45.7,
            sim_instance_id=sim_instance.id,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = created_station
        mock_db.query.return_value = mock_query

        # Get the station by name
        retrieved_station = station_crud.get_by_name(mock_db, "Named Station")
        assert retrieved_station is not None
        assert retrieved_station.id == created_station.id
        assert retrieved_station.name == "Named Station"

    def test_get_station_by_name_not_found(self, mock_db: Mock) -> None:
        """Test getting a station by name that doesn't exist."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        station = station_crud.get_by_name(mock_db, "Nonexistent Station")
        assert station is None

    def test_get_all_stations_empty(self, mock_db: Mock) -> None:
        """Test getting all stations when database is empty."""
        mock_count_query = Mock()
        mock_count_query.scalar.return_value = 0
        mock_data_query = Mock()
        mock_data_query.offset.return_value.limit.return_value.all.return_value = []
        mock_db.query.side_effect = [mock_count_query, mock_data_query]

        stations, total = station_crud.get_all(mock_db)
        assert stations == []
        assert total == 0

    def test_get_all_stations_with_data(
        self, mock_db: Mock, sim_instance: SimInstance
    ) -> None:
        """Test getting all stations with data."""
        from back.models import Station

        # Create test stations
        stations = [
            Station(
                id=i + 1,
                name=f"Station {i}",
                longitude=-73.5 + i * 0.01,
                latitude=45.5 + i * 0.01,
                sim_instance_id=sim_instance.id,
            )
            for i in range(5)
        ]

        mock_count_query = Mock()
        mock_count_query.scalar.return_value = 5
        mock_data_query = Mock()
        mock_data_query.offset.return_value.limit.return_value.all.return_value = (
            stations
        )
        mock_db.query.side_effect = [mock_count_query, mock_data_query]

        # Get all stations
        result_stations, total = station_crud.get_all(mock_db)
        assert len(result_stations) == 5
        assert total == 5

    def test_get_all_stations_with_pagination(
        self, mock_db: Mock, sim_instance: SimInstance
    ) -> None:
        """Test getting all stations with pagination."""
        from back.models import Station

        # Create test stations for pagination
        paginated_stations = [
            Station(
                id=i + 1,
                name=f"Pagination Station {i}",
                longitude=-73.5 + i * 0.01,
                latitude=45.5 + i * 0.01,
                sim_instance_id=sim_instance.id,
            )
            for i in range(3, 7)
        ]

        mock_count_query = Mock()
        mock_count_query.scalar.return_value = 10
        mock_data_query = Mock()
        mock_data_query.offset.return_value.limit.return_value.all.return_value = (
            paginated_stations
        )
        mock_db.query.side_effect = [mock_count_query, mock_data_query]

        # Test pagination
        stations, total = station_crud.get_all(mock_db, skip=3, limit=4)
        assert len(stations) == 4
        assert total == 10

        # Verify we got the right stations (should be stations 3, 4, 5, 6)
        station_names = [s.name for s in stations]
        expected_names = [f"Pagination Station {i}" for i in range(3, 7)]
        assert station_names == expected_names

    def test_update_station(self, mock_db: Mock, sim_instance: SimInstance) -> None:
        """Test updating a station."""
        from back.models import Station

        created_station = Station(
            id=1,
            name="Original Station",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = created_station
        mock_db.query.return_value = mock_query

        # Update the station
        update_data = StationUpdate(
            name="Updated Station", longitude=-73.6, latitude=45.6
        )
        updated_station = station_crud.update(mock_db, created_station.id, update_data)

        assert updated_station is not None
        assert updated_station.id == created_station.id
        assert updated_station.name == "Updated Station"
        assert updated_station.longitude == -73.6
        assert updated_station.latitude == 45.6

    def test_update_station_partial(
        self, mock_db: Mock, sim_instance: SimInstance
    ) -> None:
        """Test updating a station with partial data."""
        from back.models import Station

        created_station = Station(
            id=1,
            name="Partial Update Station",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = created_station
        mock_db.query.return_value = mock_query

        # Update only the name
        update_data = StationUpdate(name="New Name Only")  # type: ignore[call-arg]
        updated_station = station_crud.update(mock_db, created_station.id, update_data)

        assert updated_station is not None
        assert updated_station.name == "New Name Only"
        assert updated_station.longitude == -73.5  # Should remain unchanged
        assert updated_station.latitude == 45.5  # Should remain unchanged

    def test_update_station_not_found(self, mock_db: Mock) -> None:
        """Test updating a station that doesn't exist."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        update_data = StationUpdate(name="Updated Name")  # type: ignore[call-arg]
        updated_station = station_crud.update(mock_db, 999, update_data)
        assert updated_station is None

    def test_delete_station(self, mock_db: Mock, sim_instance: SimInstance) -> None:
        """Test deleting a station."""
        from back.models import Station

        created_station = Station(
            id=1,
            name="Station to Delete",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [created_station, None]
        mock_db.query.return_value = mock_query

        # Delete the station
        success = station_crud.delete(mock_db, created_station.id)
        assert success is True

        # Verify it's deleted
        retrieved_station = station_crud.get(mock_db, created_station.id)
        assert retrieved_station is None

    def test_delete_station_not_found(self, mock_db: Mock) -> None:
        """Test deleting a station that doesn't exist."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        success = station_crud.delete(mock_db, 999)
        assert success is False

    def test_create_multiple_stations_with_different_names(
        self, mock_db: Mock, sim_instance: SimInstance
    ) -> None:
        """Test creating multiple stations with different names."""
        from back.tests.mock_utils import setup_mock_db_add_with_id

        stations_data = [
            StationCreate(
                name="Station A",
                longitude=-73.5,
                latitude=45.5,
                sim_instance_id=sim_instance.id,
            ),
            StationCreate(
                name="Station B",
                longitude=-73.6,
                latitude=45.6,
                sim_instance_id=sim_instance.id,
            ),
            StationCreate(
                name="Station C",
                longitude=-73.7,
                latitude=45.7,
                sim_instance_id=sim_instance.id,
            ),
        ]

        created_stations = []
        for i, station_data in enumerate(stations_data):
            setup_mock_db_add_with_id(mock_db, i + 1)
            station = station_crud.create(mock_db, station_data)
            created_stations.append(station)
            assert station.id is not None
            assert station.name == station_data.name

        # Verify all stations are in the database
        mock_count_query = Mock()
        mock_count_query.scalar.return_value = 3
        mock_data_query = Mock()
        mock_data_query.offset.return_value.limit.return_value.all.return_value = (
            created_stations
        )
        mock_db.query.side_effect = [mock_count_query, mock_data_query]

        all_stations, total = station_crud.get_all(mock_db)
        assert total == 3
        assert len(all_stations) == 3

        # Verify we can get each by name
        # - reset mock_db.query after side_effect exhaustion
        for original_data, created_station in zip(stations_data, created_stations):
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = created_station
            mock_db.query = Mock(return_value=mock_query)

            retrieved = station_crud.get_by_name(mock_db, original_data.name)
            assert retrieved is not None
            assert retrieved.name == original_data.name
