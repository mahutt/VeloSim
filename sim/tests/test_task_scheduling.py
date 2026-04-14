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
from sim.core.simulation_environment import SimulationEnvironment
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.driver import Driver
from sim.entities.position import Position
from sim.entities.station import Station
from sim.entities.task_state import State
from sim.entities.vehicle import Vehicle
from sim.entities.shift import Shift
from sim.behaviour.default.default_TPU_strategy import DefaultTPUStrategy


@pytest.fixture
def env() -> SimulationEnvironment:
    # Create a new SimPy environment for each test and assign to Driver
    e = SimulationEnvironment()
    Driver.env = e
    return e


@pytest.fixture
def station(env: simpy.Environment) -> Station:
    # Create new test station
    station = Station(station_id=1, name="Test Station", position=Position([6, 7]))
    station.env = env
    return station


@pytest.fixture
def resource(env: simpy.Environment) -> Driver:
    # Create new test driver (resource replacement)
    res = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(res)
    res.set_vehicle(vehicle)
    # Mock the sim_behaviour and map_controller to avoid AttributeError
    res.sim_behaviour = Mock()
    # ensure TST strategy exists and returns a small/default value for tests
    res.sim_behaviour.TST_strategy = Mock()
    res.sim_behaviour.TST_strategy.get_task_servicing_time.return_value = 0
    res.map_controller = Mock()
    return res


@pytest.fixture
def driver(env: simpy.Environment) -> Driver:
    # Create new test driver (resource replacement)
    res = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(res)
    res.set_vehicle(vehicle)
    # Mock the sim_behaviour and map_controller to avoid AttributeError
    res.sim_behaviour = Mock()
    # ensure TST strategy exists and returns a small/default value for tests
    res.sim_behaviour.TST_strategy = Mock()
    res.sim_behaviour.TST_strategy.get_task_servicing_time.return_value = 0
    res.map_controller = Mock()
    return res


def test_task_immediate_spawn(env: simpy.Environment, station: Station) -> None:
    """Test that tasks with no delay spawn immediately."""
    task_immediate = BatterySwapTask(task_id=1, station=station)
    assert task_immediate.get_state() == State.OPEN, "Immediate task should be OPEN"


def test_multiple_scheduled_tasks(env: simpy.Environment, station: Station) -> None:
    # Checking when there are multiple scheduled tasks using TPU strategy.
    strategy = DefaultTPUStrategy()
    scheduled_tasks = {station.id: {2: [3], 5: [4]}}
    strategy.set_station_scheduled_tasks(scheduled_tasks)

    # Set the strategy on the station
    if not hasattr(station, "behaviour") or station.behaviour is None:
        station.behaviour = Mock()
    station.behaviour.TPU_strategy = strategy

    # Check at time 2 when first task is scheduled
    env.run(until=2.0)
    tasks_at_2 = station.behaviour.TPU_strategy.check_for_new_task(station)
    assert len(tasks_at_2) == 1
    task3 = tasks_at_2[0]
    assert (
        task3.get_state() == State.OPEN
    ), f"Task 3 should be OPEN but is {task3.get_state().name}"
    assert task3.get_task_id() == 3

    # Check at time 5 when second task is scheduled
    env.run(until=5.0)
    tasks_at_5 = station.behaviour.TPU_strategy.check_for_new_task(station)
    assert len(tasks_at_5) == 1
    task4 = tasks_at_5[0]
    assert (
        task4.get_state() == State.OPEN
    ), f"Task 4 should be OPEN but is {task4.get_state().name}"
    assert task4.get_task_id() == 4


def test_resource_immediate_dispatch(
    env: simpy.Environment, station: Station, driver: Driver
) -> None:
    task = BatterySwapTask(task_id=1, station=station)
    # Task is OPEN right away (not scheduled)

    driver.assign_task(task)
    assert task.get_state() == State.ASSIGNED, "Task should be ASSIGNED"
    # making sure after assigning a task, the state changes correctly.

    driver.dispatch_task(task)
    assert task.get_state() == State.IN_PROGRESS, "Task should be IN_PROGRESS"
    # making sure after dispatching a task, the state changes correctly.


