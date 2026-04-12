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

from back.core.config import Settings, compose_database_url_from_env, env_flag


def test_root_is_public(client: TestClient) -> None:
    """Root endpoint is public and should not require authentication."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "VeloSim Backend API"


def test_health_is_public(client: TestClient) -> None:
    """Health endpoint is public and should not require authentication."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_token_endpoint_is_public(client: TestClient) -> None:
    """Token endpoint is public and returns credential errors, not auth errors."""
    response = client.post(
        "/api/token",
        data={"username": "invalid", "password": "invalid"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid credentials"


def test_metrics_endpoint_is_public(client: TestClient) -> None:
    """Metrics endpoint is public and should not require authentication."""
    response = client.get("/api/v1/metric/metrics")
    assert response.status_code == 200


def test_env_flag_true_and_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_FLAG", "TrUe")
    assert env_flag("FEATURE_FLAG") is True

    monkeypatch.setenv("FEATURE_FLAG", " false ")
    assert env_flag("FEATURE_FLAG") is False


def test_compose_database_url_from_env_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default_url = "postgresql://default"

    for name in ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USERNAME", "DB_PASSWORD"]:
        monkeypatch.delenv(name, raising=False)
    assert compose_database_url_from_env(default_url) == default_url

    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "velosim")
    monkeypatch.setenv("DB_USERNAME", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    assert (
        compose_database_url_from_env(default_url)
        == "postgresql://user:pass@db:5432/velosim"
    )


def test_parse_allowed_origins_variants() -> None:
    assert Settings.parse_allowed_origins(None) is None
    assert Settings.parse_allowed_origins(["https://a.com"]) == ["https://a.com"]
    assert Settings.parse_allowed_origins('["https://a.com", "https://b.com"]') == [
        "https://a.com",
        "https://b.com",
    ]
    assert Settings.parse_allowed_origins("https://a.com, https://b.com") == [
        "https://a.com",
        "https://b.com",
    ]
    assert Settings.parse_allowed_origins("https://single.com") == [
        "https://single.com"
    ]
