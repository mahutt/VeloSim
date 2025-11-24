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
import simpy
from sim.entities.resource import Resource
from sim.entities.position import Position
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.task import Task, State
from sim.entities.station import Station


class TestResource:
    @pytest.fixture
    def default_position(self) -> Position:
        return Position([-73.5673, 45.5017])

    @pytest.fixture
    def simpy_env(self) -> simpy.Environment:
        return simpy.Environment()

    @pytest.fixture
    def resource(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> Resource:
        return Resource(1, default_position)

    @pytest.fixture
    def resource_with_tasks(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> Resource:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        return Resource(2, default_position, [task, task2, task3])

    def test_resource_initialization(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        resource = Resource(1, default_position)

        assert resource.id == 1
        assert resource.position == default_position
        assert resource.task_list == []
        assert resource.has_updated == False

    def test_resource_initialization_with_task_list(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task_list: list[Task] = [task, task2, task3]
        resource = Resource(2, default_position, task_list)

        assert resource.id == 2
        assert resource.position == default_position
        assert resource.task_list == task_list
        assert resource.has_updated == False

    def test_get_resource_position(
        self, resource: Resource, default_position: Position
    ) -> None:
        position = resource.get_resource_position()
        assert position == default_position
        assert position.get_position() == [-73.5673, 45.5017]

    def test_set_resource_position(self, resource: Resource) -> None:
        new_position = Position([-74.0000, 40.5017])
        resource.set_resource_position(new_position)

        assert resource.get_resource_position() == new_position
        assert resource.position.get_position() == [-74.0000, 40.5017]

    def test_assign_task(
        self, simpy_env: simpy.Environment, resource: Resource
    ) -> None:
        initial_count = resource.get_task_count()
        task = BatterySwapTask(1)

        resource.assign_task(task)

        assert resource.get_task_count() == initial_count + 1
        assert task in resource.get_task_list()

    def test_assign_multiple_tasks(
        self, simpy_env: simpy.Environment, resource: Resource
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task_list = [task, task2, task3]
        initial_count = resource.get_task_count()

        for task_id in task_list:
            resource.assign_task(task_id)

        assert resource.get_task_count() == initial_count + len(task_list)
        for task_id in task_list:
            assert task_id in resource.get_task_list()

    def test_unassign_existing_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource = Resource(2, default_position, [task, task2, task3])
        initial_count = resource.get_task_count()
        task_to_remove = task2

        assert task_to_remove in resource.get_task_list()

        resource.unassign_task(task_to_remove)

        assert resource.get_task_count() == initial_count - 1
        assert task_to_remove not in resource.get_task_list()

    def test_unassign_nonexistent_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource = Resource(2, default_position, [task, task2, task3])
        initial_count = resource.get_task_count()
        initial_tasks = resource.get_task_list().copy()
        nonexistent_task = BatterySwapTask(4)

        assert nonexistent_task not in resource.get_task_list()

        resource.unassign_task(nonexistent_task)

        # should stay unchanged
        assert resource.get_task_count() == initial_count
        assert resource.get_task_list() == initial_tasks

    def test_get_in_progress_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Arrange
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource = Resource(2, default_position, [task, task2, task3])
        task2.set_state(State.IN_PROGRESS)

        # Act
        dispatched_task = resource.get_in_progress_task()

        # Assert
        assert isinstance(dispatched_task, BatterySwapTask)
        assert dispatched_task == task2

    def test_get_in_progress_task_not_found(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Arrange
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource = Resource(2, default_position, [task, task2, task3])

        # Act
        dispatched_task = resource.get_in_progress_task()

        # Assert
        assert dispatched_task is None

    def test_dispatch_task_with_no_other_dispatched(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Arrange
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource = Resource(2, default_position, [task, task2, task3])

        # Act
        resource.dispatch_task(task2)

        # Assert
        assert task2.get_state() == State.IN_PROGRESS

    def test_dispatch_task_with_other_dispatched_same_station(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Arrange
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        station = Station(1, "Test Station", default_position)
        resource = Resource(2, default_position, [task, task2, task3])
        task.set_state(State.IN_PROGRESS)
        task.set_station(station)
        task2.set_station(station)

        # Act
        resource.dispatch_task(task2)

        # Assert
        assert task2.get_state() == State.IN_PROGRESS

    def test_dispatch_task_with_other_dispatched_diff_station(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Arrange
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        station = Station(1, "Test Station", default_position)
        station2 = Station(2, "Other Station", default_position)
        resource = Resource(2, default_position, [task, task2, task3])
        task.set_state(State.IN_PROGRESS)
        task.set_station(station)
        task2.set_station(station2)

        # Act and Assert
        with pytest.raises(Exception, match="Cannot dispatch task at this station"):
            resource.dispatch_task(task2)

    def test_service_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource = Resource(2, default_position, [task, task2, task3])
        initial_count = resource.get_task_count()
        task_to_service = task2

        assert task_to_service in resource.get_task_list()

        resource.service_task(task_to_service)

        assert resource.get_task_count() == initial_count - 1
        assert task_to_service not in resource.get_task_list()

    def test_service_nonexistent_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource = Resource(2, default_position, [task, task2, task3])
        initial_count = resource.get_task_count()
        initial_tasks = resource.get_task_list().copy()
        nonexistent_task = BatterySwapTask(4)

        assert nonexistent_task not in resource.get_task_list()

        resource.service_task(nonexistent_task)

        # should stay unchanged
        assert resource.get_task_count() == initial_count
        assert resource.get_task_list() == initial_tasks

    def test_get_task_count_empty(self, resource: Resource) -> None:
        assert resource.get_task_count() == 0

    def test_get_task_count(self, resource_with_tasks: Resource) -> None:
        assert resource_with_tasks.get_task_count() == 3

    def test_get_task_list_empty(self, resource: Resource) -> None:
        task_list = resource.get_task_list()
        assert task_list == []
        assert isinstance(task_list, list)

    def test_get_task_list_with_tasks(self, resource_with_tasks: Resource) -> None:
        task_list = resource_with_tasks.get_task_list()
        assert isinstance(task_list, list)

    def test_task_list_modifications(
        self, simpy_env: simpy.Environment, resource: Resource
    ) -> None:
        # start with empty list
        assert resource.get_task_count() == 0

        # add some tasks
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        resource.assign_task(task)
        resource.assign_task(task2)
        resource.assign_task(task3)
        assert resource.get_task_count() == 3
        assert set(resource.get_task_list()) == {task, task2, task3}

        # service a task
        resource.service_task(task2)
        assert resource.get_task_count() == 2
        assert task2 not in resource.get_task_list()
        assert set(resource.get_task_list()) == {task, task3}

        # unassign a task
        resource.unassign_task(task)
        assert resource.get_task_count() == 1
        assert resource.get_task_list() == [task3]

    def test_clear_update(self, resource: Resource) -> None:
        assert resource.has_updated == False

        resource.has_updated = True
        assert resource.has_updated == True

        resource.clear_update()
        assert resource.has_updated == False
