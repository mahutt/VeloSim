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

from dataclasses import dataclass
from typing import List, Optional

from sim.entities.driver import Driver
from sim.entities.vehicle import Vehicle
from sim.entities.station import Station
from sim.entities.task import Task


@dataclass
class Scenario:
    """Complete scenario definition with drivers, vehicles, stations, and tasks."""

    scenario_title: Optional[str]
    start_time: str
    end_time: str
    drivers: List[Driver]
    vehicles: List[Vehicle]
    stations: List[Station]
    initial_tasks: List[Task]
    scheduled_tasks: List[Task]

    def __init__(
        self,
        scenario_title: Optional[str] = None,
        start_time: str = "",
        end_time: str = "",
        drivers: Optional[List[Driver]] = None,
        vehicles: Optional[List[Vehicle]] = None,
        stations: Optional[List[Station]] = None,
        initial_tasks: Optional[List[Task]] = None,
        scheduled_tasks: Optional[List[Task]] = None,
    ):
        self.scenario_title = scenario_title
        self.start_time = start_time
        self.end_time = end_time
        self.drivers = drivers or []
        self.vehicles = vehicles or []
        self.stations = stations or []
        self.initial_tasks = initial_tasks or []
        self.scheduled_tasks = scheduled_tasks or []

    def __str__(self) -> str:
        """Readable string summary for debugging or logs."""
        return (
            f"ScenarioConfig("
            f"title='{self.scenario_title}', "
            f"start='{self.start_time}', end='{self.end_time}', "
            f"drivers={len(self.drivers)}, "
            f"vehicles={len(self.vehicles)}, "
            f"stations={len(self.stations)}, "
            f"initial_tasks={len(self.initial_tasks)}, "
            f"scheduled_tasks={len(self.scheduled_tasks)})"
        )
