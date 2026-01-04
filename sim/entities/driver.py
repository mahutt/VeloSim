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
from enum import Enum

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
    from .vehicle import Vehicle

HQ_POSITION = Position([-73.60175631192361, 45.52975346053039])
FULL_RESTOCK_TIME_SEC = 1200  # 20 minutes to fully restock


class DriverState(Enum):
    """Enumaration of driver states."""

    ON_SHIFT = 0  # Has tasks, but none in progress yet
    IDLE = 1  # Waiting to be assigned a task. Does have batteries
    IN_PROGRESS = 2  # Has a task in progress/dispatched or is servicing it
    HEADING_TO_HQ = 3  # Is returning back to HQ
    RESTOCKING_BATTERIES = 4  # Is in the process of restocking on batteries at HQ

    def __str__(self) -> str:
        if self == DriverState.ON_SHIFT:
            return "on_shift"
        elif self == DriverState.IDLE:
            return "idle"
        elif self == DriverState.IN_PROGRESS:
            return "in_progress"
        elif self == DriverState.HEADING_TO_HQ:
            return "heading_to_hq"
        elif self == DriverState.RESTOCKING_BATTERIES:
            return "restocking"


class Driver:
    """Simulation driver entity that can be assigned tasks."""

    map_controller: MapController
    sim_behaviour: "SimBehaviour"
    current_route: Route | None
    env: simpy.Environment
    vehicle: Optional["Vehicle"]

    def __init__(
        self,
        driver_id: int,
        position: "Position",  # [longitude, latitude]
        task_list: list["Task"] | None = None,
        vehicle: Optional["Vehicle"] = None,
    ) -> None:
        self.id = driver_id
        self.position = position
        self.current_route = None
        self.vehicle = vehicle
        self.route_changed = False  # flag to track if route geometry needs to be sent
        if task_list is not None:
            self.task_list = task_list
            for task in self.task_list:
                task.set_assigned_driver(self)
        else:
            self.task_list = []
        self.has_updated = False  # flag to track if a driver was updated
        # self.state = DriverState.ON_SHIFT  # directly on shift at creation (for now)
        if (
            len(self.task_list) == 0
            and self.vehicle is not None
            and self.vehicle.get_battery_count() != 0
        ):
            self.state = DriverState.IDLE
        else:
            self.state = DriverState.ON_SHIFT

    def get_position(self) -> "Position":
        """Get the current position of the driver.

        Returns:
            Position: The current geographical position of the driver.
        """
        return self.position

    def get_state(self) -> DriverState:
        """
        Get the driver's current state.

        Returns:
            state: The current state of the driver.
        """
        return self.state

    def get_vehicle(self) -> Optional["Vehicle"]:
        """Get the drivers current vehicle.

        Returns:
            Vehicle | None: The drivers current Vehicle if one is set. None otherwise.
        """
        return self.vehicle

    def set_vehicle(self, vehicle: "Vehicle") -> None:
        """Set the driver's current vehicle and mark it as updated.

        Args:
            vehicle: The vehicle to be associated with the driver.

        Returns:
            None
        """
        # Reject only if driver is bound to a DIFFERENT vehicle
        if self.vehicle is not None and self.vehicle.id != vehicle.id:
            raise Exception(
                f"Driver Error: driver: {self.id} "
                f"already assigned to vehicle: {self.vehicle.id}"
            )
        # Reject only if vehicle is bound to a DIFFERENT driver
        current_driver = vehicle.get_driver()
        if current_driver is not None and current_driver.id != self.id:
            raise Exception(
                f"Driver Error: vehicle: {vehicle.id} "
                f"already assigned to driver: {current_driver.id}"
            )
        self.vehicle = vehicle
        self.has_updated = True

    def set_behaviour(self, sim_behaviour: "SimBehaviour") -> None:
        """Set the simulation behavior controller for this driver.

        Args:
            sim_behaviour: The SimBehaviour instance that defines task selection,
                driver allocation, and other behavioral strategies.

        Returns:
            None
        """
        self.sim_behaviour = sim_behaviour

    def set_position(self, position: "Position") -> None:
        """Set the driver's position and mark it as updated.

        Args:
            position: The new geographical position for driver.

        Returns:
            None
        """
        self.position = position
        self.has_updated = True

    def set_map_controller(self, map_controller: MapController) -> None:
        """Set the map controller for route calculation and navigation.

        Args:
            map_controller: The MapController instance used for calculating routes
                and managing map-related operations.

        Returns:
            None
        """
        self.map_controller = map_controller

    def assign_task(self, task: "Task", dispatch_delay: Optional[float] = None) -> None:
        """Assign a task to this driver and optionally schedule dispatch.

        Adds the task to the driver's task list and updates the task's assigned
        driver reference. The task must be in OPEN state to be assigned.
        If a dispatch delay is provided, the task will be automatically dispatched
        after the specified delay; otherwise, it remains in ASSIGNED state until
        manually dispatched.

        Args:
            task: The task to assign to this driver. Must be in OPEN state.
            dispatch_delay: Optional delay in simulation time units before automatic
                dispatch. If None or 0, task remains ASSIGNED until manually dispatched.

        Returns:
            None
        """
        if task.get_state() == State.OPEN:
            self.task_list.append(task)
            task.set_assigned_driver(self)
            self.has_updated = True
            # Task state is now ASSIGNED (set by task.set_assigned_driver)

            # Change state to ON_SHIFT if was waiting for a task
            if self.state == DriverState.IDLE:
                self.state = DriverState.ON_SHIFT

            # Handle dispatch scheduling
            if dispatch_delay is not None and dispatch_delay > 0:
                # Schedule dispatch for later
                # Start self-dispatching process
                self.env.process(self._dispatch_after_delay(task, dispatch_delay))
            # else: Task remains ASSIGNED, can be dispatched manually later

    def _dispatch_after_delay(
        self, task: "Task", delay: float
    ) -> Generator[simpy.Event, None, None]:
        """Internal generator that dispatches a task after a specified delay.

        This is a SimPy process that waits for the specified delay and then
        dispatches the task if it's still assigned to this driver.

        Args:
            task: The task to dispatch after the delay.
            delay: The simulation time delay before dispatching the task.

        Yields:
            simpy.Event: SimPy timeout event for the delay period.
        """
        # Yield when time delta has been reached.
        yield self.env.timeout(delay)
        # Check task is still assigned to us
        if task in self.task_list and task.is_assigned():
            self.dispatch_task(task)

    def unassign_task(self, task: "Task") -> None:
        """Remove a task from this driver's task list.

        Removes the task from the driver's task list and clears the task's
        assigned driver reference. Only removes the task if it's currently
        in the task list and in ASSIGNED state.

        Args:
            task: The task to unassign from this driver.

        Returns:
            None
        """
        if task in self.task_list and task.is_assigned():
            self.task_list.remove(task)
            task.unassign_driver()
            if self.get_task_count() == 0:
                self.state = DriverState.IDLE

            self.has_updated = True

    def get_in_progress_task(self) -> Optional["Task"]:
        """Get the task currently being worked on by this driver.

        Searches through the driver's task list for a task in IN_PROGRESS state.
        Only one task should be in progress at a time.

        Returns:
            Optional[Task]: The task currently in progress, or None if no task
                is currently being worked on.
        """
        for task in self.task_list:
            if task.get_state() == State.IN_PROGRESS:
                return task
        return None

    def dispatch_task(self, task: "Task") -> None:
        """Dispatch a task to IN_PROGRESS state with station validation.

        Changes the task state from ASSIGNED to IN_PROGRESS. The task can only be
        dispatched if no other task is in progress, or if it's at the same station
        as the currently in-progress task. This ensures drivers can only work on
        tasks at one station at a time.

        Args:
            task: The task to dispatch. Must be in this driver's task list and
                in ASSIGNED state.

        Returns:
            None

        Raises:
            Exception: If attempting to dispatch a task at a different station
                while another task is in progress.
        """
        if task in self.task_list and task.is_assigned():
            task_in_progress = self.get_in_progress_task()
            if (
                task_in_progress is None
                or task.get_station() == task_in_progress.get_station()
            ):
                task.set_state(State.IN_PROGRESS)
                self.state = DriverState.IN_PROGRESS
                self.has_updated = True
            else:
                raise Exception("Cannot dispatch task at this station")

    def service_task(self, task: "Task") -> None:
        """Complete a task and remove it from the driver's task list.

        Marks the task as CLOSED and removes it from the driver's task list.
        Also uses up a battery from the vehicle.
        This should be called when a driver has finished servicing a task
        at its station.

        Args:
            task: The task to complete. Must be in this driver's task list.

        Returns:
            None
        """
        if (
            task in self.task_list
            and self.vehicle is not None
            and self.vehicle.get_battery_count() != 0
        ):
            self.task_list.remove(task)
            battery_count = self.vehicle.use_battery()
            task.set_state(State.CLOSED)
            self.state = (
                DriverState.ON_SHIFT if self.get_task_count() > 0 else DriverState.IDLE
            )
            self.has_updated = True

            if battery_count == 0:
                # return to HQ for refill
                self.env.process(self.return_to_HQ())

    def get_task_count(self) -> int:
        """Get the total number of tasks assigned to this driver.

        Returns:
            int: The total count of tasks in the driver's task list,
                including all states (SCHEDULED, ASSIGNED, IN_PROGRESS, etc.).
        """
        return len(self.task_list)

    def get_task_list(self) -> list["Task"]:
        """Get the complete list of tasks assigned to this driver.

        Returns:
            list[Task]: The full task list including tasks in all states.
        """
        tasks = self.task_list
        return tasks

    def get_visible_task_list(self) -> list["Task"]:
        """Get the list of tasks visible in the current simulation state.

        Filters out tasks that are SCHEDULED (not yet spawned) or CLOSED (completed).
        Visible tasks are those in OPEN, ASSIGNED, or IN_PROGRESS states.

        Returns:
            list[Task]: List of tasks that are currently visible and actionable.
        """
        return [
            task
            for task in self.task_list
            if task.get_state() not in [State.SCHEDULED, State.CLOSED]
        ]

    def get_visible_task_count(self) -> int:
        """Get the count of visible tasks assigned to this driver.

        Returns:
            int: The number of tasks that are currently visible (excludes
                SCHEDULED and CLOSED tasks).
        """
        return len(self.get_visible_task_list())

    def clear_update(self) -> None:
        """Clear the update flag for this driver.

        Resets the has_updated and route_changed flags to False, indicating
        that changes to this driver have been processed or acknowledged.

        Returns:
            None
        """
        self.has_updated = False
        self.route_changed = False

    def reorder_tasks(
        self, task_ids_to_reorder: list[int], apply_from_top: bool
    ) -> list[int]:
        """
        Reorder tasks in the driver's task list.

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
                # Check if task exists in global registry but not with this driver
                # Access controller via sim_behaviour if available
                if hasattr(self, "sim_behaviour") and hasattr(
                    self.sim_behaviour, "controller"
                ):
                    global_task = self.sim_behaviour.controller.get_task_by_id(task_id)
                    if global_task is not None:
                        if global_task.get_state() == State.CLOSED:
                            logger.warning(
                                f"Task {task_id} not associated with driver"
                                f"{self.id} task list - task has "
                                f"been completed (state: CLOSED)"
                            )
                        else:
                            logger.warning(
                                f"Task {task_id} not associated with driver "
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
                        f"Task {task_id} not associated to driver {self.id} task list"
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
        """SimPy process that moves the driver to a target position.

        Calculates a route using the MapController and traverses it
        step-by-step, updating the driver's position at each simulation tick.
        The process yields control back to the simulation environment at each
        step and can be interrupted.

        If the driver is already at the target position, the method returns
        immediately. If no route can be found, logs an error and stays at the
        current position.

        Args:
            position: The target Position to travel to.

        Yields:
            simpy.Event: Timeout events for each step of travel
                (1 time unit per step).

        Returns:
            Generator that yields timeout events during travel.
        """
        if self.position == position:
            return

        try:
            route = self.map_controller.getRoute(self.position, position)
        except ValueError as e:
            # Route could not be found (no path exists, network error, etc.)
            # Log the error and stay at current position
            print(
                f"Driver {self.id}: Cannot find route to "
                f"{position.get_position()}: {e}"
            )
            return

        self.current_route = route
        self.route_changed = True  # Mark that route geometry needs to be sent
        next_position = route.next()
        try:
            while self.position != position and next_position:
                # Handle case where route.next() returns tuple (position, geometry)
                if isinstance(next_position, tuple):
                    next_position = next_position[0]
                assert isinstance(
                    next_position, Position
                )  # route.next() returns Position when as_json=False
                self.set_position(next_position)
                yield self.env.timeout(1)
                next_position = route.next()
        # Allows a traveling drivers to be interrupted by other simpy entities
        except simpy.Interrupt:
            # TODO Implement interrupt logic
            pass
        finally:
            # Clear current route when travel completes or is interrupted
            self.current_route = None

    def return_to_HQ(self) -> Generator[Any, Any, Any]:
        """
        Make driver return to HQ.

        Sets driver state to HEADING_TO_HQ and makes the driver travel to HQ_Position.

        Returns:
            Generator that yields for travel_to process.
        """
        self.state = DriverState.HEADING_TO_HQ
        yield self.env.process(self.travel_to(HQ_POSITION))

    def restock_vehicle_battery(self) -> Generator[Any, Any, Any]:
        """
        Fully restock batteries of the vehicle.

        Re-stocking time is calculated according to the amount of batteries
        that are missing to be at full capacity.

        Returns:
            None
        """
        if self.vehicle is not None:
            # Calculate time it takes to re-stock batteries
            # Takes 20 minutes (1200 sec) to fully re-stock
            battery_count = self.vehicle.get_battery_count()
            max_battery_count = self.vehicle.max_battery_count
            batteries_to_add = max_battery_count - battery_count

            # Refill incrementally driver's vehicle's battery count
            if batteries_to_add > 0:
                interval = FULL_RESTOCK_TIME_SEC / max_battery_count
                for _ in range(int(batteries_to_add)):
                    yield self.env.timeout(interval)
                    self.vehicle.add_battery()

        # continues/starts shift
        if self.get_task_count() > 0:
            self.state = DriverState.ON_SHIFT
        else:  # waits for task
            self.state = DriverState.IDLE

    def run(self):  # type: ignore[no-untyped-def]
        """Main SimPy process that runs continuously throughout the simulation.

        This is the driver's main execution loop that handles task selection,
        dispatch, travel, and servicing. The process:
        1. Waits for initialization (sim_behaviour and map_controller setup)
        2. If vehicle's battery_count is 0, directly heads to HQ
        3. If driver has batteries and tasks available,
            selects and dispatches the next tasks
        4. If driver in-progress, travels to or services them
        5. If the driver arrives at HQ, restocks on batteries
        6. Yields control back to the simulation at each tick

        The process runs indefinitely until the simulation ends.

        Yields:
            simpy.Event: Timeout events and travel process events.
        """
        # Yield once at the start to ensure sim_behaviour and
        # map_controller are set
        yield self.env.timeout(1)

        while True:
            if self.state == DriverState.ON_SHIFT:
                if self.vehicle is not None and self.vehicle.get_battery_count() == 0:
                    # Return to HQ to restock
                    self.env.process(self.return_to_HQ())
                else:
                    # No task in progress, select and dispatch next task
                    next_task = self.sim_behaviour.RCNT_strategy.select_next_task(self)
                    if next_task:
                        # Dispatch the task to mark it as in-progress
                        self.dispatch_task(next_task)

            elif self.state == DriverState.IN_PROGRESS:
                # There is a task in progress
                # Check if we're close enough to the station:
                in_progress = self.get_in_progress_task()
                if in_progress is not None:
                    task_station = in_progress.get_station()
                    if task_station is not None and self.position.close_enough(
                        task_station.get_position()
                    ):
                        self.service_task(in_progress)
                    elif task_station is not None and not self.current_route:
                        yield self.env.process(
                            self.travel_to(task_station.get_position())
                        )
                    # If not at station, travel_to is still in progress

            elif self.state == DriverState.HEADING_TO_HQ:
                # Driver is heading to hq
                # Check if we're close enough to HQ:
                if self.position.close_enough(HQ_POSITION):
                    self.state = DriverState.RESTOCKING_BATTERIES
                    yield self.env.process(self.restock_vehicle_battery())

            # Wait for next tick
            yield self.env.timeout(1)
