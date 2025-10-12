

import time

class Clock:
    """Simple simulation clock that now advances in SIM SECONDS.

    Notes (breaking change vs previous version):
    - Previously one env unit == 1 sim minute. Now: 1 env unit == 1 sim second.
    - We expose both accumulated seconds and derived minutes for convenience.
    - realTimePassed tracks wall-clock seconds spent running this clock process.
    """

    realSecondsPassed: float = 0.0   # wall-clock seconds elapsed while the clock has been running
    realMinutesPassed: float = 0.0
    simTimeSeconds: float = 0.0   # env.now (seconds)
    simTimeMinutes: float = 0.0   # env.now / 60 (floor)

    def __init__(self, env):
        self.env = env

    def clock(self):
        real_time_accum = 0.0
        while True:
            start = time.perf_counter()
            # Advance by 1 simulated second each loop
            yield self.env.timeout(1)
            end = time.perf_counter()

            real_time_accum += (end - start)
            sim_seconds = self.env.now  # now measured in seconds
            self.realSecondsPassed = real_time_accum
            self.realMinutesPassed = real_time_accum / 60  # Fractional minutes
            self.simTimeSeconds = sim_seconds
            self.simTimeMinutes = sim_seconds / 60

    def run(self):
        self.env.process(self.clock())
        
      