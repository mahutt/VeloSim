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
import time
from typing import Dict, TypedDict
import uuid
import simpy

from sim.entities.inputParameters import InputParameter


class RunInfo(TypedDict):
    thread: threading.Thread
    stop: threading.Event


class Simulator:
    def __init__(self) -> None:
        self.thread_pool: Dict[str, RunInfo] = {}
        self.thread_pool_lock = threading.Lock()

    def start(self, input_parameters: InputParameter) -> str:
        run_id = str(uuid.uuid4())  # threadID / SIM ID
        stop_flag = threading.Event()

        def sim_loop() -> None:
            env = (
                simpy.Environment()
            )  # Created for later use (So we can pass to the controller)

            _ = env  # Keeps linter happy. (temporary)

            while not stop_flag.is_set():  # Run until stop is called!
                print(f"Hello From Simulator: [{run_id}]")
                time.sleep(1)
            print(f"[{run_id}] stopped.")

        t = threading.Thread(target=sim_loop, name=f"SIM-{run_id}", daemon=True)

        with self.thread_pool_lock:
            if run_id in self.thread_pool:
                raise RuntimeError(f"Run id already present: {run_id}")
            self.thread_pool[run_id] = {"thread": t, "stop": stop_flag}
            t.start()

        return run_id

    def stop(self, sim_id: str, join_timeout: float | None = 2.0) -> None:
        with self.thread_pool_lock:
            rec = self.thread_pool.get(sim_id)

        if rec is None:
            return  # Unknown/Thread is already closed.

        rec["stop"].set()
        rec["thread"].join(timeout=join_timeout)

        with self.thread_pool_lock:
            current = self.thread_pool.get(sim_id)
            if current is rec and not rec["thread"].is_alive():
                self.thread_pool.pop(sim_id, None)

    def pause(self) -> None:
        raise NotImplementedError("pause() not implemented yet")

    def status(self) -> None:
        raise NotImplementedError("status() not implemented yet")

    def stop_all(self, *, join_timeout_per_thread: float | None = 2.0) -> None:
        with self.thread_pool_lock:
            ids = list(self.thread_pool.keys())
        for sim_id in ids:
            try:
                self.stop(sim_id, join_timeout=join_timeout_per_thread)
            except Exception:
                pass  # it should still allow to kill all other threads.
