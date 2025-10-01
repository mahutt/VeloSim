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


class RunInfo(TypedDict):
    thread: threading.Thread
    stop: threading.Event


class Simulator:
    def __init__(self) -> None:
        self.threadPool: Dict[str, RunInfo] = {}

    def start(self) -> str:
        run_id = str(uuid.uuid4())  # threadID / SIM ID
        stop_flag = threading.Event()

        def sim_loop() -> None:
            env = (
                simpy.Environment()
            )  # Created for later use (So we can pass to the controller)

            print(env)  # Keeps linter happy. (temporary)

            while not stop_flag.is_set():  # Run until stop is called!
                print(f"Hello From Simulator: [{run_id}]")
                time.sleep(1)
            print(f"[{run_id}] stopped.")

        t = threading.Thread(target=sim_loop, name=f"SIM-{run_id}")
        t.start()
        self.threadPool[run_id] = {"thread": t, "stop": stop_flag}
        return run_id

    def stop(self, sim_id: str) -> None:
        sim_thread = self.threadPool.get(sim_id)

        if not sim_thread:  # if the sim thread does not exist do nothing
            return

        sim_thread[
            "stop"
        ].set()  # Set Stop Flag to True so we do not run the thread anymore.
        sim_thread["thread"].join(timeout=2.0)  # wait for shutdown
        if not sim_thread["thread"].is_alive():
            self.threadPool.pop(sim_id, None)

    def pause(self) -> None:
        raise NotImplementedError("pause() not implemented yet")

    def status(self) -> None:
        raise NotImplementedError("pause() not implemented yet")
