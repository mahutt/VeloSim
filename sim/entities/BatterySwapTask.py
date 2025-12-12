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
    """Task representing a battery swap operation at a station."""

    env: simpy.Environment

    def __init__(
        self,
        task_id: int,
        station: Optional["Station"] = None,
        spawn_delay: Optional[float] = None,
    ) -> None:
        super().__init__(task_id, station, spawn_delay)

    def get_state(self) -> State:
        """Get the current state of the task.

        Returns:
            The task state.
        """
        return self.state

    def set_state(self, state: State) -> None:
        """Set the state of the task.

        Args:
            state: The new task state.

        Returns:
            None
        """
        self.state = state
        self.has_updated = True

    def get_task_id(self) -> int:
        """Get the task ID.

        Returns:
            The task ID.
        """
        return self.id

    def get_station(self) -> Optional["Station"]:
        """Get the station associated with this task.

        Returns:
            The station if set, None otherwise.
        """
        return self.station

    def set_station(self, station: "Station") -> None:
        """Set the station for this task.

        Args:
            station: The station to associate with this task.

        Returns:
            None
        """
        self.station = station

    def get_assigned_resource(self) -> Optional["Resource"]:
        """Get the resource assigned to this task.

        Returns:
            The assigned resource if any, None otherwise.
        """
        return self.assigned_resource

    def set_assigned_resource(self, resource: "Resource") -> None:
        """Assign a resource to this task.

        Args:
            resource: The resource to assign.

        Returns:
            None
        """
        self.assigned_resource = resource
        self.state = State.ASSIGNED

    def unassign_resource(self) -> None:
        """Unassign the resource from this task.

        Returns:
            None
        """
        self.assigned_resource: Optional["Resource"] = None
        self.state = State.OPEN

    def is_assigned(self) -> bool:
        """Check if the task is assigned to a resource.

        Returns:
            True if assigned, False otherwise.
        """
        return self.assigned_resource is not None and self.state == State.ASSIGNED

    def clear_update(self) -> None:
        """Clear the update flag for this task.

        Returns:
            None
        """
        self.has_updated = False
