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
from typing import Generator, Any


class Clock:
    """Simple simulation clock that now advances in SIM SECONDS.

    Notes (breaking change vs previous version):
    - Previously one env unit == 1 sim minute. Now: 1 env unit == 1 sim second.
    - We expose both accumulated seconds and derived minutes for convenience.
    - real_time_passed tracks wall-clock seconds spent running this clock process.
    """

    real_seconds_passed: float = 0.0  # wall-clock seconds elapsed while clock running
    real_minutes_passed: float = 0.0
    sim_time_seconds: float = 0.0  # env.now (seconds)
    sim_time_minutes: float = 0.0  # env.now / 60 (floor)

    def __init__(self, env: simpy.Environment) -> None:
        self.env = env

    def clock(self) -> Generator[Any, Any, None]:
        real_time_accum = 0.0
        while True:
            start = time.perf_counter()
            # Advance by 1 simulated second each loop
            yield self.env.timeout(1)
            end = time.perf_counter()

            real_time_accum += end - start
            sim_seconds = self.env.now  # now measured in seconds
            self.real_seconds_passed = real_time_accum
            self.real_minutes_passed = real_time_accum / 60  # Fractional minutes
            self.sim_time_seconds = sim_seconds
            self.sim_time_minutes = sim_seconds / 60

    def run(self) -> None:
        self.env.process(self.clock())
