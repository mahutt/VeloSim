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
from unittest.mock import Mock
from back.crud.resource import resource_crud
from back.crud.user import user_crud

from back.models import (
    Resource,
    ResourceType,
    Station,
    StationTask,
    StationTaskType,
    TaskStatus,
    User,
    SimInstance,
)
from back.schemas import (
    ResourceCreate,
    ResourceUpdate,
)


@pytest.fixture
def test_user() -> User:
    """Create a non-admin user for testing."""
    return User(
        id=1,
        username="test_user",
        password_hash=user_crud.hash_password("test_password"),
        is_admin=False,
        is_enabled=True,
    )


@pytest.fixture
def sim_instance(test_user: User) -> SimInstance:
    """Create a test simulation instance for the normal user."""
    return SimInstance(id=1, user_id=test_user.id)


@pytest.fixture
def station(sim_instance: SimInstance) -> Station:
    """Create a station for testing tasks."""
    return Station(
        id=1,
        name="Test Station",
        longitude=0.0,
        latitude=0.0,
        sim_instance_id=sim_instance.id,
    )


@pytest.fixture
def resource(sim_instance: SimInstance) -> Resource:
    """Create a resource for testing."""
    return Resource(
        id=1,
        type=ResourceType.VEHICLE_DRIVER,
        latitude=0.0,
        longitude=0.0,
        route_start_latitude=1.0,
        route_start_longitude=1.0,
        route_end_latitude=2.0,
        route_end_longitude=2.0,
        sim_instance_id=sim_instance.id,
    )


@pytest.fixture
def task(station: Station, sim_instance: SimInstance) -> StationTask:
    """Create a station task for assignment tests."""
    return StationTask(
        id=1,
        type=StationTaskType.BATTERY_SWAP,
        status=TaskStatus.OPEN,
        station_id=station.id,
        sim_instance_id=sim_instance.id,
    )


