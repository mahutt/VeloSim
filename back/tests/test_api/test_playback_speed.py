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
from back.main import app

client = TestClient(app)


async def test_set_playback_speed_success() -> None:
    response = client.post(
        "/api/v1/playback/", json={"simulation_id": 1, "playback_speed": 2.5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["simulation_id"] == 1
    assert data["playback_speed"] == 2.5
    assert "updated successfully" in data["message"]


def test_get_playback_speed_success() -> None:
    client.post("/api/v1/playback/", json={"simulation_id": 2, "playback_speed": 3.0})
    response = client.get("/api/v1/playback/2")
    assert response.status_code == 200
    data = response.json()
    assert data["simulation_id"] == 2
    assert data["playback_speed"] == 3.0
