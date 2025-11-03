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
from typing import Optional, TYPE_CHECKING, Generator
from .task_state import State

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .position import Position
    from .task import Task


class Resource:
    # @TODO: add attribute for route once Route entity is implemented
    def __init__(
        self,
        env: simpy.Environment,
        resource_id: int,
        position: "Position",  # [longitude, latitude]
        task_list: list["Task"] | None = None,
    ) -> None:
        self.env = env
        self.id = resource_id
        self.position = position
        if task_list is not None:
            self.task_list = task_list
            for task in self.task_list:
                task.set_assigned_resource(self)
        else:
            self.task_list = []
        self.has_updated = False  # flag to track if a resource was updated

        # starting the process for periodic resource operations
        self.action = env.process(self.run())

    def get_resource_position(self) -> "Position":
        return self.position

    def set_resource_position(self, position: "Position") -> None:
        self.position = position

    def assign_task(self, task: "Task", dispatch_delay: Optional[float] = None) -> None:

        if task.get_state() == State.OPEN:
            self.task_list.append(task)
            task.set_assigned_resource(self)
            # Task state is now ASSIGNED (set by task.set_assigned_resource)
            # Handle dispatch scheduling
            if dispatch_delay is not None and dispatch_delay > 0:
                # Schedule dispatch for later
                # Start self-dispatching process
                self.env.process(self._dispatch_after_delay(task, dispatch_delay))
            # else: Task remains ASSIGNED, can be dispatched manually later

    def _dispatch_after_delay(
        self, task: "Task", delay: float
    ) -> Generator[simpy.Event, None, None]:
        # Yield when time delta has been reached.
        yield self.env.timeout(delay)
        # Check task is still assigned to us
        if task in self.task_list and task.is_assigned():
            self.dispatch_task(task)

    def unassign_task(self, task: "Task") -> None:
        if task in self.task_list and task.is_assigned():
            self.task_list.remove(task)
            task.unassign_resource()

    def get_in_progress_task(self) -> Optional["Task"]:
        for task in self.task_list:
            if task.get_state() == State.IN_PROGRESS:
                return task
        return None

    # dispatch a task in the list of tasks only if it is at the same station
    # as other in-progress tasks or if no other tasks are in-progress
    def dispatch_task(self, task: "Task") -> None:
        if task in self.task_list and task.is_assigned():
            task_in_progress = self.get_in_progress_task()
            if (
                task_in_progress is None
                or task.get_station() == task_in_progress.get_station()
            ):
                task.set_state(State.IN_PROGRESS)
            else:
                raise Exception("Cannot dispatch task at this station")

    # when a task has been completed, we want to remove it from the list of
    # tasks the resource needs to complete
    def service_task(self, task: "Task") -> None:
        if task in self.task_list:
            self.task_list.remove(task)
            task.set_state(State.CLOSED)

    def get_task_count(self) -> int:
        return len(self.task_list)

    def get_task_list(self) -> list["Task"]:
        return self.task_list

    def clear_update(self) -> None:
        self.has_updated = False

    # continous process that runs throughout the simulation
    def run(self):  # type: ignore[no-untyped-def]
        while True:
            # @TODO: replace with actual periodic logic
            yield self.env.timeout(1)
