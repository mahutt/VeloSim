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

import time
import pytest
from unittest.mock import Mock

from sim.core.simulation_environment import SimulationEnvironment
from sim.entities.driver import Driver, DriverState
from sim.entities.position import Position
from sim.entities.shift import Shift
from sim.entities.vehicle import Vehicle


class MockClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = float(start)
        self.sleeps: list[float] = []

    def perf_counter(self) -> float:
        return self.now

    def sleep(self, dt: float) -> None:
        if dt and dt > 0:
            self.sleeps.append(dt)
            self.now += dt


@pytest.fixture()
def fake_time(monkeypatch: pytest.MonkeyPatch) -> MockClock:
    """Patch time functions so no real time passes during tests."""
    clock = MockClock()
    monkeypatch.setattr(time, "perf_counter", clock.perf_counter)
    monkeypatch.setattr(time, "sleep", clock.sleep)
    return clock


def make_shift(
    sim_start: float,
    sim_end: float,
    sim_lunch: float | None = None,
) -> Shift:
    """Helper to create a shift with sim-prefixed values set."""
    # Real-time values can mirror sim values for tests
    return Shift(
        start_time=sim_start,
        end_time=sim_end,
        lunch_break=sim_lunch,
        sim_start_time=sim_start,
        sim_end_time=sim_end,
        sim_lunch_break=sim_lunch,
    )


def test_off_shift_transitions_to_pending_when_within_two_hours(
    fake_time: MockClock,
) -> None:
    """Driver in OFF_SHIFT moves to PENDING_SHIFT when start is within 2 hours."""
    env = SimulationEnvironment()
    Driver.env = env
    # Start within 2 hours (3600s), end later
    shift = make_shift(sim_start=3600, sim_end=20000)
    driver = Driver(driver_id=1, position=Position([0.0, 0.0]), shift=shift)

    # Begin in OFF_SHIFT explicitly
    driver.state = DriverState.OFF_SHIFT
    # Minimal setup for run loop
    driver.set_behaviour(Mock())
    driver.set_map_controller(Mock())

    env.process(driver.run())
    env.run(until=2)

    assert driver.get_state() == DriverState.PENDING_SHIFT


def test_off_shift_stays_off_when_start_far_away(
    fake_time: MockClock,
) -> None:
    """Driver remains OFF_SHIFT when start time is more than 2 hours away."""
    env = SimulationEnvironment()
    Driver.env = env
    # Start far ahead (100000s), end later
    shift = make_shift(sim_start=100000, sim_end=200000)
    driver = Driver(driver_id=2, position=Position([0.0, 0.0]), shift=shift)

    driver.state = DriverState.OFF_SHIFT
    driver.set_behaviour(Mock())
    driver.set_map_controller(Mock())

    env.process(driver.run())
    env.run(until=2)

    assert driver.get_state() == DriverState.OFF_SHIFT


def test_idle_heads_to_hq_near_shift_end(
    fake_time: MockClock,
) -> None:
    """Driver in IDLE heads to HQ when close to shift end (buffer applies)."""
    env = SimulationEnvironment()
    Driver.env = env
    # End soon so buffer triggers immediately
    shift = make_shift(sim_start=0, sim_end=1000)
    driver = Driver(driver_id=3, position=Position([0.0, 0.0]), shift=shift)

    # Ensure driver is operational
    vehicle = Vehicle(vehicle_id=1, battery_count=10)
    vehicle.set_driver(driver)
    driver.set_vehicle(vehicle)

    # Behaviour that selects no task
    mock_behaviour = Mock()
    mock_behaviour.RCNT_strategy = Mock()
    mock_behaviour.RCNT_strategy.select_next_task.return_value = None
    driver.set_behaviour(mock_behaviour)
    driver.set_map_controller(Mock())

    driver.state = DriverState.IDLE
    env.process(driver.run())
    env.run(until=2)

    assert driver.get_state() == DriverState.HEADING_TO_HQ


def test_idle_enters_lunch_break_during_window(
    fake_time: MockClock,
) -> None:
    """Driver in IDLE enters ON_BREAK when current time is within lunch window."""
    env = SimulationEnvironment()
    Driver.env = env
    # Lunch at current time (0) so window condition is met immediately
    shift = make_shift(sim_start=0, sim_end=50000, sim_lunch=0)
    driver = Driver(driver_id=4, position=Position([0.0, 0.0]), shift=shift)

    vehicle = Vehicle(vehicle_id=2, battery_count=10)
    vehicle.set_driver(driver)
    driver.set_vehicle(vehicle)

    mock_behaviour = Mock()
    mock_behaviour.RCNT_strategy = Mock()
    mock_behaviour.RCNT_strategy.select_next_task.return_value = None
    driver.set_behaviour(mock_behaviour)
    driver.set_map_controller(Mock())

    driver.state = DriverState.IDLE
    env.process(driver.run())
    env.run(until=2)

    assert driver.get_state() == DriverState.ON_BREAK
