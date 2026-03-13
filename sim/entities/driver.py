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
import random
from enum import Enum

from sim.core.simulation_environment import SimulationEnvironment
from sim.map.map_controller import MapController
from grafana_logging.logger import get_logger
from typing import Optional, TYPE_CHECKING
from .task_state import State
from sim.entities.route import Route
from typing import Generator, Any
from .position import Position
from .shift import Shift

logger = get_logger(__name__)

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
    """Enumeration of driver states."""

    OFF_SHIFT = 0  # Off shift
    PENDING_SHIFT = 1  # Shift Starting soon
    IDLE = 2  # Waiting to be assigned a task and/or vehicle. Does have batteries
    ON_ROUTE = 3  # Traveling, specifically to a task.
    SERVICING_STATION = 4  # Servicing a station
    ON_BREAK = 5  # Taking a break
    SEEKING_HQ_FOR_INVENTORY = 6  # Is returning back to HQ to refill batteries
    RESTOCKING_BATTERIES = 7  # Is in the process of restocking on batteries at HQ
    ENDING_SHIFT = 8  # Heading to hq to end shift for the day

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
        elif self == DriverState.SEEKING_HQ_FOR_INVENTORY:
            return "seeking_hq_for_inventory"
        elif self == DriverState.RESTOCKING_BATTERIES:
            return "restocking"
        elif self == DriverState.ENDING_SHIFT:
            return "ending_shift"


