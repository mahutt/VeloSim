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

import simpy
from unittest.mock import Mock
from sim.entities.driver import Driver, DriverState
from sim.entities.position import Position
from sim.entities.task import Task
from sim.entities.station import Station
from sim.entities.task_state import State
from sim.behaviour.sim_behaviour import SimBehaviour
from sim.entities.vehicle import Vehicle
from sim.entities.shift import Shift


class FakeTask(Task):
    """Fake task for testing"""

    def __init__(self, task_id, station=None):  # type: ignore[no-untyped-def]
        super().__init__(task_id, station)
        self._state = State.OPEN

    def get_state(self) -> State:
        return self._state

    def set_state(self, state: State) -> None:
        self._state = state

    def get_task_id(self) -> int:
        return self.id

    def get_station(self):  # type: ignore[no-untyped-def]
        return self.station

    def set_station(self, station):  # type: ignore[no-untyped-def]
        self.station = station

    # Driver-based API (current abstract methods)
    def get_assigned_driver(self):  # type: ignore[no-untyped-def]
        return self.assigned_driver

    def set_assigned_driver(self, driver):  # type: ignore[no-untyped-def]
        self.assigned_driver = driver
        # Preserve IN_PROGRESS if already dispatched
        if self._state != State.IN_PROGRESS:
            self._state = State.ASSIGNED

    def unassign_driver(self) -> None:
        self.assigned_driver = None
        self._state = State.OPEN

    def is_assigned(self) -> bool:
        # Consider both ASSIGNED and IN_PROGRESS as assigned for dispatch logic
        return self.assigned_driver is not None and self._state in (
            State.ASSIGNED,
            State.IN_PROGRESS,
        )

    # Back-compat resource-named helpers used by Resource methods in tests
    def get_assigned_resource(self):  # type: ignore[no-untyped-def]
        return self.get_assigned_driver()

    def set_assigned_resource(self, resource):  # type: ignore[no-untyped-def]
        self.set_assigned_driver(resource)

    def unassign_resource(self) -> None:
        self.unassign_driver()


# Default shift for drivers in these tests (use seconds)
DEFAULT_SHIFT = Shift(0.0, 24.0 * 60 * 60, None, 0.0, 24.0 * 60 * 60, None)


def test_travel_to_returns_immediately_when_already_at_position() -> None:
    """Test that travel_to returns early if already at destination"""
    env = simpy.Environment()
    # Ensure Driver.env is set before instantiation
    Driver.env = env
    start_pos = Position([0.0, 0.0])
    driver = Driver(driver_id=1, position=start_pos, shift=DEFAULT_SHIFT)

    # Mock map map (shouldn't be called)
    mock_map = Mock()
    driver.set_map_controller(mock_map)

    # Travel to same position - process completes immediately
    env.process(driver.travel_to(start_pos))
    env.run(until=1)

    # Should return immediately without calling map map
    mock_map.get_route.assert_not_called()
    # Resource should still be at same position
    assert driver.position == start_pos


def test_travel_to_handles_tuple_return_from_route_next() -> None:
    """Test that travel_to correctly unpacks tuple from first route.next() call"""
    env = simpy.Environment()
    Driver.env = env
    start_pos = Position([0.0, 0.0])
    dest_pos = Position([1.0, 1.0])
    driver = Driver(driver_id=1, position=start_pos, shift=DEFAULT_SHIFT)

    # Mock route that returns tuple on first call, then positions
    mock_route = Mock()
    intermediate_pos = Position([0.5, 0.5])
    full_route_geometry = [start_pos, intermediate_pos, dest_pos]

    # First call returns tuple (next_position, route_geometry)
    # Subsequent calls return just positions, then None
    mock_route.next.side_effect = [
        (intermediate_pos, full_route_geometry),
        dest_pos,
        None,
    ]

    # Mock traffic multiplier (needed for traffic-aware travel logic)
    mock_route.get_current_traffic_multiplier.return_value = 1.0

    # Mock map map
    mock_map = Mock()
    mock_map.get_route.return_value = mock_route
    driver.set_map_controller(mock_map)

    # Execute travel
    env.process(driver.travel_to(dest_pos))
    env.run(until=10)

    # Verify route was obtained
    mock_map.get_route.assert_called_once_with(start_pos, dest_pos)

    # Verify resource moved through positions
    assert driver.position == dest_pos
    # current_route should be cleared after travel completes
    assert driver.current_route is None


