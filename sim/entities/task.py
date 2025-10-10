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

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
import simpy
from .task_state import State

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .station import Station
    from .resource import Resource


class Task(ABC):
    def __init__(
        self, env: simpy.Environment, task_id: int, station: Optional["Station"] = None
    ) -> None:
        self.env = env
        self.id: int = task_id
        self.state = State.OPEN  # A task would always be open at creation
        self.station: Optional["Station"] = station
        self.assigned_resource: Optional["Resource"] = (
            None  # Initially, no resource is assigned
        )

    @abstractmethod
    def get_state(self) -> State:
        pass

    @abstractmethod
    def set_state(self, state: State) -> None:
        pass

    @abstractmethod
    def get_task_id(self) -> int:
        pass

    @abstractmethod
    def get_station(self) -> Optional["Station"]:
        pass

    @abstractmethod
    def set_station(self, station: "Station") -> None:
        pass

    @abstractmethod
    def get_assigned_resource(self) -> Optional["Resource"]:
        pass

    @abstractmethod
    def set_assigned_resource(self, resource: "Resource") -> None:
        pass

    @abstractmethod
    def unassign_resource(self) -> None:
        pass

    @abstractmethod
    def is_assigned(self) -> bool:
        pass
