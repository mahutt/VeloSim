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


class TestPlaybackSpeedAPI:
    """Tests for the Playback Speed API endpoints."""

    def test_set_playback_speed_success(self, client: TestClient, db: Session) -> None:
        """Test setting playback speed successfully."""
        payload = {"simulation_id": 1, "playback_speed": 2.5}
        response = client.post("/api/v1/playback/", json=payload)
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
            response = client.post("/api/v1/playback/", json=payload)
            assert response.status_code in (400, 422)

    def test_get_playback_speed_success(self, client: TestClient, db: Session) -> None:
        """Test getting playback speed for an existing simulation."""
        # First, set a playback speed
        payload = {"simulation_id": 2, "playback_speed": 3.0}
        client.post("/api/v1/playback/", json=payload)

        response = client.get(f"/api/v1/playback/{payload['simulation_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"] == payload["simulation_id"]
        assert data["playback_speed"] == payload["playback_speed"]

    def test_get_playback_speed_not_found(
        self, client: TestClient, db: Session
    ) -> None:
        """Test getting playback speed for a non-existing simulation."""
        response = client.get("/api/v1/playback/9999")
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Simulation not found."