def test_travel_to_handles_single_position_return_from_route_next() -> None:
    """Test that travel_to handles when route.next() returns just a position"""
    env = simpy.Environment()
    Driver.env = env
    start_pos = Position([0.0, 0.0])
    dest_pos = Position([1.0, 1.0])
    driver = Driver(driver_id=1, position=start_pos, shift=DEFAULT_SHIFT)

    # Mock route that returns single position (not tuple)
    mock_route = Mock()
    intermediate_pos = Position([0.5, 0.5])

    # Returns single positions, then None
    mock_route.next.side_effect = [
        intermediate_pos,
        dest_pos,
        None,
    ]

    # Mock traffic multiplier (needed for traffic-aware travel logic)
    mock_route.get_current_traffic_multiplier.return_value = 1.0

    # Mock map map
    mock_map = Mock()
    mock_map.get_route.return_value = mock_route
    driver.set_map_controller(mock_map)

    # Execute travel
    env.process(driver.travel_to(dest_pos))
    env.run(until=10)

    # Verify resource moved
    assert driver.position == dest_pos


def test_travel_to_can_be_interrupted() -> None:
    """Test that travel_to handles simpy.Interrupt correctly"""
    env = simpy.Environment()
    Driver.env = env
    start_pos = Position([0.0, 0.0])
    dest_pos = Position([5.0, 5.0])
    driver = Driver(driver_id=1, position=start_pos, shift=DEFAULT_SHIFT)

    # Mock route with many positions
    mock_route = Mock()
    positions = [Position([i * 1.0, i * 1.0]) for i in range(6)]

    mock_route.next.side_effect = [(positions[1], positions)] + positions[2:]

    # Mock traffic multiplier (needed for traffic-aware travel logic)
    mock_route.get_current_traffic_multiplier.return_value = 1.0

    # Mock map map
    mock_map = Mock()
    mock_map.get_route.return_value = mock_route
    driver.set_map_controller(mock_map)

    # Start travel process
    travel_process = env.process(driver.travel_to(dest_pos))

    # Interrupt after 2 time units
    def interrupter():  # type: ignore[no-untyped-def]
        yield env.timeout(2)
        travel_process.interrupt()

    env.process(interrupter())
    env.run(until=10)

    # Resource should not have reached destination due to interrupt
    assert driver.position != dest_pos


def test_driver_run_waits_for_initialization() -> None:
    """Test that driver run() yields at start to allow initialization"""
    env = simpy.Environment()
    Driver.env = env
    driver = Driver(driver_id=1, position=Position([0.0, 0.0]), shift=DEFAULT_SHIFT)
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(driver)
    driver.set_vehicle(vehicle)

    # Add a task so select_next_task will be called
    task = FakeTask(task_id=1)
    driver.assign_task(task)

    # Set up behaviour and map map after creation
    mock_behaviour = Mock(spec=SimBehaviour)
    mock_behaviour.RCNT_strategy = Mock()
    mock_behaviour.RCNT_strategy.select_next_task.return_value = task

    driver.set_behaviour(mock_behaviour)
    mock_map = Mock()
    driver.set_map_controller(mock_map)
    # Stub initial state to avoid AttributeError before run loop
    driver.state = DriverState.IDLE
    env.process(driver.run())
    # Run for 3 time units (1 for initial yield, then at least one iteration)
    env.run(until=3)

    # Should have called select_next_task at least once
    # (after initial timeout of 1)
    assert mock_behaviour.RCNT_strategy.select_next_task.call_count >= 1


def test_driver_run_selects_and_dispatches_task() -> None:
    """Test that driver run() selects and dispatches tasks correctly"""
    env = simpy.Environment()
    Driver.env = env
    start_pos = Position([0.0, 0.0])
    driver = Driver(driver_id=1, position=start_pos, shift=DEFAULT_SHIFT)
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(driver)
    driver.set_vehicle(vehicle)

    # Create a task at a station
    station_pos = Position([1.0, 1.0])
    station = Station(station_id=1, name="Station1", position=station_pos)
    station.env = env
    task = FakeTask(task_id=1, station=station)
    driver.assign_task(task)

    # Set up behaviour
    mock_behaviour = Mock(spec=SimBehaviour)
    mock_behaviour.RCNT_strategy = Mock()
    mock_behaviour.RCNT_strategy.select_next_task.return_value = task

    driver.set_behaviour(mock_behaviour)

    # Set up map map with mock route
    mock_route = Mock()
    mock_route.next.side_effect = [(station_pos, [start_pos, station_pos]), None]
    mock_route.get_current_traffic_multiplier.return_value = 1.0

    mock_map = Mock()
    mock_map.get_route.return_value = mock_route
    driver.set_map_controller(mock_map)
    # Stub initial state to avoid AttributeError before run loop
    driver.state = DriverState.IDLE

    # Run simulation for just enough time to dispatch but not complete
    env.process(driver.run())
    env.run(until=3)

    # Task should be dispatched (in progress) or already closed if it completed
    # Since the route completes quickly, task will likely be CLOSED
    assert task.get_state() in [State.IN_PROGRESS, State.CLOSED]
    # Verify RCNT strategy was called
    assert mock_behaviour.RCNT_strategy.select_next_task.called


