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

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session
from back.crud.sim_instance import sim_instance_crud
from back.crud.user import user_crud

from back.models import (
    User,
    SimInstance,
)
from back.schemas import SimInstanceCreate


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


class TestStationsAPI:
    """Test the stations API endpoints."""

    def test_get_stations_empty(self, client: TestClient, db: Session) -> None:
        """Test getting stations when database is empty."""
        response = client.get("/api/v1/stations/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["stations"] == []
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 0

    def test_get_stations_with_pagination(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test getting stations with pagination parameters."""
        # Create some test stations first
        for i in range(5):
            station_data = {
                "name": f"Station {i}",
                "longitude": -73.5 + i * 0.01,
                "latitude": 45.5 + i * 0.01,
                "sim_instance_id": sim_instance.id,
            }
            client.post("/api/v1/stations/", json=station_data)

        # Test default pagination
        response = client.get("/api/v1/stations/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["stations"]) == 5
        assert data["page"] == 1
        assert data["per_page"] == 10

        # Test custom pagination
        response = client.get("/api/v1/stations/?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["stations"]) == 2
        assert data["page"] == 2
        assert data["per_page"] == 2

    def test_get_station_by_id_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test getting a station by ID successfully."""
        # Create a test station
        station_data = {
            "name": "Test Station",
            "longitude": -73.5,
            "latitude": 45.5,
            "sim_instance_id": sim_instance.id,
        }
        create_response = client.post("/api/v1/stations/", json=station_data)
        assert create_response.status_code == 201
        created_station = create_response.json()
        station_id = created_station["id"]

        # Get the station by ID
        response = client.get(f"/api/v1/stations/{station_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == station_id
        assert data["name"] == "Test Station"
        assert data["position"] == [-73.5, 45.5]
        # Verify longitude and latitude are not in response
        assert "longitude" not in data
        assert "latitude" not in data

    def test_get_station_by_id_not_found(self, client: TestClient, db: Session) -> None:
        """Test getting a station by ID that doesn't exist."""
        response = client.get("/api/v1/stations/999")
        assert response.status_code == 404
        data = response.json()
        assert "Station with ID 999 not found" in data["detail"]

    def test_create_station_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test creating a station successfully."""
        station_data = {
            "name": "New Station",
            "longitude": -73.6,
            "latitude": 45.6,
            "sim_instance_id": sim_instance.id,
        }
        response = client.post("/api/v1/stations/", json=station_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Station"
        assert data["position"] == [-73.6, 45.6]
        assert "id" in data
        # Verify longitude and latitude are not in response
        assert "longitude" not in data
        assert "latitude" not in data

    def test_create_station_duplicate_name(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test creating a station with a duplicate name."""
        station_data = {
            "name": "Duplicate Station",
            "longitude": -73.5,
            "latitude": 45.5,
            "sim_instance_id": sim_instance.id,
        }
        # Create first station
        response1 = client.post("/api/v1/stations/", json=station_data)
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post("/api/v1/stations/", json=station_data)
        assert response2.status_code == 400
        data = response2.json()
        assert "already exists" in data["detail"]

    def test_update_station_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test updating a station successfully."""
        # Create a station
        station_data = {
            "name": "Original Station",
            "longitude": -73.5,
            "latitude": 45.5,
            "sim_instance_id": sim_instance.id,
        }
        create_response = client.post("/api/v1/stations/", json=station_data)
        station_id = create_response.json()["id"]

        # Update the station
        update_data = {"name": "Updated Station", "longitude": -73.6, "latitude": 45.6}
        response = client.put(f"/api/v1/stations/{station_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Station"
        assert data["position"] == [-73.6, 45.6]
        # Verify longitude and latitude are not in response
        assert "longitude" not in data
        assert "latitude" not in data

    def test_update_station_not_found(self, client: TestClient, db: Session) -> None:
        """Test updating a station that doesn't exist."""
        update_data = {"name": "Updated Station"}
        response = client.put("/api/v1/stations/999", json=update_data)
        assert response.status_code == 404

    def test_update_station_duplicate_name(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test updating a station to have a duplicate name."""
        # Create two stations
        station1_data = {
            "name": "Station 1",
            "longitude": -73.5,
            "latitude": 45.5,
            "sim_instance_id": sim_instance.id,
        }
        station2_data = {
            "name": "Station 2",
            "longitude": -73.6,
            "latitude": 45.6,
            "sim_instance_id": sim_instance.id,
        }

        response1 = client.post("/api/v1/stations/", json=station1_data)
        response2 = client.post("/api/v1/stations/", json=station2_data)
        assert response1.status_code == 201
        assert response2.status_code == 201

        station2_id = response2.json()["id"]

        # Try to update station 2 to have the same name as station 1
        update_data = {"name": "Station 1"}
        response = client.put(f"/api/v1/stations/{station2_id}", json=update_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_delete_station_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test deleting a station successfully."""
        # Create a station
        station_data = {
            "name": "Station to Delete",
            "longitude": -73.5,
            "latitude": 45.5,
            "sim_instance_id": sim_instance.id,
        }
        create_response = client.post("/api/v1/stations/", json=station_data)
        station_id = create_response.json()["id"]

        # Delete the station
        response = client.delete(f"/api/v1/stations/{station_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/stations/{station_id}")
        assert get_response.status_code == 404

    def test_delete_station_not_found(self, client: TestClient, db: Session) -> None:
        """Test deleting a station that doesn't exist."""
        response = client.delete("/api/v1/stations/999")
        assert response.status_code == 404

    def test_create_station_invalid_data(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        """Test creating a station with invalid data."""
        # Missing required fields
        response = client.post("/api/v1/stations/", json={"name": "Incomplete Station"})
        assert response.status_code == 422

        # Invalid longitude/latitude
        invalid_data = {
            "name": "Invalid Station",
            "longitude": "not_a_number",
            "latitude": 45.5,
            "sim_instance": 999,
        }
        response = client.post("/api/v1/stations/", json=invalid_data)
        assert response.status_code == 422
