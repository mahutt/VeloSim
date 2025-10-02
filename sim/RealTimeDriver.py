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
import time
import json
import os
from typing import Optional, Callable, Any, cast


"""Realtime driver that paces a simpy environment.

    Notes:
    - simEnv time unit is a simulated second.
    - realTimeFactor = real_seconds/ per_sim_second.
    - Calls the supplied callback once per simulated second (after each
      advancement).
    """


class RealTimeDriver:
    # Keeps track of the actual time a simulation was started at for pacing
    wallStartTime: float
    # Keeps track of the simulation start for pacing
    simStartTime: float

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from config.json file."""
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            with open(config_path, "r") as file:
                config = json.load(file)
                return cast(dict[str, Any], config.get("simulation", {}))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load config.json, using hardcoded defaults: {e}")
            # Fallback to hardcoded defaults if config file is unavailable
            return {
                # Default 1-1 real second per sim second
                "default_real_time_factor": 1.0,
                # Default No lag reporting
                "default_strict_mode": False,
                # Default Sim run time is 1 sim hour
                "default_until_time": 3600.0,
                # Default delay for recalculating remaining wall time is 2 ms
                "default_sleep_interval": 0.002,
            }

    def __init__(
        self,
        simEnv: simpy.Environment,
        # Load defaults from config, allow override
        realTimeFactor: Optional[float] = None,
        strict: Optional[bool] = None,
    ) -> None:
        # Load config once and store it
        self.config = self._load_config()
        self.simEnv = simEnv
        self.realTimeFactor = (
            realTimeFactor
            if realTimeFactor is not None
            else self.config.get("default_real_time_factor", 1.0)
        )
        self.strict = (
            strict
            if strict is not None
            else self.config.get("default_strict_mode", False)
        )
        self.running = True
        self.lag: Optional[float] = None
        self.sleep_interval = self.config.get("default_sleep_interval", 0.002)

    def resetPacingRefs(self) -> None:
        self.wallStartTime = time.perf_counter()
        self.simStartTime = self.simEnv.now

    def setRealTimeFactor(self, factor: float) -> None:
        self.resetPacingRefs()
        self.realTimeFactor = factor

    def runUntil(
        self,
        until: Optional[float] = None,
        stepCallback: Optional[Callable[[], None]] = None,
    ) -> None:
        # Use config default if until is not specified
        if until is None:
            until = self.config.get("default_until_time", 3600.0)
        self.resetPacingRefs()
        # Sim loop that controls the time real time (aka wall time) between sim steps
        while True:
            if self.running:
                # Break out of sim loop if current sim time > specified run time
                if self.simEnv.peek() >= until:
                    print("Specified Sim-time reached")
                    break

                currentSimTime = self.simEnv.now

                # Calculate target wall time
                # targetWallTime = wall time that should pass before the next sim step
                targetWallTime = (
                    self.wallStartTime
                    + (currentSimTime - self.simStartTime) * self.realTimeFactor
                )

                # Loop until actual wall time is >= target wall time
                while True:
                    # Calculate remaining time before next step
                    remainingWallTime = targetWallTime - time.perf_counter()
                    if remainingWallTime <= 0:
                        break
                    # Wait either configured sleep interval time or remaining wall time
                    time.sleep(min(remainingWallTime, self.sleep_interval))

                # Allow the simpy environment to step when target wall time is reached
                try:
                    # Callback function, presumably to emit frames, called per step
                    if stepCallback:
                        stepCallback()
                    self.simEnv.step()
                except simpy.core.EmptySchedule:
                    print("Simpy schedule is empty")
                    break
                # Calculate lag if strict mode is on
                if self.strict:
                    current_sim_seconds_passed = self.simEnv.now - self.simStartTime
                    # Same calculation and logic as the target wall time.
                    # Positive lag = we're behind schedule, negative = ahead
                    expected_wall_time = (
                        self.wallStartTime
                        + current_sim_seconds_passed * self.realTimeFactor
                    )
                    actual_wall_time = time.perf_counter()
                    lag = expected_wall_time - actual_wall_time
                    self.lag = lag

                    self.recordLag()
                    # TODO: record/report lag metrics if needed

    def pause(self) -> None:
        print("Pausing")
        self.running = False

    def resume(self) -> None:
        print("Starting")
        self.running = True

    def recordLag(self) -> None:
        pass