def test_driver_run_services_task_when_at_station() -> None:
    """Test that driver services task when arriving at station"""
    env = simpy.Environment()
    Driver.env = env
    station_pos = Position([1.0, 1.0])

    # Create station first, THEN resource (so resource.run() starts)
    station = Station(station_id=1, name="Station1", position=station_pos)
    station.env = env
    driver = Driver(driver_id=1, position=station_pos, shift=DEFAULT_SHIFT)
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(driver)
    driver.set_vehicle(vehicle)

    # Create a task and manually set it to in-progress
    task = FakeTask(task_id=1, station=station)
    task.set_state(State.IN_PROGRESS)
    task.set_assigned_driver(driver)
    driver.task_list.append(task)
    driver.state = DriverState.SERVICING_STATION

    # Set up behaviour
    mock_behaviour = Mock(spec=SimBehaviour)
    mock_behaviour.RCNT_strategy = Mock()
    driver.set_behaviour(mock_behaviour)

    mock_map = Mock()
    driver.set_map_controller(mock_map)

    # Run simulation - need enough time for initial timeout + processing
    env.process(driver.run())
    env.run(until=5)

    # Task should be serviced (closed and removed)
    assert task.get_state() == State.CLOSED
    assert task not in driver.task_list


def test_driver_run_does_not_service_task_when_not_at_station() -> None:
    """Test that driver doesn't service task when not at station"""
    env = simpy.Environment()
    Driver.env = env
    resource_pos = Position([0.0, 0.0])
    station_pos = Position([1.0, 1.0])

    # Create station first
    station = Station(station_id=1, name="Station1", position=station_pos)
    driver = Driver(driver_id=1, position=resource_pos, shift=DEFAULT_SHIFT)

    # Create a task at a different station and manually set to in-progress
    task = FakeTask(task_id=1, station=station)
    task.set_state(State.IN_PROGRESS)
    task.set_assigned_driver(driver)
    driver.task_list.append(task)

    # Set up behaviour
    mock_behaviour = Mock(spec=SimBehaviour)
    driver.set_behaviour(mock_behaviour)

    mock_map = Mock()
    driver.set_map_controller(mock_map)

    # Run simulation for a short time
    env.run(until=3)

    # Task should still be in progress (not serviced) because
    # resource is not at the station
    assert task.get_state() == State.IN_PROGRESS


def test_driver_run_handles_no_tasks() -> None:
    """Test that driver run() handles case when there are no tasks"""
    env = simpy.Environment()
    Driver.env = env
    driver = Driver(driver_id=1, position=Position([0.0, 0.0]), shift=DEFAULT_SHIFT)

    # Set up behaviour
    mock_behaviour = Mock(spec=SimBehaviour)
    mock_behaviour.RCNT_strategy = Mock()
    mock_behaviour.RCNT_strategy.select_next_task.return_value = None
    driver.set_behaviour(mock_behaviour)

    mock_map = Mock()
    driver.set_map_controller(mock_map)

    # Run simulation
    env.run(until=5)

    # Should complete without errors
    assert len(driver.task_list) == 0


def test_driver_run_handles_none_station_on_task() -> None:
    """Test that driver run() handles tasks with None station"""
    env = simpy.Environment()
    Driver.env = env
    driver = Driver(driver_id=1, position=Position([0.0, 0.0]), shift=DEFAULT_SHIFT)

    # Create a task with no station
    task = FakeTask(task_id=1, station=None)
    driver.assign_task(task)

    # Set up behaviour to select the task
    mock_behaviour = Mock(spec=SimBehaviour)
    mock_behaviour.RCNT_strategy = Mock()
    mock_behaviour.RCNT_strategy.select_next_task.return_value = task

    driver.set_behaviour(mock_behaviour)

    mock_map = Mock()
    driver.set_map_controller(mock_map)

    # Run simulation - should not crash
    env.run(until=3)

    # Task should not be dispatched since station is None
    assert task in driver.task_list
