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
import logging

from sim.map.MapController import MapController
from typing import Optional, TYPE_CHECKING
from .task_state import State
from sim.entities.route import Route
from typing import Generator, Any
from .position import Position

logger = logging.getLogger(__name__)

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .task import Task
    from sim.behaviour.sim_behaviour import SimBehaviour


class Resource:

    map_controller: MapController
    sim_behaviour: "SimBehaviour"
    current_route: Route | None
    env: simpy.Environment

    def __init__(
        self,
        resource_id: int,
        position: "Position",  # [longitude, latitude]
        task_list: list["Task"] | None = None,
    ) -> None:
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

    def reorder_tasks(
        self, task_ids_to_reorder: list[int], apply_from_top: bool
    ) -> list[int]:
        """
        Reorder tasks in the resource's task list.

        In-progress tasks are always pinned to the top in their original order.
        Specified task IDs are reordered according to the provided list.
        Unspecified tasks maintain their original order.

        Args:
            task_ids_to_reorder: Partial list of task IDs to reorder
            apply_from_top: If True, specified tasks inserted after in-progress tasks.
                           If False, specified tasks appended to end (reversed).

        Returns:
            List of task IDs in the new order

        Raises:
            ValueError: If task_ids_to_reorder is empty or contains duplicates
        """
        # Validation: empty list
        if not task_ids_to_reorder:
            raise ValueError("task_ids_to_reorder cannot be empty")

        # Validation: duplicates
        if len(task_ids_to_reorder) != len(set(task_ids_to_reorder)):
            raise ValueError("task_ids_to_reorder contains duplicate task IDs")

        # Build a map of task_id -> task for quick lookup
        current_task_map = {task.id: task for task in self.task_list}

        # Separate tasks into categories
        in_progress_tasks: list["Task"] = []
        specified_tasks: list["Task"] = []
        unspecified_tasks: list["Task"] = []

        # Track which IDs we've seen to maintain original order
        specified_ids_set = set(task_ids_to_reorder)

        # First pass: collect in-progress tasks in original order
        for task in self.task_list:
            if task.get_state() == State.IN_PROGRESS:
                in_progress_tasks.append(task)

        # Second pass: collect specified tasks (excl. in-progress)
        for task_id in task_ids_to_reorder:
            found_task = current_task_map.get(task_id)
            if found_task is None:
                # Check if task exists in global registry but not in this resource
                # Access controller via sim_behaviour if available
                if hasattr(self, "sim_behaviour") and hasattr(
                    self.sim_behaviour, "controller"
                ):
                    global_task = self.sim_behaviour.controller.get_task_by_id(task_id)
                    if global_task is not None:
                        if global_task.get_state() == State.CLOSED:
                            logger.warning(
                                f"Task {task_id} not in resource "
                                f"{self.id} task list - task has "
                                f"been completed (state: CLOSED)"
                            )
                        else:
                            logger.warning(
                                f"Task {task_id} not in resource "
                                f"{self.id} task list - task "
                                f"exists elsewhere or unassigned"
                            )
                    else:
                        logger.warning(
                            f"Task {task_id} not found in simulation - "
                            f"may not exist or invalid ID"
                        )
                else:
                    logger.warning(
                        f"Task {task_id} not in resource {self.id} task list"
                    )
            elif found_task.get_state() != State.IN_PROGRESS:
                # Only add if not already in in_progress_tasks
                specified_tasks.append(found_task)

        # Third pass: collect unspecified tasks (excl. in-progress)
        for task in self.task_list:
            if (
                task.id not in specified_ids_set
                and task.get_state() != State.IN_PROGRESS
            ):
                unspecified_tasks.append(task)

        # Build the new task list based on mode
        if apply_from_top:
            # [in_progress, specified, unspecified]
            new_task_list = in_progress_tasks + specified_tasks + unspecified_tasks
        else:
            # [in_progress, unspecified, reversed(specified)]
            new_task_list = (
                in_progress_tasks + unspecified_tasks + list(reversed(specified_tasks))
            )

        # Update the task list and mark as updated
        self.task_list = new_task_list
        self.has_updated = True

        # Return the new task ID order
        return [task.id for task in new_task_list]

    def travel_to(self, position: "Position") -> Generator[Any, None, None]:

        if self.position == position:
            return

        try:
            route = self.map_controller.getRoute(self.position, position)
        except ValueError as e:
            # Route could not be found (no path exists, network error, etc.)
            # Log the error and stay at current position
            print(
                f"Resource {self.id}: Cannot find route to "
                f"{position.get_position()}: {e}"
            )
            return

        self.current_route = route
        next_position = route.next()
        try:
            while self.position != position and next_position:
                # Handle case where route.next() returns tuple (position, geometry)
                if isinstance(next_position, tuple):
                    next_position = next_position[0]
                assert isinstance(
                    next_position, Position
                )  # route.next() returns Position when as_json=False
                self.set_resource_position(next_position)
                yield self.env.timeout(1)
                next_position = route.next()
        # Allows a traveling resource to be interrupted by other simpy entities
        except simpy.Interrupt:
            # TODO Implement interrupt logic
            pass
        finally:
            # Clear current route when travel completes or is interrupted
            self.current_route = None

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
                    # We have a task in progress
                    # Check if we're close enough to the station:
                    task_station = in_progress.get_station()
                    if task_station is not None and self.position.close_enough(
                        task_station.get_station_position()
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
