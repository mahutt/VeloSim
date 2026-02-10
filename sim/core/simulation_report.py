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


class SimulationReport:
    """
    Tracks simulation-wide metrics such as driving time and servicing time.
    """

    def __init__(self) -> None:
        self.total_driving_time = 0
        self.total_servicing_time = 0
        self.tasks_completed_per_shift: list[int] = []

    def reset(self) -> None:
        """Reset all metrics to zero.

        Returns:
            None
        """
        self.total_driving_time = 0
        self.total_servicing_time = 0
        self.tasks_completed_per_shift = []

    def increment_driving_time(self) -> None:
        """
        Increment the total driving time.

        Returns:
            None
        """
        self.total_driving_time += 1

    def increment_servicing_time(self) -> None:
        """
        Increment the total servicing time.

        Returns:
            None
        """
        self.total_servicing_time += 1

    def add_task_count_for_shift(self, task_count: int) -> None:
        """
        Adds task count for a driver's shift.

        Args:
            task_count (int): Number of tasks completed during the shift.

        Returns:
            None
        """
        self.tasks_completed_per_shift.append(task_count)

    def get_servicing_to_driving_ratio(self) -> float:
        """
        Compute the ratio of servicing time to driving time.

        Returns:
            float: The driving-to-servicing ratio, or 0 if servicing time is zero.
        """
        if self.total_driving_time == 0:
            return 0.0

        return self.total_servicing_time / self.total_driving_time

    def get_average_tasks_per_shift(self) -> float:
        """
        Retrieves the average task per shift
        Returns:
            float: average task per shift.
        """
        if len(self.tasks_completed_per_shift) == 0:
            return 0.0

        return sum(self.tasks_completed_per_shift) / len(self.tasks_completed_per_shift)
