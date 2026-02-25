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
    - sim_env time unit is a simulated second.
    - realTimeFactor = real_seconds/ per_sim_second.
    - Calls the supplied callback once per simulated second (after each
      advancement).
    """


class RealTimeDriver:
    """Drives simulation in real-time with configurable time scaling."""

    # Keeps track of the actual time a simulation was started at for pacing
    wall_start_time: float
    # Keeps track of the simulation start for pacing
    sim_start_time: float
    # Set to true to force break out of sim loop
    stop_flag: bool = False

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from config.json file."""
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
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
        sim_env: simpy.Environment,
        # Load defaults from config, allow override
        real_time_factor: Optional[float] = None,
        strict: Optional[bool] = None,
    ) -> None:
        # Load config once and store it
        self.config = self._load_config()
        self.sim_env = sim_env
        self.real_time_factor = (
            real_time_factor
            if real_time_factor is not None
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

    def reset_pacing_refs(self) -> None:
        """Reset pacing reference times to current wall and sim times.

        Returns:
            None
        """
        self.wall_start_time = time.perf_counter()
        self.sim_start_time = self.sim_env.now

    def set_real_time_factor(self, factor: float) -> None:
        """Set the real time factor for simulation pacing.

        Args:
            factor: Real seconds per simulated second.

        Returns:
            None
        """
        self.reset_pacing_refs()
        self.real_time_factor = factor

    def run_until(
        self,
        until: Optional[float] = None,
        step_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Run the simulation until specified time with real-time pacing.

        Args:
            until: Simulation time to run until (default from config).
            step_callback: Optional callback invoked after each sim second.

        Returns:
            None
        """
        # Use config default if until is not specified
        if until is None:
            until = self.config.get("default_until_time", 3600.0)
        self.reset_pacing_refs()
        # Sim loop that controls the time real time (aka wall time) between sim steps

        prev_sim_time = self.sim_start_time

        while True:

            # Stop Sim loop
            if self.stop_flag:
                break
            if self.running:
                current_sim_time = self.sim_env.now

                # Calculate target wall time
                # target_wall_time = wall time that should pass before the next sim step
                target_wall_time = (
                    self.wall_start_time
                    + (current_sim_time - self.sim_start_time) * self.real_time_factor
                )

                # Loop until actual wall time is >= target wall time
                while True:
                    # Calculate remaining time before next step
                    remaining_wall_time = target_wall_time - time.perf_counter()
                    if remaining_wall_time <= 0:
                        break
                    # Wait either configured sleep interval time or remaining wall time
                    time.sleep(min(remaining_wall_time, self.sleep_interval))

                # Allow the simpy environment to step when target wall time is reached
                try:
                    # Step the environment once, advancing simulated time
                    self.sim_env.step()
                except simpy.core.EmptySchedule:
                    print("Simpy schedule is empty")
                    break
                # Invoke the step callback once per simulated second advanced
                # Compare AFTER stepping so we see the incremented env.now
                if step_callback:
                    current_after = self.sim_env.now
                    if current_after > prev_sim_time:
                        step_callback()
                        prev_sim_time = current_after
                # After stepping, if we've reached or passed the target sim time, stop
                if self.sim_env.now >= until:
                    print("Specified Sim-time reached")
                    break

                # Calculate lag if strict mode is on
                if self.strict:
                    current_sim_seconds_passed = self.sim_env.now - self.sim_start_time
                    # Same calculation and logic as the target wall time.
                    # Positive lag = we're behind schedule, negative = ahead
                    expected_wall_time = (
                        self.wall_start_time
                        + current_sim_seconds_passed * self.real_time_factor
                    )
                    actual_wall_time = time.perf_counter()
                    lag = expected_wall_time - actual_wall_time
                    self.lag = lag
                    if lag > 0:
                        self.record_lag(lag)
                    # TODO: record/report lag metrics if needed

    def pause(self) -> None:
        """Pause the simulation execution.

        Returns:
            None
        """
        print("Pausing")
        self.running = False

    def resume(self) -> None:
        """Resume the paused simulation execution.

        Returns:
            None
        """
        print("Resuming")
        self.reset_pacing_refs()
        # Reset pacing since time during
        # pause makes sim think its lagging.
        self.running = True

    def stop(self) -> None:
        """Stop the simulation execution.

        Returns:
            None
        """
        self.stop_flag = True

    def record_lag(self, lag: float) -> None:
        """Record simulation lag for monitoring.

        Args:
            lag: The lag amount in seconds.

        Returns:
            None
        """
        pass
