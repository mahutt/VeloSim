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
from sim.entities.BatterySwapTask import BatterySwapTask, State
from sim.entities.station import Station
from sim.entities.position import Position
from sim.entities.resource import Resource

# from sim.entities.task import Task, State


class TestBatterySwapTask:
    @pytest.fixture
    def simpy_env(self) -> simpy.Environment:
        return simpy.Environment()

    @pytest.fixture
    def default_station(self, simpy_env: simpy.Environment) -> Station:
        return Station(simpy_env, 1, "Test Station", Position([-73.5673, 45.5017]))

    def test_battery_swap_task_creation(
        self, simpy_env: simpy.Environment, default_station: Station
    ) -> None:
        # Arrange
        task_id = 1

        # Act
        task = BatterySwapTask(simpy_env, task_id, default_station)

        # Assert
        assert task.get_task_id() == 1
        assert task.get_station() == default_station
        assert task.get_state() == State.OPEN
        assert task.get_assigned_resource() is None

    def test_battery_swap_task_creation_with_no_station(
        self, simpy_env: simpy.Environment
    ) -> None:
        # Arrange
        task_id = 1

        # Act
        task = BatterySwapTask(simpy_env, task_id)

        # Assert
        assert task.get_task_id() == 1
        assert task.get_station() is None
        assert task.get_state() == State.OPEN
        assert task.get_assigned_resource() is None

    def test_get_and_set_state(self, simpy_env: simpy.Environment) -> None:
        task = BatterySwapTask(simpy_env, 1)

        state = task.get_state()
        assert state == State.OPEN
        assert str(state) == "open"

        task.set_state(State.ASSIGNED)
        state = task.get_state()
        assert state == State.ASSIGNED
        assert str(state) == "assigned"

        task.set_state(State.IN_PROGRESS)
        state = task.get_state()
        assert state == State.IN_PROGRESS
        assert str(state) == "inprogress"

        task.set_state(State.CLOSED)
        state = task.get_state()
        assert state == State.CLOSED
        assert str(state) == "closed"

    def test_get_task_id(self, simpy_env: simpy.Environment) -> None:
        # Arrange
        task = BatterySwapTask(simpy_env, 1)

        # Act
        id = task.get_task_id()

        # Assert
        assert id == 1
        assert isinstance(id, int)

    def test_get_and_set_station(
        self, simpy_env: simpy.Environment, default_station: Station
    ) -> None:
        task = BatterySwapTask(simpy_env, 1)

        # default no station
        station = task.get_station()
        assert station is None

        task.set_station(default_station)
        station = task.get_station()
        assert station is not None
        assert station == default_station

    def test_get_and_set_assigned_resource(
        self, simpy_env: simpy.Environment, default_station: Station
    ) -> None:
        task = BatterySwapTask(simpy_env, 1, default_station)

        # default no resource
        assigned_resource = task.get_assigned_resource()
        assert assigned_resource is None

        resource = Resource(simpy_env, 1, Position([-73.5673, 45.5017]))
        task.set_assigned_resource(resource)
        assigned_resource = task.get_assigned_resource()
        assert assigned_resource is not None
        assert assigned_resource == resource

    def test_unassign_resource(
        self, simpy_env: simpy.Environment, default_station: Station
    ) -> None:
        # Arrange
        task = BatterySwapTask(simpy_env, 1, default_station)
        resource = Resource(simpy_env, 1, Position([-73.5673, 45.5017]))
        task.set_assigned_resource(resource)
        assert task.get_assigned_resource() == resource
        assert task.get_state() == State.ASSIGNED

        # Act
        task.unassign_resource()

        # Assert
        assert task.get_assigned_resource() is None
        assert task.get_state() == State.OPEN

    def test_is_assigned_true(
        self, simpy_env: simpy.Environment, default_station: Station
    ) -> None:
        # Arrange
        task = BatterySwapTask(simpy_env, 1, default_station)
        resource = Resource(simpy_env, 1, Position([-73.5673, 45.5017]))
        task.set_assigned_resource(resource)

        # Act
        assigned = task.is_assigned()

        # Assert
        assert assigned == True
        assert task.get_state() == State.ASSIGNED

    def test_is_assigned_false(
        self, simpy_env: simpy.Environment, default_station: Station
    ) -> None:
        # Arrange
        task = BatterySwapTask(simpy_env, 1, default_station)

        # Act
        assigned = task.is_assigned()

        # Assert
        assert assigned == False
        assert task.get_state() == State.OPEN
