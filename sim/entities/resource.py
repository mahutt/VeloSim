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

from sim.map.MapController import MapController
from typing import Optional, TYPE_CHECKING
from .task_state import State
from sim.entities.route import Route
from typing import Generator, Any

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .position import Position
    from .task import Task
    from sim.behaviour.sim_behaviour import SimBehaviour


class Resource:

    map_controller: MapController
    sim_behaviour: "SimBehaviour"
    current_route: Route | None

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
        self.current_route = None
        if task_list is not None:
            self.task_list = task_list
            for task in self.task_list:
                task.set_assigned_resource(self)
        else:
            self.task_list = []
        self.has_updated = False  # flag to track if a resource was updated

    def get_resource_position(self) -> "Position":
        return self.position

    def set_behaviour(self, sim_behaviour: "SimBehaviour") -> None:
        self.sim_behaviour = sim_behaviour

    def set_resource_position(self, position: "Position") -> None:
        self.position = position
        self.has_updated = True

    def set_map_controller(self, map_controller: MapController) -> None:
        self.map_controller = map_controller

    def assign_task(self, task: "Task", dispatch_delay: Optional[float] = None) -> None:

        if task.get_state() == State.OPEN:
            self.task_list.append(task)
            task.set_assigned_resource(self)
            self.has_updated = True
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
            self.has_updated = True

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
                self.has_updated = True
            else:
                raise Exception("Cannot dispatch task at this station")

    # when a task has been completed, we want to remove it from the list of
    # tasks the resource needs to complete
    def service_task(self, task: "Task") -> None:
        if task in self.task_list:
            self.task_list.remove(task)
            task.set_state(State.CLOSED)
            self.has_updated = True

    def get_task_count(self) -> int:
        return len(self.task_list)

    def get_task_list(self) -> list["Task"]:
        return self.task_list

    def get_visible_task_list(self) -> list["Task"]:
        return [
            task
            for task in self.task_list
            if task.get_state() not in [State.SCHEDULED, State.CLOSED]
        ]

    def get_visible_task_count(self) -> int:
        return len(self.get_visible_task_list())

    def clear_update(self) -> None:
        self.has_updated = False

    def travel_to(self, position: "Position") -> Generator[Any, None, None]:

        if self.position == position:
            return

        route = self.map_controller.getRoute(self.position, position)
        self.current_route = route
        first_result = route.next()
        if isinstance(first_result, tuple):
            next_position, full_route = first_result
            self.current_route = full_route  # type: ignore[assignment]
        else:
            next_position = first_result  # type: ignore[assignment]
        try:
            while self.position != position and next_position:

                self.set_resource_position(next_position)
                yield self.env.timeout(1)
                next_position = route.next()  # type: ignore[assignment]
        # Allows a traveling resource to be interrupted by other simpy entities
        except simpy.Interrupt:
            # TODO Implement interrupt logic
            pass

    # continous process that runs throughout the simulation
    def run(self):  # type: ignore[no-untyped-def]
        # Yield once at the start to ensure sim_behaviour and
        # map_controller are set
        yield self.env.timeout(1)

        while True:
            # @TODO: replace with actual periodic logic

            # Select Next Task
            if len(self.task_list) > 0:
                in_progress = self.get_in_progress_task()
                # shorter, equivalent print for the in-progress task
                if in_progress:
                    # We have a task in progress - check if we're at the station
                    task_station = in_progress.get_station()
                    if (
                        task_station is not None
                        and self.position == task_station.get_station_position()
                    ):
                        self.service_task(in_progress)
                    elif task_station and not self.current_route:
                        yield self.env.process(
                            self.travel_to(task_station.get_station_position())
                        )
                    # If not at station, travel_to is still in progress
                else:
                    # No task in progress, select and dispatch next task
                    next_task = self.sim_behaviour.RCNT_strategy.select_next_task(self)
                    if next_task:
                        # Dispatch the task to mark it as in-progress
                        self.dispatch_task(next_task)
                        # Travel to the task's station
                        task_station = next_task.get_station()
                        if task_station is not None:
                            task_position = task_station.get_station_position()
                            yield self.env.process(self.travel_to(task_position))
                            if self.position == task_position:
                                self.service_task(next_task)

            # Wait for next tick
            yield self.env.timeout(1)
