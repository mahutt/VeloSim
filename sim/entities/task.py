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
    from .driver import Driver
    from sim.behaviour.sim_behaviour import SimBehaviour


class Task(ABC):
    """Abstract base class for simulation tasks."""

    env: simpy.Environment
    spawn_time: float

    def __init__(
        self,
        task_id: int,
        station: Optional[Station] = None,
        spawn_time: float = 0.0,
    ) -> None:
        self.id: int = task_id
        self.station: Optional[Station] = station
        self.assigned_driver: Optional[Driver] = None
        self.has_updated = False
        self.state = State.OPEN
        self.spawn_time = spawn_time

    def _spawn_after_delay(self, delay: float) -> Generator[simpy.Event, None, None]:
        """Internal generator that spawns a task after a specified delay.

        This is a SimPy process that waits for the spawn delay and then transitions
        the task from SCHEDULED to OPEN state. Updates the task, station, and driver
        flags to trigger state change notifications.

        Args:
            delay: The simulation time delay before spawning the task.

        Yields:
            simpy.Event: SimPy timeout event for the delay period.
        """
        # Yield until scheduled time has been reached.
        yield self.env.timeout(delay)
        self.set_state(State.OPEN)
        self.has_updated = True
        if self.station is not None:
            self.station.has_updated = True
        if self.assigned_driver is not None:
            self.assigned_driver.has_updated = True

    @abstractmethod
    def get_state(self) -> State:
        """Get the current state of the task.

        Returns:
            State: The current state (SCHEDULED, OPEN, ASSIGNED, IN_PROGRESS,
                or CLOSED).
        """
        pass

    @abstractmethod
    def set_state(self, state: State) -> None:
        """Set the state of the task.

        Args:
            state: The new state to set for the task.

        Returns:
            None
        """
        pass

    @abstractmethod
    def get_task_id(self) -> int:
        """Get the unique identifier for this task.

        Returns:
            int: The task's unique ID.
        """
        pass

    @abstractmethod
    def get_station(self) -> Optional["Station"]:
        """Get the station where this task is located.

        Returns:
            Optional[Station]: The station assigned to this task, or None if
                no station is assigned.
        """
        pass

    @abstractmethod
    def set_station(self, station: "Station") -> None:
        """Set the station where this task is located.

        Args:
            station: The station to assign to this task.

        Returns:
            None
        """
        pass

    @abstractmethod
    def get_assigned_driver(self) -> Optional["Driver"]:
        """Get the driver assigned to work on this task.

        Returns:
            Optional[Driver]: The driver assigned to this task, or None if
                no driver is assigned.
        """
        pass

    @abstractmethod
    def set_assigned_driver(self, driver: "Driver") -> None:
        """Assign a driver to work on this task.

        Args:
            driver: The driver to assign to this task.

        Returns:
            None
        """
        pass

    @abstractmethod
    def unassign_driver(self) -> None:
        """Remove the driver assignment from this task.

        Clears the assigned_driver reference and typically transitions the task
        back to OPEN state.

        Returns:
            None
        """
        pass

    @abstractmethod
    def is_assigned(self) -> bool:
        """Check if the task is assigned to a driver.

        Returns:
            bool: True if the task is in ASSIGNED state, False otherwise.
        """
        pass

    def set_behaviour(self, behaviour: "SimBehaviour") -> None:
        """Set the simulation behavior controller for this task.

        Args:
            behaviour: The SimBehaviour instance that defines task-related
                behavioral strategies.

        Returns:
            None
        """
        self.behaviour = behaviour

    def clear_update(self) -> None:
        """Clear the update flag for this task.

        Resets the has_updated flag to False, indicating that changes to this
        task have been processed or acknowledged.

        Returns:
            None
        """
        self.has_updated = False

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary representation.

        Returns:
            Dictionary containing task ID, state, station ID, and driver ID.
        """
        return {
            "id": self.id,
            "state": str(self.state),
            "station_id": (self.station.id if self.station is not None else None),
            "assigned_driver_id": (
                self.assigned_driver.id if self.assigned_driver is not None else None
            ),
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Task):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
