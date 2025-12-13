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
from back.crud.station_task import station_task_crud
from back.crud.user import user_crud
from back.schemas import StationTaskCreate, StationTaskUpdate
from back.models import Station, StationTaskType, TaskStatus, SimInstance, User


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
    return Station(
        id=1,
        name="Test Station",
        longitude=0.0,
        latitude=0.0,
        sim_instance_id=sim_instance.id,
    )


class TestStationTaskCRUD:
    def test_create_station_task(
        self, mock_db: Mock, station: Station, sim_instance: SimInstance
    ) -> None:
        from typing import Any

        # Mock context manager
        mock_db.begin.return_value.__enter__ = Mock()
        mock_db.begin.return_value.__exit__ = Mock()

        # Mock add to also set database default for status
        def mock_add(obj: Any) -> None:
            obj.id = 1
            obj.status = TaskStatus.OPEN  # Database default

        mock_db.add.side_effect = mock_add
        mock_db.flush = Mock()
        mock_db.refresh = Mock()

        task_data = StationTaskCreate(
            type=StationTaskType.BATTERY_SWAP,
            station_id=station.id,
            sim_instance_id=sim_instance.id,
        )
        task = station_task_crud.create(mock_db, task_data)
        assert task.id is not None
        assert task.type == StationTaskType.BATTERY_SWAP
        assert task.station_id == station.id
        assert task.status == TaskStatus.OPEN

    def test_get_station_task_by_id(
        self, mock_db: Mock, station: Station, sim_instance: SimInstance
    ) -> None:
        from back.models import StationTask

        created_task = StationTask(
            id=1,
            type=StationTaskType.BATTERY_SWAP,
            station_id=station.id,
            sim_instance_id=sim_instance.id,
            status=TaskStatus.OPEN,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = created_task
        mock_db.query.return_value = mock_query

        retrieved_task = station_task_crud.get(mock_db, created_task.id)
        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.type == StationTaskType.BATTERY_SWAP

    def test_get_station_task_by_id_not_found(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        task = station_task_crud.get(mock_db, 99999)
        assert task is None

    def test_get_all_station_tasks_empty(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_query.count.return_value = 0
        mock_query.offset.return_value.limit.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        tasks, total = station_task_crud.get_all(mock_db)
        assert tasks == []
        assert total == 0

    def test_get_all_station_tasks_with_data(
        self, mock_db: Mock, station: Station, sim_instance: SimInstance
    ) -> None:
        from back.models import StationTask

        tasks_list = [
            StationTask(
                id=i + 1,
                type=StationTaskType.BATTERY_SWAP,
                station_id=station.id,
                sim_instance_id=sim_instance.id,
                status=TaskStatus.OPEN,
            )
            for i in range(3)
        ]

        mock_query = Mock()
        mock_query.count.return_value = 3
        mock_query.offset.return_value.limit.return_value.all.return_value = tasks_list
        mock_db.query.return_value = mock_query

        tasks, total = station_task_crud.get_all(mock_db)
        assert len(tasks) == 3
        assert total == 3

    def test_update_station_task_status(
        self, mock_db: Mock, station: Station, sim_instance: SimInstance
    ) -> None:
        from back.models import StationTask

        created_task = StationTask(
            id=1,
            type=StationTaskType.BATTERY_SWAP,
            station_id=station.id,
            sim_instance_id=sim_instance.id,
            status=TaskStatus.OPEN,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = created_task
        mock_db.query.return_value = mock_query

        # Mock context manager
        mock_db.begin.return_value.__enter__ = Mock()
        mock_db.begin.return_value.__exit__ = Mock()

        update_data = StationTaskUpdate(status=TaskStatus.CLOSED)
        updated_task = station_task_crud.update(mock_db, created_task.id, update_data)
        assert updated_task is not None
        assert updated_task.id == created_task.id
        assert updated_task.status == TaskStatus.CLOSED

    def test_update_station_task_status_not_found(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Mock context manager
        mock_db.begin.return_value.__enter__ = Mock()
        mock_db.begin.return_value.__exit__ = Mock()

        update_data = StationTaskUpdate(status=TaskStatus.CLOSED)
        updated_task = station_task_crud.update(mock_db, 99999, update_data)
        assert updated_task is None

    def test_delete_station_task(
        self, mock_db: Mock, station: Station, sim_instance: SimInstance
    ) -> None:
        from back.models import StationTask

        created_task = StationTask(
            id=1,
            type=StationTaskType.BATTERY_SWAP,
            station_id=station.id,
            sim_instance_id=sim_instance.id,
            status=TaskStatus.OPEN,
        )

        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [created_task, None]
        mock_db.query.return_value = mock_query

        # Mock context manager
        mock_db.begin.return_value.__enter__ = Mock()
        mock_db.begin.return_value.__exit__ = Mock()

        success = station_task_crud.delete(mock_db, created_task.id)
        assert success is True
        retrieved_task = station_task_crud.get(mock_db, created_task.id)
        assert retrieved_task is None

    def test_delete_station_task_not_found(self, mock_db: Mock) -> None:
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Mock context manager
        mock_db.begin.return_value.__enter__ = Mock()
        mock_db.begin.return_value.__exit__ = Mock()

        success = station_task_crud.delete(mock_db, 99999)
        assert success is False
