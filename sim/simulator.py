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

from sim.core.simulation_environment import SimulationEnvironment
from sim.entities.inputParameters import InputParameter
from sim.entities.request_type import RequestType
from sim.core.frame_emitter import FrameEmitter
from sim.utils.subscriber import Subscriber
from sim.core.SimulatorController import SimulatorController
from sim.entities.task import Task
from sim.behaviour.sim_behaviour import SimBehaviour
from sim.map.MapController import MapController


class RunInfo(TypedDict):
    """Type definition for simulation run metadata."""

    thread: Optional[threading.Thread]
    emitter: FrameEmitter
    simController: SimulatorController


class Simulator:
    """Manager for multiple concurrent simulation instances."""

    def __init__(self) -> None:
        """Initialize the Simulator with an empty thread pool.

        Creates a thread-safe pool for managing multiple concurrent simulations.
        Each simulation is identified by a unique run_id and has its own thread,
        emitter, and controller.
        """
        self.thread_pool: Dict[str, RunInfo] = {}
        self.thread_pool_lock = threading.Lock()

    def initialize(
        self,
        input_parameters: InputParameter,
        subscribers: List[Subscriber],
        sim_behaviour: SimBehaviour = SimBehaviour(),
        run_id: str | None = None,
        map_controller: MapController | None = None,
        env: SimulationEnvironment | None = None,
    ) -> str:
        """Initialize a simulation instance without starting the simulation loop.

        Creates a new simulation environment with the specified parameters and
        subscribers, generates a unique run ID, and stores the simulation in the
        thread pool. The simulation loop must be started separately using start().

        Args:
            input_parameters: Simulation configuration including stations, resources,
                tasks, and timing parameters.
            subscribers: List of subscribers to receive frame updates from the
                simulation.
            sim_behaviour: Custom simulation behavior for task assignment and
                resource selection strategies. Defaults to SimBehaviour().

        Returns:
            Unique simulation run ID (UUID string) for controlling this simulation.

        Raises:
            RuntimeError: If the generated run_id already exists in the thread pool.
        """
        # Initialize a simulation and send the initial frame, but don't start
        # the simulation loop.

        if run_id is None:
            run_id = str(uuid.uuid4())

        emitter = FrameEmitter(run_id)

        for sub in subscribers:
            emitter.attach(sub)

        if env is None:
            env = SimulationEnvironment()
        else:
            env = env

        simController = SimulatorController(
            simEnv=env,
            inputParameters=input_parameters,
            frameEmitter=emitter,
            sim_behaviour=sim_behaviour,
            strict=True,
            map_controller=map_controller,
        )

        simController.map_controller.get_route

        with self.thread_pool_lock:
            if run_id in self.thread_pool:
                raise RuntimeError(f"Run id already present: {run_id}")
            # Store the map but don't start the thread yet
            self.thread_pool[run_id] = {
                "thread": None,  # No thread yet
                "emitter": emitter,
                "simController": simController,
            }

        return run_id

    def start(self, sim_id: str, simTime: int) -> None:
        """Start the simulation loop for an initialized simulation.

        Creates and starts a daemon thread that runs the simulation for the
        specified duration. The simulation must have been initialized first
        using initialize().

        Args:
            sim_id: Unique simulation ID returned from initialize().
            simTime: Maximum simulation time in seconds.

        Returns:
            None

        Raises:
            RuntimeError: If simulation not found or already running.
        """
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
        """Stop a running simulation and clean up resources.

        Signals the simulation controller to stop, waits for the thread to
        terminate, and removes the simulation from the thread pool if the
        thread has stopped.

        Args:
            sim_id: Unique simulation ID to stop.
            join_timeout: Maximum time in seconds to wait for thread termination.
                Defaults to 2.0. Use None for indefinite wait.

        Returns:
            None
        """
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

    def pause(self, sim_id: str) -> None:
        """Pause a running simulation.

        Temporarily halts simulation time progression while maintaining all
        simulation state. The simulation can be resumed using resume().

        Args:
            sim_id: Unique simulation ID to pause.

        Returns:
            None
        """
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].pause()
        except Exception as e:
            print(f"Could not pause simulation due to: {e}")

    def resume(self, sim_id: str) -> None:
        """Resume a paused simulation.

        Continues simulation time progression from the point where it was paused.

        Args:
            sim_id: Unique simulation ID to resume.

        Returns:
            None
        """
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].resume()
        except Exception as e:
            print(f"Could not resume simulation due to: {e}")

    def set_factor(self, sim_id: str, factor: float) -> None:
        """Set the real-time speed factor for a simulation.

        Adjusts how fast simulation time progresses relative to real time.
        A factor of 1.0 means real-time, 2.0 means twice as fast, etc.

        Args:
            sim_id: Unique simulation ID.
            factor: Speed multiplier for simulation time progression.

        Returns:
            None
        """
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].set_factor(factor)
        except Exception as e:
            print(f"Could not set factor due to: {e}")

    def status(self) -> None:
        """Get the status of all simulations.

        Returns:
            None

        Raises:
            NotImplementedError: This method is not yet implemented.
        """
        raise NotImplementedError("status() not implemented yet")

    def send_request(self, request_type: RequestType) -> None:
        """Send a request to a simulation.

        Args:
            request_type: Type of request to send to the simulation.

        Returns:
            None

        Raises:
            NotImplementedError: This method is not yet implemented.
        """
        raise NotImplementedError("send_request() not implemented yet")

    def get_sim_by_id(self, sim_id: str) -> Optional[RunInfo]:
        """Retrieve simulation information by ID.

        Args:
            sim_id: Unique simulation ID to retrieve.

        Returns:
            RunInfo containing thread, emitter, and controller for the simulation.

        Raises:
            Exception: If the simulation ID is not found in the thread pool.
        """
        if sim_id in self.thread_pool:
            return self.thread_pool.get(sim_id)
        else:
            raise Exception(f"Simulation {sim_id} does not exist in the thread pool")

    def add_task_to_sim(self, sim_id: str, task: Task) -> None:
        """Add a new task to a running simulation.

        Dynamically adds a task to the simulation's task queue during execution.

        Args:
            sim_id: Unique simulation ID.
            task: Task object to add to the simulation.

        Returns:
            None
        """
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].add_task(task)
        except Exception as e:
            print(f"Could not add task to sim due to: {e}")

    def assign_task_to_driver(self, sim_id: str, task_id: int, driver_id: int) -> None:
        """Assign a task to a specific driver in the simulation.

        Args:
            sim_id: Unique simulation ID.
            task_id: ID of the task to assign.
            driver_id: ID of the driver to assign the task to.

        Returns:
            None
        """
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].assign_task_to_driver(task_id, driver_id)
        except Exception as e:
            print(f"Could not assign task due to: {e}")

    def unassign_task_from_driver(
        self, sim_id: str, task_id: int, driver_id: int
    ) -> None:
        """Remove a task assignment from a driver in the simulation.

        Args:
            sim_id: Unique simulation ID.
            task_id: ID of the task to unassign.
            driver_id: ID of the driver to unassign the task from.

        Returns:
            None
        """
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].unassign_task_from_driver(task_id, driver_id)
        except Exception as e:
            print(f"Could not unassign task due to: {e}")

    def reassign_task(
        self, sim_id: str, task_id: int, old_driver_id: int, new_driver_id: int
    ) -> None:
        """Reassign a task from one driver to another in the simulation.

        Args:
            sim_id: Unique simulation ID.
            task_id: ID of the task to reassign.
            old_driver_id: ID of the current driver holding the task.
            new_driver_id: ID of the driver to reassign the task to.

        Returns:
            None
        """
        try:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                sim_info["simController"].reassign_task(
                    task_id, old_driver_id, new_driver_id
                )
        except Exception as e:
            print(f"Error occurred: {e}")

    def reorder_driver_tasks(
        self,
        sim_id: str,
        driver_id: int,
        task_ids_to_reorder: list[int],
        apply_from_top: bool,
    ) -> list[int]:
        """
        Reorder tasks in a driver's task list.

        Args:
            sim_id: Simulation ID
            driver_id: ID of the driver whose tasks should be reordered
            task_ids_to_reorder: Partial list of task IDs to reorder
            apply_from_top: If True, specified tasks inserted after in-progress.
                           If False, specified tasks appended to end (reversed).

        Returns:
            List of task IDs in the new order

        Raises:
            Exception: If simulation, driver not found, or reordering fails
        """
        with self.thread_pool_lock:
            sim_info = self.get_sim_by_id(sim_id)
            if sim_info is not None:
                try:
                    return sim_info["simController"].reorder_driver_tasks(
                        driver_id, task_ids_to_reorder, apply_from_top
                    )
                except Exception as e:
                    raise Exception(f"Error occurred: {e}")
            else:
                raise Exception(f"Simulation {sim_id} not found")

    # For later use, we will be implementing a stream
    # type for continuous communication between BE and SIM (i.e. Frames)
    def get_stream(
        self,
    ) -> None:
        """Get a stream for continuous communication with the simulation.

        This will provide a stream interface for real-time frame updates between
        the backend and simulation.

        Returns:
            None

        Raises:
            NotImplementedError: This method is not yet implemented.
        """
        raise NotImplementedError("get_stream() not implemented yet")

    def stop_all(self, *, join_timeout_per_thread: float | None = 2.0) -> None:
        """Stop all running simulations and clean up resources.

        Iterates through all simulations in the thread pool and attempts to stop
        each one. Continues stopping remaining simulations even if individual
        stops fail.

        Args:
            join_timeout_per_thread: Maximum time in seconds to wait for each
                thread to terminate. Defaults to 2.0. Use None for indefinite wait.

        Returns:
            None
        """
        with self.thread_pool_lock:
            ids = list(self.thread_pool.keys())
        for sim_id in ids:
            try:
                self.stop(sim_id, join_timeout=join_timeout_per_thread)
            except Exception:
                pass  # it should still allow to kill all other threads.
