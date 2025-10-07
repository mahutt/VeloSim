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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestStationTasksAPI:
    """Test the station tasks API endpoints."""

    def _create_test_station(self, client: TestClient) -> Any:
        """Helper method to create a test station and return its ID."""
        station_data = {"name": "Test Station", "longitude": -73.5, "latitude": 45.5}
        response = client.post("/api/v1/stations/", json=station_data)
        assert response.status_code == 201
        return response.json()["id"]

    def test_get_station_tasks_empty(self, client: TestClient, db: Session) -> None:
        """Test getting station tasks when database is empty."""
        response = client.get("/api/v1/stationTasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["station_tasks"] == []
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 0

    def test_get_station_tasks_with_pagination(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting station tasks with pagination parameters."""
        # Create a test station first
        station_id = self._create_test_station(client)

        # Create some test station tasks
        for i in range(5):
            task_data = {
                "station_id": station_id,
                "type": "battery_swap" if i % 2 == 0 else "battery_swap",
            }
            client.post("/api/v1/stationTasks/", json=task_data)

        # Test default pagination
        response = client.get("/api/v1/stationTasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["station_tasks"]) == 5
        assert data["page"] == 1
        assert data["per_page"] == 10

        # Test custom pagination
        response = client.get("/api/v1/stationTasks/?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["station_tasks"]) == 2
        assert data["page"] == 2
        assert data["per_page"] == 2

    def test_get_station_tasks_with_station_filter(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting station tasks filtered by station ID."""
        # Create two test stations
        station1_id = self._create_test_station(client)
        station2_data = {"name": "Test Station 2", "longitude": -73.6, "latitude": 45.6}
        station2_response = client.post("/api/v1/stations/", json=station2_data)
        station2_id = station2_response.json()["id"]

        # Create tasks for both stations
        for station_id in [station1_id, station2_id]:
            for i in range(2):
                task_data = {"station_id": station_id, "type": "battery_swap"}
                client.post("/api/v1/stationTasks/", json=task_data)

        # Filter by station 1
        response = client.get(f"/api/v1/stationTasks/?stationId={station1_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for task in data["station_tasks"]:
            assert task["station_id"] == station1_id

    def test_get_station_tasks_with_status_filter(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting station tasks filtered by status."""
        station_id = self._create_test_station(client)

        # Create a task and update its status
        task_data = {"station_id": station_id, "type": "battery_swap"}
        create_response = client.post("/api/v1/stationTasks/", json=task_data)
        task_id = create_response.json()["id"]

        # Update task to completed status
        update_data = {"station_id": station_id, "status": "completed"}
        client.put(f"/api/v1/stationTasks/{task_id}", json=update_data)

        # Create another task (will be unassigned by default)
        client.post("/api/v1/stationTasks/", json=task_data)

        # Filter by completed status
        response = client.get("/api/v1/stationTasks/?taskStatus=completed")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["station_tasks"][0]["status"] == "completed"

    def test_get_station_task_by_id_success(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting a station task by ID successfully."""
        station_id = self._create_test_station(client)

        # Create a test station task
        task_data = {"station_id": station_id, "type": "battery_swap"}
        create_response = client.post("/api/v1/stationTasks/", json=task_data)
        assert create_response.status_code == 201
        created_task = create_response.json()
        task_id = created_task["id"]

        # Get the task by ID
        response = client.get(f"/api/v1/stationTasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["station_id"] == station_id
        assert data["type"] == "battery_swap"
        assert data["status"] == "unassigned"
        assert "date_created" in data
        assert "date_updated" in data

    def test_get_station_task_by_id_not_found(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting a station task by ID that doesn't exist."""
        response = client.get("/api/v1/stationTasks/999")
        assert response.status_code == 404
        data = response.json()
        assert "Station task with ID 999 not found" in data["detail"]

    def test_create_station_task_success(self, client: TestClient, db: Session) -> None:
        """Test creating a station task successfully."""
        station_id = self._create_test_station(client)

        task_data = {"station_id": station_id, "type": "battery_swap"}
        response = client.post("/api/v1/stationTasks/", json=task_data)
        assert response.status_code == 201
        data = response.json()
        assert data["station_id"] == station_id
        assert data["type"] == "battery_swap"
        assert data["status"] == "unassigned"
        assert "id" in data
        assert "date_created" in data
        assert "date_updated" in data

    def test_create_station_task_invalid_station(
        self, client: TestClient, db: Session
    ) -> None:
        """Test creating a station task with invalid station ID."""
        task_data = {"station_id": 999, "type": "battery_swap"}
        response = client.post("/api/v1/stationTasks/", json=task_data)
        assert response.status_code == 400
        data = response.json()
        assert "Station with ID 999 not found" in data["detail"]

    def test_update_station_task_success(self, client: TestClient, db: Session) -> None:
        """Test updating a station task successfully."""
        station_id = self._create_test_station(client)

        # Create a station task
        task_data = {"station_id": station_id, "type": "battery_swap"}
        create_response = client.post("/api/v1/stationTasks/", json=task_data)
        task_id = create_response.json()["id"]

        # Update the task status
        update_data = {"station_id": station_id, "status": "completed"}
        response = client.put(f"/api/v1/stationTasks/{task_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["station_id"] == station_id
        assert data["type"] == "battery_swap"

    def test_update_station_task_not_found(
        self, client: TestClient, db: Session
    ) -> None:
        """Test updating a station task that doesn't exist."""
        station_id = self._create_test_station(client)
        update_data = {"station_id": station_id, "status": "completed"}
        response = client.put("/api/v1/stationTasks/999", json=update_data)
        assert response.status_code == 404

    def test_delete_station_task_success(self, client: TestClient, db: Session) -> None:
        """Test deleting a station task successfully."""
        station_id = self._create_test_station(client)

        # Create a station task
        task_data = {"station_id": station_id, "type": "battery_swap"}
        create_response = client.post("/api/v1/stationTasks/", json=task_data)
        task_id = create_response.json()["id"]

        # Delete the task
        response = client.delete(f"/api/v1/stationTasks/{task_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/stationTasks/{task_id}")
        assert get_response.status_code == 404

    def test_delete_station_task_not_found(
        self, client: TestClient, db: Session
    ) -> None:
        """Test deleting a station task that doesn't exist."""
        response = client.delete("/api/v1/stationTasks/999")
        assert response.status_code == 404

    def test_create_station_task_invalid_data(
        self, client: TestClient, db: Session
    ) -> None:
        """Test creating a station task with invalid data."""
        # Missing required fields
        response = client.post("/api/v1/stationTasks/", json={"station_id": 1})
        assert response.status_code == 422

        # Invalid task type
        invalid_data = {"station_id": 1, "type": "INVALID_TYPE"}
        response = client.post("/api/v1/stationTasks/", json=invalid_data)
        assert response.status_code == 422

    def test_update_station_task_invalid_data(
        self, client: TestClient, db: Session
    ) -> None:
        """Test updating a station task with invalid data."""
        station_id = self._create_test_station(client)

        # Create a station task
        task_data = {"station_id": station_id, "type": "battery_swap"}
        create_response = client.post("/api/v1/stationTasks/", json=task_data)
        task_id = create_response.json()["id"]

        # Try to update with invalid status
        invalid_data = {"station_id": station_id, "status": "INVALID_STATUS"}
        response = client.put(f"/api/v1/stationTasks/{task_id}", json=invalid_data)
        assert response.status_code == 422
