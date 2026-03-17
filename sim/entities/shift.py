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

from typing import Optional


class Shift:
    """Represents a driver's work shift schedule.

    A shift defines the start and end times for a driver's working period
    and may optionally include a lunch break.

    Similarly to the clock class, Shift times are available with respect to sim
    time and real time. Real time is used in frame payloads. Sim time is used
    for internal sim calculations

    Attributes:
        start_time: absolute shift start time in seconds.
        end_time: absolute shift end time in seconds.
        lunch_break: Optional absolute lunch break start time in seconds.
        relative_start_time: shift start time in seconds after sim start time.
        relative_end_time: shift end time in seconds after sim start time.
        relative_lunch_break: Optional lunch break start time in seconds
          after sim start time.
    """

    start_time: float
    end_time: float
    lunch_break: float | None
    relative_start_time: float
    relative_end_time: float
    relative_lunch_break: float | None

    def __init__(
        self,
        start_time: float,
        end_time: float,
        lunch_break: Optional[float],
        sim_start_time: float,
    ):
        """
        Args:
            start_time: Absolute shift start time in seconds.
            end_time: Absolute shift end time in seconds.
            lunch_break: Optional absolute lunch break start time,
              or None.
            sim_start_time: Absolute simulation start time used
              to compute relative times.
        """

        self.start_time = start_time
        self.end_time = end_time
        self.lunch_break = lunch_break

        # Duplicate attributes for values relative to the simulation's start time
        self.relative_start_time = start_time - sim_start_time
        self.relative_end_time = end_time - sim_start_time
        self.relative_lunch_break = (
            (lunch_break - sim_start_time) if lunch_break is not None else None
        )

    def get_start_time(self) -> float:
        """Get the shift start time.

        Returns:
            float: The absolute start time of the shift in seconds.
        """
        return self.start_time

    def get_end_time(self) -> float:
        """Get the shift end time.

        Returns:
            float: The absolute end time of the shift in seconds.
        """
        return self.end_time

    def get_lunch_break(self) -> float | None:
        """Get the lunch break start time".

        Returns:
            float | None: The absolute lunch break start time in seconds,
              or None if not set.
        """
        return self.lunch_break

    # --- relative duplicates ---
    def get_relative_start_time(self) -> float:
        """Get the relative shift start time.

        Returns:
            float: The shift start time in seconds after sim start time.
        """
        return self.relative_start_time

    def get_relative_end_time(self) -> float:
        """Get the relative shift end time.

        Returns:
            float: The shift end time in seconds after sim start time.
        """
        return self.relative_end_time

    def get_relative_lunch_break(self) -> float | None:
        """Get the relative lunch break start time.

        Returns:
            float | None: The lunch break start time in seconds after
              sim start time, or None if not set.
        """
        return self.relative_lunch_break