def test_resource_scheduled_dispatch(env: simpy.Environment, station: Station) -> None:
    # Dispatching with delays
    task = BatterySwapTask(task_id=2, station=station)
    resource = Driver(
        driver_id=2,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )
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
    # Testing task waiting / scheduled time using TPU strategy
    strategy = DefaultTPUStrategy()
    scheduled_tasks = {station.id: {2: [1]}}
    strategy.set_station_scheduled_tasks(scheduled_tasks)

    # Set the strategy on the station
    if not hasattr(station, "behaviour") or station.behaviour is None:
        station.behaviour = Mock()
    station.behaviour.TPU_strategy = strategy

    env.run(until=1.0)
    tasks_at_1 = station.behaviour.TPU_strategy.check_for_new_task(station)
    assert len(tasks_at_1) == 0, "Task should not have spawned at t=1"

    # Check at exactly time 2 when task is scheduled
    env.run(until=2.0)
    tasks_at_2 = station.behaviour.TPU_strategy.check_for_new_task(station)
    assert len(tasks_at_2) == 1, "Task should have spawned at t=2"
    assert tasks_at_2[0].get_state() == State.OPEN


def test_full_lifecycle_with_scheduling(
    env: simpy.Environment, station: Station, driver: Driver
) -> None:
    # Testing complete task lifecycle with scheduling using TPU strategy
    strategy = DefaultTPUStrategy()
    scheduled_tasks = {station.id: {2: [1]}}
    strategy.set_station_scheduled_tasks(scheduled_tasks)

    # Set the strategy on the station
    if not hasattr(station, "behaviour") or station.behaviour is None:
        station.behaviour = Mock()
    station.behaviour.TPU_strategy = strategy

    # Check at exactly time 2 when task is scheduled
    env.run(until=2.0)
    tasks = station.behaviour.TPU_strategy.check_for_new_task(station)
    assert len(tasks) == 1
    task = tasks[0]
    assert task.get_state() == State.OPEN

    assign_time = env.now
    driver.assign_task(task, dispatch_delay=1.5)
    assert task.get_state() == State.ASSIGNED

    env.run(until=assign_time + 2.0)
    assert task.get_state() == State.IN_PROGRESS

    # run servicing process so the task is closed (service_task is a SimPy generator)
    env.process(driver.service_task(task))
    env.run()
    assert task.get_state() == State.CLOSED


def test_task_unassign_driver(
    env: simpy.Environment, station: Station, driver: Driver
) -> None:
    # Test unassigning tasks. Assumed that its possible a task might be still available.
    task = BatterySwapTask(task_id=1, station=station)

    driver.assign_task(task)
    assert task.get_state() == State.ASSIGNED
    assert task.get_assigned_driver() == driver

    task.unassign_driver()
    assert task.get_state() == State.OPEN
    assert task.get_assigned_driver() is None


def test_driver_unassign_task(
    env: simpy.Environment, station: Station, driver: Driver
) -> None:
    # Test resource unassigning a task
    task = BatterySwapTask(task_id=1, station=station)

    driver.assign_task(task)
    assert task in driver.get_task_list()
    assert task.get_state() == State.ASSIGNED

    driver.unassign_task(task)
    assert task not in driver.get_task_list()
    assert task.get_state() == State.OPEN


def test_resource_get_in_progress_task(
    env: simpy.Environment, station: Station
) -> None:
    # Ensure that a task cannot get interrupted by another assignment.
    resource = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(resource)
    resource.set_vehicle(vehicle)
    # ensure local driver has sim_behaviour and TST strategy for service_task
    resource.sim_behaviour = Mock()
    resource.sim_behaviour.TST_strategy = Mock()
    resource.sim_behaviour.TST_strategy.get_task_servicing_time.return_value = 0
    resource.map_controller = Mock()
    # ensure local driver has sim_behaviour and TST strategy for service_task
    resource.sim_behaviour = Mock()
    resource.sim_behaviour.TST_strategy = Mock()
    resource.sim_behaviour.TST_strategy.get_task_servicing_time.return_value = 0
    resource.map_controller = Mock()
    # Local resource may be used in tests; set minimal sim_behaviour/map_controller
    resource.sim_behaviour = Mock()
    resource.sim_behaviour.TST_strategy = Mock()
    resource.sim_behaviour.TST_strategy.get_task_servicing_time.return_value = 0
    resource.map_controller = Mock()
    task1 = BatterySwapTask(task_id=1, station=station)
    task2 = BatterySwapTask(task_id=2, station=station)

    mock_map = Mock()
    mock_map.get_route.return_value = Mock()
    resource.set_map_controller(mock_map)

    resource.assign_task(task1)
    resource.assign_task(task2)

    assert resource.get_in_progress_task() is None

    resource.dispatch_task(task1)
    assert resource.get_in_progress_task() == task1

    # run servicing process to complete the in-progress task
    env.process(resource.service_task(task1))
    env.run()
    assert resource.get_in_progress_task() is None


