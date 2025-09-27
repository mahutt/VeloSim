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
from typing import Optional, Callable


"""Realtime driver that paces a simpy environment.

    Notes:
    - simEnv time unit is a simulated second.
    - realTimeFactor = real_seconds/ per_sim_second.
    - Calls the supplied callback once per simulated second (after each
      advancement).
    """


class RealTimeDriver:

    def __init__(
        self,
        simEnv: simpy.Environment,
        realTimeFactor: float = 1.0,
        strict: bool = False,
    ) -> None:
        self.simEnv = simEnv
        self.realTimeFactor = realTimeFactor
        self.strict = strict
        self.wallStartTime: float = 0.0
        self.simStartTime: float = 0.0
        self.running = True
        self.lag: Optional[float] = None

    def resetPacingRefs(self) -> None:
        self.wallStartTime = time.perf_counter()
        self.simStartTime = self.simEnv.now

    def setRealTimeFactor(self, factor: float) -> None:
        self.resetPacingRefs()
        self.realTimeFactor = factor

    def runUntil(
        self, until: float = 3600, stepCallback: Optional[Callable[[], None]] = None
    ) -> None:
        self.resetPacingRefs()

        while True:
            if self.running:
                # Check if next sim time >= until time, break if so
                if self.simEnv.peek() >= until:
                    print("Specified Sim-time reached")
                    break

                currentSimTime = self.simEnv.now
                targetWallTime = (
                    self.wallStartTime
                    + (currentSimTime - self.simStartTime) * self.realTimeFactor
                )

                while True:
                    remainingWallTime = targetWallTime - time.perf_counter()
                    if remainingWallTime <= 0:
                        break
                    time.sleep(min(remainingWallTime, 0.002))

                try:
                    if stepCallback:
                        stepCallback()
                    self.simEnv.step()
                except simpy.core.EmptySchedule:
                    print("Simpy schedule is empty")
                    break

                if self.strict:
                    current_sim_seconds_passed = self.simEnv.now - self.simStartTime
                    expected_wall_time = (
                        self.wallStartTime
                        + current_sim_seconds_passed * self.realTimeFactor
                    )
                    actual_wall_time = time.perf_counter()
                    lag = expected_wall_time - actual_wall_time
                    self.lag = lag
                    # Positive lag = we're behind schedule, negative = ahead
                    # TODO: record/report lag metrics if needed

    def pause(self) -> None:
        print("Pausing")
        self.running = False

    def resume(self) -> None:
        print("Starting")
        self.running = True
