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
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from typing import Any, Generator, cast

from back.main import app
from back.auth.dependency import get_user_id
from back.models.sim_frame import SimFrame
from back.exceptions import ItemNotFoundError


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Authenticated user fixture."""

    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


def create_mock_driver_frame_data(
    num_drivers: int = 5, num_tasks: int = 10, num_vehicles: int = 5
) -> dict[str, Any]:
    """Create realistic frame data for driver testing."""
    tasks = [
        {
            "id": i + 1,
            "state": ["OPEN", "ASSIGNED", "IN_PROGRESS"][i % 3],
            "stationId": (i % 3) + 1,
        }
        for i in range(num_tasks)
    ]

    vehicles = [
        {
            "id": i + 1,
            "batteryCount": 80 - i * 10,
            "batteryCapacity": 100,
        }
        for i in range(num_vehicles)
    ]

    drivers = []
    states = ["IDLE", "ON_ROUTE", "EXECUTING_TASK", "CHARGING"]
    for i in range(num_drivers):
        driver = {
            "id": i + 1,
            "state": states[i % 4],
            "position": [45.5 + i * 0.01, -73.5 - i * 0.01],
            "vehicleId": (i % num_vehicles) + 1,
            "tasks": [
                t["id"] for t in tasks if cast(int, t["id"]) <= (i + 1) * 2
            ],  # Assign some tasks
            "currentTask": i + 1 if i < num_tasks else None,
            "batteryLevel": 85.5 - i * 5,
        }
        drivers.append(driver)

    return {
        "simId": "test-sim-123",
        "clock": {"simSecondsPassed": 3600.0},
        "tasks": tasks,
        "stations": [],
        "drivers": drivers,
        "vehicles": vehicles,
    }


class TestDriverListAPI:
    """Test the driver listing endpoint."""

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_basic(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test basic driver listing without filters."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_driver_frame_data(
            num_drivers=5, num_tasks=10, num_vehicles=5
        )
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.0,
            frame_data=frame_data,
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        response = authenticated_client.get("/api/v1/simulation/100/drivers")
        assert response.status_code == 200
        data = response.json()

        assert "drivers" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

        assert data["total"] == 5
        assert len(data["drivers"]) == 5
        assert data["per_page"] == 500
        assert data["page"] == 1
        assert data["total_pages"] == 1

        # Verify driver structure
        driver = data["drivers"][0]
        assert "id" in driver
        assert "state" in driver
        assert "position" in driver
        assert "vehicle_id" in driver
        assert "tasks" in driver
        assert isinstance(driver["tasks"], list)
        # Without expand, tasks should be just IDs (ints)
        if len(driver["tasks"]) > 0:
            assert isinstance(driver["tasks"][0], int)

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_with_state_filter(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test filtering drivers by state."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_driver_frame_data(
            num_drivers=8, num_tasks=10, num_vehicles=5
        )
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.0,
            frame_data=frame_data,
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        # Filter for IDLE drivers only (indices 0, 4)
        response = authenticated_client.get("/api/v1/simulation/100/drivers?state=IDLE")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert all(driver["state"] == "IDLE" for driver in data["drivers"])

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_expand_tasks(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test expanding tasks in driver response."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_driver_frame_data(
            num_drivers=3, num_tasks=10, num_vehicles=3
        )
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.0,
            frame_data=frame_data,
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        response = authenticated_client.get(
            "/api/v1/simulation/100/drivers?expand=tasks"
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["drivers"]) == 3

        # With expand=tasks, tasks should be objects with id, state, station_id
        driver = data["drivers"][0]
        if len(driver["tasks"]) > 0:
            task = driver["tasks"][0]
            assert isinstance(task, dict)
            assert "id" in task
            assert "state" in task
            assert "station_id" in task

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_expand_vehicle(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test expanding vehicle in driver response."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_driver_frame_data(
            num_drivers=3, num_tasks=10, num_vehicles=3
        )
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.0,
            frame_data=frame_data,
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        response = authenticated_client.get(
            "/api/v1/simulation/100/drivers?expand=vehicle"
        )
        assert response.status_code == 200
        data = response.json()

        # With expand=vehicle, vehicle field should be populated
        driver = data["drivers"][0]
        assert driver["vehicle"] is not None
        assert "id" in driver["vehicle"]
        assert "battery_count" in driver["vehicle"]
        assert "battery_capacity" in driver["vehicle"]

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_expand_multiple(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test expanding multiple entities (tasks and vehicle)."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_driver_frame_data(
            num_drivers=3, num_tasks=10, num_vehicles=3
        )
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.0,
            frame_data=frame_data,
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        response = authenticated_client.get(
            "/api/v1/simulation/100/drivers?expand=tasks,vehicle"
        )
        assert response.status_code == 200
        data = response.json()

        driver = data["drivers"][0]

        # Both tasks and vehicle should be expanded
        if len(driver["tasks"]) > 0:
            assert isinstance(driver["tasks"][0], dict)
        assert driver["vehicle"] is not None

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_pagination(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test pagination with maxResults and startResult."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_driver_frame_data(
            num_drivers=10, num_tasks=10, num_vehicles=5
        )
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.0,
            frame_data=frame_data,
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        # Get first page (5 results)
        response = authenticated_client.get(
            "/api/v1/simulation/100/drivers?maxResults=5&startResult=0"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 10
        assert len(data["drivers"]) == 5
        assert data["per_page"] == 5
        assert data["page"] == 1
        assert data["total_pages"] == 2

        # Get second page
        response = authenticated_client.get(
            "/api/v1/simulation/100/drivers?maxResults=5&startResult=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 10
        assert len(data["drivers"]) == 5
        assert data["page"] == 2

    @patch("back.api.v1.simulation.sim_instance_crud.get_by_uuid")
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    def test_get_drivers_simulation_not_found(
        self,
        mock_sim_get: MagicMock,
        mock_sim_get_by_uuid: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test 404 when simulation not found."""
        mock_sim_get_by_uuid.return_value = None

        response = authenticated_client.get("/api/v1/simulation/nonexistent/drivers")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    def test_get_drivers_unauthorized(
        self,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test 403 when user doesn't own simulation."""
        mock_sim = MagicMock()
        mock_sim.user_id = 999  # Different user
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        response = authenticated_client.get("/api/v1/simulation/100/drivers")
        assert response.status_code == 403
        assert "unauthorized" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_admin_access(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test admin can access any simulation's drivers."""
        mock_sim = MagicMock()
        mock_sim.user_id = 999  # Different user
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = True  # Admin user
        mock_user_get.return_value = mock_user

        frame_data = create_mock_driver_frame_data(
            num_drivers=3, num_tasks=5, num_vehicles=3
        )
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.0,
            frame_data=frame_data,
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        response = authenticated_client.get("/api/v1/simulation/100/drivers")
        assert response.status_code == 200

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_drivers_no_keyframe(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test 404 when no keyframe exists."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        mock_get_last_keyframe.side_effect = ItemNotFoundError("No keyframe found.")

        response = authenticated_client.get("/api/v1/simulation/100/drivers")
        assert response.status_code == 404
        assert "no keyframe found" in response.json()["detail"].lower()
