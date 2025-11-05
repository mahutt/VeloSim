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
from unittest.mock import Mock
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.resource import Resource
from sim.entities.position import Position
from sim.entities.station import Station
from sim.entities.task_state import State


@pytest.fixture
def env() -> simpy.Environment:
    # Create a new SimPy environment for each test
    return simpy.Environment()


@pytest.fixture
def station(env: simpy.Environment) -> Station:
    # Create new test station
    return Station(env, station_id=1, name="Test Station", position=Position([6, 7]))


@pytest.fixture
def resource(env: simpy.Environment) -> Resource:
    # Create new test resource
    res = Resource(env, resource_id=1, position=Position([0.0, 0.0]))
    # Mock the sim_behaviour and map_controller to avoid AttributeError
    res.sim_behaviour = Mock()
    res.map_controller = Mock()
    return res


def test_task_immediate_spawn(env: simpy.Environment, station: Station) -> None:
    """Test that tasks with no delay spawn immediately."""
    task_immediate = BatterySwapTask(env, task_id=1, station=station)
    assert task_immediate.get_state() == State.OPEN, "Immediate task should be OPEN"


def test_task_scheduled_spawn(env: simpy.Environment, station: Station) -> None:
    # Testing tasks which have a spawn delay (task is scheduled)
    task_scheduled = BatterySwapTask(env, task_id=2, station=station, spawn_delay=5.0)
    assert (
        task_scheduled.get_state() == State.SCHEDULED
    ), "Delayed task should be SCHEDULED"

    env.run(until=6.0)
    assert (
        task_scheduled.get_state() == State.OPEN
    ), f"Task should be OPEN but is {task_scheduled.get_state().name}"


def test_multiple_scheduled_tasks(env: simpy.Environment, station: Station) -> None:
    # Checking when there are multiple scheduled tasks.
    creation_time = env.now
    task3 = BatterySwapTask(env, task_id=3, station=station, spawn_delay=2.0)
    task4 = BatterySwapTask(env, task_id=4, station=station, spawn_delay=5.0)

    env.run(until=creation_time + 3.0)
    assert (
        task3.get_state() == State.OPEN
    ), f"Task 3 should be OPEN but is {task3.get_state().name}"
    assert (
        task4.get_state() == State.SCHEDULED
    ), f"Task 4 should still be SCHEDULED but is {task4.get_state().name}"

    env.run(until=creation_time + 6.0)
    assert (
        task4.get_state() == State.OPEN
    ), f"Task 4 should be OPEN but is {task4.get_state().name}"


def test_resource_immediate_dispatch(
    env: simpy.Environment, station: Station, resource: Resource
) -> None:
    task = BatterySwapTask(env, task_id=1, station=station)
    # Task is OPEN right away (not scheduled)

    resource.assign_task(task)
    assert task.get_state() == State.ASSIGNED, "Task should be ASSIGNED"
    # making sure after assigning a task, the state changes correctly.

    resource.dispatch_task(task)
    assert task.get_state() == State.IN_PROGRESS, "Task should be IN_PROGRESS"
    # making sure after dispatching a task, the state changes correctly.


def test_resource_scheduled_dispatch(env: simpy.Environment, station: Station) -> None:
    # Dispatching with delays
    task = BatterySwapTask(env, task_id=2, station=station)
    resource = Resource(env, resource_id=2, position=Position([0.0, 0.0]))
    # Mock the sim_behaviour and map_controller to avoid AttributeError
    resource.sim_behaviour = Mock()
    resource.map_controller = Mock()

    assign_time = env.now
    resource.assign_task(task, dispatch_delay=3.0)
    assert task.get_state() == State.ASSIGNED, "Task should be ASSIGNED"

    env.run(until=assign_time + 4.0)
    assert (
        task.get_state() == State.IN_PROGRESS
    ), f"Task should be IN_PROGRESS but is {task.get_state().name}"


def test_simulation_time_waiting(env: simpy.Environment, station: Station) -> None:
    # Testing task waiting / scheduled time
    task = BatterySwapTask(env, task_id=1, station=station, spawn_delay=2.0)
    assert task.get_state() == State.SCHEDULED

    env.run(until=1.0)
    assert task.get_state() == State.SCHEDULED, "Task should still be SCHEDULED at t=1"

    env.run(until=3.0)
    assert task.get_state() == State.OPEN, "Task should have spawned by t=3"


def test_full_lifecycle_with_scheduling(
    env: simpy.Environment, station: Station, resource: Resource
) -> None:
    # Testing complete task lifecylce with delays
    task = BatterySwapTask(env, task_id=1, station=station, spawn_delay=2.0)
    assert task.get_state() == State.SCHEDULED

    env.run(until=3.0)
    assert task.get_state() == State.OPEN

    assign_time = env.now
    resource.assign_task(task, dispatch_delay=1.5)
    assert task.get_state() == State.ASSIGNED

    env.run(until=assign_time + 2.0)
    assert task.get_state() == State.IN_PROGRESS

    resource.service_task(task)
    assert task.get_state() == State.CLOSED


def test_task_unassign_resource(
    env: simpy.Environment, station: Station, resource: Resource
) -> None:
    # Test unassigning tasks. Assumed that its possible a task might be still available.
    task = BatterySwapTask(env, task_id=1, station=station)

    resource.assign_task(task)
    assert task.get_state() == State.ASSIGNED
    assert task.get_assigned_resource() == resource

    task.unassign_resource()
    assert task.get_state() == State.OPEN
    assert task.get_assigned_resource() is None


