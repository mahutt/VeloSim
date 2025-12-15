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
import simpy
import threading
from typing import Optional, Dict
from sim.entities.station import Station
from sim.core.frame_emitter import FrameEmitter
from sim.entities.task_state import State
from sim.entities.frame import Frame
from sim.entities.resource import Resource
from sim.entities.clock import Clock
from sim.entities.task import Task
from sim.entities.inputParameters import InputParameter
from sim.behaviour.sim_behaviour import SimBehaviour
from sim.map.MapController import MapController


class SimulatorController:
    """Main controller for simulation execution and entity management."""

    def __init__(
        self,
        simEnv: simpy.Environment,
        frameEmitter: FrameEmitter,
        inputParameters: InputParameter,
        sim_behaviour: SimBehaviour,
        strict: bool = False,
    ) -> None:
        self.simEnv = simEnv
        self.map_controller = MapController()
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

        # Unpack InputParameter object to populate entity lists
        self.station_entities: Dict[int, Station] = (
            inputParameters.get_station_entities()
        )
        self.resource_entities: Dict[int, Resource] = (
            inputParameters.get_resource_entities()
        )
        self.task_entities = inputParameters.get_task_entities()

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

        for _, resource in self.resource_entities.items():
            resource.set_behaviour(self.sim_behaviour)
            resource.set_map_controller(self.map_controller)
            # Rebind to the actual simulation environment
            resource.env = self.simEnv
            self.simEnv.process(resource.run())

    def start(self, sim_time: int) -> None:
        """Start the simulation for specified time.

        Args:
            sim_time: Duration to run the simulation in sim seconds.

        Returns:
            None
        """
        # Load entities into sim event queue and pass behaviour and/or mapcontroller
        self.prep_entities()
        # start sim clock
        self.clock.run()
        self.sim_time = sim_time
        self.sim_thread = threading.Thread(
            target=self.realTimeDriver.run_until, args=(sim_time, self.emit_frame)
        )
        self.sim_thread.start()

    def stop(self) -> None:
        """Stop the running simulation.

        Returns:
            None
        """
        self.realTimeDriver.stop()
        if hasattr(self, "sim_thread") and self.sim_thread.is_alive():
            self.sim_thread.join()

        final_frame = self.create_frame(is_key=True)
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

    def get_resource_by_id(self, resource_id: int) -> Optional[Resource]:
        """Get a resource by its ID.

        Args:
            resource_id: The resource ID to look up.

        Returns:
            The resource if found, None otherwise.
        """
        return self.resource_entities.get(resource_id)

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

    def assign_task_to_resource(
        self, task_id: int, resource_id: int, dispatch_delay: Optional[float] = None
    ) -> None:
        """Assign a task to a resource.

        Args:
            task_id: The task ID to assign.
            resource_id: The resource ID to assign to.
            dispatch_delay: Optional delay before task dispatch.

        Returns:
            None

        Raises:
            Exception: If task or resource not found.
        """
        found_task = self.get_task_by_id(task_id)
        found_resource = self.get_resource_by_id(resource_id)

        if found_task and found_resource:
            found_resource.assign_task(found_task, dispatch_delay)
        elif found_task is None:
            raise Exception(f"Could not find task in sim with id: {task_id}")
        else:
            raise Exception(f"Could not find resource in sim with id: {resource_id}")

    def unassign_task_from_resource(self, task_id: int, resource_id: int) -> None:
        """Unassign a task from a resource.

        Args:
            task_id: The task ID to unassign.
            resource_id: The resource ID to unassign from.

        Returns:
            None

        Raises:
            Exception: If task or resource not found.
        """
        found_task = self.get_task_by_id(task_id)
        found_resource = self.get_resource_by_id(resource_id)

        if found_task and found_resource:
            found_resource.unassign_task(found_task)
        elif found_task is None:
            raise Exception(f"Could not find task in sim with id: {task_id}")
        else:
            raise Exception(f"Could not find resource in sim with id: {resource_id}")

    def reassign_task(
        self,
        task_id: int,
        old_resource_id: int,
        new_resource_id: int,
        dispatch_delay: Optional[float] = None,
    ) -> None:
        """Reassign a task from one resource to another.

        Args:
            task_id: The task ID to reassign.
            old_resource_id: The current resource ID.
            new_resource_id: The new resource ID to assign to.
            dispatch_delay: Optional delay before task dispatch.

        Returns:
            None

        Raises:
            Exception: If task or resources not found.
        """
        try:
            self.unassign_task_from_resource(task_id, old_resource_id)
            self.assign_task_to_resource(task_id, new_resource_id, dispatch_delay)
        except Exception as e:
            error_message = str(e)
            if str(task_id) in error_message:
                raise Exception(
                    f"Reassigning task failed as could not find task {task_id}"
                )
            elif str(old_resource_id) in error_message:
                raise Exception(
                    f"Reassigning failed as could not find resource {old_resource_id}"
                )
            elif str(new_resource_id) in error_message:
                # Assigns back the task to its original resource as reassigning failed
                self.assign_task_to_resource(task_id, old_resource_id, dispatch_delay)
                raise Exception(
                    f"Reassigning failed as could not find resource {new_resource_id}"
                )
            else:
                raise Exception(f"Reassigning task failed due to error {e}")

    def reorder_resource_tasks(
        self, resource_id: int, task_ids_to_reorder: list[int], apply_from_top: bool
    ) -> list[int]:
        """
        Reorder tasks in a resource's task list.

        Args:
            resource_id: ID of the resource whose tasks should be reordered
            task_ids_to_reorder: Partial list of task IDs to reorder
            apply_from_top: If True, specified tasks inserted after in-progress.
                           If False, specified tasks appended to end (reversed).

        Returns:
            List of task IDs in the new order

        Raises:
            Exception: If resource not found or reordering fails
        """
        found_resource = self.get_resource_by_id(resource_id)

        if found_resource:
            return found_resource.reorder_tasks(task_ids_to_reorder, apply_from_top)
        else:
            raise Exception(f"Could not find resource in sim with id: {resource_id}")

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
        # Resources
        for resource in self.resource_entities.values():
            resource.clear_update()

    def create_frame(self, is_key: bool = False) -> Frame:
        """Create a frame containing entity data.

        Args:
            is_key: Whether to create a key frame (True) or diff frame (False).

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
            assigned_resource = task.get_assigned_resource()
            tasks.append(
                {
                    "id": task.get_task_id(),
                    "state": str(task.get_state()),
                    "stationId": task_station.id,
                    "assignedResourceId": (
                        assigned_resource.id if assigned_resource is not None else None
                    ),
                }
            )

        stations = [
            {
                "id": station.id,
                "name": station.name,
                "position": (station.get_station_position().get_position()),
                "taskIds": [task.id for task in station.get_visible_tasks()],
            }
            for station in self.station_entities.values()
            if (is_key or station.has_updated)
        ]

        resources = []
        for resource in self.resource_entities.values():
            if is_key or resource.has_updated:
                in_progress_task = resource.get_in_progress_task()
                resources.append(
                    {
                        "id": resource.id,
                        "position": (resource.get_resource_position().get_position()),
                        "taskIds": [
                            task.id for task in resource.get_visible_task_list()
                        ],
                        "inProgressTaskId": (
                            in_progress_task.get_task_id()
                            if in_progress_task is not None
                            else None
                        ),
                    }
                )

        payload = {
            "simId": self.frameEmitter.sim_id,
            "tasks": tasks,
            "stations": stations,
            "resources": resources,
            "clock": {
                "realSecondsPassed": self.clock.real_seconds_passed,
                "realMinutesPassed": self.clock.real_minutes_passed,
                "simSecondsPassed": self.clock.sim_time_seconds,
                "simMinutesPassed": self.clock.sim_time_minutes,
                "startTime": self.start_time,
            },
        }
        frame = Frame(seq_numb=self.frameCounter, payload=payload, is_key=is_key)
        return frame
