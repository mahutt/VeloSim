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
import uuid
from sim.behaviour.sim_behaviour import SimBehaviour
from sim.entities.task_state import State
from .BatterySwapTask import BatterySwapTask
from typing import TYPE_CHECKING

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .task import Task
    from .position import Position


class Station:
    """Simulation station entity where tasks can be performed."""

    env: simpy.Environment

    def __init__(
        self,
        station_id: int,
        name: str,
        position: "Position",  # [longitude, latitude]
        tasks: list["Task"] | None = None,
    ) -> None:
        self.id = station_id
        self.name = name
        self.position = position
        self.tasks = (
            tasks if tasks is not None else []
        )  # list of tasks assigned to a given station
        self.has_updated = False
        self.pop_up_tasks: list["Task"] = []

    def add_task(self, task: "Task") -> None:
        """Add a task to this station's task list.

        Appends the task to the station's tasks list and sets this station
        as the task's assigned station.

        Args:
            task: The task to add to this station.

        Returns:
            None
        """
        self.tasks.append(task)
        task.set_station(self)

    def add_pop_up_task(self, task: "Task") -> None:
        """Add a newly spawned task to the pop-up tasks list.

        Pop-up tasks are tasks that appear dynamically during the simulation
        (e.g., new battery swap requests). This marks the station as updated
        to trigger UI/state notifications.

        Args:
            task: The newly spawned task to track as a pop-up task.

        Returns:
            None
        """
        self.pop_up_tasks.append(task)
        self.has_updated = True

    def remove_task(self, task: "Task") -> None:
        """Remove a task from this station's task list.

        Args:
            task: The task to remove from the station.

        Returns:
            None
        """
        if task in self.tasks:
            self.tasks.remove(task)

    def get_visible_tasks(self) -> list["Task"]:
        """Get the list of visible tasks at this station.

        Filters out tasks that are SCHEDULED (not yet spawned) or CLOSED (completed).
        Visible tasks are those in OPEN, ASSIGNED, or IN_PROGRESS states.

        Returns:
            list[Task]: List of tasks that are currently visible and actionable.
        """
        return [
            task
            for task in self.tasks
            if task.get_state() not in [State.SCHEDULED, State.CLOSED]
        ]

    def get_task_count(self) -> int:
        """Get the total number of tasks at this station.

        Returns:
            int: The total count of tasks including all states.
        """
        return len(self.tasks)

    def get_visible_task_count(self) -> int:
        """Get the count of visible tasks at this station.

        Returns:
            int: The number of tasks that are currently visible (excludes
                SCHEDULED and CLOSED tasks).
        """
        return len(self.get_visible_tasks())

    def get_position(self) -> "Position":
        """Get the geographical position of this station.

        Returns:
            Position: The station's position coordinates.
        """
        return self.position

    def set_behaviour(self, behaviour: SimBehaviour) -> None:
        """Set the simulation behavior controller for this station.

        Args:
            behaviour: The SimBehaviour instance that defines task pop-up
                strategies and other station behaviors.

        Returns:
            None
        """
        # Store behaviour consistently under 'behaviour'
        self.behaviour = behaviour

    def check_for_new_task(self) -> None:
        """Check if a new task should spawn at this station.

        Consults the Task Pop-Up (TPU) strategy from the behaviour controller
        to determine if a new task should be created. If a new task is needed,
        creates a BatterySwapTask and adds it to both the station's task list
        and pop-up task list.

        The task ID is temporarily generated using UUID for testing purposes.

        Returns:
            None
        """
        # Use the behaviour reference set via set_behaviour
        has_new_task = False
        if hasattr(self, "behaviour") and hasattr(self.behaviour, "TPU_strategy"):
            has_new_task = self.behaviour.TPU_strategy.check_for_new_task(self)

        if has_new_task:

            # TEMPORARY ID SOLUTION FOR TESTING
            task_id = uuid.uuid4().int % 1_000_000_000
            # Create BatterySwapTask and set its env attribute
            task = BatterySwapTask(task_id=task_id, station=self)
            task.env = self.env
            self.add_task(task)
            self.add_pop_up_task(task)

    def clear_update(self) -> None:
        """Clear the update flag for this station.

        Resets the has_updated flag to False, indicating that changes to this
        station have been processed or acknowledged.

        Returns:
            None
        """
        self.has_updated = False

    def run(self):  # type: ignore[no-untyped-def]
        """Main SimPy process that runs continuously throughout the simulation.

        This is the station's main execution loop that periodically checks for
        new tasks to spawn based on the Task Pop-Up strategy. The process:
        1. Waits for initialization (behaviour setup)
        2. Checks for new tasks at each simulation tick
        3. Yields control back to the simulation environment

        The process runs indefinitely until the simulation ends.

        Yields:
            simpy.Event: Timeout events for each simulation tick.
        """
        # Yield once at the start to ensure behaviour is set
        yield self.env.timeout(1)

        # TODO: replace with periodic operations
        while True:
            self.check_for_new_task()
            yield self.env.timeout(1)
