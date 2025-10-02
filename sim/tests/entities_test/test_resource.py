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
        return Resource(simpy_env, 1, default_position)

    @pytest.fixture
    def resource_with_tasks(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> Resource:
        return Resource(simpy_env, 2, default_position, [101, 102, 103])

    def test_resource_initialization(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        resource = Resource(simpy_env, 1, default_position)

        assert resource.env == simpy_env
        assert resource.id == 1
        assert resource.position == default_position
        assert resource.task_list == []
        assert resource.action is not None

    def test_resource_initialization_with_task_list(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task_list = [101, 102, 103]
        resource = Resource(simpy_env, 2, default_position, task_list)

        assert resource.env == simpy_env
        assert resource.id == 2
        assert resource.position == default_position
        assert resource.task_list == task_list
        assert resource.action is not None

    def test_get_resource_position(
        self, resource: Resource, default_position: Position
    ) -> None:
        position = resource.get_resource_position()
        assert position == default_position
        assert position.getPosition() == [-73.5673, 45.5017]

    def test_set_resource_position(self, resource: Resource) -> None:
        new_position = Position([-74.0000, 40.5017])
        resource.set_resource_position(new_position)

        assert resource.get_resource_position() == new_position
        assert resource.position.getPosition() == [-74.0000, 40.5017]

    def test_assign_task(self, resource: Resource) -> None:
        initial_count = resource.get_task_count()
        task_id = 201

        resource.assign_task(task_id)

        assert resource.get_task_count() == initial_count + 1
        assert task_id in resource.get_task_list()

    def test_assign_multiple_tasks(self, resource: Resource) -> None:
        task_ids = [301, 302, 303]
        initial_count = resource.get_task_count()

        for task_id in task_ids:
            resource.assign_task(task_id)

        assert resource.get_task_count() == initial_count + len(task_ids)
        for task_id in task_ids:
            assert task_id in resource.get_task_list()

    def test_unassign_existing_task(self, resource_with_tasks: Resource) -> None:
        initial_count = resource_with_tasks.get_task_count()
        task_to_remove = 102

        assert task_to_remove in resource_with_tasks.get_task_list()

        resource_with_tasks.unassign_task(task_to_remove)

        assert resource_with_tasks.get_task_count() == initial_count - 1
        assert task_to_remove not in resource_with_tasks.get_task_list()

    def test_unassign_nonexistent_task(self, resource_with_tasks: Resource) -> None:
        initial_count = resource_with_tasks.get_task_count()
        initial_tasks = resource_with_tasks.get_task_list().copy()
        nonexistent_task = 999

        assert nonexistent_task not in resource_with_tasks.get_task_list()

        resource_with_tasks.unassign_task(nonexistent_task)

        # should stay unchanged
        assert resource_with_tasks.get_task_count() == initial_count
        assert resource_with_tasks.get_task_list() == initial_tasks

    def test_service_task(self, resource_with_tasks: Resource) -> None:
        initial_count = resource_with_tasks.get_task_count()
        task_to_service = 101

        assert task_to_service in resource_with_tasks.get_task_list()

        resource_with_tasks.service_task(task_to_service)

        assert resource_with_tasks.get_task_count() == initial_count - 1
        assert task_to_service not in resource_with_tasks.get_task_list()

    def test_service_nonexistent_task(self, resource_with_tasks: Resource) -> None:
        initial_count = resource_with_tasks.get_task_count()
        initial_tasks = resource_with_tasks.get_task_list().copy()
        nonexistent_task = 999

        assert nonexistent_task not in resource_with_tasks.get_task_list()

        resource_with_tasks.service_task(nonexistent_task)

        # should stay unchanged
        assert resource_with_tasks.get_task_count() == initial_count
        assert resource_with_tasks.get_task_list() == initial_tasks

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
        assert task_list == [101, 102, 103]
        assert isinstance(task_list, list)

    def test_task_list_modifications(self, resource: Resource) -> None:
        # start with empty list
        assert resource.get_task_count() == 0

        # add some tasks
        resource.assign_task(401)
        resource.assign_task(402)
        resource.assign_task(403)
        assert resource.get_task_count() == 3
        assert set(resource.get_task_list()) == {401, 402, 403}

        # service a task
        resource.service_task(402)
        assert resource.get_task_count() == 2
        assert 402 not in resource.get_task_list()
        assert set(resource.get_task_list()) == {401, 403}

        # unassign a task
        resource.unassign_task(401)
        assert resource.get_task_count() == 1
        assert resource.get_task_list() == [403]
