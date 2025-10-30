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
from back.crud.station import station_crud
from back.crud.user import user_crud
from back.crud.sim_instance import sim_instance_crud
from back.schemas import StationCreate, StationUpdate, SimInstanceCreate
from back.models import User, SimInstance


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a non-admin user for testing."""
    test_user = User(
        username="test_user",
        password_hash=user_crud.hash_password("test_password"),
        is_admin=False,
        is_enabled=True,
    )
    db.add(test_user)
    db.flush()
    db.refresh(test_user)
    return test_user


@pytest.fixture
def sim_instance(db: Session, test_user: User) -> SimInstance:
    """Create a test simulation instance for the normal user."""
    sim_instance_data = SimInstanceCreate(user_id=test_user.id)
    sim = sim_instance_crud.create(db, sim_instance_data)
    db.commit()
    return sim


class TestStationCRUD:
    """Test the station CRUD operations."""

    def test_create_station(self, db: Session, sim_instance: SimInstance) -> None:
        """Test creating a station."""
        station_data = StationCreate(
            name="Test Station",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )
        station = station_crud.create(db, station_data)

        assert station.id is not None
        assert station.name == "Test Station"
        assert station.longitude == -73.5
        assert station.latitude == 45.5

    def test_get_station_by_id(self, db: Session, sim_instance: SimInstance) -> None:
        """Test getting a station by ID."""
        # Create a station first
        station_data = StationCreate(
            name="Get Test Station",
            longitude=-73.6,
            latitude=45.6,
            sim_instance_id=sim_instance.id,
        )
        created_station = station_crud.create(db, station_data)

        # Get the station by ID
        retrieved_station = station_crud.get(db, created_station.id)
        assert retrieved_station is not None
        assert retrieved_station.id == created_station.id
        assert retrieved_station.name == "Get Test Station"

    def test_get_station_by_id_not_found(self, db: Session) -> None:
        """Test getting a station by ID that doesn't exist."""
        station = station_crud.get(db, 999)
        assert station is None

    def test_get_station_by_name(self, db: Session, sim_instance: SimInstance) -> None:
        """Test getting a station by name."""
        # Create a station first
        station_data = StationCreate(
            name="Named Station",
            longitude=-73.7,
            latitude=45.7,
            sim_instance_id=sim_instance.id,
        )
        created_station = station_crud.create(db, station_data)

        # Get the station by name
        retrieved_station = station_crud.get_by_name(db, "Named Station")
        assert retrieved_station is not None
        assert retrieved_station.id == created_station.id
        assert retrieved_station.name == "Named Station"

    def test_get_station_by_name_not_found(self, db: Session) -> None:
        """Test getting a station by name that doesn't exist."""
        station = station_crud.get_by_name(db, "Nonexistent Station")
        assert station is None

    def test_get_all_stations_empty(self, db: Session) -> None:
        """Test getting all stations when database is empty."""
        stations, total = station_crud.get_all(db)
        assert stations == []
        assert total == 0

    def test_get_all_stations_with_data(
        self, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test getting all stations with data."""
        # Create multiple stations
        for i in range(5):
            station_data = StationCreate(
                name=f"Station {i}",
                longitude=-73.5 + i * 0.01,
                latitude=45.5 + i * 0.01,
                sim_instance_id=sim_instance.id,
            )
            station_crud.create(db, station_data)

        # Get all stations
        stations, total = station_crud.get_all(db)
        assert len(stations) == 5
        assert total == 5

    def test_get_all_stations_with_pagination(
        self, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test getting all stations with pagination."""
        # Create multiple stations
        for i in range(10):
            station_data = StationCreate(
                name=f"Pagination Station {i}",
                longitude=-73.5 + i * 0.01,
                latitude=45.5 + i * 0.01,
                sim_instance_id=sim_instance.id,
            )
            station_crud.create(db, station_data)

        # Test pagination
        stations, total = station_crud.get_all(db, skip=3, limit=4)
        assert len(stations) == 4
        assert total == 10

        # Verify we got the right stations (should be stations 3, 4, 5, 6)
        station_names = [s.name for s in stations]
        expected_names = [f"Pagination Station {i}" for i in range(3, 7)]
        assert station_names == expected_names

    def test_update_station(self, db: Session, sim_instance: SimInstance) -> None:
        """Test updating a station."""
        # Create a station first
        station_data = StationCreate(
            name="Original Station",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )
        created_station = station_crud.create(db, station_data)

        # Update the station
        update_data = StationUpdate(
            name="Updated Station", longitude=-73.6, latitude=45.6
        )
        updated_station = station_crud.update(db, created_station.id, update_data)

        assert updated_station is not None
        assert updated_station.id == created_station.id
        assert updated_station.name == "Updated Station"
        assert updated_station.longitude == -73.6
        assert updated_station.latitude == 45.6

    def test_update_station_partial(
        self, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test updating a station with partial data."""
        # Create a station first
        station_data = StationCreate(
            name="Partial Update Station",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )
        created_station = station_crud.create(db, station_data)

        # Update only the name
        update_data = StationUpdate(name="New Name Only")  # type: ignore[call-arg]
        updated_station = station_crud.update(db, created_station.id, update_data)

        assert updated_station is not None
        assert updated_station.name == "New Name Only"
        assert updated_station.longitude == -73.5  # Should remain unchanged
        assert updated_station.latitude == 45.5  # Should remain unchanged

    def test_update_station_not_found(self, db: Session) -> None:
        """Test updating a station that doesn't exist."""
        update_data = StationUpdate(name="Updated Name")  # type: ignore[call-arg]
        updated_station = station_crud.update(db, 999, update_data)
        assert updated_station is None

    def test_delete_station(self, db: Session, sim_instance: SimInstance) -> None:
        """Test deleting a station."""
        # Create a station first
        station_data = StationCreate(
            name="Station to Delete",
            longitude=-73.5,
            latitude=45.5,
            sim_instance_id=sim_instance.id,
        )
        created_station = station_crud.create(db, station_data)

        # Delete the station
        success = station_crud.delete(db, created_station.id)
        assert success is True

        # Verify it's deleted
        retrieved_station = station_crud.get(db, created_station.id)
        assert retrieved_station is None

    def test_delete_station_not_found(self, db: Session) -> None:
        """Test deleting a station that doesn't exist."""
        success = station_crud.delete(db, 999)
        assert success is False

    def test_create_multiple_stations_with_different_names(
        self, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test creating multiple stations with different names."""
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
        for station_data in stations_data:
            station = station_crud.create(db, station_data)
            created_stations.append(station)
            assert station.id is not None
            assert station.name == station_data.name

        # Verify all stations are in the database
        all_stations, total = station_crud.get_all(db)
        assert total == 3
        assert len(all_stations) == 3

        # Verify we can get each by name
        for original_data in stations_data:
            retrieved = station_crud.get_by_name(db, original_data.name)
            assert retrieved is not None
            assert retrieved.name == original_data.name