def test_resource_unassign_task(
    env: simpy.Environment, station: Station, resource: Resource
) -> None:
    # Test resource unassigning a task
    task = BatterySwapTask(env, task_id=1, station=station)

    resource.assign_task(task)
    assert task in resource.get_task_list()
    assert task.get_state() == State.ASSIGNED

    resource.unassign_task(task)
    assert task not in resource.get_task_list()
    assert task.get_state() == State.OPEN


def test_resource_get_in_progress_task(
    env: simpy.Environment, station: Station
) -> None:
    # Ensure that a task cannot get interrupted by another assignment.
    resource = Resource(env, resource_id=1, position=Position([0.0, 0.0]))
    task1 = BatterySwapTask(env, task_id=1, station=station)
    task2 = BatterySwapTask(env, task_id=2, station=station)

    resource.assign_task(task1)
    resource.assign_task(task2)

    assert resource.get_in_progress_task() is None

    resource.dispatch_task(task1)
    assert resource.get_in_progress_task() == task1

    resource.service_task(task1)
    assert resource.get_in_progress_task() is None


def test_dispatch_multiple_tasks_same_station(
    env: simpy.Environment, station: Station
) -> None:
    # Test dispatching multiple tasks at the same station
    resource = Resource(env, resource_id=1, position=Position([0.0, 0.0]))
    task1 = BatterySwapTask(env, task_id=1, station=station)
    task2 = BatterySwapTask(env, task_id=2, station=station)

    resource.assign_task(task1)
    resource.assign_task(task2)

    resource.dispatch_task(task1)
    assert task1.get_state() == State.IN_PROGRESS

    # Should be able to dispatch task2 since it's at the same station
    resource.dispatch_task(task2)
    assert task2.get_state() == State.IN_PROGRESS


def test_dispatch_task_different_station_raises_exception(
    env: simpy.Environment, station: Station
) -> None:
    # Test that dispatching tasks at different stations raises exception.
    resource = Resource(env, resource_id=1, position=Position([0.0, 0.0]))
    station2 = Station(
        env, station_id=2, name="Station 2", position=Position([1.0, 1.0])
    )

    task1 = BatterySwapTask(env, task_id=1, station=station)
    task2 = BatterySwapTask(env, task_id=2, station=station2)

    resource.assign_task(task1)
    resource.assign_task(task2)
    resource.dispatch_task(task1)

    with pytest.raises(Exception, match="Cannot dispatch task at this station"):
        resource.dispatch_task(task2)


def test_resource_with_initial_task_list(
    env: simpy.Environment, station: Station
) -> None:
    # Test creating a resource with an initial task list.
    task1 = BatterySwapTask(env, task_id=1, station=station)
    task2 = BatterySwapTask(env, task_id=2, station=station)

    resource = Resource(
        env, resource_id=1, position=Position([0.0, 0.0]), task_list=[task1, task2]
    )

    assert resource.get_task_count() == 2
    assert task1 in resource.get_task_list()
    assert task2 in resource.get_task_list()
    assert task1.get_assigned_resource() == resource
    assert task2.get_assigned_resource() == resource


def test_zero_spawn_delay_creates_open_task(
    env: simpy.Environment, station: Station
) -> None:
    # Test that spawn_delay of 0 creates an OPEN task immediately.
    task = BatterySwapTask(env, task_id=1, station=station, spawn_delay=0)
    assert task.get_state() == State.OPEN


def test_zero_dispatch_delay_keeps_task_assigned(
    env: simpy.Environment, station: Station
) -> None:
    # Test that dispatch_delay of 0 keeps task ASSIGNED (not auto-dispatched).
    task = BatterySwapTask(env, task_id=1, station=station)
    resource = Resource(env, resource_id=1, position=Position([0.0, 0.0]))

    resource.assign_task(task, dispatch_delay=0)
    assert task.get_state() == State.ASSIGNED

    # Even after running simulation, task stays ASSIGNED (waiting for manual dispatch)
    env.run(until=1.0)
    assert task.get_state() == State.ASSIGNED


def test_spawn_time_tracking(env: simpy.Environment, station: Station) -> None:
    # Test that spawn_time is correctly tracked for tasks.
    creation_time = env.now

    task_immediate = BatterySwapTask(env, task_id=1, station=station)
    assert task_immediate.spawn_time == creation_time

    task_delayed = BatterySwapTask(env, task_id=2, station=station, spawn_delay=5.0)
    assert task_delayed.spawn_time == creation_time + 5.0


def test_task_state_string_conversions(
    env: simpy.Environment, station: Station
) -> None:
    # Test that all task states convert to their string representations correctly

    # Test SCHEDULED state string conversion (helps with code coverage)
    task = BatterySwapTask(env, task_id=1, station=station, spawn_delay=1.0)
    assert task.get_state() == State.SCHEDULED
    assert str(task.get_state()) == "scheduled"
    task_dict = task.to_dict()
    assert task_dict["state"] == "scheduled"

    # Test OPEN state
    env.run(until=2.0)
    assert str(task.get_state()) == "open"

    # Test ASSIGNED state
    resource = Resource(env, resource_id=1, position=Position([0.0, 0.0]))
    resource.assign_task(task)
    assert str(task.get_state()) == "assigned"

    # Test IN_PROGRESS state
    resource.dispatch_task(task)
    assert str(task.get_state()) == "inprogress"

    # Test CLOSED state
    resource.service_task(task)
    assert str(task.get_state()) == "closed"
