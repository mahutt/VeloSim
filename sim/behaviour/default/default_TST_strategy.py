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

from sim.behaviour.resource_behaviour.task_servicing_time_strategy import (
    TaskServicingTimeStrategy,
)


class DefaultTSTStrategy(TaskServicingTimeStrategy):
    """Default task servicing time strategy.

    Returns a flat, default servicing time (in seconds) used when no
    custom Task Servicing Time (TST) strategy is provided. This class is
    used as the framework default and in tests that expect a consistent
    servicing duration.
    """

    def get_task_servicing_time(self) -> int:
        """Flat default time required to service a task

        Args:
            None

        Returns:
            Integer corresponding to the default time taken to the time
            required to service a task
        """
        return 240
