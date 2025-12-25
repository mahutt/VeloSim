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

from typing import Optional, cast

from sim.entities.scenario import Scenario
from sim.entities.station import Station
from sim.entities.task import Task
from sim.entities.task_state import State
from sim.entities.driver import Driver
from sim.entities.vehicle import Vehicle


class MockDriver(Driver):
    def __init__(self, name: str) -> None:
        # Minimal stub: assign an id and ignore position/vehicle
        self.name = name
        self.id = hash(name)
        self.task_list = []


class MockStation(Station):
    def __init__(self, id: int) -> None:
        self.id = id


class MockTask(Task):
    def __init__(self, name: str) -> None:
        self._name: str = name
        self._state: State = State.IN_PROGRESS
        self._station: Optional[Station] = None
        # Driver-based assignment
        self._assigned_driver = None

    def get_task_id(self) -> int:
        return hash(self._name)

    def get_state(self) -> State:
        return self._state

    def set_state(self, state: State) -> None:
        self._state = state

    def get_station(self) -> Optional[Station]:
        return self._station

    def set_station(self, station: Optional[Station]) -> None:
        self._station = station

    def is_assigned(self) -> bool:
        return self._assigned_driver is not None

    # Implement required driver-based abstract methods for Task
    def get_assigned_driver(self):  # type: ignore[no-untyped-def]
        return self._assigned_driver

    def set_assigned_driver(self, driver):  # type: ignore[no-untyped-def]
        self._assigned_driver = driver
        if self._state != State.IN_PROGRESS:
            self._state = State.ASSIGNED

    def unassign_driver(self) -> None:
        self._assigned_driver = None
        if self._state != State.IN_PROGRESS:
            self._state = State.OPEN


def test_default_initialization() -> None:
    """Ensure Scenario initializes with empty lists when no arguments are passed."""
    scenario = Scenario()

    assert scenario.scenario_title is None
    assert scenario.start_time == ""
    assert scenario.end_time == ""
    assert scenario.drivers == []
    assert scenario.vehicles == []
    assert scenario.stations == []
    assert scenario.initial_tasks == []
    assert scenario.scheduled_tasks == []


def test_custom_initialization() -> None:
    """Ensure Scenario correctly sets custom values."""
    drivers = [MockDriver("alice"), MockDriver("bob")]
    vehicles = [Vehicle(vehicle_id=1, battery_count=999)]
    stations = [MockStation(1), MockStation(2)]
    initial_tasks = [MockTask("load"), MockTask("deliver")]
    scheduled_tasks = [MockTask("refuel")]

    scenario = Scenario(
        scenario_title="Morning Run",
        start_time="08:00",
        end_time="12:00",
        drivers=cast(list[Driver], drivers),
        vehicles=vehicles,
        stations=cast(list[Station], stations),
        initial_tasks=cast(list[Task], initial_tasks),
        scheduled_tasks=cast(list[Task], scheduled_tasks),
    )

    assert scenario.scenario_title == "Morning Run"
    assert scenario.start_time == "08:00"
    assert scenario.end_time == "12:00"
    assert scenario.drivers == drivers
    assert scenario.vehicles == vehicles
    assert scenario.stations == stations
    assert scenario.initial_tasks == initial_tasks
    assert scenario.scheduled_tasks == scheduled_tasks


def test_list_defaults_are_independent() -> None:
    """Ensure mutable defaults are not shared between instances."""
    s1 = Scenario()
    s2 = Scenario()
    s1.drivers.append(MockDriver("van"))

    assert len(s1.drivers) == 1
    assert len(s2.drivers) == 0


def test_str_representation() -> None:
    """Ensure __str__ provides a clear and accurate summary."""
    scenario = Scenario(
        scenario_title="Evening Shift",
        start_time="18:00",
        end_time="22:00",
        drivers=cast(list[Driver], [MockDriver("alice")]),
        vehicles=[Vehicle(vehicle_id=1, battery_count=999)],
        stations=cast(list[Station], [MockStation(1)]),
        initial_tasks=cast(list[Task], [MockTask("pickup")]),
        scheduled_tasks=cast(list[Task], [MockTask("return")]),
    )

    result = str(scenario)

    assert "ScenarioConfig(" in result
    assert "title='Evening Shift'" in result
    assert "drivers=1" in result
    assert "vehicles=1" in result
    assert "stations=1" in result
    assert "initial_tasks=1" in result
    assert "scheduled_tasks=1" in result
