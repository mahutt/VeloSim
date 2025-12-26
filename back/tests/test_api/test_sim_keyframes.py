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
from back.models.sim_keyframe import SimKeyframe


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Authenticated user fixture."""

    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def non_admin_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Non-admin user fixture."""

    def mock_get_user_id() -> int:
        return 2

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_keyframe() -> SimKeyframe:
    """Return a test keyframe."""
    return SimKeyframe(
        id=1,
        sim_instance_id=100,
        sim_seconds_elapsed=120.5,
        frame_data={"simId": "test-123", "tasks": [], "stations": [], "drivers": []},
        created_at=datetime.now(),
    )


class TestSimKeyframesAPI:
    """Test the sim-keyframes API endpoints."""

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_by_sim_instance")
    def test_get_keyframes_success(
        self,
        mock_get_by_sim: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
        test_keyframe: SimKeyframe,
    ) -> None:
        """Test successfully getting keyframes for a simulation."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        mock_get_by_sim.return_value = ([test_keyframe], 1)

        response = authenticated_client.get(
            "/api/v1/simulation/100/keyframes?page=1&per_page=20"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["keyframes"]) == 1
        assert data["keyframes"][0]["sim_instance_id"] == 100
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total_pages"] == 1

    @patch("back.api.v1.simulation.sim_instance_crud.get_by_uuid")
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    def test_get_keyframes_simulation_not_found(
        self,
        mock_sim_get: MagicMock,
        mock_sim_get_by_uuid: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test getting keyframes for non-existent simulation."""
        mock_sim_get_by_uuid.return_value = None  # Not found in DB by UUID
        mock_sim_get.return_value = None

        response = authenticated_client.get(
            "/api/v1/simulation/999/keyframes?page=1&per_page=20"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    def test_get_keyframes_unauthorized(
        self,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test getting keyframes when user doesn't own simulation."""
        mock_sim = MagicMock()
        mock_sim.user_id = 999  # Different user
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        response = authenticated_client.get(
            "/api/v1/simulation/100/keyframes?page=1&per_page=20"
        )
        assert response.status_code == 403
        assert "unauthorized" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_by_sim_instance")
    def test_get_keyframes_pagination(
        self,
        mock_get_by_sim: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test keyframe pagination."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        # Create 50 keyframes, return page 2
        keyframes = [
            SimKeyframe(
                id=i,
                sim_instance_id=100,
                sim_seconds_elapsed=float(i * 10),
                frame_data={},
                created_at=datetime.now(),
            )
            for i in range(20, 40)  # Page 2 (skip=20, limit=20)
        ]
        mock_get_by_sim.return_value = (keyframes, 50)

        response = authenticated_client.get(
            "/api/v1/simulation/100/keyframes?page=2&per_page=20"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 50
        assert len(data["keyframes"]) == 20
        assert data["page"] == 2
        assert data["total_pages"] == 3

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_by_sim_time")
    def test_get_keyframe_at_time_success(
        self,
        mock_get_by_time: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
        test_keyframe: SimKeyframe,
    ) -> None:
        """Test getting keyframe at specific time."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        mock_get_by_time.return_value = test_keyframe

        response = authenticated_client.get("/api/v1/simulation/100/keyframes/120.5")
        assert response.status_code == 200
        data = response.json()
        assert data["sim_seconds_elapsed"] == 120.5
        assert data["sim_instance_id"] == 100

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_by_sim_time")
    def test_get_keyframe_at_time_none_found(
        self,
        mock_get_by_time: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        """Test getting keyframe when none exist before requested time."""
        mock_sim = MagicMock()
        mock_sim.user_id = 1
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = False
        mock_user_get.return_value = mock_user

        mock_get_by_time.return_value = None

        response = authenticated_client.get("/api/v1/simulation/100/keyframes/5.0")
        assert response.status_code == 404
        assert "no keyframe found" in response.json()["detail"].lower()

    @patch(
        "back.api.v1.simulation.simulation_service.active_simulations",
        {"100": {"db_id": 100}},
    )
    @patch("back.api.v1.simulation.sim_instance_crud.get")
    @patch("back.api.v1.simulation.user_crud.get")
    @patch("back.api.v1.simulation.sim_keyframe_crud.get_by_sim_time")
    def test_get_keyframe_at_time_admin_access(
        self,
        mock_get_by_time: MagicMock,
        mock_user_get: MagicMock,
        mock_sim_get: MagicMock,
        authenticated_client: TestClient,
        test_keyframe: SimKeyframe,
    ) -> None:
        """Test admin can access any simulation's keyframes."""
        mock_sim = MagicMock()
        mock_sim.user_id = 999  # Different user
        mock_sim_get.return_value = mock_sim

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_admin = True  # Admin user
        mock_user_get.return_value = mock_user

        mock_get_by_time.return_value = test_keyframe

        response = authenticated_client.get("/api/v1/simulation/100/keyframes/120.5")
        assert response.status_code == 200

    def test_get_keyframes_invalid_pagination(
        self, authenticated_client: TestClient
    ) -> None:
        """Test that invalid pagination parameters are rejected."""
        response = authenticated_client.get(
            "/api/v1/simulation/100/keyframes?page=0&per_page=20"
        )
        assert response.status_code == 422  # Validation error

        response = authenticated_client.get(
            "/api/v1/simulation/100/keyframes?page=1&per_page=0"
        )
        assert response.status_code == 422

        response = authenticated_client.get(
            "/api/v1/simulation/100/keyframes?page=1&per_page=1000"
        )
        assert response.status_code == 422

    def test_get_keyframe_at_time_negative_seconds(
        self, authenticated_client: TestClient
    ) -> None:
        """Test that negative sim_seconds are rejected."""
        response = authenticated_client.get("/api/v1/simulation/100/keyframes/-10.0")
        assert response.status_code == 422  # Validation error
