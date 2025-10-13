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
from sqlalchemy.orm import Session
from back.crud.simulation_speed import playback_speed_crud


class TestPlaybackSpeedAPI:
    """Tests for the Playback Speed API endpoints."""

    def test_set_playback_speed_success(self, client: TestClient, db: Session) -> None:
        """Test setting playback speed successfully."""
        payload = {"simulation_id": 1, "playback_speed": 2.5}
        response = client.post("/api/v1/playback_speed/", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"] == payload["simulation_id"]
        assert data["playback_speed"] == payload["playback_speed"]
        assert "message" in data

    def test_set_playback_speed_invalid_value(
        self, client: TestClient, db: Session
    ) -> None:
        """Test setting playback speed with invalid values (negative or too high)."""
        invalid_payloads = [
            {"simulation_id": 1, "playback_speed": -1},
            {"simulation_id": 1, "playback_speed": 1000},
        ]
        for payload in invalid_payloads:
            response = client.post("/api/v1/playback_speed/", json=payload)
            assert response.status_code in (400, 422)

    def test_update_playback_speed(self, client: TestClient, db: Session) -> None:
        """Test updating an existing playback speed."""
        payload = {"simulation_id": 5, "playback_speed": 2.0}
        client.post("/api/v1/playback_speed/", json=payload)

        # Update the speed
        updated_payload = {"simulation_id": 5, "playback_speed": 4.5}
        response = client.post("/api/v1/playback_speed/", json=updated_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["playback_speed"] == updated_payload["playback_speed"]

        # Confirm GET returns updated speed
        response = client.get(f"/api/v1/playback_speed/{payload['simulation_id']}")
        data = response.json()
        assert data["playback_speed"] == updated_payload["playback_speed"]

    def test_get_playback_speed_success(self, client: TestClient, db: Session) -> None:
        """Test getting playback speed for an existing simulation."""
        payload = {"simulation_id": 2, "playback_speed": 3.0}
        client.post("/api/v1/playback_speed/", json=payload)

        response = client.get(f"/api/v1/playback_speed/{payload['simulation_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"] == payload["simulation_id"]
        assert data["playback_speed"] == payload["playback_speed"]

    def test_get_playback_speed_not_found(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting playback speed for a non-existing simulation."""
        response = client.get("/api/v1/playback_speed/9999")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Simulation not found."

    def test_get_all_playback_speeds(self, client: TestClient, db: Session) -> None:
        """Test retrieving all playback speeds."""
        # Clear existing store
        playback_speed_crud._store.clear()

        # Add multiple playback speeds
        speeds = [
            {"simulation_id": 10, "playback_speed": 1.0},
            {"simulation_id": 20, "playback_speed": 2.5},
            {"simulation_id": 30, "playback_speed": 3.0},
        ]
        for speed in speeds:
            client.post("/api/v1/playback_speed/", json=speed)

        response = client.get("/api/v1/playback_speed/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(speeds)
        for item in data:
            matching = next(
                (s for s in speeds if s["simulation_id"] == item["simulation_id"]), None
            )
            assert matching is not None
            assert item["playback_speed"] == matching["playback_speed"]

    def test_get_all_playback_speeds_empty(
        self, client: TestClient, db: Session
    ) -> None:
        """Test retrieving all playback speeds when store is empty."""
        playback_speed_crud._store.clear()
        response = client.get("/api/v1/playback_speed/")
        assert response.status_code == 200
        data = response.json()
        assert data == []
