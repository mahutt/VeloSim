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
from back.crud.station import station_crud
from back.crud.station_task import station_task_crud
from back.schemas import StationCreate, StationTaskCreate, StationTaskUpdate
from back.models import Station, StationTaskType, TaskStatus


@pytest.fixture
def station(db: Session) -> Station:
    station_data = StationCreate(name="Test Station", longitude=0.0, latitude=0.0)
    station = station_crud.create(db, station_data)
    return station


class TestStationTaskCRUD:
    def test_create_station_task(self, db: Session, station: Station) -> None:
        task_data = StationTaskCreate(
            type=StationTaskType.BATTERY_SWAP, station_id=station.id
        )
        task = station_task_crud.create(db, task_data)
        assert task.id is not None
        assert task.type == StationTaskType.BATTERY_SWAP
        assert task.station_id == station.id
        assert task.status == TaskStatus.UNASSIGNED

    def test_get_station_task_by_id(self, db: Session, station: Station) -> None:
        task_data = StationTaskCreate(
            type=StationTaskType.BATTERY_SWAP, station_id=station.id
        )
        created_task = station_task_crud.create(db, task_data)
        retrieved_task = station_task_crud.get(db, created_task.id)
        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.type == StationTaskType.BATTERY_SWAP

    def test_get_station_task_by_id_not_found(self, db: Session) -> None:
        task = station_task_crud.get(db, 99999)
        assert task is None

    def test_get_all_station_tasks_empty(self, db: Session) -> None:
        tasks, total = station_task_crud.get_all(db)
        assert tasks == []
        assert total == 0

    def test_get_all_station_tasks_with_data(
        self, db: Session, station: Station
    ) -> None:
        for _ in range(3):
            task_data = StationTaskCreate(
                type=StationTaskType.BATTERY_SWAP, station_id=station.id
            )
            station_task_crud.create(db, task_data)
        tasks, total = station_task_crud.get_all(db)
        assert len(tasks) == 3
        assert total == 3

    def test_update_station_task_status(self, db: Session, station: Station) -> None:
        task_data = StationTaskCreate(
            type=StationTaskType.BATTERY_SWAP, station_id=station.id
        )
        created_task = station_task_crud.create(db, task_data)
        update_data = StationTaskUpdate(status=TaskStatus.COMPLETED)
        updated_task = station_task_crud.update(db, created_task.id, update_data)
        assert updated_task is not None
        assert updated_task.id == created_task.id
        assert updated_task.status == TaskStatus.COMPLETED

    def test_update_station_task_status_not_found(self, db: Session) -> None:
        update_data = StationTaskUpdate(status=TaskStatus.COMPLETED)
        updated_task = station_task_crud.update(db, 99999, update_data)
        assert updated_task is None

    def test_delete_station_task(self, db: Session, station: Station) -> None:
        task_data = StationTaskCreate(
            type=StationTaskType.BATTERY_SWAP, station_id=station.id
        )
        created_task = station_task_crud.create(db, task_data)
        success = station_task_crud.delete(db, created_task.id)
        assert success is True
        retrieved_task = station_task_crud.get(db, created_task.id)
        assert retrieved_task is None

    def test_delete_station_task_not_found(self, db: Session) -> None:
        success = station_task_crud.delete(db, 99999)
        assert success is False
