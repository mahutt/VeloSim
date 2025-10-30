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

from typing import Any, Dict
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from back.models import SimInstance, User
from back.schemas import SimInstanceCreate
from back.crud.sim_instance import sim_instance_crud


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a non-admin test user."""
    user = User(
        username="test_user",
        password_hash="test_password",
        is_admin=False,
        is_enabled=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture
def sim_instance(db: Session, test_user: User) -> SimInstance:
    """Create a test simulation instance for the normal user."""
    sim_instance_data = SimInstanceCreate(user_id=test_user.id)
    sim = sim_instance_crud.create(db, sim_instance_data)
    db.commit()
    return sim


def make_resource_payload(
    *,
    type_value: str = "vehicle_driver",
    latitude: float = 45.5,
    longitude: float = -73.5,
    route_start_latitude: float = 45.4,
    route_start_longitude: float = -73.6,
    route_end_latitude: float = 45.6,
    route_end_longitude: float = -73.4,
    sim_instance_id: int,
) -> Dict[str, Any]:
    """Helper to build a full valid resource creation payload."""
    return {
        "type": type_value,
        "latitude": latitude,
        "longitude": longitude,
        "route_start_latitude": route_start_latitude,
        "route_start_longitude": route_start_longitude,
        "route_end_latitude": route_end_latitude,
        "route_end_longitude": route_end_longitude,
        "sim_instance_id": sim_instance_id,
    }


class TestResourcesAPI:
    """Test the resources API endpoints."""

    def test_get_resources_empty(self, client: TestClient, db: Session) -> None:
        """Test getting resources when database is empty."""
        response = client.get("/api/v1/resources/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["resources"] == []
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 0

    def test_create_resource_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test creating a resource successfully."""
        payload = make_resource_payload(
            latitude=45.5,
            longitude=-73.5,
            route_start_latitude=45.4,
            route_start_longitude=-73.6,
            route_end_latitude=45.6,
            route_end_longitude=-73.4,
            sim_instance_id=sim_instance.id,
        )

        response = client.post("/api/v1/resources/", json=payload)
        assert response.status_code == 201, response.text
        data = response.json()

        # Input used enum value; output serializes enum as name.
        assert data["type"] == "vehicle_driver"
        assert "id" in data

        # ResourceResponse exposes position ( [longitude, latitude] ) and route.
        assert data["position"] == [payload["longitude"], payload["latitude"]]
        assert data["route"] == [
            [payload["route_start_longitude"], payload["route_start_latitude"]],
            [payload["route_end_longitude"], payload["route_end_latitude"]],
        ]

    def test_get_resource_by_id_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test retrieving a resource by ID successfully."""
        # Create resource
        payload = make_resource_payload(
            type_value="vehicle_driver",
            latitude=45.7,
            longitude=-73.7,
            sim_instance_id=sim_instance.id,
        )
        create_response = client.post("/api/v1/resources/", json=payload)
        assert create_response.status_code == 201, create_response.text
        created = create_response.json()
        resource_id = created["id"]

        # Retrieve it
        response = client.get(f"/api/v1/resources/{resource_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == resource_id
        assert data["type"] == "vehicle_driver"
        assert data["position"] == [payload["longitude"], payload["latitude"]]

    def test_get_resource_by_id_not_found(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting a resource by an invalid ID."""
        response = client.get("/api/v1/resources/999999")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower()

    def test_get_resources_with_pagination(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test listing resources with pagination."""
        # Create multiple resources
        for i in range(5):
            payload = make_resource_payload(
                latitude=45.5 + i * 0.01,
                longitude=-73.5,
                route_start_latitude=45.4,
                route_start_longitude=-73.6,
                route_end_latitude=45.6,
                route_end_longitude=-73.4,
                sim_instance_id=sim_instance.id,
            )
            resp = client.post("/api/v1/resources/", json=payload)
            assert resp.status_code == 201, resp.text

        # Default pagination
        response = client.get("/api/v1/resources/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["resources"]) == 5
        assert data["page"] == 1
        assert data["per_page"] == 10

        # Non-default pagination
        # skip=2, limit=2, page 2, per_page 2, 2 items returned
        response = client.get("/api/v1/resources/?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["resources"]) == 2
        assert data["page"] == 2
        assert data["per_page"] == 2

    def test_update_resource_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test updating a resource successfully."""
        # Create resource
        payload = make_resource_payload(
            latitude=45.5, longitude=-73.5, sim_instance_id=sim_instance.id
        )
        create_response = client.post("/api/v1/resources/", json=payload)
        assert create_response.status_code == 201, create_response.text
        resource_id = create_response.json()["id"]

        # Update its position (ResourceUpdate accepts partial updates)
        update_data = {"latitude": 45.6, "longitude": -73.6}
        response = client.put(f"/api/v1/resources/{resource_id}", json=update_data)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["position"] == [update_data["longitude"], update_data["latitude"]]

    def test_update_resource_not_found(self, client: TestClient, db: Session) -> None:
        """Test updating a non-existent resource."""
        update_data = {"latitude": 45.5, "longitude": -73.5}
        response = client.put("/api/v1/resources/999999", json=update_data)
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_delete_resource_success(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test deleting a resource successfully."""
        # Create resource
        payload = make_resource_payload(
            latitude=45.5, longitude=-73.5, sim_instance_id=sim_instance.id
        )
        create_response = client.post("/api/v1/resources/", json=payload)
        assert create_response.status_code == 201, create_response.text
        resource_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/resources/{resource_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/api/v1/resources/{resource_id}")
        assert get_response.status_code == 404

    def test_delete_resource_not_found(self, client: TestClient, db: Session) -> None:
        """Test deleting a non-existent resource."""
        response = client.delete("/api/v1/resources/999999")
        assert response.status_code == 404

    def test_get_resource_types(self, client: TestClient) -> None:
        """Test retrieving supported resource types."""
        response = client.get("/api/v1/resources/types")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(isinstance(t, str) for t in data)
        # The API serializes enum names in responses
        assert "vehicle_driver" in data

    def test_filter_resources_by_type(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        """Test filtering resources by type."""
        # Create two resources
        p1 = make_resource_payload(
            latitude=45.5, longitude=-73.5, sim_instance_id=sim_instance.id
        )
        p2 = make_resource_payload(
            latitude=46.0, longitude=-74.0, sim_instance_id=sim_instance.id
        )
        r1 = client.post("/api/v1/resources/", json=p1)
        r2 = client.post("/api/v1/resources/", json=p2)
        assert r1.status_code == 201, r1.text
        assert r2.status_code == 201, r2.text

        # Filter by type (use enum value in query)
        response = client.get("/api/v1/resources/?type=vehicle_driver")
        assert response.status_code == 200
        data = response.json()

        # All returned resources should have the serialized type name
        assert all(r["type"] == "vehicle_driver" for r in data["resources"])

    def create_station_task_resource(
        self, client: TestClient, sim_instance: SimInstance
    ) -> tuple[int, int, int]:
        """
        Helper to create a station, a station task, and a resource.
        Returns: (station_id, task_id, resource_id)
        """
        # Create station
        station_data = {
            "name": "Test Station",
            "longitude": -73.5,
            "latitude": 45.5,
            "sim_instance_id": sim_instance.id,
        }
        station_resp = client.post("/api/v1/stations/", json=station_data)
        assert station_resp.status_code == 201
        station_id = station_resp.json()["id"]

        # Create station task
        task_data = {
            "station_id": station_id,
            "type": "battery_swap",
            "sim_instance_id": sim_instance.id,
        }
        task_resp = client.post("/api/v1/stationTasks/", json=task_data)
        assert task_resp.status_code == 201
        task_id = task_resp.json()["id"]

        # Create resource
        resource_payload = make_resource_payload(
            type_value="vehicle_driver", sim_instance_id=sim_instance.id
        )
        resource_resp = client.post("/api/v1/resources/", json=resource_payload)
        assert resource_resp.status_code == 201
        resource_id = resource_resp.json()["id"]

        return station_id, task_id, resource_id

    def test_assign_tasks_to_resource(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        _, task_id, resource_id = self.create_station_task_resource(
            client, sim_instance
        )

        # Assign the task to the resource
        response = client.post(
            f"/api/v1/resources/{resource_id}/assign", json={"task_ids": [task_id]}
        )
        assert response.status_code == 200
        expected_message = f"Task(s) [{task_id}] assigned to resource {resource_id}"
        assert response.json()["message"] == expected_message

    def test_unassign_tasks_from_resource(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        _, task_id, resource_id = self.create_station_task_resource(
            client, sim_instance
        )

        # Assign the task to the resource first
        client.post(
            f"/api/v1/resources/{resource_id}/assign", json={"task_ids": [task_id]}
        )

        # Unassign the task from the resource afterwards
        response = client.post(
            f"/api/v1/resources/{resource_id}/unassign", json={"task_ids": [task_id]}
        )
        assert response.status_code == 200
        expected_message = f"Task(s) [{task_id}] unassigned from resource {resource_id}"
        assert response.json()["message"] == expected_message

    def test_service_tasks_for_resource(
        self, client: TestClient, db: Session, sim_instance: SimInstance
    ) -> None:
        _, task_id, resource_id = self.create_station_task_resource(
            client, sim_instance
        )

        # Assign the task to the resource first
        client.post(
            f"/api/v1/resources/{resource_id}/assign", json={"task_ids": [task_id]}
        )

        # Service the task from the resource afterwards
        response = client.post(
            f"/api/v1/resources/{resource_id}/service", json={"task_ids": [task_id]}
        )
        assert response.status_code == 200
        expected_message = f"Task(s) [{task_id}] serviced by resource {resource_id}"
        assert response.json()["message"] == expected_message
