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
from sqlalchemy.orm import Session
from back.crud.resource import resource_crud
from back.crud.station import station_crud
from back.crud.station_task import station_task_crud
from back.crud.sim_instance import sim_instance_crud
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
    StationCreate,
    StationTaskCreate,
    SimInstanceCreate,
)


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a non-admin user for testing."""
    test_user = User(
        username="test_user",
        password_hash=user_crud.hash_password("test_password"),
        is_admin=False,
        is_enabled=True,
    )
    db.add(test_user)
    db.flush()
    db.refresh(test_user)
    return test_user


@pytest.fixture
def sim_instance(db: Session, test_user: User) -> SimInstance:
    """Create a test simulation instance for the normal user."""
    sim_instance_data = SimInstanceCreate(user_id=test_user.id)
    sim = sim_instance_crud.create(db, sim_instance_data)
    db.commit()
    return sim


@pytest.fixture
def station(db: Session, sim_instance: SimInstance) -> Station:
    """Create a station for testing tasks."""
    station_data = StationCreate(
        name="Test Station",
        longitude=0.0,
        latitude=0.0,
        sim_instance_id=sim_instance.id,
    )
    return station_crud.create(db, station_data)


@pytest.fixture
def resource(db: Session, sim_instance: SimInstance) -> Resource:
    """Create a resource for testing."""
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
    return resource_crud.create(db, resource_data)


@pytest.fixture
def task(db: Session, station: Station, sim_instance: SimInstance) -> StationTask:
    """Create a station task for assignment tests."""
    task_data = StationTaskCreate(
        type=StationTaskType.BATTERY_SWAP,
        station_id=station.id,
        sim_instance_id=sim_instance.id,
    )
    return station_task_crud.create(db, task_data)


class TestResourceCRUD:
    """Tests for Resource CRUD operations."""

    def test_create_resource(self, db: Session, sim_instance: SimInstance) -> None:
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
        r = resource_crud.create(db, resource_data)
        assert r.id is not None
        assert r.type == ResourceType.VEHICLE_DRIVER
        assert r.get_task_count() == 0

    def test_get_resource_by_id(self, db: Session, resource: Resource) -> None:
        r = resource_crud.get(db, resource.id)
        assert r is not None
        assert r.id == resource.id

    def test_get_resource_by_id_not_found(self, db: Session) -> None:
        r = resource_crud.get(db, 99999)
        assert r is None

    def test_get_all_resources_empty(self, db: Session) -> None:
        resources, total = resource_crud.get_all(db)
        assert resources == []
        assert total == 0

    def test_get_all_resources_with_data(self, db: Session, resource: Resource) -> None:
        resources, total = resource_crud.get_all(db)
        assert resource in resources
        assert total >= 1

    def test_update_resource(self, db: Session, resource: Resource) -> None:
        r = resource_crud.get(db, resource.id)
        assert r is not None

        update_data = ResourceUpdate(
            latitude=10.0,
            longitude=10.0,
            route_start_latitude=r.route_start_latitude,
            route_start_longitude=r.route_start_longitude,
            route_end_latitude=r.route_end_latitude,
            route_end_longitude=r.route_end_longitude,
        )

        updated = resource_crud.update(db, resource.id, update_data)
        assert updated is not None
        assert updated.latitude == 10.0
        assert updated.longitude == 10.0
        assert updated.route_start_latitude == r.route_start_latitude
        assert updated.route_end_longitude == r.route_end_longitude

    def test_update_resource_not_found(self, db: Session, resource: Resource) -> None:
        update_data = ResourceUpdate(
            latitude=10.0,
            longitude=10.0,
            route_start_latitude=resource.route_start_latitude,
            route_start_longitude=resource.route_start_longitude,
            route_end_latitude=resource.route_end_latitude,
            route_end_longitude=resource.route_end_longitude,
        )
        updated = resource_crud.update(db, 99999, update_data)
        assert updated is None

    def test_delete_resource(self, db: Session, resource: Resource) -> None:
        assert resource_crud.delete(db, resource.id)
        assert resource_crud.get(db, resource.id) is None

    def test_delete_resource_not_found(self, db: Session) -> None:
        assert not resource_crud.delete(db, 99999)

    def test_assign_task_by_id(
        self, db: Session, resource: Resource, task: StationTask
    ) -> None:
        assert resource_crud.assign_task(db, resource.id, task.id)
        assert task in resource.tasks
        assert task.resource == resource
        assert task.status == TaskStatus.ASSIGNED

    def test_assign_task_by_id_to_nonexistent_resource(
        self, db: Session, task: StationTask
    ) -> None:
        assert not resource_crud.assign_task(db, 99999, task.id)
        assert task.status == TaskStatus.OPEN

    def test_assign_task_by_id_nonexistent_task(
        self, db: Session, resource: Resource
    ) -> None:
        assert not resource_crud.assign_task(db, resource.id, 99999)

    def test_unassign_task_by_id(
        self, db: Session, resource: Resource, task: StationTask
    ) -> None:
        resource_crud.assign_task(db, resource.id, task.id)
        assert resource_crud.unassign_task(db, resource.id, task.id)
        assert task not in resource.tasks
        assert task.status == TaskStatus.OPEN

    def test_unassign_task_by_id_nonexistent_resource(
        self, db: Session, task: StationTask
    ) -> None:
        assert not resource_crud.unassign_task(db, 99999, task.id)

    def test_unassign_task_by_id_nonexistent_task(
        self, db: Session, resource: Resource
    ) -> None:
        assert not resource_crud.unassign_task(db, resource.id, 99999)

    def test_service_task_by_id(
        self, db: Session, resource: Resource, task: StationTask
    ) -> None:
        resource_crud.assign_task(db, resource.id, task.id)
        assert resource_crud.service_task(db, resource.id, task.id)
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
        self, db: Session, resource: Resource, task: StationTask
    ) -> None:
        resource_crud.assign_task(db, resource.id, task.id)
        resource_crud.delete(db, resource.id)
        assert task.status == TaskStatus.OPEN
        assert task.resource is None
