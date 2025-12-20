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

"""Deprecated resource tests placeholder.

This file intentionally keeps no active tests to avoid confusion
after refactoring to Driver/Vehicle. Imports removed for flake8.
"""


class TestResource:
    pass
    # @pytest.fixture
    # def default_position(self) -> Position:
    #     return Position([-73.5673, 45.5017])

    # @pytest.fixture
    # def simpy_env(self) -> simpy.Environment:
    #     return simpy.Environment()

    # @pytest.fixture
    # def resource(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> Resource:
    #     return Resource(1, default_position)

    # @pytest.fixture
    # def resource_with_tasks(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> Resource:
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     return Resource(2, default_position, [task, task2, task3])

    # def test_resource_initialization(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     resource = Resource(1, default_position)

    #     assert resource.id == 1
    #     assert resource.position == default_position
    #     assert resource.task_list == []
    #     assert resource.has_updated == False

    # def test_resource_initialization_with_task_list(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task_list: list[Task] = [task, task2, task3]
    #     resource = Resource(2, default_position, task_list)

    #     assert resource.id == 2
    #     assert resource.position == default_position
    #     assert resource.task_list == task_list
    #     assert resource.has_updated == False

    # def test_get_resource_position(
    #     self, resource: Resource, default_position: Position
    # ) -> None:
    #     position = resource.get_resource_position()
    #     assert position == default_position
    #     assert position.get_position() == [-73.5673, 45.5017]

    # def test_set_resource_position(self, resource: Resource) -> None:
    #     new_position = Position([-74.0000, 40.5017])
    #     resource.set_resource_position(new_position)

    #     assert resource.get_resource_position() == new_position
    #     assert resource.position.get_position() == [-74.0000, 40.5017]

    # def test_assign_task(
    #     self, simpy_env: simpy.Environment, resource: Resource
    # ) -> None:
    #     initial_count = resource.get_task_count()
    #     task = BatterySwapTask(1)

    #     resource.assign_task(task)

    #     assert resource.get_task_count() == initial_count + 1
    #     assert task in resource.get_task_list()

    # def test_assign_multiple_tasks(
    #     self, simpy_env: simpy.Environment, resource: Resource
    # ) -> None:
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task_list = [task, task2, task3]
    #     initial_count = resource.get_task_count()

    #     for task_id in task_list:
    #         resource.assign_task(task_id)

    #     assert resource.get_task_count() == initial_count + len(task_list)
    #     for task_id in task_list:
    #         assert task_id in resource.get_task_list()

    # def test_unassign_existing_task(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(2, default_position, [task, task2, task3])
    #     initial_count = resource.get_task_count()
    #     task_to_remove = task2

    #     assert task_to_remove in resource.get_task_list()

    #     resource.unassign_task(task_to_remove)

    #     assert resource.get_task_count() == initial_count - 1
    #     assert task_to_remove not in resource.get_task_list()

    # def test_unassign_nonexistent_task(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(2, default_position, [task, task2, task3])
    #     initial_count = resource.get_task_count()
    #     initial_tasks = resource.get_task_list().copy()
    #     nonexistent_task = BatterySwapTask(4)

    #     assert nonexistent_task not in resource.get_task_list()

    #     resource.unassign_task(nonexistent_task)

    #     # should stay unchanged
    #     assert resource.get_task_count() == initial_count
    #     assert resource.get_task_list() == initial_tasks

    # def test_get_in_progress_task(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     # Arrange
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(2, default_position, [task, task2, task3])
    #     task2.set_state(State.IN_PROGRESS)

    #     # Act
    #     dispatched_task = resource.get_in_progress_task()

    #     # Assert
    #     assert isinstance(dispatched_task, BatterySwapTask)
    #     assert dispatched_task == task2

    # def test_get_in_progress_task_not_found(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     # Arrange
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(2, default_position, [task, task2, task3])

    #     # Act
    #     dispatched_task = resource.get_in_progress_task()

    #     # Assert
    #     assert dispatched_task is None

    # def test_dispatch_task_with_no_other_dispatched(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     # Arrange
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(2, default_position, [task, task2, task3])

    #     # Act
    #     resource.dispatch_task(task2)

    #     # Assert
    #     assert task2.get_state() == State.IN_PROGRESS

    # def test_dispatch_task_with_other_dispatched_same_station(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     # Arrange
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     station = Station(1, "Test Station", default_position)
    #     resource = Resource(2, default_position, [task, task2, task3])
    #     task.set_state(State.IN_PROGRESS)
    #     task.set_station(station)
    #     task2.set_station(station)

    #     # Act
    #     resource.dispatch_task(task2)

    #     # Assert
    #     assert task2.get_state() == State.IN_PROGRESS

    # def test_dispatch_task_with_other_dispatched_diff_station(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     # Arrange
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     station = Station(1, "Test Station", default_position)
    #     station2 = Station(2, "Other Station", default_position)
    #     resource = Resource(2, default_position, [task, task2, task3])
    #     task.set_state(State.IN_PROGRESS)
    #     task.set_station(station)
    #     task2.set_station(station2)

    #     # Act and Assert
    #     with pytest.raises(Exception, match="Cannot dispatch task at this station"):
    #         resource.dispatch_task(task2)

    # def test_service_task(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(2, default_position, [task, task2, task3])
    #     initial_count = resource.get_task_count()
    #     task_to_service = task2

    #     assert task_to_service in resource.get_task_list()

    #     resource.service_task(task_to_service)

    #     assert resource.get_task_count() == initial_count - 1
    #     assert task_to_service not in resource.get_task_list()

    # def test_service_nonexistent_task(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(2, default_position, [task, task2, task3])
    #     initial_count = resource.get_task_count()
    #     initial_tasks = resource.get_task_list().copy()
    #     nonexistent_task = BatterySwapTask(4)

    #     assert nonexistent_task not in resource.get_task_list()

    #     resource.service_task(nonexistent_task)

    #     # should stay unchanged
    #     assert resource.get_task_count() == initial_count
    #     assert resource.get_task_list() == initial_tasks

    # def test_get_task_count_empty(self, resource: Resource) -> None:
    #     assert resource.get_task_count() == 0

    # def test_get_task_count(self, resource_with_tasks: Resource) -> None:
    #     assert resource_with_tasks.get_task_count() == 3

    # def test_get_task_list_empty(self, resource: Resource) -> None:
    #     task_list = resource.get_task_list()
    #     assert task_list == []
    #     assert isinstance(task_list, list)

    # def test_get_task_list_with_tasks(self, resource_with_tasks: Resource) -> None:
    #     task_list = resource_with_tasks.get_task_list()
    #     assert isinstance(task_list, list)

    # def test_task_list_modifications(
    #     self, simpy_env: simpy.Environment, resource: Resource
    # ) -> None:
    #     # start with empty list
    #     assert resource.get_task_count() == 0

    #     # add some tasks
    #     task = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource.assign_task(task)
    #     resource.assign_task(task2)
    #     resource.assign_task(task3)
    #     assert resource.get_task_count() == 3
    #     assert set(resource.get_task_list()) == {task, task2, task3}

    #     # service a task
    #     resource.service_task(task2)
    #     assert resource.get_task_count() == 2
    #     assert task2 not in resource.get_task_list()
    #     assert set(resource.get_task_list()) == {task, task3}

    #     # unassign a task
    #     resource.unassign_task(task)
    #     assert resource.get_task_count() == 1
    #     assert resource.get_task_list() == [task3]

    # def test_clear_update(self, resource: Resource) -> None:
    #     assert resource.has_updated == False

    #     resource.has_updated = True
    #     assert resource.has_updated == True

    #     resource.clear_update()
    #     assert resource.has_updated == False

    # # Tests for reorder_tasks

    # def test_reorder_tasks_empty_list_raises_error(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test that empty task_ids list raises ValueError."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     resource = Resource(1, default_position, [task1, task2])

    #     with pytest.raises(ValueError, match="task_ids_to_reorder cannot be empty"):
    #         resource.reorder_tasks([], apply_from_top=True)

    # def test_reorder_tasks_duplicate_ids_raises_error(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test that duplicate task IDs raise ValueError."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     resource = Resource(1, default_position, [task1, task2, task3])

    #     with pytest.raises(ValueError, match="contains duplicate task IDs"):
    #         resource.reorder_tasks([1, 2, 1], apply_from_top=True)

    # def test_reorder_tasks_top_mode_basic(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test basic top mode reordering without in-progress tasks."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task4 = BatterySwapTask(4)
    #     resource = Resource(1, default_position, [task1, task2, task3, task4])

    #     # Reorder: want [3, 1] at top, then [2, 4] unspecified
    #     new_order = resource.reorder_tasks([3, 1], apply_from_top=True)

    #     assert new_order == [3, 1, 2, 4]
    #     assert resource.task_list == [task3, task1, task2, task4]
    #     assert resource.has_updated == True

    # def test_reorder_tasks_bottom_mode_basic(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test basic bottom mode reordering (reversed at end)."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task4 = BatterySwapTask(4)
    #     resource = Resource(1, default_position, [task1, task2, task3, task4])

    #     # Reorder: unspecified [2, 4], then reversed([3, 1]) = [1, 3]
    #     new_order = resource.reorder_tasks([3, 1], apply_from_top=False)

    #     assert new_order == [2, 4, 1, 3]
    #     assert resource.task_list == [task2, task4, task1, task3]
    #     assert resource.has_updated == True

    # def test_reorder_tasks_with_in_progress_pinned_to_top(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test that IN_PROGRESS tasks are always pinned to top."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task4 = BatterySwapTask(4)
    #     task5 = BatterySwapTask(5)

    #     resource = Resource(1, default_position, [task1, task2, task3, task4, task5])

    #     # Set task2 and task4 as IN_PROGRESS (after Resource creation)
    #     task2.set_state(State.IN_PROGRESS)
    #     task4.set_state(State.IN_PROGRESS)

    #     # Reorder with top mode: [5, 3, 1]
    #     # Original: [1, 2*, 3, 4*, 5] (* = in-progress)
    #     # Expected: [2*, 4*] (in-progress, original order),
    #     #           [5, 3, 1] (specified), [] (unspecified)
    #     new_order = resource.reorder_tasks([5, 3, 1], apply_from_top=True)

    #     assert new_order == [2, 4, 5, 3, 1]
    #     assert resource.task_list == [task2, task4, task5, task3, task1]

    # def test_reorder_tasks_with_in_progress_in_specified_list(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test that if a specified task is IN_PROGRESS, it stays at top."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task4 = BatterySwapTask(4)

    #     resource = Resource(1, default_position, [task1, task2, task3, task4])

    #     # Set task2 as IN_PROGRESS (after Resource creation)
    #     task2.set_state(State.IN_PROGRESS)

    #     # Try to reorder including task2 (which is in-progress)
    #     # Original: [1, 2*, 3, 4] (* = in-progress)
    #     # Specified: [4, 2, 1], but 2 is in-progress so excluded from specified
    #     # Expected: [2*] (in-progress), [4, 1] (specified), [3] (unspecified)
    #     new_order = resource.reorder_tasks([4, 2, 1], apply_from_top=True)

    #     assert new_order == [2, 4, 1, 3]
    #     assert resource.task_list == [task2, task4, task1, task3]

    # def test_reorder_tasks_bottom_mode_with_in_progress(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test bottom mode with in-progress tasks pinned."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task4 = BatterySwapTask(4)
    #     task5 = BatterySwapTask(5)

    #     resource = Resource(1, default_position, [task1, task2, task3, task4, task5])

    #     # Set task2 as IN_PROGRESS (after Resource creation)
    #     task2.set_state(State.IN_PROGRESS)

    #     # Bottom mode: [5, 3]
    #     # Original: [1, 2*, 3, 4, 5] (* = in-progress)
    #     # Expected: [2*] (in-progress), [1, 4] (unspecified, original order),
    #     #           reversed([5, 3]) = [3, 5]
    #     new_order = resource.reorder_tasks([5, 3], apply_from_top=False)

    #     assert new_order == [2, 1, 4, 3, 5]
    #     assert resource.task_list == [task2, task1, task4, task3, task5]

    # def test_reorder_tasks_invalid_task_ids_ignored_with_warning(
    #     self, simpy_env: simpy.Environment, default_position: Position, caplog: Any
    # ) -> None:
    #     """Test that invalid task IDs are ignored and warning logged."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)

    #     resource = Resource(1, default_position, [task1, task2, task3])

    #     # Include invalid task ID 99
    #     new_order = resource.reorder_tasks([3, 99, 1], apply_from_top=True)

    #     # Task 99 should be ignored
    #     assert new_order == [3, 1, 2]
    #     assert resource.task_list == [task3, task1, task2]

    #     # Check warning was logged
    #     assert "Task 99 not in resource 1 task list" in caplog.text

    # def test_reorder_tasks_all_tasks_specified(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test reordering when all tasks are specified."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)

    #     resource = Resource(1, default_position, [task1, task2, task3])

    #     # Specify all tasks in reverse order
    #     new_order = resource.reorder_tasks([3, 2, 1], apply_from_top=True)

    #     assert new_order == [3, 2, 1]
    #     assert resource.task_list == [task3, task2, task1]

    # def test_reorder_tasks_partial_list_resilience(
    #     self, simpy_env: simpy.Environment, default_position: Position
    # ) -> None:
    #     """Test that partial list handles tasks gracefully."""
    #     task1 = BatterySwapTask(1)
    #     task2 = BatterySwapTask(2)
    #     task3 = BatterySwapTask(3)
    #     task4 = BatterySwapTask(4)

    #     resource = Resource(1, default_position, [task1, task2, task3, task4])

    #     # Only reorder 2 tasks, others should maintain order
    #     new_order = resource.reorder_tasks([4, 2], apply_from_top=True)

    #     # Expected: [4, 2] (specified), [1, 3] (unspecified in original order)
    #     assert new_order == [4, 2, 1, 3]
    #     assert resource.task_list == [task4, task2, task1, task3]
