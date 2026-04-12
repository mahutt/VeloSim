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

from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from back.auth.dependency import get_user_id
from back.crud.traffic_template import TrafficTemplateCRUD
from back.main import app
from back.schemas.traffic_template import TrafficTemplateUpdateRequest
from back.schemas.utils.validators import (
    validate_latitude,
    validate_longitude,
    validate_unique_task_ids,
)
from sim.traffic.traffic_parser import TrafficParseError


VALID_TRAFFIC_CSV = (
    "TYPE,start_time,segment_key,duration,weight\n"
    'local_traffic,08:00,"((-73.5731,45.5013),(-73.5610,45.5070))",60,0.5'
)


@pytest.fixture
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    def mock_get_user_id() -> int:
        return 1

    app.dependency_overrides[get_user_id] = mock_get_user_id
    yield client
    app.dependency_overrides.clear()


class TestTrafficTemplatesAPI:
    @patch("back.api.v1.traffic_templates.traffic_template_crud.get_all")
    def test_get_templates_success(
        self,
        mock_get_all: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        now = datetime.now(timezone.utc)

        template = MagicMock()
        template.id = 1
        template.key = "default"
        template.content = VALID_TRAFFIC_CSV
        template.description = "Default"
        template.date_created = now
        template.date_updated = now

        mock_get_all.return_value = ([template], 1)

        response = authenticated_client.get("/api/v1/trafficTemplates/?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["templates"]) == 1
        assert data["templates"][0]["key"] == "default"
        assert "content" not in data["templates"][0]

    @patch("back.api.v1.traffic_templates.user_crud.get")
    def test_admin_required_for_create(
        self, mock_get_user: MagicMock, authenticated_client: TestClient
    ) -> None:
        non_admin = MagicMock()
        non_admin.is_admin = False
        non_admin.is_enabled = True
        mock_get_user.return_value = non_admin

        response = authenticated_client.post(
            "/api/v1/trafficTemplates/",
            json={"key": "default", "content": VALID_TRAFFIC_CSV},
        )
        assert response.status_code == 403
        assert "cannot manage traffic templates" in response.json()["detail"]

    @patch("back.api.v1.traffic_templates.traffic_template_crud.get_all")
    def test_non_admin_can_read_templates(
        self,
        mock_get_all: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        now = datetime.now(timezone.utc)

        template = MagicMock()
        template.id = 1
        template.key = "default"
        template.content = VALID_TRAFFIC_CSV
        template.description = "Default"
        template.date_created = now
        template.date_updated = now
        mock_get_all.return_value = ([template], 1)

        response = authenticated_client.get("/api/v1/trafficTemplates/")
        assert response.status_code == 200

    @patch("back.api.v1.traffic_templates.traffic_template_crud.get_by_key")
    def test_non_admin_can_get_template_by_key(
        self,
        mock_get_by_key: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        now = datetime.now(timezone.utc)

        template = MagicMock()
        template.id = 1
        template.key = "default"
        template.content = VALID_TRAFFIC_CSV
        template.description = "Default"
        template.date_created = now
        template.date_updated = now
        mock_get_by_key.return_value = template

        response = authenticated_client.get("/api/v1/trafficTemplates/default")
        assert response.status_code == 200
        assert response.json()["key"] == "default"

    @patch("back.api.v1.traffic_templates.user_crud.get")
    def test_non_admin_cannot_validate_template(
        self,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        non_admin = MagicMock()
        non_admin.is_admin = False
        non_admin.is_enabled = True
        mock_get_user.return_value = non_admin

        response = authenticated_client.post(
            "/api/v1/trafficTemplates/validate",
            json={"content": VALID_TRAFFIC_CSV},
        )
        assert response.status_code == 403

    def test_auth_required(self, client: TestClient) -> None:
        response = client.get("/api/v1/trafficTemplates/")
        assert response.status_code == 401

    @patch("back.api.v1.traffic_templates.user_crud.get")
    @patch("back.api.v1.traffic_templates.traffic_template_crud.get_optional_by_key")
    @patch("back.api.v1.traffic_templates.traffic_template_crud.create")
    def test_create_template_success(
        self,
        mock_create: MagicMock,
        mock_get_optional: MagicMock,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        now = datetime.now(timezone.utc)

        admin = MagicMock()
        admin.is_admin = True
        admin.is_enabled = True
        mock_get_user.return_value = admin

        mock_get_optional.return_value = None

        created = MagicMock()
        created.id = 1
        created.key = "default"
        created.content = VALID_TRAFFIC_CSV
        created.description = "Default"
        created.date_created = now
        created.date_updated = now
        mock_create.return_value = created

        response = authenticated_client.post(
            "/api/v1/trafficTemplates/",
            json={
                "key": "default",
                "content": VALID_TRAFFIC_CSV,
                "description": "Default",
            },
        )
        assert response.status_code == 201
        assert response.json()["key"] == "default"

    @patch("back.api.v1.traffic_templates.user_crud.get")
    @patch("back.api.v1.traffic_templates.traffic_template_crud.get_optional_by_key")
    def test_create_template_duplicate_key(
        self,
        mock_get_optional: MagicMock,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        admin = MagicMock()
        admin.is_admin = True
        admin.is_enabled = True
        mock_get_user.return_value = admin

        mock_get_optional.return_value = MagicMock()

        response = authenticated_client.post(
            "/api/v1/trafficTemplates/",
            json={"key": "default", "content": VALID_TRAFFIC_CSV},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @patch("back.api.v1.traffic_templates.user_crud.get")
    def test_validate_template_invalid_csv(
        self,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        admin = MagicMock()
        admin.is_admin = True
        admin.is_enabled = True
        mock_get_user.return_value = admin

        response = authenticated_client.post(
            "/api/v1/trafficTemplates/validate",
            json={"content": "not,a,valid,csv"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    @patch("back.api.v1.traffic_templates.user_crud.get")
    @patch("back.api.v1.traffic_templates.traffic_template_crud.get_by_key")
    def test_get_template_not_found(
        self,
        mock_get_by_key: MagicMock,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        from back.exceptions import ItemNotFoundError

        admin = MagicMock()
        admin.is_admin = True
        admin.is_enabled = True
        mock_get_user.return_value = admin

        mock_get_by_key.side_effect = ItemNotFoundError(
            "Traffic template 'missing' not found"
        )

        response = authenticated_client.get("/api/v1/trafficTemplates/missing")
        assert response.status_code == 404

    @patch("back.api.v1.traffic_templates.user_crud.get")
    @patch("back.api.v1.traffic_templates.traffic_template_crud.update")
    def test_update_template_success(
        self,
        mock_update: MagicMock,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        now = datetime.now(timezone.utc)

        admin = MagicMock()
        admin.is_admin = True
        admin.is_enabled = True
        mock_get_user.return_value = admin

        updated = MagicMock()
        updated.id = 1
        updated.key = "default"
        updated.content = VALID_TRAFFIC_CSV
        updated.description = "Updated"
        updated.date_created = now
        updated.date_updated = now
        mock_update.return_value = updated

        response = authenticated_client.put(
            "/api/v1/trafficTemplates/default",
            json={"description": "Updated"},
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Updated"

    def test_update_template_requires_at_least_one_field(
        self,
        authenticated_client: TestClient,
    ) -> None:
        response = authenticated_client.put(
            "/api/v1/trafficTemplates/default",
            json={},
        )
        assert response.status_code == 422

    @patch("back.api.v1.traffic_templates.user_crud.get")
    def test_non_admin_cannot_update_template(
        self,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        non_admin = MagicMock()
        non_admin.is_admin = False
        non_admin.is_enabled = True
        mock_get_user.return_value = non_admin

        response = authenticated_client.put(
            "/api/v1/trafficTemplates/default",
            json={"description": "Updated"},
        )
        assert response.status_code == 403

    @patch("back.api.v1.traffic_templates.user_crud.get")
    @patch("back.api.v1.traffic_templates.traffic_template_crud.delete")
    def test_delete_template_success(
        self,
        mock_delete: MagicMock,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        admin = MagicMock()
        admin.is_admin = True
        admin.is_enabled = True
        mock_get_user.return_value = admin

        response = authenticated_client.delete("/api/v1/trafficTemplates/default")
        assert response.status_code == 204
        mock_delete.assert_called_once()

    @patch("back.api.v1.traffic_templates.user_crud.get")
    def test_non_admin_cannot_delete_template(
        self,
        mock_get_user: MagicMock,
        authenticated_client: TestClient,
    ) -> None:
        non_admin = MagicMock()
        non_admin.is_admin = False
        non_admin.is_enabled = True
        mock_get_user.return_value = non_admin

        response = authenticated_client.delete("/api/v1/trafficTemplates/default")
        assert response.status_code == 403


def test_validate_longitude_bounds_and_cast() -> None:
    assert validate_longitude(180) == 180.0
    assert validate_longitude(-180) == -180.0

    with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
        validate_longitude(181)


def test_validate_latitude_bounds_and_cast() -> None:
    assert validate_latitude(90) == 90.0
    assert validate_latitude(-90) == -90.0

    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        validate_latitude(-91)


def test_validate_unique_task_ids_cases() -> None:
    assert validate_unique_task_ids(None) == []
    assert validate_unique_task_ids((1, 2, 3)) == [1, 2, 3]

    with pytest.raises(ValueError, match="Duplicate task_id"):
        validate_unique_task_ids([1, 2, 1])

    with pytest.raises(ValueError, match="task_ids must be a list of integers"):
        validate_unique_task_ids(5)


def test_traffic_template_update_requires_at_least_one_field() -> None:
    with pytest.raises(Exception):
        TrafficTemplateUpdateRequest(content=None, description=None)


@patch("back.api.v1.traffic_templates.user_crud.get")
@patch("back.api.v1.traffic_templates.TrafficParser.parse")
def test_validate_template_parse_error_returns_invalid_payload(
    mock_parse: MagicMock,
    mock_get_user: MagicMock,
    authenticated_client: TestClient,
) -> None:
    admin = MagicMock(is_admin=True, is_enabled=True)
    mock_get_user.return_value = admin
    mock_parse.side_effect = TrafficParseError(["bad header"])

    response = authenticated_client.post(
        "/api/v1/trafficTemplates/validate",
        json={"content": VALID_TRAFFIC_CSV},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert "bad header" in payload["errors"][0]


@patch("back.api.v1.traffic_templates.user_crud.get")
@patch("back.api.v1.traffic_templates.traffic_template_crud.get_optional_by_key")
@patch("back.api.v1.traffic_templates.traffic_template_crud.create")
@patch("back.api.v1.traffic_templates.TrafficParser.parse")
def test_create_template_parse_error_returns_400(
    mock_parse: MagicMock,
    mock_create: MagicMock,
    mock_get_optional: MagicMock,
    mock_get_user: MagicMock,
    authenticated_client: TestClient,
) -> None:
    admin = MagicMock(is_admin=True, is_enabled=True)
    mock_get_user.return_value = admin
    mock_get_optional.return_value = None
    mock_create.return_value = None
    mock_parse.side_effect = TrafficParseError(["bad row"])

    response = authenticated_client.post(
        "/api/v1/trafficTemplates/",
        json={"key": "default", "content": VALID_TRAFFIC_CSV},
    )

    assert response.status_code == 400
    assert "Invalid traffic template content" in response.json()["detail"]


@patch("back.api.v1.traffic_templates.user_crud.get")
@patch("back.api.v1.traffic_templates.traffic_template_crud.update")
@patch("back.api.v1.traffic_templates.TrafficParser.parse")
def test_update_template_parse_error_returns_400(
    mock_parse: MagicMock,
    mock_update: MagicMock,
    mock_get_user: MagicMock,
    authenticated_client: TestClient,
) -> None:
    admin = MagicMock(is_admin=True, is_enabled=True)
    mock_get_user.return_value = admin
    mock_update.return_value = None
    mock_parse.side_effect = TrafficParseError(["invalid duration"])

    response = authenticated_client.put(
        "/api/v1/trafficTemplates/default",
        json={"content": VALID_TRAFFIC_CSV},
    )

    assert response.status_code == 400
    assert "Invalid traffic template content" in response.json()["detail"]


def test_traffic_template_crud_create_update_delete_paths() -> None:
    crud = TrafficTemplateCRUD()
    mock_db = MagicMock()

    template_data = MagicMock()
    template_data.key = "default"
    template_data.content = VALID_TRAFFIC_CSV
    template_data.description = "desc"

    created = crud.create(mock_db, template_data)
    assert created.key == "default"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    template = MagicMock()
    query = MagicMock()
    query.filter.return_value.first.return_value = template
    mock_db.query.return_value = query
    assert crud.get_by_key(mock_db, "default") is template

    update_data = MagicMock()
    update_data.model_dump.return_value = {"description": "updated"}
    updated = crud.update(mock_db, "default", update_data)
    assert updated is template
    assert template.description == "updated"

    crud.delete(mock_db, "default")
    mock_db.delete.assert_called_with(template)


def test_traffic_template_crud_error_branches() -> None:
    crud = TrafficTemplateCRUD()
    mock_db = MagicMock()

    invalid = MagicMock()
    invalid.key = ""
    invalid.content = "x"
    invalid.description = None
    with pytest.raises(Exception):
        crud.create(mock_db, invalid)

    query = MagicMock()
    query.filter.return_value.first.return_value = None
    mock_db.query.return_value = query
    with pytest.raises(Exception):
        crud.get_by_key(mock_db, "missing")

    mock_db.query.return_value = query
    assert crud.get_optional_by_key(mock_db, "missing") is None

    count_query = MagicMock()
    count_query.scalar.return_value = 0
    data_query = MagicMock()
    ordered = data_query.order_by.return_value
    offsetted = ordered.offset.return_value
    limited = offsetted.limit.return_value
    limited.all.return_value = []
    mock_db.query.side_effect = [count_query, data_query]
    rows, total = crud.get_all(mock_db, skip=0, limit=5)
    assert rows == []
    assert total == 0
