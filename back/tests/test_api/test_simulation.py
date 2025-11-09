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

import asyncio
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Generator, TypedDict, List, cast, Any

from back.api.v1.utils.sim_websocket_helpers import WebSocketSubscriber
from back.main import app
from back.auth.dependency import get_user_id
from back.exceptions import VelosimPermissionError, ItemNotFoundError
from back.schemas import (
    ResourceTaskAssignResponse,
    ResourceTaskUnassignResponse,
    ResourceTaskReassignResponse,
)
from back.schemas.playback_speed import PlaybackSpeedResponse, SimulationPlaybackStatus
from back.schemas.resource import (
    ResourceTaskAssignRequest,
    ResourceTaskReassignRequest,
    ResourceTaskUnassignRequest,
)
from back.services.simulation_service import simulation_service

from back.models.user import User

SCENARIO_PAYLOAD = {
    "id": 1,
    "name": "Morning Operations",
    "content": {
        "start_time": "06:00",
        "end_time": "12:00",
        "stations": [
            {
                "station_id": 1,
                "station_name": "Station Alpha",
                "station_position": [45.5017, -73.5673],
            },
            {
                "station_id": 2,
                "station_name": "Station Bravo",
                "station_position": [45.5088, -73.5540],
            },
            {
                "station_id": 3,
                "station_name": "Station Charlie",
                "station_position": [45.5120, -73.5800],
            },
        ],
        "resources": [
            {"resource_id": 101, "resource_position": [45.505, -73.56]},
            {"resource_id": 102, "resource_position": [45.509, -73.57]},
        ],
        "initial_tasks": [
            {"id": "t1", "station_id": "1"},
            {"id": "t2", "station_id": "2"},
        ],
        "scheduled_tasks": [
            {"id": "t3", "time": 600, "station_id": "3"},
            {"id": "t4", "time": 1800, "station_id": "1"},
            {"id": "t5", "time": 3600, "station_id": "2"},
            {"id": "t6", "time": 5400, "station_id": "1"},
        ],
    },
}

# Apply patches before any simulator code is imported
pytestmark = pytest.mark.usefixtures("mock_heavy_sim_operations")


