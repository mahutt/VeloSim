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

        station = Station(simpy_env, station_id, name, default_position)

        assert station.id == station_id
        assert station.name == name
        assert station.position == default_position
        assert station.tasks == []
        assert station.env == simpy_env
        assert station.action is not None

    def test_station_creation_with_tasks(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station_id = 2
        name = "Station with Tasks"
        initial_tasks = [1, 2, 3]

        station = Station(simpy_env, station_id, name, default_position, initial_tasks)

        assert station.id == station_id
        assert station.name == name
        assert station.position == default_position
        assert station.tasks == initial_tasks
        assert len(station.tasks) == 3

    def test_add_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station = Station(simpy_env, 1, "Test Station", default_position)

        assert len(station.tasks) == 0

        # adding a single task
        station.add_task(101)
        assert 101 in station.tasks
        assert len(station.tasks) == 1

        # adding multiple tasks
        station.add_task(102)
        station.add_task(103)
        assert station.tasks == [101, 102, 103]
        assert len(station.tasks) == 3

    def test_remove_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        initial_tasks = [1, 2, 3, 4]
        station = Station(
            simpy_env, 1, "Test Station", default_position, initial_tasks.copy()
        )

        # removing existing task
        station.remove_task(2)
        assert 2 not in station.tasks
        assert station.tasks == [1, 3, 4]
        assert len(station.tasks) == 3

        # removing another task
        station.remove_task(1)
        assert station.tasks == [3, 4]
        assert len(station.tasks) == 2

    def test_remove_nonexistent_task(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        initial_tasks = [1, 2, 3]
        station = Station(
            simpy_env, 1, "Test Station", default_position, initial_tasks.copy()
        )

        # attempting to remove non-existent task
        station.remove_task(999)

        assert station.tasks == [1, 2, 3]
        assert len(station.tasks) == 3

    def test_get_count(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station = Station(simpy_env, 1, "Empty Station", default_position)
        assert station.get_task_count() == 0

        tasks = [10, 20, 30, 40, 50]
        station_with_tasks = Station(
            simpy_env, 2, "Busy Station", default_position, tasks
        )
        assert station_with_tasks.get_task_count() == 5

        station.add_task(100)
        station.add_task(200)
        assert station.get_task_count() == 2

        station.remove_task(100)
        assert station.get_task_count() == 1

    def test_get_station_position(
        self, simpy_env: simpy.Environment, default_position: Position
    ) -> None:
        station = Station(simpy_env, 1, "Test Station", default_position)

        returned_position = station.get_station_position()
        assert returned_position == default_position
        assert returned_position.get_position() == [-73.5673, 45.5017]