def test_dispatch_multiple_tasks_same_station(
    env: simpy.Environment, station: Station
) -> None:
    # Test dispatching multiple tasks at the same station raises an exception
    resource = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )
    task1 = BatterySwapTask(task_id=1, station=station)
    task2 = BatterySwapTask(task_id=2, station=station)

    mock_map = Mock()
    mock_map.get_route.return_value = Mock()
    resource.set_map_controller(mock_map)

    resource.assign_task(task1)
    resource.assign_task(task2)

    resource.dispatch_task(task1)
    assert task1.get_state() == State.IN_PROGRESS

    with pytest.raises(
        Exception,
        match="Cannot dispatch this task since there exists one already in-progress",
    ):
        resource.dispatch_task(task2)


def test_dispatch_task_different_station_raises_exception(
    env: simpy.Environment, station: Station
) -> None:
    # Test that dispatching tasks at different stations raises exception.
    resource = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )
    station2 = Station(station_id=2, name="Station 2", position=Position([1.0, 1.0]))

    mock_map = Mock()
    mock_map.get_route.return_value = Mock()
    resource.set_map_controller(mock_map)

    task1 = BatterySwapTask(task_id=1, station=station)
    task2 = BatterySwapTask(task_id=2, station=station2)

    resource.assign_task(task1)
    resource.assign_task(task2)
    resource.dispatch_task(task1)

    with pytest.raises(
        Exception,
        match="Cannot dispatch this task since there exists one already in-progress",
    ):
        resource.dispatch_task(task2)


def test_resource_with_initial_task_list(
    env: simpy.Environment, station: Station
) -> None:
    # Test creating a resource with an initial task list.
    task1 = BatterySwapTask(task_id=1, station=station)
    task2 = BatterySwapTask(task_id=2, station=station)

    resource = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
        task_list=[task1, task2],
    )

    assert resource.get_task_count() == 2
    assert task1 in resource.get_task_list()
    assert task2 in resource.get_task_list()
    assert task1.get_assigned_driver() == resource
    assert task2.get_assigned_driver() == resource


def test_zero_dispatch_delay_keeps_task_assigned(
    env: simpy.Environment, station: Station
) -> None:
    # Test that dispatch_delay of 0 keeps task ASSIGNED (not auto-dispatched).
    task = BatterySwapTask(task_id=1, station=station)
    resource = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )

    mock_map = Mock()
    mock_map.get_route.return_value = Mock()
    resource.set_map_controller(mock_map)

    resource.assign_task(task, dispatch_delay=0)
    assert task.get_state() == State.ASSIGNED

    # Even after running simulation, task stays ASSIGNED (waiting for manual dispatch)
    env.run(until=1.0)
    assert task.get_state() == State.ASSIGNED


def test_task_state_string_conversions(
    env: simpy.Environment, station: Station
) -> None:
    # Test that all task states convert to their string representations correctly

    # Test OPEN state - create task directly in OPEN state
    task = BatterySwapTask(task_id=1, station=station)
    assert task.get_state() == State.OPEN
    assert str(task.get_state()) == "open"

    # Test ASSIGNED state
    resource = Driver(
        driver_id=1,
        position=Position([0.0, 0.0]),
        shift=Shift(
            start_time=0.0,
            end_time=86400.0,
            lunch_break=None,
            sim_start_time=0.0,
        ),
    )
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(resource)
    resource.set_vehicle(vehicle)

    # ensure local driver has sim_behaviour and TST strategy for service_task
    resource.sim_behaviour = Mock()
    resource.sim_behaviour.TST_strategy = Mock()
    resource.sim_behaviour.TST_strategy.get_task_servicing_time.return_value = 0

    mock_map = Mock()
    mock_map.get_route.return_value = Mock()
    resource.set_map_controller(mock_map)

    resource.assign_task(task)
    assert str(task.get_state()) == "assigned"

    # Test IN_PROGRESS state
    resource.dispatch_task(task)
    assert str(task.get_state()) == "inprogress"

    # Test CLOSED state
    # service the task as a SimPy process so it completes
    env.process(resource.service_task(task))
    env.run()
    assert str(task.get_state()) == "closed"
