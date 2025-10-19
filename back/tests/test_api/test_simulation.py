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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Generator
from back.models.user import User
from back.crud.sim_instance import sim_instance_crud
from back.services.simulation_service import simulation_service

# Auth temporarily disabled - no need to import generate_access_token
# from back.auth import generate_access_token


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user with ID=1 (default dev user)."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.id == 1).first()
    if existing_user:
        return existing_user

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
def test_user2(db: Session) -> User:
    """Create a second test user."""
    user = User(
        username="testuser2",
        password_hash="hashedpassword2",
        is_admin=False,
        is_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# Auth temporarily disabled - no need for auth headers fixtures
# @pytest.fixture
# def auth_headers(test_user: User) -> dict[str, str]:
#     """Generate authorization headers with JWT token for test_user."""
#     token = generate_access_token(test_user.id)
#     return {"Authorization": f"Bearer {token}"}


# @pytest.fixture
# def auth_headers_user2(test_user2: User) -> dict[str, str]:
#     """Generate authorization headers with JWT token for test_user2."""
#     token = generate_access_token(test_user2.id)
#     return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def cleanup_simulations(db: Session) -> Generator[None, None, None]:
    """Cleanup all simulations before and after each test."""
    # Clean up before test
    simulation_service.active_simulations.clear()
    yield
    # Clean up after test
    try:
        simulation_service.stop_all_simulations(db)
    except Exception:
        # If DB cleanup fails, at least clear the in-memory state
        simulation_service.active_simulations.clear()


class TestSimulationAPI:
    """Test the simulation API endpoints."""

    def test_start_simulation_success(
        self, client: TestClient, db: Session, test_user: User
    ) -> None:
        """Test starting a simulation successfully (auth temporarily disabled)."""
        response = client.post("/api/v1/simulation/start")

        assert response.status_code == 200
        data = response.json()
        assert "sim_id" in data
        assert "db_id" in data
        assert data["status"] == "started"
        assert data["db_id"] > 0

        # Verify database record was created with default user_id=1
        sim_instance = sim_instance_crud.get(db, data["db_id"])
        assert sim_instance is not None
        assert sim_instance.user_id == 1  # Default dev user

    def test_stop_simulation_success(
        self, client: TestClient, db: Session, test_user: User
    ) -> None:
        """Test stopping a simulation successfully (auth temporarily disabled)."""
        # Start a simulation first
        start_response = client.post("/api/v1/simulation/start")
        assert start_response.status_code == 200
        sim_id = start_response.json()["sim_id"]

        # Stop the simulation
        stop_response = client.post(f"/api/v1/simulation/stop/{sim_id}")

        assert stop_response.status_code == 200
        data = stop_response.json()
        assert data["sim_id"] == sim_id
        assert data["status"] == "stopped"

    def test_stop_simulation_not_found(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test stopping a simulation that doesn't exist."""
        response = client.post("/api/v1/simulation/stop/nonexistent-sim-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_simulations(
        self, client: TestClient, db: Session, test_user: User
    ) -> None:
        """Test listing active simulations."""
        # Start two simulations
        client.post("/api/v1/simulation/start")
        client.post("/api/v1/simulation/start")

        # List simulations
        response = client.get("/api/v1/simulation/list")

        assert response.status_code == 200
        data = response.json()
        assert "active_simulations" in data
        assert len(data["active_simulations"]) == 2

    def test_get_simulation_status(
        self, client: TestClient, db: Session, test_user: User
    ) -> None:
        """Test getting the status of a specific simulation."""
        # Start a simulation
        start_response = client.post("/api/v1/simulation/start")
        sim_id = start_response.json()["sim_id"]

        # Get status
        response = client.get(f"/api/v1/simulation/status/{sim_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["sim_id"] == sim_id
        assert data["status"] == "running"

    def test_get_simulation_status_not_found(self, client: TestClient) -> None:
        """Test getting status of a simulation that doesn't exist."""
        response = client.get("/api/v1/simulation/status/nonexistent-sim-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_stop_all_simulations(
        self, client: TestClient, db: Session, test_user: User
    ) -> None:
        """Test stopping all running simulations."""
        # Start two simulations
        client.post("/api/v1/simulation/start")
        client.post("/api/v1/simulation/start")

        # Stop all
        response = client.post("/api/v1/simulation/stop-all")

        assert response.status_code == 200
        assert "stopped" in response.json()["message"].lower()

        # Verify all simulations are stopped
        list_response = client.get("/api/v1/simulation/list")
        assert len(list_response.json()["active_simulations"]) == 0

        # Verify database records are deleted (for default user_id=1)
        user_sims = sim_instance_crud.get_by_user(db, 1)
        assert len(user_sims) == 0
