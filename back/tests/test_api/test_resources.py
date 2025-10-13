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
from sqlalchemy.orm import Session


def make_resource_payload(
    *,
    type_value: str = "vehicle_driver",
    latitude: float = 45.5,
    longitude: float = -73.5,
    route_start_latitude: float = 45.4,
    route_start_longitude: float = -73.6,
    route_end_latitude: float = 45.6,
    route_end_longitude: float = -73.4,
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

    def test_create_resource_success(self, client: TestClient, db: Session) -> None:
        """Test creating a resource successfully."""
        payload = make_resource_payload(
            latitude=45.5,
            longitude=-73.5,
            route_start_latitude=45.4,
            route_start_longitude=-73.6,
            route_end_latitude=45.6,
            route_end_longitude=-73.4,
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

    def test_get_resource_by_id_success(self, client: TestClient, db: Session) -> None:
        """Test retrieving a resource by ID successfully."""
        # Create resource
        payload = make_resource_payload(
            type_value="vehicle_driver", latitude=45.7, longitude=-73.7
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
        self, client: TestClient, db: Session
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

    def test_update_resource_success(self, client: TestClient, db: Session) -> None:
        """Test updating a resource successfully."""
        # Create resource
        payload = make_resource_payload(latitude=45.5, longitude=-73.5)
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

    def test_delete_resource_success(self, client: TestClient, db: Session) -> None:
        """Test deleting a resource successfully."""
        # Create resource
        payload = make_resource_payload(latitude=45.5, longitude=-73.5)
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

    def test_filter_resources_by_type(self, client: TestClient, db: Session) -> None:
        """Test filtering resources by type."""
        # Create two resources
        p1 = make_resource_payload(latitude=45.5, longitude=-73.5)
        p2 = make_resource_payload(latitude=46.0, longitude=-74.0)
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

    def create_station_task_resource(self, client: TestClient) -> tuple[int, int, int]:
        """
        Helper to create a station, a station task, and a resource.
        Returns: (station_id, task_id, resource_id)
        """
        # Create station
        station_data = {"name": "Test Station", "longitude": -73.5, "latitude": 45.5}
        station_resp = client.post("/api/v1/stations/", json=station_data)
        assert station_resp.status_code == 201
        station_id = station_resp.json()["id"]

        # Create station task
        task_data = {"station_id": station_id, "type": "battery_swap"}
        task_resp = client.post("/api/v1/stationTasks/", json=task_data)
        assert task_resp.status_code == 201
        task_id = task_resp.json()["id"]

        # Create resource
        resource_payload = make_resource_payload(type_value="vehicle_driver")
        resource_resp = client.post("/api/v1/resources/", json=resource_payload)
        assert resource_resp.status_code == 201
        resource_id = resource_resp.json()["id"]

        return station_id, task_id, resource_id

    def test_assign_task_to_resource(self, client: TestClient, db: Session) -> None:
        _, task_id, resource_id = self.create_station_task_resource(client)

        # Assign the task to the resource
        response = client.post(f"/api/v1/resources/{resource_id}/assign/{task_id}")
        assert response.status_code == 200
        expected_message = f"Task {task_id} assigned to resource {resource_id}"
        assert response.json()["message"] == expected_message

    def test_unassign_task_from_resource(self, client: TestClient, db: Session) -> None:
        _, task_id, resource_id = self.create_station_task_resource(client)

        # Assign the task to the resource first
        assign_resp = client.post(f"/api/v1/resources/{resource_id}/assign/{task_id}")
        assert assign_resp.status_code == 200

        # Unassign the task from the resource afterwards
        unassign_resp = client.post(
            f"/api/v1/resources/{resource_id}/unassign/{task_id}"
        )
        assert unassign_resp.status_code == 200
        expected_message = f"Task {task_id} unassigned from resource {resource_id}"
        assert unassign_resp.json()["message"] == expected_message

    def test_service_task_for_resource(self, client: TestClient, db: Session) -> None:
        _, task_id, resource_id = self.create_station_task_resource(client)

        # Assign the task to the resource first
        assign_resp = client.post(f"/api/v1/resources/{resource_id}/assign/{task_id}")
        assert assign_resp.status_code == 200

        # Service the task from the resource afterwards
        service_resp = client.post(f"/api/v1/resources/{resource_id}/service/{task_id}")
        assert service_resp.status_code == 200
        expected_message = f"Task {task_id} serviced by resource {resource_id}"
        assert service_resp.json()["message"] == expected_message
