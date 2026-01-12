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
from typing import Any
from unittest.mock import patch, MagicMock

from sim.entities.driver import Driver, DriverState
from sim.entities.position import Position
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.task import Task, State
from sim.entities.station import Station
from sim.entities.vehicle import Vehicle
from sim.entities.shift import Shift


class TestDriver:
    @pytest.fixture
    def default_position(self) -> Position:
        return Position([-73.5673, 45.5017])

    @pytest.fixture
    def simpy_env(self) -> simpy.Environment:
        env = simpy.Environment()
        # Ensure Driver has an env before any instantiation
        from sim.entities.driver import Driver

        Driver.env = env
        return env

    # Default shift used across tests
    DEFAULT_SHIFT = Shift(0.0, 24.0, None, 0.0, 24.0, None)

    @pytest.fixture
    def driver(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> Driver:
        return Driver(1, default_position, self.DEFAULT_SHIFT)

    @pytest.fixture
    def driver_with_tasks(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> Driver:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        return Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])

    def test_driver_initialization(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Ensure Driver.env is set before instantiation
        from sim.entities.driver import Driver

        Driver.env = simpy_env
        driver = Driver(1, default_position, self.DEFAULT_SHIFT)

        assert driver.id == 1
        assert driver.position == default_position
        assert driver.task_list == []
        assert driver.has_updated == False

    def test_driver_initialization_with_task_list(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        from sim.entities.driver import Driver

        Driver.env = simpy_env
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task_list: list[Task] = [task, task2, task3]
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, task_list)

        assert driver.id == 2
        assert driver.position == default_position
        assert driver.task_list == task_list
        assert driver.has_updated == False

    def test_get_position(self, driver: Driver, default_position: Position) -> None:
        position = driver.get_position()
        assert position == default_position
        assert position.get_position() == [-73.5673, 45.5017]

    def test_set_position(self, driver: Driver) -> None:
        new_position = Position([-74.0000, 40.5017])
        driver.set_position(new_position)

        assert driver.get_position() == new_position
        assert driver.position.get_position() == [-74.0000, 40.5017]

    def test_get_state(self, driver: Driver) -> None:
        driver.state = DriverState.IDLE
        assert driver.get_state() == DriverState.IDLE

    def test_assign_task(self, simpy_env: simpy.Environment, driver: Driver) -> None:
        initial_count = driver.get_task_count()
        task = BatterySwapTask(1)

        driver.assign_task(task)

        assert driver.get_task_count() == initial_count + 1
        assert task in driver.get_task_list()

    def test_assign_multiple_tasks(
        self, simpy_env: simpy.Environment, driver: Driver
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task_list = [task, task2, task3]
        initial_count = driver.get_task_count()

        for t in task_list:
            driver.assign_task(t)

        assert driver.get_task_count() == initial_count + len(task_list)
        for t in task_list:
            assert t in driver.get_task_list()

    def test_unassign_existing_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])
        initial_count = driver.get_task_count()
        task_to_remove = task2

        assert task_to_remove in driver.get_task_list()

        driver.unassign_task(task_to_remove)

        assert driver.get_task_count() == initial_count - 1
        assert task_to_remove not in driver.get_task_list()

    def test_unassign_nonexistent_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])
        initial_count = driver.get_task_count()
        initial_tasks = driver.get_task_list().copy()
        nonexistent_task = BatterySwapTask(4)

        assert nonexistent_task not in driver.get_task_list()

        driver.unassign_task(nonexistent_task)

        # should stay unchanged
        assert driver.get_task_count() == initial_count
        assert driver.get_task_list() == initial_tasks

    def test_get_in_progress_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Arrange
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])
        task2.set_state(State.IN_PROGRESS)

        # Act
        dispatched_task = driver.get_in_progress_task()

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
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])

        # Act
        dispatched_task = driver.get_in_progress_task()

        # Assert
        assert dispatched_task is None

    def test_dispatch_task_with_no_other_dispatched(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        # Arrange
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])

        # Act
        driver.dispatch_task(task2)

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
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])
        task.set_state(State.IN_PROGRESS)
        task.set_station(station)
        task2.set_station(station)

        # Act
        driver.dispatch_task(task2)

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
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])
        task.set_state(State.IN_PROGRESS)
        task.set_station(station)
        task2.set_station(station2)

        # Act and Assert
        with pytest.raises(Exception, match="Cannot dispatch task at this station"):
            driver.dispatch_task(task2)

    def test_service_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])
        vehicle = Vehicle(vehicle_id=1, battery_count=10)
        vehicle.set_driver(driver)
        driver.set_vehicle(vehicle)
        initial_count = driver.get_task_count()
        task_to_service = task2

        assert task_to_service in driver.get_task_list()

        driver.service_task(task_to_service)

        assert vehicle.get_battery_count() == 9
        assert driver.get_task_count() == initial_count - 1
        assert task_to_service not in driver.get_task_list()

    def test_service_nonexistent_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2, task3])
        initial_count = driver.get_task_count()
        initial_tasks = driver.get_task_list().copy()
        nonexistent_task = BatterySwapTask(4)

        assert nonexistent_task not in driver.get_task_list()

        driver.service_task(nonexistent_task)

        # should stay unchanged
        assert driver.get_task_count() == initial_count
        assert driver.get_task_list() == initial_tasks

    def test_service_task_with_one_battery(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2])
        driver.env = simpy_env
        vehicle = Vehicle(vehicle_id=1, battery_count=1)
        vehicle.set_driver(driver)
        driver.set_vehicle(vehicle)

        with patch.object(Driver, "return_to_HQ") as mock_hq:
            driver.service_task(task2)
            mock_hq.assert_called_once()
            assert vehicle.battery_count == 0

    def test_restock_vehicle_battery_full_restock(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        driver = Driver(2, default_position, self.DEFAULT_SHIFT, [task, task2])
        driver.env = simpy_env
        mock_vehicle = MagicMock()
        mock_vehicle.vehicle_id = 1
        mock_vehicle.get_battery_count.return_value = 2
        mock_vehicle.max_battery_count = 10
        mock_vehicle.set_driver(driver)
        driver.vehicle = mock_vehicle
        driver.state = DriverState.RESTOCKING_BATTERIES

        expected_duration = (1200 / 10) * 8
        start_time = simpy_env.now

        simpy_env.process(driver.restock_vehicle_battery())
        simpy_env.run()

        assert simpy_env.now == start_time + expected_duration
        assert mock_vehicle.add_battery.call_count == 8

    def test_get_task_count_empty(self, driver: Driver) -> None:
        assert driver.get_task_count() == 0

    def test_get_task_count(self, driver_with_tasks: Driver) -> None:
        assert driver_with_tasks.get_task_count() == 3

    def test_get_task_list_empty(self, driver: Driver) -> None:
        task_list = driver.get_task_list()
        assert task_list == []
        assert isinstance(task_list, list)

    def test_get_task_list_with_tasks(self, driver_with_tasks: Driver) -> None:
        task_list = driver_with_tasks.get_task_list()
        assert isinstance(task_list, list)

    def test_task_list_modifications(
        self, simpy_env: simpy.Environment, driver: Driver
    ) -> None:
        # associate vehicle to driver
        vehicle = Vehicle(vehicle_id=1, battery_count=10)
        vehicle.set_driver(driver)
        driver.set_vehicle(vehicle)

        # start with empty list
        assert driver.get_task_count() == 0

        # add some tasks
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver.assign_task(task)
        driver.assign_task(task2)
        driver.assign_task(task3)
        assert driver.get_task_count() == 3
        assert set(driver.get_task_list()) == {task, task2, task3}

        # service a task
        driver.service_task(task2)
        assert driver.get_task_count() == 2
        assert vehicle.get_battery_count() == 9
        assert task2 not in driver.get_task_list()
        assert set(driver.get_task_list()) == {task, task3}

        # unassign a task
        driver.unassign_task(task)
        assert driver.get_task_count() == 1
        assert driver.get_task_list() == [task3]

    def test_clear_update(self, driver: Driver) -> None:
        assert driver.has_updated == False

        driver.has_updated = True
        assert driver.has_updated == True

        driver.clear_update()
        assert driver.has_updated == False

    # Tests for reorder_tasks

    def test_reorder_tasks_empty_list_raises_error(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test that empty task_ids list raises ValueError."""
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        driver = Driver(1, default_position, self.DEFAULT_SHIFT, [task1, task2])

        with pytest.raises(ValueError, match="task_ids_to_reorder cannot be empty"):
            driver.reorder_tasks([], apply_from_top=True)

    def test_reorder_tasks_duplicate_ids_raises_error(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test that duplicate task IDs raise ValueError."""
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3])

        with pytest.raises(ValueError, match="contains duplicate task IDs"):
            driver.reorder_tasks([1, 2, 2], apply_from_top=True)

    def test_reorder_tasks_top_mode_basic(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test basic top mode reordering without in-progress tasks."""
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)
        driver = Driver(
            1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3, task4]
        )

        # Reorder: want [3, 1] at top, then [2, 4] unspecified
        new_order = driver.reorder_tasks([3, 1], apply_from_top=True)

        assert new_order == [3, 1, 2, 4]
        assert driver.task_list == [task3, task1, task2, task4]
        assert driver.has_updated == True

    def test_reorder_tasks_bottom_mode_basic(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test basic bottom mode reordering (reversed at end)."""
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)
        driver = Driver(
            1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3, task4]
        )

        # Reorder: unspecified [2, 4], then reversed([3, 1]) = [1, 3]
        new_order = driver.reorder_tasks([3, 1], apply_from_top=False)

        assert new_order == [2, 4, 1, 3]
        assert driver.task_list == [task2, task4, task1, task3]
        assert driver.has_updated == True

    def test_reorder_tasks_with_in_progress_pinned_to_top(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test that IN_PROGRESS tasks are always pinned to top."""
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)
        task5 = BatterySwapTask(5)

        driver = Driver(
            1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3, task4, task5]
        )

        # Set task2 and task4 as IN_PROGRESS (after Driver creation)
        task2.set_state(State.IN_PROGRESS)
        task4.set_state(State.IN_PROGRESS)

        # Reorder with top mode: [5, 3, 1]
        # Original: [1, 2*, 3, 4*, 5] (* = in-progress)
        # Expected: [2*, 4*] (in-progress, original order),
        #           [5, 3, 1] (specified), [] (unspecified)
        new_order = driver.reorder_tasks([5, 3, 1], apply_from_top=True)

        assert new_order == [2, 4, 5, 3, 1]
        assert driver.task_list == [task2, task4, task5, task3, task1]

    def test_reorder_tasks_with_in_progress_in_specified_list(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test that if a specified task is IN_PROGRESS, it stays at top."""
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)

        driver = Driver(
            1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3, task4]
        )
        task3.set_state(State.IN_PROGRESS)

        # Reorder: [3, 1] includes an in-progress task
        new_order = driver.reorder_tasks([3, 1], apply_from_top=True)

        assert new_order[0] == 3
        assert driver.task_list[0] == task3

    def test_reorder_tasks_bottom_mode_with_in_progress(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)

        driver = Driver(
            1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3, task4]
        )
        task2.set_state(State.IN_PROGRESS)

        new_order = driver.reorder_tasks([3, 1], apply_from_top=False)

        assert new_order[0] == 2
        assert driver.task_list[0] == task2

    def test_reorder_tasks_invalid_task_ids_ignored_with_warning(
        self, simpy_env: simpy.Environment, default_position: Position, caplog: Any
    ) -> None:
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3])

        with caplog.at_level("WARNING"):
            new_order = driver.reorder_tasks([99, 1], apply_from_top=True)

        assert new_order[0] in [t.id for t in driver.task_list]

    def test_reorder_tasks_all_tasks_specified(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        driver = Driver(1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3])

        new_order = driver.reorder_tasks([3, 2, 1], apply_from_top=True)

        assert new_order == [3, 2, 1]
        assert driver.task_list == [task3, task2, task1]

    def test_reorder_tasks_partial_list_resilience(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task1 = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)
        driver = Driver(
            1, default_position, self.DEFAULT_SHIFT, [task1, task2, task3, task4]
        )

        new_order = driver.reorder_tasks([4], apply_from_top=True)

        assert new_order[0] == 4

    def test_get_full_route_with_hq_next_stop(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test that nextTaskEndIndex points to HQ when driver is heading to HQ."""
        station1 = Station(1, "Station 1", Position([-73.5, 45.5]))
        station2 = Station(2, "Station 2", Position([-73.6, 45.6]))
        task1 = BatterySwapTask(1, station=station1)
        task2 = BatterySwapTask(2, station=station2)

        driver = Driver(1, default_position, [task1, task2])

        mock_map_controller = MagicMock()
        mock_route_to_hq = MagicMock()
        mock_route_to_hq.get_raw_coordinates.return_value = [
            [-73.5673, 45.5017],
            [-73.59, 45.52],
            [-73.60175631192361, 45.52975346053039],  # HQ position
        ]
        mock_route_to_task1 = MagicMock()
        mock_route_to_task1.get_raw_coordinates.return_value = [
            [-73.60175631192361, 45.52975346053039],  # HQ position
            [-73.55, 45.51],
            [-73.5, 45.5],  # Task 1 position
        ]
        mock_route_to_task2 = MagicMock()
        mock_route_to_task2.get_raw_coordinates.return_value = [
            [-73.5, 45.5],  # Task 1 position
            [-73.55, 45.55],
            [-73.6, 45.6],  # Task 2 position
        ]

        mock_map_controller.get_route.side_effect = [
            mock_route_to_hq,
            mock_route_to_task1,
            mock_route_to_task2,
        ]
        driver.set_map_controller(mock_map_controller)

        # Set driver state to HEADING_TO_HQ
        driver.state = DriverState.HEADING_TO_HQ

        # Get full route
        result = driver.get_full_route()

        assert result is not None
        assert "coordinates" in result
        assert "nextTaskEndIndex" in result

        # nextTaskEndIndex should point to HQ endpoint (index 2 in the combined route)
        # Route: [start, waypoint, HQ, waypoint, task1, waypoint, task2]
        # HQ is at index 2
        assert result["nextTaskEndIndex"] == 2
        assert result["coordinates"][2] == [
            -73.60175631192361,
            45.52975346053039,
        ]  # HQ

    def test_get_full_route_without_hq(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        """Test that nextTaskEndIndex points to first task when not heading to HQ."""
        station1 = Station(1, "Station 1", Position([-73.5, 45.5]))
        station2 = Station(2, "Station 2", Position([-73.6, 45.6]))
        task1 = BatterySwapTask(1, station=station1)
        task2 = BatterySwapTask(2, station=station2)

        driver = Driver(1, default_position, [task1, task2])

        mock_map_controller = MagicMock()
        mock_route_to_task1 = MagicMock()
        mock_route_to_task1.get_raw_coordinates.return_value = [
            [-73.5673, 45.5017],  # Driver position
            [-73.55, 45.51],
            [-73.5, 45.5],  # Task 1 position
        ]
        mock_route_to_task2 = MagicMock()
        mock_route_to_task2.get_raw_coordinates.return_value = [
            [-73.5, 45.5],  # Task 1 position (duplicate will be removed)
            [-73.55, 45.55],
            [-73.6, 45.6],  # Task 2 position
        ]

        mock_map_controller.get_route.side_effect = [
            mock_route_to_task1,
            mock_route_to_task2,
        ]
        driver.set_map_controller(mock_map_controller)

        # Driver is NOT heading to HQ (default state is ON_SHIFT)
        driver.state = DriverState.ON_SHIFT

        # Get full route
        result = driver.get_full_route()

        assert result is not None
        assert "coordinates" in result
        assert "nextTaskEndIndex" in result

        # nextTaskEndIndex should point to first task endpoint (index 2)
        # Route: [start, waypoint, task1, waypoint, task2]
        # Task1 is at index 2
        assert result["nextTaskEndIndex"] == 2
        assert result["coordinates"][2] == [-73.5, 45.5]  # Task 1
