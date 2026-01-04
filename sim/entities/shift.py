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

    Args:
        start_time: The start time of the shift in hours.
        end_time: The end time of the shift in hours.
        lunch_break: Optional lunch break duration in hours. Use None if no lunch.

    """

    def __init__(
        self, start_time: float, end_time: float, lunch_break: Optional[float]
    ):

        self.start_time = start_time
        self.end_time = end_time
        self.lunch_break = lunch_break

    def get_start_time(self) -> float:
        """Get the shift start time.

        Returns:
            float: The start time of the shift in hours.
        """
        return self.start_time

    def set_start_time(self, value: float) -> None:
        """Set the shift start time.

        Args:
            value: The new start time in hours.
        Returns:
            None
        """
        self.start_time = value

    def get_end_time(self) -> float:
        """Get the shift end time.

        Returns:
            float: The end time of the shift in hours.
        """
        return self.end_time

    def set_end_time(self, value: float) -> None:
        """Set the shift end time.

        Args:
            value: The new end time in hours.
        Returns:
            None
        """
        self.end_time = value

    def get_lunch_break(self) -> float | None:
        """Get the lunch break duration.

        Returns:
            float | None: Lunch break duration in hours, or None if not set.
        """
        return self.lunch_break

    def set_lunch_break(self, value: float) -> None:
        """Set the lunch break duration.

        Args:
            value: Lunch break duration in hours.

        Returns:
            None
        """
        self.lunch_break = value
