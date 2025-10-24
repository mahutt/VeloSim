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
from unittest.mock import patch, MagicMock, ANY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Generator, cast, TypedDict, List
import asyncio

from back.main import app
from back.auth.dependency import get_user_id
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.services.simulation_service import simulation_service
from back.api.v1.simulation import WebSocketSubscriber
from fastapi import WebSocket

from sim.frame_emitter import FrameEmitter


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Client with authenticated default user (ID=1)."""

    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def non_admin_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Client with non-admin user (ID=2)."""

    def mock_get_user_id() -> int:
        return 2

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def disabled_admin_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Client with disabled admin user (ID=3)."""

    def mock_get_user_id() -> int:
        return 3

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def ws_client(client: TestClient) -> Generator[TestClient, None, None]:
    yield client


class TestSimulationAPI:

    @patch("back.services.simulation_service.simulation_service.start_simulation")
    def test_start_simulation_success(
        self, mock_start: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Test starting a simulation successfully."""
        mock_start.return_value = ("sim123", 42)
        response = authenticated_client.post("/api/v1/simulation/start")
        assert response.status_code == 200
        data = response.json()
        assert data["sim_id"] == "sim123"
        assert data["db_id"] == 42
        assert data["status"] == "started"
        mock_start.assert_called_once_with(ANY, 1)

    @patch("back.services.simulation_service.simulation_service.start_simulation")
    def test_start_simulation_permission_error(
        self, mock_start: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        """Non-admin user cannot start simulation if restricted."""
        mock_start.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.post("/api/v1/simulation/start")
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]
        mock_start.assert_called_once_with(ANY, 2)

    @patch("back.services.simulation_service.simulation_service.start_simulation")
    def test_start_simulation_generic_error(
        self, mock_start: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_start.side_effect = Exception("Unexpected error")
        response = authenticated_client.post("/api/v1/simulation/start")
        assert response.status_code == 500

    @patch("back.services.simulation_service.simulation_service.stop_simulation")
    def test_stop_simulation_success(
        self, mock_stop: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Stop a simulation successfully."""
        response = authenticated_client.post("/api/v1/simulation/stop/sim123")
        assert response.status_code == 200
        data = response.json()
        assert data["sim_id"] == "sim123"
        assert data["status"] == "stopped"
        mock_stop.assert_called_once_with(ANY, "sim123", 1)

    @patch("back.services.simulation_service.simulation_service.stop_simulation")
    def test_stop_simulation_permission_error(
        self, mock_stop: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_stop.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.post("/api/v1/simulation/stop/sim123")
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.stop_simulation")
    def test_stop_simulation_not_found(
        self, mock_stop: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_stop.side_effect = ItemNotFoundError("Simulation not found")
        response = authenticated_client.post("/api/v1/simulation/stop/unknown")
        assert response.status_code == 404
        assert "Simulation not found" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.stop_simulation")
    def test_stop_simulation_generic_error(
        self, mock_stop: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_stop.side_effect = Exception("Unexpected")
        response = authenticated_client.post("/api/v1/simulation/stop/sim123")
        assert response.status_code == 500

    @patch(
        "back.services.simulation_service.simulation_service."
        "get_active_user_simulations"
    )
    def test_list_my_simulations_success(
        self, mock_list: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_list.return_value = ["sim1"]
        response = authenticated_client.get("/api/v1/simulation/my")
        assert response.status_code == 200
        data = response.json()
        assert data["active_simulations"] == ["sim1"]
        mock_list.assert_called_once_with(ANY, 1)

    @patch(
        "back.services.simulation_service.simulation_service."
        "get_active_user_simulations"
    )
    def test_list_my_simulations_permission_error(
        self, mock_list: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_list.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.get("/api/v1/simulation/my")
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch(
        "back.services.simulation_service.simulation_service.get_all_active_simulations"
    )
    def test_list_all_simulations_success(
        self, mock_list: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_list.return_value = ["sim1", "sim2"]
        response = authenticated_client.get("/api/v1/simulation/list")
        assert response.status_code == 200
        data = response.json()
        assert data["active_simulations"] == ["sim1", "sim2"]
        mock_list.assert_called_once_with(ANY, 1)

    @patch(
        "back.services.simulation_service.simulation_service.get_all_active_simulations"
    )
    def test_list_all_simulations_permission_error(
        self, mock_list: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_list.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.get("/api/v1/simulation/list")
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.get_simulation_status")
    def test_get_simulation_status_success(
        self, mock_status: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_status.return_value = "running"
        response = authenticated_client.get("/api/v1/simulation/status/sim123")
        assert response.status_code == 200
        data = response.json()
        assert data["sim_id"] == "sim123"
        assert data["status"] == "running"
        mock_status.assert_called_once_with(ANY, "sim123", 1)

    @patch("back.services.simulation_service.simulation_service.get_simulation_status")
    def test_get_simulation_status_permission_error(
        self, mock_status: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_status.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.get("/api/v1/simulation/status/sim123")
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.get_simulation_status")
    def test_get_simulation_status_not_found(
        self, mock_status: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_status.side_effect = ItemNotFoundError("Simulation not found")
        response = authenticated_client.get("/api/v1/simulation/status/unknown")
        assert response.status_code == 404
        assert "Simulation not found" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.get_simulation_status")
    def test_get_simulation_status_generic_error(
        self, mock_status: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_status.side_effect = Exception("Unexpected")
        response = authenticated_client.get("/api/v1/simulation/status/sim123")
        assert response.status_code == 500

    @patch("back.services.simulation_service.simulation_service.stop_all_simulations")
    def test_stop_all_simulations_success(
        self, mock_stop_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        response = authenticated_client.post("/api/v1/simulation/stop-all")
        assert response.status_code == 200
        assert "stopped" in response.json()["message"].lower()
        mock_stop_all.assert_called_once_with(ANY, 1)

    @patch("back.services.simulation_service.simulation_service.stop_all_simulations")
    def test_stop_all_simulations_permission_error(
        self, mock_stop_all: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_stop_all.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.post("/api/v1/simulation/stop-all")
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.stop_all_simulations")
    def test_stop_all_simulations_generic_error(
        self, mock_stop_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_stop_all.side_effect = Exception("Unexpected")
        response = authenticated_client.post("/api/v1/simulation/stop-all")
        assert response.status_code == 500

    def test_websocket_subscriber_on_frame(self) -> None:
        """Test that WebSocketSubscriber schedules frames correctly."""

        class FrameData(TypedDict):
            sim_id: str
            seq_numb: int
            payload: str
            timestamp: int

        class DummyWebSocket:
            """Fake WebSocket to capture JSON messages."""

            def __init__(self) -> None:
                self.sent: List[FrameData] = []

            async def send_json(self, data: FrameData) -> None:
                self.sent.append(data)

        dummy_ws = DummyWebSocket()
        subscriber = WebSocketSubscriber(cast(WebSocket, dummy_ws), "sim123")
        subscriber.set_event_loop(asyncio.get_event_loop())

        # Mock a frame
        frame = MagicMock()
        frame.seq_number = 1
        frame.payload_str = "payload"
        frame.timestamp_ms = 12345

        # Trigger the frame
        subscriber.on_frame(frame)

        # Wait a little for the coroutine to execute
        asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.01))

        assert len(dummy_ws.sent) == 1
        assert dummy_ws.sent[0] == {
            "sim_id": "sim123",
            "seq_numb": 1,
            "payload": "payload",
            "timestamp": 12345,
        }

    def test_websocket_stream_endpoint(self, ws_client: TestClient) -> None:
        """Test the /stream/{sim_id} WebSocket endpoint."""

        # Prepare active simulation
        simulation_service.active_simulations = {"sim123": {}}

        simulator = simulation_service.get_simulator()

        # Use real FrameEmitter, mock the thread and simController
        with simulator.thread_pool_lock:
            simulator.thread_pool["sim123"] = {
                "emitter": FrameEmitter("sim123"),
                "thread": MagicMock(),
                "simController": MagicMock(),
            }

        with ws_client.websocket_connect(
            "/api/v1/simulation/stream/sim123"
        ) as websocket:
            # Receive initial connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connection_established"
            assert data["sim_id"] == "sim123"
            assert "Connected to simulation frame stream" in data["message"]

            # Send ping, expect pong
            websocket.send_text("ping")
            pong = websocket.receive_json()
            assert pong["type"] == "pong"
