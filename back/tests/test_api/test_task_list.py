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
from typing import Any, Generator

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


def create_mock_frame_data(
    num_tasks: int = 10, num_stations: int = 3
) -> dict[str, Any]:
    """Create realistic frame data for testing."""
    stations = [
        {
            "id": i + 1,
            "name": f"Station {i + 1}",
            "position": [45.5 + i * 0.01, -73.5 - i * 0.01],
        }
        for i in range(num_stations)
    ]

    tasks = []
    for i in range(num_tasks):
        station_id = (i % num_stations) + 1
        driver_id = (i + 1) if i < 5 else None  # First 5 tasks assigned

        task = {
            "id": i + 1,
            "state": ["OPEN", "ASSIGNED", "IN_PROGRESS", "COMPLETED"][i % 4],
            "stationId": station_id,
            "driverId": driver_id,
            "taskType": "PICKUP" if i % 2 == 0 else "DROPOFF",
            "priority": i % 3,
            "createdAt": f"2026-02-05T10:{i:02d}:00Z",
        }
        tasks.append(task)

    return {
        "simId": "test-sim-123",
        "clock": {"simSecondsPassed": 3600.0},
        "tasks": tasks,
        "stations": stations,
        "drivers": [],
        "vehicles": [],
    }


class TestTaskListAPI:
    """Test the task listing endpoint."""

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_basic(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test basic task listing without filters."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        # Create realistic frame with 10 tasks
        frame_data = create_mock_frame_data(num_tasks=10, num_stations=3)
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

        response = authenticated_client.get("/api/v1/simulation/100/tasks")
        assert response.status_code == 200
        data = response.json()

        assert "tasks" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "total_pages" in data

        assert data["total"] == 10
        assert len(data["tasks"]) == 10
        assert data["per_page"] == 500
        assert data["page"] == 1
        assert data["total_pages"] == 1

        # Verify task structure
        task = data["tasks"][0]
        assert "id" in task
        assert "state" in task
        assert "station_id" in task
        assert "station" in task
        assert task["station"]["name"] == "Station 1"

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_with_state_filter(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test filtering tasks by state."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_frame_data(num_tasks=10, num_stations=3)
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

        # Filter for OPEN tasks only (tasks 0, 4, 8 have state OPEN)
        response = authenticated_client.get("/api/v1/simulation/100/tasks?state=OPEN")
        assert response.status_code == 200
        data = response.json()

        # Should have 3 OPEN tasks (indices 0, 4, 8)
        assert data["total"] == 3
        assert all(task["state"] == "OPEN" for task in data["tasks"])

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_with_multiple_states(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test filtering tasks by multiple states."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_frame_data(num_tasks=10, num_stations=3)
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
            "/api/v1/simulation/100/tasks?state=OPEN,ASSIGNED"
        )
        assert response.status_code == 200
        data = response.json()

        # Should have 6 tasks (3 OPEN + 3 ASSIGNED, indices 0,1,4,5,8,9)
        assert data["total"] == 6
        assert all(task["state"] in ["OPEN", "ASSIGNED"] for task in data["tasks"])

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_with_station_filter(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test filtering tasks by station."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_frame_data(num_tasks=10, num_stations=3)
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

        response = authenticated_client.get("/api/v1/simulation/100/tasks?station=1")
        assert response.status_code == 200
        data = response.json()

        # Tasks 0, 3, 6, 9 are at station 1
        assert data["total"] == 4
        assert all(task["station_id"] == 1 for task in data["tasks"])

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_with_driver_filter(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test filtering tasks by driver."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        frame_data = create_mock_frame_data(num_tasks=10, num_stations=3)
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

        response = authenticated_client.get("/api/v1/simulation/100/tasks?driver=1")
        assert response.status_code == 200
        data = response.json()

        # Task 0 has driver_id=1
        assert data["total"] == 1
        assert all(task["driver_id"] == 1 for task in data["tasks"])

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_pagination(
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

        frame_data = create_mock_frame_data(num_tasks=10, num_stations=3)
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
            "/api/v1/simulation/100/tasks?maxResults=5&startResult=0"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 10
        assert len(data["tasks"]) == 5
        assert data["per_page"] == 5
        assert data["page"] == 1
        assert data["total_pages"] == 2

        # Get second page
        response = authenticated_client.get(
            "/api/v1/simulation/100/tasks?maxResults=5&startResult=5"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 10
        assert len(data["tasks"]) == 5
        assert data["page"] == 2
        assert data["total_pages"] == 2

    @patch("back.api.v1.simulation.sim_instance_crud.get_by_uuid")
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    def test_get_tasks_simulation_not_found(
        self,
        mock_sim_get: MagicMock,
        mock_sim_get_by_uuid: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test 404 when simulation not found."""
        mock_sim_get_by_uuid.return_value = None

        response = authenticated_client.get("/api/v1/simulation/nonexistent/tasks")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    def test_get_tasks_unauthorized(
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

        response = authenticated_client.get("/api/v1/simulation/100/tasks")
        assert response.status_code == 403
        assert "unauthorized" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_admin_access(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test admin can access any simulation's tasks."""
        mock_sim = MagicMock()
        mock_sim.user_id = 999  # Different user
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = True  # Admin user
        mock_user_get.return_value = mock_user

        frame_data = create_mock_frame_data(num_tasks=5, num_stations=2)
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

        response = authenticated_client.get("/api/v1/simulation/100/tasks")
        assert response.status_code == 200

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_tasks_no_keyframe(
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

        response = authenticated_client.get("/api/v1/simulation/100/tasks")
        assert response.status_code == 404
        assert "no keyframe found" in response.json()["detail"].lower()