class TestResourceCRUD:
    """Tests for Resource CRUD operations."""

    def test_create_resource(self, mock_db: Mock, sim_instance: SimInstance) -> None:
        from back.tests.mock_utils import setup_mock_db_add_with_id

        # Mock db.begin context manager
        mock_db.begin.return_value.__enter__ = Mock()
        mock_db.begin.return_value.__exit__ = Mock()

        # Mock db.add to assign ID on refresh
        setup_mock_db_add_with_id(mock_db, 1)

        resource_data = ResourceCreate(
            type=ResourceType.VEHICLE_DRIVER,
            latitude=0.0,
            longitude=0.0,
            route_start_latitude=1.0,
            route_start_longitude=1.0,
            route_end_latitude=2.0,
            route_end_longitude=2.0,
            sim_instance_id=sim_instance.id,
        )
        r = resource_crud.create(mock_db, resource_data)
        assert r.id is not None
        assert r.type == ResourceType.VEHICLE_DRIVER
        assert r.get_task_count() == 0

    def test_get_resource_by_id(self, mock_db: Mock, resource: Resource) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_query

        r = resource_crud.get(mock_db, resource.id)
        assert r is not None
        assert r.id == resource.id

    def test_get_resource_by_id_not_found(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        r = resource_crud.get(mock_db, 99999)
        assert r is None

    def test_get_all_resources_empty(self, mock_db: Mock) -> None:
        # Mock for count query (uses scalar)
        mock_count_query = Mock()
        mock_count_query.scalar.return_value = 0

        # Mock for data query
        mock_data_query = Mock()
        mock_data_query.offset.return_value.limit.return_value.all.return_value = []

        mock_db.query.side_effect = [mock_count_query, mock_data_query]

        resources, total = resource_crud.get_all(mock_db)
        assert resources == []
        assert total == 0

    def test_get_all_resources_with_data(
        self, mock_db: Mock, resource: Resource
    ) -> None:
        # Mock for count query (uses scalar)
        mock_count_query = Mock()
        mock_count_query.scalar.return_value = 1

        # Mock for data query
        mock_data_query = Mock()
        mock_data_query.offset.return_value.limit.return_value.all.return_value = [
            resource
        ]

        mock_db.query.side_effect = [mock_count_query, mock_data_query]

        resources, total = resource_crud.get_all(mock_db)
        assert resource in resources
        assert total >= 1

    def test_update_resource(self, mock_db: Mock, resource: Resource) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_query

        update_data = ResourceUpdate(
            latitude=10.0,
            longitude=10.0,
            route_start_latitude=resource.route_start_latitude,
            route_start_longitude=resource.route_start_longitude,
            route_end_latitude=resource.route_end_latitude,
            route_end_longitude=resource.route_end_longitude,
        )

        updated = resource_crud.update(mock_db, resource.id, update_data)
        assert updated is not None
        assert updated.latitude == 10.0
        assert updated.longitude == 10.0
        assert updated.route_start_latitude == resource.route_start_latitude
        assert updated.route_end_longitude == resource.route_end_longitude

    def test_update_resource_not_found(self, mock_db: Mock, resource: Resource) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        update_data = ResourceUpdate(
            latitude=10.0,
            longitude=10.0,
            route_start_latitude=resource.route_start_latitude,
            route_start_longitude=resource.route_start_longitude,
            route_end_latitude=resource.route_end_latitude,
            route_end_longitude=resource.route_end_longitude,
        )
        updated = resource_crud.update(mock_db, 99999, update_data)
        assert updated is None

    def test_delete_resource(self, mock_db: Mock, resource: Resource) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [resource, None]
        mock_db.query.return_value = mock_query

        assert resource_crud.delete(mock_db, resource.id)
        assert resource_crud.get(mock_db, resource.id) is None

    def test_delete_resource_not_found(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        assert not resource_crud.delete(mock_db, 99999)

    def test_assign_task_by_id(
        self, mock_db: Mock, resource: Resource, task: StationTask
    ) -> None:
        # Mock query for resource
        mock_resource_query = Mock()
        mock_resource_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_resource_query

        # Mock db.get for task
        mock_db.get.return_value = task

        assert resource_crud.assign_task(mock_db, resource.id, task.id)
        assert task in resource.tasks
        assert task.resource == resource
        assert task.status == TaskStatus.ASSIGNED

    def test_assign_task_by_id_to_nonexistent_resource(
        self, mock_db: Mock, task: StationTask
    ) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [None, task]
        mock_db.query.return_value = mock_query

        assert not resource_crud.assign_task(mock_db, 99999, task.id)
        assert task.status == TaskStatus.OPEN

    def test_assign_task_by_id_nonexistent_task(
        self, mock_db: Mock, resource: Resource
    ) -> None:
        # Mock query for resource
        mock_resource_query = Mock()
        mock_resource_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_resource_query

        # Mock db.get for nonexistent task
        mock_db.get.return_value = None

        assert not resource_crud.assign_task(mock_db, resource.id, 99999)

    def test_unassign_task_by_id(
        self, mock_db: Mock, resource: Resource, task: StationTask
    ) -> None:
        # Mock query for resource (same for both calls)
        mock_resource_query = Mock()
        mock_resource_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_resource_query

        # Mock db.get for task (same for both calls)
        mock_db.get.return_value = task

        resource_crud.assign_task(mock_db, resource.id, task.id)
        assert resource_crud.unassign_task(mock_db, resource.id, task.id)
        assert task not in resource.tasks
        assert task.status == TaskStatus.OPEN

    def test_unassign_task_by_id_nonexistent_resource(
        self, mock_db: Mock, task: StationTask
    ) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [None, task]
        mock_db.query.return_value = mock_query

        assert not resource_crud.unassign_task(mock_db, 99999, task.id)

    def test_unassign_task_by_id_nonexistent_task(
        self, mock_db: Mock, resource: Resource
    ) -> None:
        # Mock query for resource
        mock_resource_query = Mock()
        mock_resource_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_resource_query

        # Mock db.get for nonexistent task
        mock_db.get.return_value = None

        assert not resource_crud.unassign_task(mock_db, resource.id, 99999)

    def test_service_task_by_id(
        self, mock_db: Mock, resource: Resource, task: StationTask
    ) -> None:
        # Mock query for resource (same for both calls)
        mock_resource_query = Mock()
        mock_resource_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_resource_query

        # Mock db.get for task (same for both calls)
        mock_db.get.return_value = task

        resource_crud.assign_task(mock_db, resource.id, task.id)
        assert resource_crud.service_task(mock_db, resource.id, task.id)
        assert task not in resource.tasks
        assert task.status == TaskStatus.CLOSED

    def test_assign_task_model_errors(
        self, resource: Resource, task: StationTask
    ) -> None:
        resource.assign_task(task)
        with pytest.raises(ValueError):
            resource.assign_task(task)  # Already assigned

        task.status = TaskStatus.CLOSED
        with pytest.raises(ValueError):
            resource.assign_task(task)  # Task not open

        with pytest.raises(ValueError):
            resource.assign_task(None)  # type: ignore[arg-type]

    def test_unassign_task_model_errors(
        self, resource: Resource, task: StationTask
    ) -> None:
        with pytest.raises(ValueError):
            resource.unassign_task(task)  # Not assigned

        with pytest.raises(ValueError):
            resource.unassign_task(None)  # type: ignore[arg-type]

    def test_service_task_model_errors(
        self, resource: Resource, task: StationTask
    ) -> None:
        with pytest.raises(ValueError):
            resource.service_task(task)  # Not assigned

        with pytest.raises(ValueError):
            resource.service_task(None)  # type: ignore[arg-type]

    def test_delete_resets_tasks(
        self, mock_db: Mock, resource: Resource, task: StationTask
    ) -> None:
        # Mock query for resource (same for both calls)
        mock_resource_query = Mock()
        mock_resource_query.filter.return_value.first.return_value = resource
        mock_db.query.return_value = mock_resource_query

        # Mock db.get for task
        mock_db.get.return_value = task

        resource_crud.assign_task(mock_db, resource.id, task.id)
        resource_crud.delete(mock_db, resource.id)
        assert task.status == TaskStatus.OPEN
        assert task.resource is None
