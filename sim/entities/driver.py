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
import random
from enum import Enum

from sim.map.MapController import MapController
from typing import Optional, TYPE_CHECKING
from .task_state import State
from sim.entities.route import Route
from typing import Generator, Any
from .position import Position
from .shift import Shift

logger = logging.getLogger(__name__)

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .task import Task
    from sim.behaviour.sim_behaviour import SimBehaviour
    from .vehicle import Vehicle

# These constants will eventually be abstracted to logical classes,
# Or added to a new scenario schema in R3
FULL_RESTOCK_TIME_SEC = 1200  # 20 minutes to fully restock
LUNCH_BREAK_DURATION = 1800  # 30 minutes for lunch
LUNCH_DISTANCE_METERS = 1000  # Lunch location ~1km away
METERS_PER_DEGREE = 111111  # conversion factor for lunch location calculation
SHIFT_END_BUFFER_TIME = 1200  # Start Heading back to HQ 20 min before shifts


class DriverState(Enum):
    """Enumaration of driver states."""

    OFF_SHIFT = 0  # Off shift
    PENDING_SHIFT = 1  # Shift Starting soon
    IDLE = 2  # Waiting to be assigned a task and/or vehicle. Does have batteries
    ON_ROUTE = 3  # Traveling, specifically to a task.
    SERVICING_STATION = 4  # Servicing a station
    ON_BREAK = 5  # Taking a break
    HEADING_TO_HQ = (
        6  # Is returning back to HQ (Either off shift or going to get batteries)
    )
    RESTOCKING_BATTERIES = 7  # Is in the process of restocking on batteries at HQ

    def __str__(self) -> str:
        if self == DriverState.OFF_SHIFT:
            return "off_shift"
        elif self == DriverState.PENDING_SHIFT:
            return "pending_shift"
        elif self == DriverState.IDLE:
            return "idle"
        elif self == DriverState.ON_ROUTE:
            return "on_route"
        elif self == DriverState.SERVICING_STATION:
            return "servicing_station"
        elif self == DriverState.ON_BREAK:
            return "on_break"
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
    shift: Shift

    def __init__(
        self,
        driver_id: int,
        position: "Position",  # [longitude, latitude]
        shift: Shift,
        task_list: list["Task"] | None = None,
        vehicle: Optional["Vehicle"] = None,
    ) -> None:
        self.id = driver_id
        self.position = position
        self.current_route = None
        self.vehicle = vehicle
        self.route_changed = False  # flag to track if route geometry needs to be sent
        self.shift = shift
        # Parse shift into sim shift time
        self.lunch_location: Optional[Position] = None

        if task_list is not None:
            self.task_list = task_list
            for task in self.task_list:
                task.set_assigned_driver(self)
        else:
            self.task_list = []
        self.has_updated = False  # flag to track if a driver was updated
        self.state = DriverState.OFF_SHIFT  # Overwritten by sim controller if needed

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

    def set_state(self, state: DriverState) -> None:
        """Set the driver's state and mark it as updated.

        Args:
            state: The new `DriverState` to apply.

        Returns:
            None
        """
        self.state = state
        self.has_updated = True

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

    def get_driver_shift(self) -> Shift:
        """Get the driver's current shift.

        Returns:
            Shift: The driver's shift.
        """
        return self.shift

    def set_driver_shift(self, shift: Shift) -> None:
        """Set the driver's shift and mark it as updated.

        Args:
            shift: The Shift to associate with the driver.

        Returns:
            None
        """
        self.shift = shift
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
            self.route_changed = True
            # Task state is now ASSIGNED (set by task.set_assigned_driver)

            # Change state to ON_SHIFT if was waiting for a task
            # if self.state == DriverState.IDLE:
            #     self.state = DriverState.ON_SHIFT

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
            # if self.get_task_count() == 0:
            #     self.state = DriverState.IDLE

            self.has_updated = True
            self.route_changed = True

    def unassign_vehicle(self) -> None:
        """Unassign the current vehicle from this driver.

        Clears the association between the driver and its vehicle, and
        clears the vehicle's driver reference. After unassignment, the
        driver transitions to IDLE.

        Returns:
            None
        """
        if self.vehicle is not None:
            vehicle = self.vehicle
            # Clear driver's vehicle reference
            self.vehicle = None
            # Clear vehicle's driver reference (if method available)
            if hasattr(vehicle, "unassign_driver"):
                vehicle.unassign_driver()
            else:
                # Fallback in case vehicle lacks unassign_driver
                vehicle.driver = None
            self.env.hq.push_vehicle(vehicle)
            # Transition to IDLE since the driver has no vehicle
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
                self.has_updated = True
                self.route_changed = True
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
            self.has_updated = True
            self.route_changed = True

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
        self.route_changed = True

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
            route = self.map_controller.get_route(self.position, position)
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

    def get_full_route(self) -> dict | None:
        """Get the full route for all tasks in driver's task queue.

        Returns:
            Full route geometry and index where the next task's route ends,
            or None if there are no tasks / no route can be made.

            The dictionary has the keys:
                - "coordinates": list[list[float]] of route coordinates.
                - "nextTaskEndIndex": int index in coordinates where
                  the first task's route segment ends.
        """
        visible_tasks = self.get_visible_task_list()
        include_hq = self.state == DriverState.HEADING_TO_HQ

        if not visible_tasks and not include_hq:
            return None

        full_geometry: list[list[float]] = []
        next_task_end_index = 0
        current_pos = self.position

        # if driver needs to go to HQ, make HQ route the "next task"
        if include_hq:
            try:
                route = self.map_controller.get_route(current_pos, self.env.hq.position)
                segment_coords = route.get_raw_coordinates()

                if segment_coords:
                    full_geometry.extend(segment_coords)
                    next_task_end_index = len(full_geometry) - 1
                    current_pos = self.env.hq.position

            except ValueError as e:
                print(f"Driver {self.id}: Cannot get route to HQ: {e}")

        for task_idx, task in enumerate(visible_tasks):
            task_station = task.get_station()

            if task_station is None:
                continue

            target_pos = task_station.get_position()

            try:
                route = self.map_controller.get_route(current_pos, target_pos)
                segment_coords = route.get_raw_coordinates()

                if segment_coords:
                    if full_geometry and full_geometry[-1] == segment_coords[0]:
                        segment_coords = segment_coords[1:]

                    full_geometry.extend(segment_coords)

                    # set next_task_end_index to the next task if HQ isn't next
                    if task_idx == 0 and not include_hq:
                        next_task_end_index = len(full_geometry) - 1

                    current_pos = target_pos

            except ValueError as e:
                print(
                    f"Driver {self.id}: Cannot get route segment to {target_pos}: {e}"
                )
                break

        return (
            {"coordinates": full_geometry, "nextTaskEndIndex": next_task_end_index}
            if full_geometry
            else None
        )

    def return_to_HQ(self) -> Generator[Any, Any, Any]:
        """
        Make driver return to HQ.

        Sets driver state to HEADING_TO_HQ and makes the driver travel to HQ_Position.

        Returns:
            Generator that yields for travel_to process.
        """
        # self.state = DriverState.HEADING_TO_HQ
        self.route_changed = True
        yield self.env.process(self.travel_to(self.env.hq.position))

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

        # # continues/starts shift
        # if self.get_task_count() > 0:
        #     self.state = DriverState.ON_SHIFT
        # else:  # waits for task
        #     self.state = DriverState.IDLE

    def get_initial_state(self) -> DriverState:
        """
        Get a driver's initial state based on the time and their shift

        Implemented mostly for resumability convenience.
        A sim could start mid lunch break, near end of shift, etc.

        Returns:
            DriverState: The computed initial state for the driver.
        """
        current_sim_time = self.env.now
        start_time = self.shift.get_sim_start_time()
        end_time = self.shift.get_sim_end_time()
        lunch_time = self.shift.get_sim_lunch_break()

        # Before shift
        if current_sim_time < start_time - 2 * 60 * 60:
            self.state = DriverState.OFF_SHIFT
            return self.state

        # Within pending window ( 2 hours or less before start)
        if current_sim_time < start_time:
            self.state = DriverState.PENDING_SHIFT
            return self.state

        # Near or after shift end, wrap up by heading to HQ
        if current_sim_time >= end_time - SHIFT_END_BUFFER_TIME:
            self.state = DriverState.HEADING_TO_HQ
            return self.state

        # Lunch break window
        if (
            lunch_time is not None
            and lunch_time <= current_sim_time < lunch_time + LUNCH_BREAK_DURATION
        ):
            self.state = DriverState.ON_BREAK
            return self.state

        # During shift: determine operational readiness
        if self.vehicle is None:
            # No vehicle assigned: remain idle
            self.state = DriverState.IDLE
            return self.state

        if self.vehicle.get_battery_count() == 0:
            # Out of batteries: head to HQ to restock
            self.state = DriverState.HEADING_TO_HQ
            return self.state

        # Has vehicle and batteries; if tasks exist, start from IDLE
        # Run loop will select and dispatch next task.
        self.state = DriverState.IDLE
        return self.state

    def _off_shift(self, current_sim_time: float) -> None:
        """Handle OFF_SHIFT transitions."""
        time_to_shift = self.shift.get_sim_start_time() - current_sim_time
        if 0 < time_to_shift <= 60 * 60 * 2:
            self.set_state(DriverState.PENDING_SHIFT)

    def _pending_shift(self, current_sim_time: float) -> None:
        """Handle PENDING_SHIFT transitions."""
        time_to_shift = self.shift.get_sim_start_time() - current_sim_time
        if time_to_shift <= 0:
            self.set_state(DriverState.IDLE)

    def _idle(self, current_sim_time: float) -> None:
        """Handle IDLE transitions and task dispatch decisions."""
        time_to_shift_end = self.shift.get_sim_end_time() - current_sim_time
        lunch_break = self.shift.get_sim_lunch_break()

        if self.vehicle is None and self.env.hq.has_vehicles():
            self.set_vehicle(self.env.hq.pop_vehicle())

        if time_to_shift_end <= SHIFT_END_BUFFER_TIME or (
            self.vehicle is not None and self.vehicle.get_battery_count() == 0
        ):
            self.set_state(DriverState.HEADING_TO_HQ)
            return

        if (
            lunch_break is not None
            and lunch_break <= current_sim_time < lunch_break + LUNCH_BREAK_DURATION
        ):
            self.lunch_location = self._generate_lunch_location()
            self.set_state(DriverState.ON_BREAK)
            return

        if self.vehicle is not None and self.get_visible_task_count() > 0:
            next_task = self.sim_behaviour.RCNT_strategy.select_next_task(self)
            if next_task:
                self.dispatch_task(next_task)
                self.set_state(DriverState.ON_ROUTE)
                return

    def _on_route(self) -> Generator[Any, None, None]:
        """Handle ON_ROUTE travel and arrival transitions."""
        in_progress = self.get_in_progress_task()
        if in_progress is not None:
            task_station = in_progress.get_station()
            if task_station is not None and self.position.close_enough(
                task_station.get_position()
            ):
                self.set_state(DriverState.SERVICING_STATION)
                return
            if task_station is not None and not self.current_route:
                yield self.env.process(self.travel_to(task_station.get_position()))
                self.set_state(DriverState.SERVICING_STATION)
                return
        self.set_state(DriverState.IDLE)

    def _servicing_station(self) -> None:
        """Handle SERVICING_STATION transitions."""
        in_progress = self.get_in_progress_task()
        if in_progress is not None:
            self.service_task(in_progress)
        self.set_state(DriverState.IDLE)

    def _on_break(self) -> Generator[Any, None, None]:
        # travel to lunch location
        if self.lunch_location and not self.position.close_enough(self.lunch_location):
            yield self.env.process(self.travel_to(self.lunch_location))

        yield self.env.timeout(LUNCH_BREAK_DURATION)
        self.set_state(DriverState.IDLE)

    def _restocking_batteries(self) -> Generator[Any, None, None]:
        """Handle RESTOCKING_BATTERIES: restock then return to IDLE."""
        yield self.env.process(self.restock_vehicle_battery())
        self.set_state(DriverState.IDLE)

    def _heading_to_hq(self) -> Generator[Any, None, None]:
        """Handle HEADING_TO_HQ travel and arrival logic."""
        yield self.env.process(self.return_to_HQ())
        if self.position.close_enough(self.env.hq.position):
            current_sim_time = self.env.now
            time_to_shift_end = self.shift.get_sim_end_time() - current_sim_time

            if time_to_shift_end <= SHIFT_END_BUFFER_TIME:
                for task in self.task_list:
                    self.unassign_task(task)
                self.unassign_vehicle()
                self.set_state(DriverState.OFF_SHIFT)
                return

            if self.vehicle is not None and self.vehicle.get_battery_count() == 0:
                self.set_state(DriverState.RESTOCKING_BATTERIES)
                return

    def _generate_lunch_location(self) -> Position:
        """Generate a random lunch location
            LUNCH_DISTANCE_METERS away from driver's current position.

        Returns:
            Position: A new Position object representing the lunch location.
        """
        # convert meters to degrees
        offset = LUNCH_DISTANCE_METERS / METERS_PER_DEGREE
        current_lon, current_lat = self.position.get_position()

        delta_lon = random.uniform(-offset, offset)
        delta_lat = random.uniform(-offset, offset)

        return Position([current_lon + delta_lon, current_lat + delta_lat])

    def run(self):  # type: ignore[no-untyped-def]
        """Driver state machine in simple one-liners.

        - OFF_SHIFT: move to pending within 2h of shift start.
        - PENDING_SHIFT: switch to idle when shift starts.
        - IDLE: head to HQ near shift end or empty batteries; take lunch during
            window; dispatch task then go on_route; else stay idle.
        - ON_ROUTE: travel to task station; then service or go idle if none.
        - SERVICING_STATION: complete task and return to idle.
        - ON_BREAK: wait lunch duration, then return to idle.
        - HEADING_TO_HQ: travel to HQ; end shift (off_shift) at end time or
            restock if empty.
        - RESTOCKING_BATTERIES: restock batteries, then return to idle.
        """
        # Yield once at the start to ensure sim_behaviour and
        # map_controller are set
        yield self.env.timeout(1)

        while True:

            current_sim_time = self.env.now

            # Driver State Machine
            match self.state:

                case DriverState.OFF_SHIFT:
                    self._off_shift(current_sim_time)

                case DriverState.PENDING_SHIFT:
                    self._pending_shift(current_sim_time)

                case DriverState.IDLE:
                    self._idle(current_sim_time)

                case DriverState.ON_ROUTE:
                    yield from self._on_route()

                case DriverState.SERVICING_STATION:
                    self._servicing_station()

                case DriverState.ON_BREAK:
                    yield from self._on_break()

                case DriverState.RESTOCKING_BATTERIES:
                    yield from self._restocking_batteries()

                case DriverState.HEADING_TO_HQ:
                    yield from self._heading_to_hq()

            yield self.env.timeout(1)
