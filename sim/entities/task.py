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

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Generator, Optional, TYPE_CHECKING

import simpy

from .task_state import State

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .station import Station
    from .resource import Resource
    from sim.behaviour.sim_behaviour import SimBehaviour


class Task(ABC):
    def __init__(
        self,
        env: simpy.Environment,
        task_id: int,
        station: Optional[Station] = None,
        spawn_delay: Optional[float] = None,
    ) -> None:
        self.env = env
        self.id: int = task_id
        self.station: Optional[Station] = station
        self.assigned_resource: Optional[Resource] = None
        self.has_updated = False

        self.spawn_time: float = env.now + (spawn_delay if spawn_delay else 0)

        # Handle scheduling
        if spawn_delay is not None and spawn_delay > 0:
            # Task starts SCHEDULED, will become OPEN after delay
            self.state = State.SCHEDULED
            # Start self-spawning process
            env.process(self._spawn_after_delay(spawn_delay))
        else:
            # Task is immediately OPEN
            self.state = State.OPEN

    def _spawn_after_delay(self, delay: float) -> Generator[simpy.Event, None, None]:
        # Yield until scheduled time has been reached.
        yield self.env.timeout(delay)
        self.set_state(State.OPEN)

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

    def set_behaviour(self, behaviour: "SimBehaviour") -> None:
        self.behaviour = behaviour

    def clear_update(self) -> None:
        self.has_updated = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "state": str(self.state),
            "station_id": (self.station.id if self.station is not None else None),
            "assigned_resource_id": (
                self.assigned_resource.id
                if self.assigned_resource is not None
                else None
            ),
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
