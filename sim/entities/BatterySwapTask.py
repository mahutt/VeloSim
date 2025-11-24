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
from typing import Optional, TYPE_CHECKING
from .task import Task
from .task_state import State

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .station import Station
    from .resource import Resource


class BatterySwapTask(Task):
    env: simpy.Environment

    def __init__(
        self,
        task_id: int,
        station: Optional["Station"] = None,
        spawn_delay: Optional[float] = None,
    ) -> None:
        super().__init__(task_id, station, spawn_delay)

    def get_state(self) -> State:
        return self.state

    def set_state(self, state: State) -> None:
        self.state = state
        self.has_updated = True

    def get_task_id(self) -> int:
        return self.id

    def get_station(self) -> Optional["Station"]:
        return self.station

    def set_station(self, station: "Station") -> None:
        self.station = station

    def get_assigned_resource(self) -> Optional["Resource"]:
        return self.assigned_resource

    def set_assigned_resource(self, resource: "Resource") -> None:
        self.assigned_resource = resource
        self.state = State.ASSIGNED

    def unassign_resource(self) -> None:
        self.assigned_resource: Optional["Resource"] = None
        self.state = State.OPEN

    def is_assigned(self) -> bool:
        return self.assigned_resource is not None and self.state == State.ASSIGNED

    def clear_update(self) -> None:
        self.has_updated = False
