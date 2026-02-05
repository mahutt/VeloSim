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
from typing import Generator

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


class TestSimStateAPI:
    """Test the simulation state convenience endpoint."""

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_state_success(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test successfully getting simulation state."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        # Mock the latest keyframe
        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=3600.5,
            frame_data={
                "simId": "test-sim-123",
                "clock": {
                    "simSecondsPassed": 3600.5,
                    "simMinutesPassed": 60.0,
                    "realSecondsPassed": 36.05,
                    "running": True,
                },
                "tasks": [{"id": 1, "state": "OPEN"}],
                "drivers": [{"id": 1, "state": "IDLE"}],
                "stations": [{"id": 1, "name": "Station A"}],
                "vehicles": [{"id": 1, "batteryCount": 85}],
                "headquarters": {"position": [45.5, -73.6]},
            },
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        response = authenticated_client.get("/api/v1/simulation/100/state")
        assert response.status_code == 200
        data = response.json()
        assert data["sim_id"] == "test-sim-123"
        assert data["sim_seconds"] == 3600.5
        assert "clock" in data
        assert data["tasks"] == [{"id": 1, "state": "OPEN"}]
        assert data["drivers"] == [{"id": 1, "state": "IDLE"}]
        assert data["stations"] == [{"id": 1, "name": "Station A"}]
        assert data["vehicles"] == [{"id": 1, "batteryCount": 85}]
        assert data["headquarters"] == {"position": [45.5, -73.6]}

    @patch("back.api.v1.simulation.sim_instance_crud.get_by_uuid")
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    def test_get_state_simulation_not_found(
        self,
        mock_sim_get: MagicMock,
        mock_sim_get_by_uuid: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test getting state for non-existent simulation."""
        mock_sim_get_by_uuid.return_value = None
        mock_sim_get.return_value = None

        response = authenticated_client.get("/api/v1/simulation/999/state")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    def test_get_state_unauthorized(
        self,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test getting state when user doesn't own simulation."""
        mock_sim = MagicMock()
        mock_sim.user_id = 999  # Different user
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        response = authenticated_client.get("/api/v1/simulation/100/state")
        assert response.status_code == 403
        assert "unauthorized" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_state_no_keyframes(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test getting state when no keyframes exist."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        # No keyframes found - method raises exception
        mock_get_last_keyframe.side_effect = ItemNotFoundError("No keyframe found.")

        response = authenticated_client.get("/api/v1/simulation/100/state")
        assert response.status_code == 404
        assert "no keyframe found" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_last_keyframe")
    def test_get_state_admin_access(
        self,
        mock_get_last_keyframe: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test admin can access any simulation's state."""
        mock_sim = MagicMock()
        mock_sim.user_id = 999  # Different user
        mock_sim.uuid = "100"
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = True  # Admin user
        mock_user_get.return_value = mock_user

        mock_keyframe = SimFrame(
            id=1,
            sim_instance_id=100,
            seq_number=1,
            sim_seconds_elapsed=100.0,
            frame_data={
                "simId": "test-123",
                "clock": {"simSecondsPassed": 100.0},
                "tasks": [],
                "drivers": [],
                "stations": [],
                "vehicles": [],
            },
            is_key=True,
            created_at=datetime.now(),
        )
        mock_get_last_keyframe.return_value = mock_keyframe

        response = authenticated_client.get("/api/v1/simulation/100/state")
        assert response.status_code == 200