class Driver:
    """Simulation driver entity that can be assigned tasks."""

    map_controller: MapController
    sim_behaviour: "SimBehaviour"
    current_route: Route | None
    env: SimulationEnvironment
    vehicle: Optional["Vehicle"]
    shift: Shift
    routes: list[Route]

    def __init__(
        self,
        driver_id: int,
        position: "Position",  # [longitude, latitude]
        shift: Shift,
        task_list: list["Task"] | None = None,
        vehicle: Optional["Vehicle"] = None,
        name: str | None = None,
        route: Optional["Route"] = None,
    ) -> None:
        self.id = driver_id
        self.name = name if name is not None else f"Driver {driver_id}"
        self.position = position
        self.current_route = route
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
        self.state: DriverState | None = None  # Overwritten by sim controller if needed
        self.routes = []

    def get_position(self) -> "Position":
        """Get the current position of the driver.

        Returns:
            Position: The current geographical position of the driver.
        """
        return self.position

    def get_state(self) -> DriverState | None:
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
        vehicle.set_driver(self)
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
            self.compute_routes()
            # Task state is now ASSIGNED (set by task.set_assigned_driver)

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
        in the task list and either in ASSIGNED state or IN_PROGRESS state.

        Args:
            task: The task to unassign from this driver.

        Returns:
            None
        """
        if task in self.task_list and (
            task.is_assigned() or task.get_state() == State.IN_PROGRESS
        ):
            self.task_list.remove(task)
            task.unassign_driver()
            # if self.get_task_count() == 0:
            #     self.state = DriverState.IDLE

            self.has_updated = True
            self.compute_routes()

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
            # Clear vehicle's driver reference
            vehicle.unassign_driver()
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

    def get_in_service_task(self) -> Optional["Task"]:
        """Get the task currently being serviced by this driver.

        Searches through the driver's task list for a task in IN_SERVICE state.
        Only one task should be in service at a time.

        Returns:
            Optional[Task]: The task currently in service, or None if no task
                is currently being serviced on.
        """
        for task in self.task_list:
            if task.get_state() == State.IN_SERVICE:
                return task
        return None

    def dispatch_task(self, task: "Task") -> None:
        """Dispatch a task to IN_PROGRESS state.

        Changes the task state from ASSIGNED to IN_PROGRESS. The task can only be
        dispatched if no other task is in progress. This ensures drivers can only work
        on one task at a time.

        Args:
            task: The task to dispatch. Must be in this driver's task list and
                in ASSIGNED state.

        Returns:
            None

        Raises:
            Exception: If attempting to dispatch a task
                while another task is in progress.
        """
        if task in self.task_list and task.is_assigned():
            task_in_progress = self.get_in_progress_task()
            if task_in_progress is None:
                task.set_state(State.IN_PROGRESS)
                self.has_updated = True
                self.compute_routes()
            else:
                raise Exception(
                    "Cannot dispatch this task since there exists "
                    "one already in-progress"
                )

    def service_task(self, task: "Task") -> Generator[Any, Any, None]:
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
            task_servicing_time = (
                self.sim_behaviour.TST_strategy.get_task_servicing_time()
            )

            for _ in range(task_servicing_time):
                yield self.env.timeout(1)
                self.env.report.increment_servicing_time()

            self.task_list.remove(task)
            battery_count = self.vehicle.use_battery()
            task.set_state(State.CLOSED)

            # increment completed task count for reporting.
            self.vehicle.tasks_completed += 1

            # Get service time and add it to reporting.
            spawn_time = getattr(task, "spawn_time", 0)
            self.env.report.add_service_time(self.env.now - spawn_time)

            self.has_updated = True
            self.compute_routes()

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
        for route in self.routes:
            route.has_traffic_changed = False

    def reorder_tasks(
        self, task_ids_to_reorder: list[int], apply_from_top: bool
    ) -> list[int]:
        """
        Reorder tasks in the driver's task list.

        In-service task is pinned at the top if any
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
        in_service_task = None
        specified_tasks: list["Task"] = []
        unspecified_tasks: list["Task"] = []

        # Track which IDs we've seen to maintain original order
        specified_ids_set = set(task_ids_to_reorder)

        # First pass: collect specified tasks (incl. in-progress)
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
            elif found_task.get_state() != State.IN_SERVICE:
                # in-service tasks should not be reordered
                specified_tasks.append(found_task)

        # Second pass: collect unspecified tasks (excl. in-service)
        for task in self.task_list:
            if (
                task.id not in specified_ids_set
                and task.get_state() != State.IN_SERVICE
            ):
                unspecified_tasks.append(task)
            elif task.get_state() == State.IN_SERVICE:
                in_service_task = task

        # Build the new task list based on mode
        if apply_from_top:
            # [in_service, specified, unspecified]
            new_task_list = specified_tasks + unspecified_tasks
        else:
            # [in_service, unspecified, reversed(specified)]
            new_task_list = unspecified_tasks + list(reversed(specified_tasks))

        # Add in-service task at top of list if not None
        if in_service_task is not None:
            new_task_list.insert(0, in_service_task)

        # If an in-progress task was reordered, set its state to ASSIGNED as the driver
        # will prioritize another task
        if new_task_list and new_task_list[0].get_state() != State.IN_PROGRESS:
            in_progress_task = self.get_in_progress_task()
            if in_progress_task is not None:
                in_progress_task.set_state(State.ASSIGNED)

        # Update the task list and mark as updated
        self.task_list = new_task_list
        self.has_updated = True
        self.compute_routes()

        # Return the new task ID order
        return [task.id for task in new_task_list]

    def travel_to_next_stop(self) -> Generator[Any, None, None]:
        """SimPy process that moves the driver to the next stop in their route.

        Traverses the first route in self.routes until completion or interruption.
        The route should already be computed via compute_routes().

        The driver will stop traveling if:
        - The route is completed
        - The driver's state is ON_ROUTE but there's no in-progress task
        - The process is interrupted by another SimPy entity

        Returns:
            Generator that yields timeout events during travel.
        """
        if not self.routes:
            return

        self.current_route = self.routes[0]
        next_position = self.current_route.next()
        try:
            while next_position:
                # Handle case where driver is on_route but in_progress task
                # got unassigned or reordered
                if (
                    self.state == DriverState.ON_ROUTE
                    and not self.get_in_progress_task()
                ):
                    return
                # Handle case where route.next() returns tuple (position, geometry)
                if isinstance(next_position, tuple):
                    next_position = next_position[0]
                assert isinstance(
                    next_position, Position
                )  # route.next() returns Position when as_json=False
                self.set_position(next_position)
                yield self.env.timeout(1)

                # increment driving time after timeout elapses.
                self.env.report.increment_driving_time()

                next_position = self.current_route.next()
            self.routes.pop(0)  # Remove the completed route
        # Allows a traveling drivers to be interrupted by other simpy entities
        except simpy.Interrupt:
            # TODO Implement interrupt logic
            self.compute_routes()

    def get_route_json(self) -> dict | None:
        """Get the current route for the driver in JSON format.

        Returns:
            Current route geometry as a dictionary, or None if no route is set.

            The dictionary has the key:
                - "coordinates": list[list[float]] of route coordinates.
        """

        if not self.routes:
            return None

        combined_raw_coordinates: list[list[float]] = []

        for route in self.routes:
            segment_coords = route.get_raw_coordinates()
            if segment_coords:
                # Remove duplicate coordinates at segment boundaries
                if combined_raw_coordinates:
                    segment_coords = segment_coords[1:]
                combined_raw_coordinates.extend(segment_coords)

        return {
            "coordinates": combined_raw_coordinates,
            "nextStopIndex": len(self.routes[0].get_raw_coordinates()) - 1,
        }

    @property
    def traffic_changed(self) -> bool:
        """Check if any route's traffic triples have changed.

        Returns:
            True if any route has pending traffic changes.
        """
        return any(route.has_traffic_changed for route in self.routes)

    def compute_routes(self) -> list[Route]:
        """
        Compute the full set of routes for the driver based on current state.

        Routes are currently affected by whether the driver is heading to HQ,
        and by the driver's visible tasks. This function should be called on every
        transition to / from HEADING_TO_HQ and on every modification of the
        visible task list.

        Returns:
            list[Route]: List of Route objects representing the driver's path.
        """
        stops: list[Position] = []

        if self.state in [
            DriverState.SEEKING_HQ_FOR_INVENTORY,
            DriverState.ENDING_SHIFT,
        ]:
            stops.append(self.env.hq.position)

        elif self.state == DriverState.ON_BREAK:
            if self.lunch_location is None:
                self.lunch_location = self._generate_lunch_location()
            stops.append(self.lunch_location)

        # Don't add task stops if ending shift
        if self.state != DriverState.ENDING_SHIFT:
            local_battery_count = (
                self.vehicle.get_battery_count() if self.vehicle else 0
            )

            for task in self.get_visible_task_list():
                station = task.get_station()
                if station is None or task.get_state() == State.IN_SERVICE:
                    continue
                stops.append(station.get_position())
                local_battery_count -= 1
                # add HQ to route if battery will deplete
                if local_battery_count == 0 and self.state not in [
                    DriverState.SEEKING_HQ_FOR_INVENTORY,
                    DriverState.ON_BREAK,
                    DriverState.ENDING_SHIFT,
                ]:
                    stops.append(self.env.hq.position)
                    local_battery_count = (
                        self.vehicle.max_battery_count if self.vehicle else 0
                    )

        new_routes: list[Route] = []

        for i in range(len(stops)):
            start_position = self.position if i == 0 else stops[i - 1]
            end_position = stops[i]
            try:
                route = self.map_controller.get_route(start_position, end_position)
                new_routes.append(route)
            except ValueError as e:
                print(
                    f"Driver {self.id}: Cannot get route from "
                    f"{start_position} to {end_position}: {e}"
                )
                break
        self.routes = new_routes
        self.route_changed = True
        return self.routes

    def return_to_HQ(self) -> Generator[Any, Any, Any]:
        """
        Make driver return to HQ.

        Returns:
            Generator that yields for travel_to_next_stop process.
        """
        self.compute_routes()
        yield self.env.process(self.travel_to_next_stop())

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

    def get_initial_state(self) -> DriverState:
        """
        Get a driver's initial state based on the time and their shift

        Implemented mostly for resumability convenience.
        A sim could start mid lunch break, near end of shift, etc.

        Returns:
            DriverState: The computed initial state for the driver.
        """
        current_sim_time = self.env.now
        start_time = self.shift.get_relative_start_time()
        end_time = self.shift.get_relative_end_time()
        lunch_time = self.shift.get_relative_lunch_break()

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
            self.state = DriverState.ENDING_SHIFT
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
            self.state = DriverState.SEEKING_HQ_FOR_INVENTORY
            return self.state

        # Has vehicle and batteries; if tasks exist, start from IDLE
        # Run loop will select and dispatch next task.
        self.state = DriverState.IDLE
        return self.state

    def _off_shift(self, current_sim_time: float) -> None:
        """Handle OFF_SHIFT transitions."""
        time_to_shift = self.shift.get_relative_start_time() - current_sim_time
        if 0 < time_to_shift <= 60 * 60 * 2:
            self.set_state(DriverState.PENDING_SHIFT)

    def _pending_shift(self, current_sim_time: float) -> None:
        """Handle PENDING_SHIFT transitions."""
        time_to_shift = self.shift.get_relative_start_time() - current_sim_time
        if time_to_shift <= 0:
            self.set_state(DriverState.IDLE)

    def _idle(self, current_sim_time: float) -> None:
        """Handle IDLE transitions and task dispatch decisions."""
        time_to_shift_end = self.shift.get_relative_end_time() - current_sim_time
        lunch_break = self.shift.get_relative_lunch_break()

        if self.vehicle is None and self.env.hq.has_vehicles():
            vehicle_to_assign = self.env.hq.pop_vehicle()
            if vehicle_to_assign is not None:
                # assign vehicle and use the local reference to satisfy type checkers
                self.set_vehicle(vehicle_to_assign)
                if (
                    vehicle_to_assign.get_battery_count()
                    < vehicle_to_assign.get_max_battery_count()
                ):
                    self.set_state(DriverState.RESTOCKING_BATTERIES)
                    return

        if time_to_shift_end <= SHIFT_END_BUFFER_TIME:
            self.set_state(DriverState.ENDING_SHIFT)
            return

        if self.vehicle is not None and self.vehicle.get_battery_count() == 0:
            # `set_state` mutates `self.state` and returns None — do not assign
            # its return value back to `self.state` (that would set it to None).
            self.set_state(DriverState.SEEKING_HQ_FOR_INVENTORY)
            return

        if (
            lunch_break is not None
            and lunch_break <= current_sim_time < lunch_break + LUNCH_BREAK_DURATION
        ):
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
                in_progress.set_state(State.IN_SERVICE)
                self.set_state(DriverState.SERVICING_STATION)
                return
            if task_station is not None:
                yield self.env.process(self.travel_to_next_stop())
                if self.get_in_progress_task() is not None:
                    in_progress.set_state(State.IN_SERVICE)
                    self.set_state(DriverState.SERVICING_STATION)
                    return
                # else sets state to IDLE
        self.set_state(DriverState.IDLE)

    def _servicing_station(self) -> Generator[Any, None, None]:
        """Handle SERVICING_STATION transitions."""
        in_service = self.get_in_service_task()
        if in_service is not None:
            yield self.env.process(self.service_task(in_service))
        self.set_state(DriverState.IDLE)

    def _on_break(self) -> Generator[Any, None, None]:
        self.compute_routes()
        yield self.env.process(self.travel_to_next_stop())

        yield self.env.timeout(LUNCH_BREAK_DURATION)
        self.set_state(DriverState.IDLE)

    def _seeking_hq_for_inventory(self) -> Generator[Any, None, None]:
        yield self.env.process(self.return_to_HQ())
        if self.position.close_enough(self.env.hq.position):
            self.set_state(DriverState.RESTOCKING_BATTERIES)

    def _ending_shift(self) -> Generator[Any, None, None]:
        yield self.env.process(self.return_to_HQ())
        if self.position.close_enough(self.env.hq.position):
            for task in self.task_list:
                self.unassign_task(task)

            if self.vehicle is not None:
                self.env.report.add_task_count_for_shift(self.vehicle.tasks_completed)
                self.vehicle.tasks_completed = 0
            self.unassign_vehicle()
            self.set_state(DriverState.OFF_SHIFT)

    def _restocking_batteries(self) -> Generator[Any, None, None]:
        """Handle RESTOCKING_BATTERIES: restock then return to IDLE."""
        yield self.env.process(self.restock_vehicle_battery())
        self.set_state(DriverState.IDLE)

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
        - ENDING_SHIFT: travel to HQ to end shift
        - SEEKING_HQ_FOR_INVENTORY: travel to HQ to refil batteries
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
                    yield from self._servicing_station()

                case DriverState.ON_BREAK:
                    yield from self._on_break()

                case DriverState.SEEKING_HQ_FOR_INVENTORY:
                    yield from self._seeking_hq_for_inventory()

                case DriverState.RESTOCKING_BATTERIES:
                    yield from self._restocking_batteries()

                case DriverState.ENDING_SHIFT:
                    yield from self._ending_shift()

            yield self.env.timeout(1)
