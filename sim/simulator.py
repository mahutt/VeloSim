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

import threading
from typing import Dict, List, TypedDict, Optional
import uuid
import simpy

from sim.entities.inputParameters import InputParameter
from sim.entities.request_type import RequestType
from sim.frame_emitter import FrameEmitter
from sim.utils.subscriber import Subscriber
from sim.SimulatorController import SimulatorController
from sim.entities.task import Task


class RunInfo(TypedDict):
    thread: Optional[threading.Thread]
    emitter: FrameEmitter
    simController: SimulatorController


class Simulator:
    def __init__(self) -> None:
        self.thread_pool: Dict[str, RunInfo] = {}
        self.thread_pool_lock = threading.Lock()

    def initialize(
        self, input_parameters: InputParameter, subscribers: List[Subscriber]
    ) -> str:
        # Initialize a simulation and send the initial frame, but don't start
        # the simulation loop.
        run_id = str(uuid.uuid4())  # threadID / SIM ID
        emitter = FrameEmitter(run_id)

        for sub in subscribers:
            emitter.attach(sub)

        env = simpy.Environment()

        simController = SimulatorController(
            simEnv=env,
            inputParameters=input_parameters,
            frameEmitter=emitter,
            strict=False,
        )

        # Send the initial frame immediately
        simController.emit_initial_frame()

        with self.thread_pool_lock:
            if run_id in self.thread_pool:
                raise RuntimeError(f"Run id already present: {run_id}")
            # Store the controller but don't start the thread yet
            self.thread_pool[run_id] = {
                "thread": None,  # No thread yet
                "emitter": emitter,
                "simController": simController,
            }

        return run_id

    def start(self, sim_id: str, simTime: int) -> None:
        # Start the simulation loop for an already initialized simulation.
        with self.thread_pool_lock:
            rec = self.thread_pool.get(sim_id)

        if rec is None:
            raise RuntimeError(
                f"Simulation {sim_id} not found. Call initialize() first."
            )

        if rec["thread"] is not None:
            raise RuntimeError(f"Simulation {sim_id} is already running.")

        # Create and start the simulation thread
        t = threading.Thread(
            target=rec["simController"].start,
            args=(simTime,),
            name=f"SIM-{sim_id}",
            daemon=True,
        )

        with self.thread_pool_lock:
            self.thread_pool[sim_id]["thread"] = t
            t.start()

    def stop(self, sim_id: str, join_timeout: float | None = 2.0) -> None:
        with self.thread_pool_lock:
            rec = self.thread_pool.get(sim_id)

        if rec is None:
            return  # Unknown/Thread is already closed.

        rec["simController"].stop()

        # Only join if there's an actual thread
        if rec["thread"] is not None:
            rec["thread"].join(timeout=join_timeout)

        with self.thread_pool_lock:
            current = self.thread_pool.get(sim_id)
            if current is rec and (
                rec["thread"] is None or not rec["thread"].is_alive()
            ):
                self.thread_pool.pop(sim_id, None)
        print(f"{sim_id} ended")

    def pause(self) -> None:
        raise NotImplementedError("pause() not implemented yet")

    def status(self) -> None:
        raise NotImplementedError("status() not implemented yet")

    def send_request(self, request_type: RequestType) -> None:
        raise NotImplementedError("send_request() not implemented yet")

    def get_sim_by_id(self, sim_id: str) -> Optional[RunInfo]:
        if sim_id in self.thread_pool:
            return self.thread_pool.get(sim_id)
        else:
            raise Exception(f"Simulation {sim_id} does not exist in the thread pool")

    def add_task_to_sim(self, sim_id: str, task: Task) -> None:
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].taskEntities.append(task)
        except Exception as e:
            print(f"Could not add task to sim due to: {e}")

    def assign_task_to_resource(
        self, sim_id: str, task_id: int, resource_id: int
    ) -> None:
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].assign_task_to_resource(task_id, resource_id)
        except Exception as e:
            print(f"Could not assign task due to: {e}")

    def unassign_task_from_resource(
        self, sim_id: str, task_id: int, resource_id: int
    ) -> None:
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].unassign_task_from_resource(
                    task_id, resource_id
                )
        except Exception as e:
            print(f"Could not unassign task due to: {e}")

    def reassign_task(
        self, sim_id: str, task_id: int, old_resource_id: int, new_resource_id: int
    ) -> None:
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].reassign_task(
                    task_id, old_resource_id, new_resource_id
                )
        except Exception as e:
            print(f"Error occurred: {e}")

    # For later use, we will be implementing a stream
    # type for continuous communication between BE and SIM (i.e. Frames)
    def get_stream(
        self,
    ) -> None:
        raise NotImplementedError("get_stream() not implemented yet")

    def stop_all(self, *, join_timeout_per_thread: float | None = 2.0) -> None:
        with self.thread_pool_lock:
            ids = list(self.thread_pool.keys())
        for sim_id in ids:
            try:
                self.stop(sim_id, join_timeout=join_timeout_per_thread)
            except Exception:
                pass  # it should still allow to kill all other threads.
