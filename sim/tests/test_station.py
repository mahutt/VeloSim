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
from sim.entities.position import Position
from sim.entities.station import Station


class TestStation:
    @pytest.fixture  # type: ignore[misc]
    def defaultPosition(self) -> Position:
        return Position(45.5017, -73.5673)

    @pytest.fixture  # type: ignore[misc]
    def simpyEnv(self) -> simpy.Environment:
        return simpy.Environment()

    def testStationCreation(
        self, simpyEnv: simpy.Environment, defaultPosition: Position
    ) -> None:
        stationId = 1
        name = "Test Station Name"

        station = Station(simpyEnv, stationId, name, defaultPosition)

        assert station.id == stationId
        assert station.name == name
        assert station.position == defaultPosition
        assert station.tasks == []
        assert station.env == simpyEnv
        assert station.action is not None

    def testStationCreationWithTasks(
        self, simpyEnv: simpy.Environment, defaultPosition: Position
    ) -> None:
        stationId = 2
        name = "Station with Tasks"
        initialTasks = [1, 2, 3]

        station = Station(simpyEnv, stationId, name, defaultPosition, initialTasks)

        assert station.id == stationId
        assert station.name == name
        assert station.position == defaultPosition
        assert station.tasks == initialTasks
        assert len(station.tasks) == 3

    def testAddTask(
        self, simpyEnv: simpy.Environment, defaultPosition: Position
    ) -> None:
        station = Station(simpyEnv, 1, "Test Station", defaultPosition)

        assert len(station.tasks) == 0

        # adding a single task
        station.addTask(101)
        assert 101 in station.tasks
        assert len(station.tasks) == 1

        # adding multiple tasks
        station.addTask(102)
        station.addTask(103)
        assert station.tasks == [101, 102, 103]
        assert len(station.tasks) == 3

    def testRemoveTask(
        self, simpyEnv: simpy.Environment, defaultPosition: Position
    ) -> None:
        initialTasks = [1, 2, 3, 4]
        station = Station(
            simpyEnv, 1, "Test Station", defaultPosition, initialTasks.copy()
        )

        # removing existing task
        station.removeTask(2)
        assert 2 not in station.tasks
        assert station.tasks == [1, 3, 4]
        assert len(station.tasks) == 3

        # removing another task
        station.removeTask(1)
        assert station.tasks == [3, 4]
        assert len(station.tasks) == 2

    def testRemoveNonexistentTask(
        self, simpyEnv: simpy.Environment, defaultPosition: Position
    ) -> None:
        """Test removing non-existent tasks from a station."""
        initialTasks = [1, 2, 3]
        station = Station(
            simpyEnv, 1, "Test Station", defaultPosition, initialTasks.copy()
        )

        # attempting to remove non-existent task
        station.removeTask(999)

        assert station.tasks == [1, 2, 3]
        assert len(station.tasks) == 3

    def testGetCount(
        self, simpyEnv: simpy.Environment, defaultPosition: Position
    ) -> None:
        station = Station(simpyEnv, 1, "Empty Station", defaultPosition)
        assert station.getTaskCount() == 0

        tasks = [10, 20, 30, 40, 50]
        stationWithTasks = Station(simpyEnv, 2, "Busy Station", defaultPosition, tasks)
        assert stationWithTasks.getTaskCount() == 5

        station.addTask(100)
        station.addTask(200)
        assert station.getTaskCount() == 2

        station.removeTask(100)
        assert station.getTaskCount() == 1

    def testGetStationPosition(
        self, simpyEnv: simpy.Environment, defaultPosition: Position
    ) -> None:
        station = Station(simpyEnv, 1, "Test Station", defaultPosition)

        returnedPosition = station.getStationPosition()
        assert returnedPosition == defaultPosition
        assert returnedPosition.latitude == defaultPosition.latitude
        assert returnedPosition.longitude == defaultPosition.longitude