@pytest.fixture(scope="session", autouse=True)
def mock_heavy_sim_operations() -> Generator[None, None, None]:
    """
    Mock heavy simulation operations at the session level to prevent
    OSM data loading and CH network building during tests.
    """
    with (
        patch("sim.DAO.OSMConnection.OSMConnection._initialize_osm_data_file"),
        patch("sim.DAO.OSMConnection.OSMConnection._get_drivable_network"),
        patch("sim.DAO.OSMConnection.OSMConnection._set_projected_nodes"),
        patch("sim.DAO.OSMConnection.OSMConnection._build_edge_index"),
        patch("sim.DAO.OSMConnection.OSMConnection.create_networkx_graph"),
        patch("sim.DAO.OSMConnection.OSMConnection.build_ch_network"),
        patch("sim.SimulatorController.SimulatorController.start") as mock_start,
    ):
        # Make start() a no-op that doesn't spawn threads or do heavy work
        mock_start.return_value = None
        yield


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
def ws_client_authenticated(client: TestClient) -> Generator[TestClient, None, None]:
    """WebSocket client with get_user_id mocked."""

    def mock_get_user_id() -> int:
        return 1  # Use any test user ID

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def active_sim_id() -> Generator[str, None, None]:
    """Provides a dummy in-memory active simulation for tests."""
    sim_id = "sim-test-123"
    simulation_service.active_simulations[sim_id] = {"db_id": 999, "status": "running"}
    yield sim_id
    del simulation_service.active_simulations[sim_id]


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user with ID=1 for authenticated_client fixture."""
    # authenticated_client fixture mocks get_user_id to return 1
    # So we need to create a user with ID=1 in the test database
    user = db.query(User).filter(User.id == 1).first()
    if user:
        return user
    user = User(
        id=1,
        username="testuser",
        password_hash="hashedpassword",
        is_admin=False,
        is_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin test user with ID=999."""
    user = db.query(User).filter(User.id == 999).first()
    if user:
        return user
    user = User(
        id=999,
        username="adminuser",
        password_hash="hashedpassword2",
        is_admin=True,
        is_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def ws_client(client: TestClient) -> Generator[TestClient, None, None]:
    yield client


@pytest.fixture
def mocked_simulator(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Mock the simulator object to prevent DB or thread access in tests."""
    mock_sim = MagicMock()
    mock_emitter = MagicMock()
    mock_sim.thread_pool = {
        "sim123": {
            "emitter": mock_emitter,
            "thread": MagicMock(),
            "simController": MagicMock(),
        }
    }
    mock_sim.thread_pool_lock = MagicMock()

    # Patch the simulator getter
    monkeypatch.setattr(
        "back.services.simulation_service.simulation_service.get_simulator",
        lambda: mock_sim,
    )
    yield


class FrameData(TypedDict):
    seq: int
    timestamp: int
    is_key: bool
    payload: Any


class DummyWebSocket:
    """Fake WebSocket to capture JSON messages."""

    def __init__(self) -> None:
        self.sent: List[FrameData] = []
        self.client_state = WebSocketState.CONNECTED

    async def send_json(self, data: FrameData) -> None:
        self.sent.append(data)


class TestSimulationAPI:

    @patch("back.services.simulation_service.simulation_service.initialize_simulation")
    def test_initialize_simulation_success(
        self, mock_init: MagicMock, authenticated_client: TestClient
    ) -> None:
        mock_init.return_value = {
            "sim_id": "sim123",
            "db_id": 42,
            "status": "initialized",
        }
        response = authenticated_client.post(
            "/api/v1/simulation/initialize", json=SCENARIO_PAYLOAD
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sim_id"] == "sim123"
        assert data["db_id"] == 42
        assert data["status"] == "initialized"
        mock_init.assert_called_once()

    @patch("back.services.simulation_service.simulation_service.initialize_simulation")
    def test_initialize_simulation_permission_error(
        self, mock_init: MagicMock, non_admin_client: TestClient
    ) -> None:
        mock_init.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.post(
            "/api/v1/simulation/initialize", json=SCENARIO_PAYLOAD
        )
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.initialize_simulation")
    def test_initialize_simulation_generic_error(
        self, mock_init: MagicMock, authenticated_client: TestClient
    ) -> None:
        mock_init.side_effect = Exception("Unexpected error")
        response = authenticated_client.post(
            "/api/v1/simulation/initialize", json=SCENARIO_PAYLOAD
        )
        assert response.status_code == 500
        assert "Unexpected error" in response.json()["detail"]

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
        # Create a mock SimInstance object
        mock_sim = MagicMock()
        mock_sim.id = 1
        mock_sim.user_id = 1
        mock_sim.date_created = "2025-01-01T00:00:00"
        mock_sim.date_updated = "2025-01-01T00:00:00"
        mock_sim.resources = []
        mock_sim.stations = []
        mock_sim.tasks = []

        mock_list.return_value = ([mock_sim], 1)
        response = authenticated_client.get("/api/v1/simulation/my")
        assert response.status_code == 200
        data = response.json()
        assert "simulations" in data
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 1
        mock_list.assert_called_once_with(ANY, 1, 0, 10)

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
        # Create mock SimInstance objects
        mock_sim1 = MagicMock()
        mock_sim1.id = 1
        mock_sim1.user_id = 1
        mock_sim1.date_created = "2025-01-01T00:00:00"
        mock_sim1.date_updated = "2025-01-01T00:00:00"
        mock_sim1.resources = []
        mock_sim1.stations = []
        mock_sim1.tasks = []

        mock_sim2 = MagicMock()
        mock_sim2.id = 2
        mock_sim2.user_id = 1
        mock_sim2.date_created = "2025-01-01T00:00:00"
        mock_sim2.date_updated = "2025-01-01T00:00:00"
        mock_sim2.resources = []
        mock_sim2.stations = []
        mock_sim2.tasks = []

        mock_list.return_value = ([mock_sim1, mock_sim2], 2)
        response = authenticated_client.get("/api/v1/simulation/list")
        assert response.status_code == 200
        data = response.json()
        assert "simulations" in data
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 1
        mock_list.assert_called_once_with(ANY, 1, 0, 10)

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
        response = authenticated_client.post("/api/v1/simulation/stopAll")
        assert response.status_code == 200
        assert "stopped" in response.json()["message"].lower()
        mock_stop_all.assert_called_once_with(ANY, 1)

    @patch("back.services.simulation_service.simulation_service.stop_all_simulations")
    def test_stop_all_simulations_permission_error(
        self, mock_stop_all: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_stop_all.side_effect = VelosimPermissionError("No permission")
        response = non_admin_client.post("/api/v1/simulation/stopAll")
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.stop_all_simulations")
    def test_stop_all_simulations_generic_error(
        self, mock_stop_all: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_stop_all.side_effect = Exception("Unexpected")
        response = authenticated_client.post("/api/v1/simulation/stopAll")
        assert response.status_code == 500

    @patch("back.services.simulation_service.simulation_service.get_playback_speed")
    def test_get_playback_speed_success(
        self, mock_get_speed: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Successfully get playback speed and status."""

        mock_get_speed.return_value = PlaybackSpeedResponse(
            simulation_id="sim123",
            playback_speed=2.0,
            status=SimulationPlaybackStatus.RUNNING,
        )

        response = authenticated_client.get("/api/v1/simulation/sim123/playbackSpeed")
        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"] == "sim123"
        assert data["playback_speed"] == 2.0
        assert data["status"] == "running"

        mock_get_speed.assert_called()

    @patch("back.services.simulation_service.simulation_service.get_playback_speed")
    def test_get_playback_speed_not_found(
        self, mock_get_speed: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_get_speed.side_effect = ItemNotFoundError("Simulation not found")

        response = authenticated_client.get("/api/v1/simulation/unknown/playbackSpeed")
        assert response.status_code == 404
        assert "Simulation not found" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.get_playback_speed")
    def test_get_playback_speed_permission_error(
        self, mock_get_speed: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_get_speed.side_effect = VelosimPermissionError("Forbidden")

        response = non_admin_client.get("/api/v1/simulation/sim123/playbackSpeed")
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.get_playback_speed")
    def test_get_playback_speed_generic_error(
        self, mock_get_speed: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_get_speed.side_effect = Exception("Unexpected")

        response = authenticated_client.get("/api/v1/simulation/sim123/playbackSpeed")
        assert response.status_code == 500

    @patch("back.services.simulation_service.simulation_service.set_playback_speed")
    def test_set_playback_speed_success(
        self, mock_set_speed: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        """Successfully set playback speed."""
        mock_set_speed.return_value = PlaybackSpeedResponse(
            simulation_id="sim123",
            playback_speed=4.0,
            status=SimulationPlaybackStatus.RUNNING,
        )

        payload = {"playback_speed": 4.0}
        response = authenticated_client.post(
            "/api/v1/simulation/sim123/playbackSpeed", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"] == "sim123"
        assert data["playback_speed"] == 4.0
        assert data["status"] == "running"

        mock_set_speed.assert_called()

    @patch("back.services.simulation_service.simulation_service.set_playback_speed")
    def test_set_playback_speed_not_found(
        self, mock_set_speed: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_set_speed.side_effect = ItemNotFoundError("Simulation not found")

        response = authenticated_client.post(
            "/api/v1/simulation/unknown/playbackSpeed",
            json={"playback_speed": 2.0},
        )
        assert response.status_code == 404
        assert "Simulation not found" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.set_playback_speed")
    def test_set_playback_speed_permission_error(
        self, mock_set_speed: MagicMock, non_admin_client: TestClient, db: Session
    ) -> None:
        mock_set_speed.side_effect = VelosimPermissionError("Forbidden")

        response = non_admin_client.post(
            "/api/v1/simulation/sim123/playbackSpeed",
            json={"playback_speed": 1.0},
        )
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    @patch("back.services.simulation_service.simulation_service.set_playback_speed")
    def test_set_playback_speed_generic_error(
        self, mock_set_speed: MagicMock, authenticated_client: TestClient, db: Session
    ) -> None:
        mock_set_speed.side_effect = Exception("Unexpected")

        response = authenticated_client.post(
            "/api/v1/simulation/sim123/playbackSpeed",
            json={"playback_speed": 1.0},
        )
        assert response.status_code == 500

    def test_set_playback_speed_invalid_payload(
        self, authenticated_client: TestClient
    ) -> None:
        """Invalid payload should raise validation error (422)."""
        response = authenticated_client.post(
            "/api/v1/simulation/sim123/playbackSpeed",
            json={"playback_speed": 3.14159},  # invalid speed not in ALLOWED_SPEEDS
        )
        assert response.status_code == 422

    def test_websocket_subscriber_on_frame(self) -> None:
        """Test that WebSocketSubscriber schedules frames correctly."""

        # Create a new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            dummy_ws = DummyWebSocket()
            subscriber = WebSocketSubscriber(cast(WebSocket, dummy_ws))
            subscriber.set_event_loop(loop)

            # Mock a frame
            frame = MagicMock()
            frame.seq_number = 1
            frame.payload_dict = {"some": "data"}
            frame.timestamp_ms = 12345
            frame.is_key = True

            # Directly call the async method instead of going through on_frame
            # which uses run_coroutine_threadsafe (requires running loop in bg)
            loop.run_until_complete(subscriber._send_frame(frame))

            assert len(dummy_ws.sent) == 1
            assert dummy_ws.sent[0] == {
                "seq": 1,
                "timestamp": 12345,
                "is_key": True,
                "payload": {"some": "data"},
            }
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def test_websocket_subscriber_multiple_frames(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            dummy_ws = DummyWebSocket()
            subscriber = WebSocketSubscriber(cast(WebSocket, dummy_ws))
            subscriber.set_event_loop(loop)

            frames = [
                MagicMock(
                    seq_number=i,
                    payload_dict={"data": f"payload{i}"},
                    timestamp_ms=1000 + i,
                    is_key=(i == 0),
                )
                for i in range(3)
            ]

            # Send frames directly using the async method
            for frame in frames:
                loop.run_until_complete(subscriber._send_frame(frame))

            for i, frame in enumerate(frames):
                assert dummy_ws.sent[i] == {
                    "seq": frame.seq_number,
                    "timestamp": frame.timestamp_ms,
                    "is_key": frame.is_key,
                    "payload": frame.payload_dict,
                }
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def test_websocket_subscriber_send_error(self) -> None:
        class FailingWS(DummyWebSocket):
            async def send_json(self, data: FrameData) -> None:
                # Simulate realistic ASGI error when websocket is closed
                raise RuntimeError(
                    "Unexpected ASGI message 'websocket.send'"
                    ", after sending 'websocket.close'"
                )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            failing_ws = FailingWS()
            subscriber = WebSocketSubscriber(cast(WebSocket, failing_ws))
            subscriber.set_event_loop(loop)

            frame = MagicMock(
                seq_number=1,
                payload_dict={"data": "payload"},
                timestamp_ms=123,
                is_key=False,
            )

            # Should not raise even though send_json fails with ASGI error
            loop.run_until_complete(subscriber._send_frame(frame))

            # Subscriber should be marked as closed after error
            assert subscriber.closed is True
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def test_websocket_subscriber_init_and_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            dummy_ws = DummyWebSocket()
            subscriber = WebSocketSubscriber(cast(WebSocket, dummy_ws))

            # Setting the event loop should not raise
            subscriber.set_event_loop(loop)

            # Verify that sending a frame works using the event loop
            frame = MagicMock(
                seq_number=1,
                payload_dict={"data": "payload"},
                timestamp_ms=123,
                is_key=True,
            )

            # Directly call the async method
            loop.run_until_complete(subscriber._send_frame(frame))

            # Check that frame was sent
            assert len(dummy_ws.sent) == 1
            assert dummy_ws.sent[0]["seq"] == 1
            assert dummy_ws.sent[0]["payload"] == {"data": "payload"}
            assert dummy_ws.sent[0]["timestamp"] == 123
            assert dummy_ws.sent[0]["is_key"] is True
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def test_websocket_subscriber_malformed_frame(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            dummy_ws = DummyWebSocket()
            subscriber = WebSocketSubscriber(cast(WebSocket, dummy_ws))
            subscriber.set_event_loop(loop)

            # Frame with missing/None attributes
            frame = MagicMock(
                payload_dict={"data": "payload"}, timestamp_ms=123, is_key=False
            )
            frame.seq_number = None  # simulate missing

            # Directly call the async method
            loop.run_until_complete(subscriber._send_frame(frame))

            # Frame sent with None seq
            assert len(dummy_ws.sent) == 1
            assert dummy_ws.sent[0]["seq"] is None
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    @patch("back.api.v1.simulation.resource_service.assign_task")
    def test_assign_task_success(
        self,
        mock_assign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_assign.return_value = ResourceTaskAssignResponse(resource_id=7, task_id=42)
        payload = {"resource_id": 7, "task_id": 42}

        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/assign", json=payload
        )

        assert response.status_code == 200
        assert response.json() == {"resource_id": 7, "task_id": 42}

        mock_assign.assert_called_once_with(
            db=ANY,
            sim_id=active_sim_id,
            requesting_user=1,
            task_assign_data=ResourceTaskAssignRequest(**payload),
        )

    @patch("back.api.v1.simulation.resource_service.assign_task")
    def test_assign_task_permission_error(
        self,
        mock_assign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_assign.side_effect = VelosimPermissionError("No permission")
        payload = {"resource_id": 7, "task_id": 42}
        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/assign", json=payload
        )
        assert response.status_code == 403
        assert "No permission" in response.json()["detail"]

    @patch("back.api.v1.simulation.resource_service.assign_task")
    def test_assign_task_not_found(
        self,
        mock_assign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_assign.side_effect = ItemNotFoundError("Task not found")
        payload = {"resource_id": 999, "task_id": 42}
        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/assign", json=payload
        )
        assert response.status_code == 404

    @patch("back.api.v1.simulation.resource_service.unassign_task")
    def test_unassign_task_success(
        self,
        mock_unassign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_unassign.return_value = ResourceTaskUnassignResponse(
            resource_id=7, task_id=42
        )
        payload = {"resource_id": 7, "task_id": 42}

        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/unassign", json=payload
        )

        assert response.status_code == 200
        assert response.json() == {"resource_id": 7, "task_id": 42}

        mock_unassign.assert_called_once_with(
            db=ANY,
            sim_id=active_sim_id,
            requesting_user=1,
            task_unassign_data=ResourceTaskUnassignRequest(**payload),
        )

    @patch("back.api.v1.simulation.resource_service.unassign_task")
    def test_unassign_task_permission_error(
        self,
        mock_unassign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_unassign.side_effect = VelosimPermissionError("No permission")
        payload = {"resource_id": 7, "task_id": 42}
        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/unassign", json=payload
        )
        assert response.status_code == 403

    @patch("back.api.v1.simulation.resource_service.reassign_task")
    def test_reassign_task_success(
        self,
        mock_reassign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_reassign.return_value = ResourceTaskReassignResponse(
            task_id=42, old_resource_id=7, new_resource_id=8
        )
        payload = {"task_id": 42, "old_resource_id": 7, "new_resource_id": 8}

        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/reassign", json=payload
        )

        assert response.status_code == 200
        assert response.json() == {
            "task_id": 42,
            "old_resource_id": 7,
            "new_resource_id": 8,
        }

        mock_reassign.assert_called_once_with(
            db=ANY,
            sim_id=active_sim_id,
            requesting_user=1,
            task_reassign_data=ResourceTaskReassignRequest(**payload),
        )

    @patch("back.api.v1.simulation.resource_service.reassign_task")
    def test_reassign_task_permission_error(
        self,
        mock_reassign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_reassign.side_effect = VelosimPermissionError("No permission")
        payload = {"task_id": 42, "old_resource_id": 7, "new_resource_id": 8}
        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/reassign", json=payload
        )
        assert response.status_code == 403

    @patch("back.api.v1.simulation.resource_service.reassign_task")
    def test_reassign_task_not_found(
        self,
        mock_reassign: MagicMock,
        authenticated_client: TestClient,
        active_sim_id: str,
    ) -> None:
        mock_reassign.side_effect = ItemNotFoundError("Task not found")
        payload = {"task_id": 999, "old_resource_id": 7, "new_resource_id": 8}
        response = authenticated_client.post(
            f"/api/v1/simulation/{active_sim_id}/resources/reassign", json=payload
        )
        assert response.status_code == 404


class TestSimulationListIntegration:
    """Integration tests for simulation listing with full flow."""

    @pytest.fixture(autouse=True)
    def reset_simulation_service(self) -> Generator[None, None, None]:
        """Reset simulation service before each integration test."""
        # Clear active simulations before test
        simulation_service.active_simulations.clear()
        yield
        # Clean up after test
        simulation_service.active_simulations.clear()

    def test_start_and_list_my_simulations(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        # Step 1: Start simulation
        start_response = authenticated_client.post(
            "/api/v1/simulation/initialize", json=SCENARIO_PAYLOAD
        )
        assert start_response.status_code == 200
        sim_data = start_response.json()
        sim_id = sim_data["sim_id"]
        db_id = sim_data["db_id"]

        # Step 2: List simulations
        list_response = authenticated_client.get("/api/v1/simulation/my")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] == 1
        simulation = list_data["simulations"][0]
        assert simulation["id"] == db_id

        # Step 3: Stop simulation
        stop_response = authenticated_client.post(f"/api/v1/simulation/stop/{sim_id}")
        assert stop_response.status_code == 200

    def test_list_with_pagination(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        sim_ids = []
        for _ in range(3):
            response = authenticated_client.post(
                "/api/v1/simulation/initialize", json=SCENARIO_PAYLOAD
            )
            assert response.status_code == 200
            sim_ids.append(response.json()["sim_id"])

        # page 1, limit 2
        response = authenticated_client.get("/api/v1/simulation/my?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["simulations"]) == 2

        # page 2, limit 2
        response = authenticated_client.get("/api/v1/simulation/my?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["simulations"]) == 1

        # Cleanup
        for sim_id in sim_ids:
            authenticated_client.post(f"/api/v1/simulation/stop/{sim_id}")

    def test_empty_simulation_list(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        """Test listing when no simulations are running."""
        response = authenticated_client.get("/api/v1/simulation/my")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total_pages"] == 0
        assert len(data["simulations"]) == 0

    def test_pagination_edge_cases(
        self, authenticated_client: TestClient, db: Session, test_user: User
    ) -> None:
        start_response = authenticated_client.post(
            "/api/v1/simulation/initialize", json=SCENARIO_PAYLOAD
        )
        assert start_response.status_code == 200
        sim_id = start_response.json()["sim_id"]

        # Large limit
        response = authenticated_client.get("/api/v1/simulation/my?skip=0&limit=100")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["total_pages"] == 1

        # skip beyond total
        response = authenticated_client.get("/api/v1/simulation/my?skip=10&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["simulations"]) == 0
        assert data["page"] == 2

        # Cleanup
        authenticated_client.post(f"/api/v1/simulation/stop/{sim_id}")

    def test_unauthorized_list_returns_401(self, client: TestClient) -> None:
        """Test that listing without authentication returns 401."""
        response = client.get("/api/v1/simulation/my")
        assert response.status_code == 401
