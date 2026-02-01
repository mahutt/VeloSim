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

from sim.core.RealTimeDriver import RealTimeDriver
import threading
from typing import Callable, Optional, Dict
from sim.core.types import BatchAssignResult
from sim.core.simulation_environment import SimulationEnvironment
from sim.entities.station import Station
from sim.core.frame_emitter import FrameEmitter
from sim.entities.task_state import State
from sim.entities.frame import Frame
from sim.entities.driver import Driver
from sim.entities.vehicle import Vehicle
from sim.entities.shift import Shift
from sim.entities.clock import Clock
from sim.entities.task import Task
from sim.entities.inputParameters import InputParameter
from sim.behaviour.sim_behaviour import SimBehaviour
from sim.map.MapController import MapController
from grafana_logging.logger import get_logger

logger = get_logger(__name__)


class SimulatorController:
    """Main controller for simulation execution and entity management."""

    def __init__(
        self,
        simEnv: SimulationEnvironment,
        frameEmitter: FrameEmitter,
        inputParameters: InputParameter,
        sim_behaviour: SimBehaviour,
        strict: bool = False,
        map_controller: MapController | None = None,
        on_completed_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.simEnv = simEnv

        self.map_controller = map_controller or MapController()

        # Get parameters directly from InputParameter object
        real_time_factor = inputParameters.get_real_time_factor()
        keyframe_freq = inputParameters.get_key_frame_freq()
        if keyframe_freq is None:
            keyframe_freq = 60

        self.realTimeDriver = RealTimeDriver(simEnv, real_time_factor, strict)
        self.frameEmitter = frameEmitter
        self.keyframeFreq = keyframe_freq
        self.clock = Clock(simEnv)
        self.sim_behaviour = sim_behaviour
        self.frameCounter: int = 0
        self.start_time: int = inputParameters.get_start_time()
        self.on_completed_callback = on_completed_callback

        # Unpack InputParameter object to populate entity lists
        self.station_entities: Dict[int, Station] = (
            inputParameters.get_station_entities()
        )
        self.driver_entities: Dict[int, Driver] = inputParameters.get_driver_entities()

        self.vehicle_entities: Dict[int, Vehicle] = (
            inputParameters.get_vehicle_entities()
        )

        self.task_entities = inputParameters.get_task_entities()
        self.prep_entities()

    def prep_entities(self) -> None:
        """Prepare all entities for simulation by setting behaviors and env.

        Returns:
            None
        """

        for _, station in self.station_entities.items():
            station.set_behaviour(self.sim_behaviour)
            # Rebind to the actual simulation environment
            station.env = self.simEnv
            self.simEnv.process(station.run())

        for _, task in self.task_entities.items():
            task.set_behaviour(self.sim_behaviour)
            # Rebind to the actual simulation environment
            task.env = self.simEnv
            task.spawn_time = self.simEnv.now + (
                task.spawn_delay if task.spawn_delay else 0
            )
            # Handle scheduling
            if task.spawn_delay is not None and task.spawn_delay > 0:
                # Task starts SCHEDULED, will become OPEN after delay
                task.state = State.SCHEDULED
                # Start self-spawning process
                self.simEnv.process(task._spawn_after_delay(task.spawn_delay))
            else:
                # Initial (non-scheduled) tasks are automatically
                # set to assigned in json_parser_strategy
                pass

        for _, driver in self.driver_entities.items():
            driver.set_behaviour(self.sim_behaviour)
            driver.set_map_controller(self.map_controller)

            driver.env = self.simEnv

            if driver.state is None:
                driver.state = driver.get_initial_state()

            self.simEnv.process(driver.run())

        for _, vehicle in self.vehicle_entities.items():
            vehicle.env = self.simEnv
            if vehicle.get_driver() is None:
                self.simEnv.hq.push_vehicle(vehicle)

    def start(self, sim_time: int) -> None:
        """Start the simulation.

        Args:
            sim_time (int): Total simulation time to run.

        Returns:
            None
        """
        # start sim clock
        self.clock.run()
        self.sim_time = sim_time

        def run() -> None:
            """Run the simulation loop until the configured simulation time.

            Returns:
                None
            """

            try:
                self.realTimeDriver.run_until(
                    until=sim_time,
                    step_callback=self.emit_frame,
                )
            finally:

                running_at_completion = self.realTimeDriver.running

                # Emit final keyframe only if sim ended naturally
                if running_at_completion:
                    final_frame = self.create_frame(
                        is_key=True,
                        paused_by_user=False,
                    )
                    self.emit_frame(final_frame)

                # If the sim reaches end_time, realTimeDriver.running = true
                # If diconnected/paused, realTimeDriver.running = false
                if running_at_completion and self.on_completed_callback:
                    self.on_completed_callback(self.frameEmitter.sim_id)

        self.sim_thread = threading.Thread(
            target=run,
        )
        self.sim_thread.start()

    def stop(self) -> None:
        """Stop the running simulation.

        Returns:
            None
        """
        # Capture running state before stopping - if already paused, the correct
        # keyframe was already emitted (by user pause or cleanup_simulation)
        was_running = self.realTimeDriver.running

        self.realTimeDriver.stop()
        if hasattr(self, "sim_thread") and self.sim_thread.is_alive():
            self.sim_thread.join()

        # Clean up map controller resources
        if hasattr(self, "map_controller") and self.map_controller:
            self.map_controller.close()

        # Only emit final keyframe if sim was still running (natural completion).
        # If already paused, the correct keyframe was already emitted with the
        # proper paused_by_user flag by either user pause or cleanup_simulation.
        if was_running:
            final_frame = self.create_frame(is_key=True, paused_by_user=False)
            self.emit_frame(final_frame)

    def pause(self) -> None:
        """Pause the running simulation.

        Returns:
            None
        """
        self.realTimeDriver.pause()

    def resume(self) -> None:
        """Resume the paused simulation.

        Returns:
            None
        """
        self.realTimeDriver.resume()

    def set_factor(self, factor: float) -> None:
        """Set the real-time factor for simulation pacing.

        Args:
            factor: Real seconds per simulated second.

        Returns:
            None
        """
        self.realTimeDriver.set_real_time_factor(factor)

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Get a task by its ID.

        Args:
            task_id: The task ID to look up.

        Returns:
            The task if found, None otherwise.
        """
        return self.task_entities.get(task_id)

    def get_driver_by_id(self, driver_id: int) -> Optional[Driver]:
        """Get a driver by its ID.

        Args:
            driver_id: The driver ID to look up.

        Returns:
            The driver if found, None otherwise.
        """
        return self.driver_entities.get(driver_id)

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        """Get a vehicle by its ID.

        Args:
            vehicle_id: The vehicle ID to look up.

        Returns:
            The vehicle if found, None otherwise.
        """
        return self.vehicle_entities.get(vehicle_id)

    def get_station_by_id(self, station_id: int) -> Optional[Station]:
        """Get a station by its ID.

        Args:
            station_id: The station ID to look up.

        Returns:
            The station if found, None otherwise.
        """
        return self.station_entities.get(station_id)

    def add_task(self, task: Task) -> None:
        """Add a new task to the simulation.

        Args:
            task: The task to add.

        Returns:
            None

        Raises:
            Exception: If a task with the same ID already exists.
        """
        task_id = task.get_task_id()
        found_task = self.get_task_by_id(task_id)

        if found_task is None:
            self.task_entities[task_id] = task
        else:  # task with same id exists already
            raise Exception(f"Task with id {task_id} already exists")

    def assign_task_to_driver(
        self, task_id: int, driver_id: int, dispatch_delay: Optional[float] = None
    ) -> None:
        """Assign a task to a driver.

        Args:
            task_id: The task ID to assign.
            driver_id: The driver ID to assign to.
            dispatch_delay: Optional delay before task dispatch.

        Returns:
            None

        Raises:
            Exception: If task or driver not found.
        """
        found_task = self.get_task_by_id(task_id)
        found_driver = self.get_driver_by_id(driver_id)

        if found_task and found_driver:
            found_driver.assign_task(found_task, dispatch_delay)
        elif found_task is None:
            raise Exception(f"Could not find task in sim with id: {task_id}")
        else:
            raise Exception(f"Could not find driver in sim with id: {driver_id}")

    def batch_assign_tasks_to_driver(
        self, driver_id: int, task_ids: list[int]
    ) -> list[BatchAssignResult]:
        """Best-effort assign many tasks to a single driver.

        Attempts to assign each task in ``task_ids`` to ``driver_id``. Each
        assignment is attempted independently; no rollback is performed.

        Args:
            driver_id: The driver to assign tasks to.
            task_ids: List of task IDs to assign to the driver.

        Returns:
            list[dict]: Per-item result dicts with keys ``task_id``,
            ``driver_id``, ``success`` (bool) and ``error`` (str|None).
        """
        results: list[BatchAssignResult] = []
        for task_id in task_ids:
            try:
                self.assign_task_to_driver(task_id, driver_id)
                results.append(
                    {
                        "task_id": task_id,
                        "driver_id": driver_id,
                        "success": True,
                        "error": None,
                    }
                )
            except Exception as e:
                logger.warning(
                    "Batch assign failed for task %s (driver %s): %s",
                    task_id,
                    driver_id,
                    e,
                )
                results.append(
                    {
                        "task_id": task_id,
                        "driver_id": driver_id,
                        "success": False,
                        "error": str(e),
                    }
                )
        return results

    def unassign_task_from_driver(self, task_id: int, driver_id: int) -> None:
        """Unassign a task from a driver.

        Args:
            task_id: The task ID to unassign.
            driver_id: The driver ID to unassign from.

        Returns:
            None

        Raises:
            Exception: If task or driver not found.
        """
        found_task = self.get_task_by_id(task_id)
        found_driver = self.get_driver_by_id(driver_id)

        if found_task and found_driver:
            found_driver.unassign_task(found_task)
        elif found_task is None:
            raise Exception(f"Could not find task in sim with id: {task_id}")
        else:
            raise Exception(f"Could not find driver in sim with id: {driver_id}")

    def reassign_task(
        self,
        task_id: int,
        old_driver_id: int,
        new_driver_id: int,
        dispatch_delay: Optional[float] = None,
    ) -> None:
        """Reassign a task from one driver to another.

        Args:
            task_id: The task ID to reassign.
            old_driver_id: The current driver ID.
            new_driver_id: The new driver ID to assign to.
            dispatch_delay: Optional delay before task dispatch.

        Returns:
            None

        Raises:
            Exception: If task or drivers not found.
        """
        try:
            self.unassign_task_from_driver(task_id, old_driver_id)
            self.assign_task_to_driver(task_id, new_driver_id, dispatch_delay)
        except Exception as e:
            error_message = str(e)
            if str(task_id) in error_message:
                raise Exception(
                    f"Reassigning task failed as could not find task {task_id}"
                )
            elif str(old_driver_id) in error_message:
                raise Exception(
                    f"Reassigning failed as could not find driver {old_driver_id}"
                )
            elif str(new_driver_id) in error_message:
                # Assigns back the task to its original driver as reassigning failed
                self.assign_task_to_driver(task_id, old_driver_id, dispatch_delay)
                raise Exception(
                    f"Reassigning failed as could not find driver {new_driver_id}"
                )
            else:
                raise Exception(f"Reassigning task failed due to error {e}")

    def reorder_driver_tasks(
        self, driver_id: int, task_ids_to_reorder: list[int], apply_from_top: bool
    ) -> list[int]:
        """
        Reorder tasks in a driver's task list.

        Args:
            driver_id: ID of the driver whose tasks should be reordered
            task_ids_to_reorder: Partial list of task IDs to reorder
            apply_from_top: If True, specified tasks inserted after in-progress.
                           If False, specified tasks appended to end (reversed).

        Returns:
            List of task IDs in the new order

        Raises:
            Exception: If driver not found or reordering fails
        """
        found_driver = self.get_driver_by_id(driver_id)

        if found_driver:
            return found_driver.reorder_tasks(task_ids_to_reorder, apply_from_top)
        else:
            raise Exception(f"Could not find driver in sim with id: {driver_id}")

    # First frame sent from back to front end with station data, etc
    def emit_initial_frame(self) -> None:
        """Emit the initial key frame with all entity data.

        Returns:
            None
        """
        frame = self.create_frame(is_key=True)
        self.emit_frame(frame)

    # Should call frame emitter
    def emit_frame(self, frame: Optional[Frame] = None) -> None:
        """Emit a frame to all subscribers.

        Args:
            frame: Optional frame to emit; if None, creates key or diff frame.

        Returns:
            None
        """
        # generate key frame if the current frame is a multiple of the n
        # specified for key frames
        if not frame:
            is_key = (
                self.frameCounter % self.keyframeFreq == 0
                or self.frameCounter == self.sim_time
                or self.frameCounter == 0
            )
            frame = self.create_frame(is_key=is_key)
        self.frameEmitter.notify(frame=frame)
        # After emitting the frame, clear update flags so only fresh
        # changes appear next time
        self.clear_entity_updates()
        self.frameCounter += 1

    def clear_entity_updates(self) -> None:
        """Clear update flags on all entities after emitting frame.

        Returns:
            None
        """
        # Tasks
        for task in self.task_entities.values():
            task.clear_update()
        # Stations
        for station in self.station_entities.values():
            station.clear_update()
        # Drivers
        for driver in self.driver_entities.values():
            driver.clear_update()
        # Vehicles
        for vehicle in self.vehicle_entities.values():
            vehicle.clear_update()

    def create_frame(self, is_key: bool = False, paused_by_user: bool = False) -> Frame:
        """Create a frame containing entity data.

        Args:
            is_key: Whether to create a key frame (True) or diff frame (False).
            paused_by_user: Whether this keyframe represents a user-initiated pause.

        Returns:
            A Frame object with the current entity states.
        """

        # Collect newly created pop-up tasks for inclusion in frame
        # Aggregate newly created pop-up tasks from stations (if any)
        new_task_objects = [
            task
            for station in self.station_entities.values()
            for task in getattr(station, "pop_up_tasks", [])
        ]

        # Ensure pop-up tasks are added to global task_entities
        for task in new_task_objects:
            tid = task.get_task_id()
            task.has_updated = True  # Mark new tasks as updated for diff frame
            if tid not in self.task_entities:
                self.task_entities[tid] = task

        # Clear pop-up tasks after including them in the frame to avoid duplicates
        if new_task_objects:
            for station in self.station_entities.values():
                if getattr(station, "pop_up_tasks", None):
                    station.pop_up_tasks.clear()

        tasks = []
        for task in self.task_entities.values():
            task_station = task.get_station()
            if (
                not is_key and not task.has_updated
            ) or task_station is None:  # stationId should not be null
                continue
            assigned_driver = task.get_assigned_driver()
            tasks.append(
                {
                    "id": task.get_task_id(),
                    "state": str(task.get_state()),
                    "stationId": task_station.id,
                    "assignedDriverId": (
                        assigned_driver.id if assigned_driver is not None else None
                    ),
                }
            )

        stations = [
            {
                "id": station.id,
                "name": station.name,
                "position": (station.get_position().get_position()),
                "taskIds": [task.id for task in station.get_visible_tasks()],
            }
            for station in self.station_entities.values()
            if (is_key or station.has_updated)
        ]

        drivers = []
        for driver in self.driver_entities.values():
            if is_key or (driver.has_updated):
                in_progress_task = driver.get_in_progress_task()
                current_vehicle = driver.get_vehicle()
                shift: Shift = driver.get_driver_shift()
                # Build driver data
                driver_data = {
                    "id": driver.id,
                    "name": driver.name,
                    "position": (driver.get_position().get_position()),
                    "taskIds": [task.id for task in driver.get_visible_task_list()],
                    "state": str(driver.get_state()),
                    "inProgressTaskId": (
                        in_progress_task.get_task_id()
                        if in_progress_task is not None
                        else None
                    ),
                    "shift": {
                        "startTime": shift.get_start_time(),
                        "endTime": shift.get_end_time(),
                        "lunchBreak": shift.get_lunch_break(),
                    },
                    "vehicleId": (
                        current_vehicle.id if current_vehicle is not None else None
                    ),
                }

                # Include route in key frames (for replayability) or when route changes
                # Only include route field when there's something to communicate:
                # - Key frames: always include (coordinates or null)
                # - Diff frames: only include if route_changed
                if is_key or driver.route_changed:
                    driver_data["route"] = driver.get_route_json()

                drivers.append(driver_data)

        vehicles = []
        for vehicle in self.vehicle_entities.values():
            if is_key or vehicle.has_updated:
                current_driver = vehicle.get_driver()
                vehicles.append(
                    {
                        "id": vehicle.id,
                        "batteryCount": vehicle.get_battery_count(),
                        "batteryCapacity": vehicle.get_max_battery_count(),
                        "driverId": (
                            current_driver.id if current_driver is not None else None
                        ),
                    }
                )

        payload = {
            "simId": self.frameEmitter.sim_id,
            "headquarters": {
                "position": self.simEnv.hq.position.get_position(),
            },
            "tasks": tasks,
            "stations": stations,
            "drivers": drivers,
            "vehicles": vehicles,  # Placeholder for future vehicle entities
            "clock": {
                "realSecondsPassed": self.clock.real_seconds_passed,
                "realMinutesPassed": self.clock.real_minutes_passed,
                "simSecondsPassed": self.clock.sim_time_seconds,
                "simMinutesPassed": self.clock.sim_time_minutes,
                "startTime": self.start_time,
                "running": self.realTimeDriver.running,
                "realTimeFactor": self.realTimeDriver.real_time_factor,
                "pausedByUser": paused_by_user,
            },
        }
        frame = Frame(seq_numb=self.frameCounter, payload=payload, is_key=is_key)
        return frame
