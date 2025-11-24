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
from sim.entities.station import Station
from sim.entities.position import Position
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.task import Task


class TestStation:
    @pytest.fixture
    def default_position(self) -> Position:
        return Position([-73.5673, 45.5017])  # [longitude, latitude]

    @pytest.fixture
    def simpy_env(self) -> simpy.Environment:
        return simpy.Environment()

    def test_station_creation(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station_id = 1
        name = "Test Station Name"

        station = Station(station_id, name, default_position)

        assert station.id == station_id
        assert station.name == name
        assert station.position == default_position
        assert station.tasks == []

    def test_station_creation_with_tasks(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station_id = 2
        name = "Station with Tasks"
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        initial_tasks: list[Task] = [task, task2]

        station = Station(station_id, name, default_position, initial_tasks)

        assert station.id == station_id
        assert station.name == name
        assert station.position == default_position
        assert station.tasks == initial_tasks
        assert len(station.tasks) == 2

    def test_add_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station = Station(1, "Test Station", default_position)

        assert len(station.tasks) == 0

        # adding a single task
        task = BatterySwapTask(1)
        station.add_task(task)
        assert task in station.tasks
        assert len(station.tasks) == 1

        # adding multiple tasks
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        station.add_task(task2)
        station.add_task(task3)
        assert station.tasks == [task, task2, task3]
        assert len(station.tasks) == 3

    def test_remove_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)
        initial_tasks: list[Task] = [task, task2, task3, task4]
        station = Station(1, "Test Station", default_position, initial_tasks.copy())

        # removing existing task
        station.remove_task(task2)
        assert task2 not in station.tasks
        assert station.tasks == [task, task3, task4]
        assert len(station.tasks) == 3

        # removing another task
        station.remove_task(task)
        assert station.tasks == [task3, task4]
        assert len(station.tasks) == 2

    def test_remove_nonexistent_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        initial_tasks: list[Task] = [task, task2, task3]
        station = Station(1, "Test Station", default_position, initial_tasks.copy())

        # attempting to remove non-existent task
        task4 = BatterySwapTask(4)
        station.remove_task(task4)

        assert station.tasks == [task, task2, task3]
        assert len(station.tasks) == 3

    def test_get_count(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station = Station(1, "Empty Station", default_position)
        assert station.get_task_count() == 0

        task = BatterySwapTask(1)
        task2 = BatterySwapTask(2)
        task3 = BatterySwapTask(3)
        task4 = BatterySwapTask(4)
        task5 = BatterySwapTask(5)
        tasks: list[Task] = [task, task2, task3, task4, task5]
        station_with_tasks = Station(2, "Busy Station", default_position, tasks)
        assert station_with_tasks.get_task_count() == 5

        station.add_task(task)
        station.add_task(task2)
        assert station.get_task_count() == 2

        station.remove_task(task)
        assert station.get_task_count() == 1

    def test_get_station_position(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station = Station(1, "Test Station", default_position)

        returned_position = station.get_station_position()
        assert returned_position == default_position
        assert returned_position.get_position() == [-73.5673, 45.5017]
