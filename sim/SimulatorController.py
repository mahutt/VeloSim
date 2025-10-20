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

from sim.RealTimeDriver import RealTimeDriver
import simpy
import threading
from typing import List, Optional
from sim.entities.station import Station
from sim.frame_emitter import FrameEmitter
from sim.entities.frame import Frame
from sim.entities.resource import Resource
from sim.entities.clock import Clock
from sim.entities.task import Task
from sim.entities.inputParameters import InputParameter


class SimulatorController:

    def __init__(
        self,
        simEnv: simpy.Environment,
        frameEmitter: FrameEmitter,
        inputParameters: InputParameter,
        strict: bool = False,
    ) -> None:
        self.simEnv = simEnv

        # Get parameters directly from InputParameter object
        real_time_factor = inputParameters.get_real_time_factor()
        keyframe_freq = inputParameters.get_key_frame_freq()
        if keyframe_freq is None:
            keyframe_freq = 60

        self.realTimeDriver = RealTimeDriver(simEnv, real_time_factor, strict)
        self.frameEmitter = frameEmitter
        self.keyframeFreq = keyframe_freq
        self.clock = Clock(simEnv)

        # Unpack InputParameter object to populate entity lists
        self.stationEntities: List[Station] = inputParameters.get_station_entities()
        self.resourceEntities: List[Resource] = inputParameters.get_resource_entities()
        self.taskEntities: List[Task] = inputParameters.get_task_entities()

        # Initialize frame counter
        self.frameCounter: int = 0

    def start(self, simTime: int) -> None:
        # TODO process initial entities into the sim env
        # start sim clock
        self.clock.run()
        self.sim_thread = threading.Thread(
            target=self.realTimeDriver.run_until, args=(simTime, self.emit_frame)
        )
        self.sim_thread.start()

    def stop(self) -> None:
        self.realTimeDriver.stop()
        if hasattr(self, "sim_thread") and self.sim_thread.is_alive():
            self.sim_thread.join()

    def pause(self) -> None:
        self.realTimeDriver.pause()

    def resume(self) -> None:
        self.realTimeDriver.resume()

    def set_factor(self, factor: float) -> None:
        self.realTimeDriver.set_real_time_factor(factor)

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        for task in self.taskEntities:
            if task.id == task_id:
                return task
        return None

    def get_resource_by_id(self, resource_id: int) -> Optional[Resource]:
        for resource in self.resourceEntities:
            if resource.id == resource_id:
                return resource
        return None

    def assign_task_to_resource(self, task_id: int, resource_id: int) -> None:
        found_task = self.get_task_by_id(task_id)
        found_resource = self.get_resource_by_id(resource_id)

        if found_task and found_resource:
            found_resource.assign_task(found_task)
        elif found_task is None:
            raise Exception(f"Could not find task in sim with id: {task_id}")
        else:
            raise Exception(f"Could not find resource in sim with id: {resource_id}")

    def unassign_task_from_resource(self, task_id: int, resource_id: int) -> None:
        found_task = self.get_task_by_id(task_id)
        found_resource = self.get_resource_by_id(resource_id)

        if found_task and found_resource:
            found_resource.unassign_task(found_task)
        elif found_task is None:
            raise Exception(f"Could not find task in sim with id: {task_id}")
        else:
            raise Exception(f"Could not find resource in sim with id: {resource_id}")

    def reassign_task(
        self, task_id: int, old_resource_id: int, new_resource_id: int
    ) -> None:
        try:
            self.unassign_task_from_resource(task_id, old_resource_id)
            self.assign_task_to_resource(task_id, new_resource_id)
        except Exception as e:
            error_message = str(e)
            if str(task_id) in error_message:
                raise Exception(
                    f"Reassiging task failed as could not find task {task_id}"
                )
            elif str(old_resource_id) in error_message:
                raise Exception(
                    f"Reassiging failed as could not find resource {old_resource_id}"
                )
            elif str(new_resource_id) in error_message:
                # Assigns back the task to its original resource as reassiging failed
                self.assign_task_to_resource(task_id, old_resource_id)
                raise Exception(
                    f"Reassiging failed as could node find resource {new_resource_id}"
                )
            else:
                raise Exception(f"Reassiging task failed due to error {e}")

    # First frame sent from back to front end with station data, etc
    def emit_initial_frame(self) -> None:
        frame = self.create_key_frame()
        self.emit_frame(frame)

    # Should call frame emitter
    def emit_frame(self, frame: Optional[Frame] = None) -> None:
        # generate key frame if the current frame is a multiple of the n
        # specified for key frames
        if not frame:
            frame = (
                self.create_key_frame()
                if self.frameCounter % self.keyframeFreq == 0
                else self.create_diff_frame()
            )
        self.frameEmitter.notify(frame=frame)
        self.frameCounter += 1

    def create_diff_frame(self) -> Frame:
        tasks = []
        for task in self.taskEntities:
            if task.has_updated:
                station = task.get_station()
                assigned_resource = task.get_assigned_resource()
                tasks.append(
                    {
                        "task_id": task.get_task_id(),
                        "task_state": str(task.get_state()),
                        "station_id": station.id if station is not None else None,
                        "station_name": station.name if station is not None else None,
                        "assigned_resource_id": (
                            assigned_resource.id
                            if assigned_resource is not None
                            else None
                        ),
                        "is_assigned": task.is_assigned(),
                    }
                )

        stations = [
            {
                "station_id": station.id,
                "station_name": station.name,
                "station_position": (station.get_station_position().get_position()),
                "station_tasks": station.tasks,
                "task_count": station.get_task_count(),
            }
            for station in self.stationEntities
            if station.has_updated
        ]

        resources = []
        for resource in self.resourceEntities:
            if resource.has_updated:
                in_progress_task = resource.get_in_progress_task()
                resources.append(
                    {
                        "resource_id": resource.id,
                        "resource_position": (
                            resource.get_resource_position().get_position()
                        ),
                        "resource_tasks": resource.get_task_list(),
                        "task_count": resource.get_task_count(),
                        "in_progress_task_id": (
                            in_progress_task.get_task_id()
                            if in_progress_task is not None
                            else None
                        ),
                    }
                )

        payload = {
            "sim_id": self.frameEmitter.sim_id,
            "tasks": tasks,
            "stations": stations,
            "resources": resources,
            "clock": {
                "realSecondsPassed": self.clock.real_seconds_passed,
                "realMinutesPassed": self.clock.real_minutes_passed,
                "simSecondsPassed": self.clock.sim_time_seconds,
                "simMinutesPassed": self.clock.sim_time_minutes,
            },
        }
        frame = Frame(seq_numb=self.frameCounter, payload=payload)
        return frame

    def create_key_frame(self) -> Frame:
        tasks = []
        for task in self.taskEntities:
            station = task.get_station()
            assigned_resource = task.get_assigned_resource()
            tasks.append(
                {
                    "task_id": task.get_task_id(),
                    "task_state": str(task.get_state()),
                    "station_id": station.id if station is not None else None,
                    "station_name": station.name if station is not None else None,
                    "assigned_resource_id": (
                        assigned_resource.id if assigned_resource is not None else None
                    ),
                    "is_assigned": task.is_assigned(),
                }
            )

        stations = [
            {
                "station_id": station.id,
                "station_name": station.name,
                "station_position": (station.get_station_position().get_position()),
                "station_tasks": station.tasks,
                "task_count": station.get_task_count(),
            }
            for station in self.stationEntities
        ]

        resources = []
        for resource in self.resourceEntities:
            in_progress_task = resource.get_in_progress_task()
            resources.append(
                {
                    "resource_id": resource.id,
                    "resource_position": (
                        resource.get_resource_position().get_position()
                    ),
                    "resource_tasks": resource.get_task_list(),
                    "task_count": resource.get_task_count(),
                    "in_progress_task_id": (
                        in_progress_task.get_task_id()
                        if in_progress_task is not None
                        else None
                    ),
                }
            )

        payload = {
            "sim_id": self.frameEmitter.sim_id,
            "tasks": tasks,
            "stations": stations,
            "resources": resources,
            "clock": {
                "realSecondsPassed": self.clock.real_seconds_passed,
                "realMinutesPassed": self.clock.real_minutes_passed,
                "simSecondsPassed": self.clock.sim_time_seconds,
                "simMinutesPassed": self.clock.sim_time_minutes,
            },
        }
        frame = Frame(seq_numb=self.frameCounter, payload=payload)
        return frame
