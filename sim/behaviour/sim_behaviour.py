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

from sim.behaviour.resource_behaviour.resource_choose_next_task_strategy import (
    DriverChooseNextTaskStrategy,
)

from sim.behaviour.station_behaviour.strategies.task_popup_strategy import (
    TaskPopupStrategy,
)

from sim.behaviour.resource_behaviour.task_servicing_time_strategy import (
    TaskServicingTimeStrategy,
)

from sim.behaviour.default.default_TPU_strategy import DefaultTPUStrategy

from sim.behaviour.default.default_RCNT_strategy import DefaultRCNTStrategy

from sim.behaviour.default.default_TST_strategy import DefaultTSTStrategy


class SimBehaviour:
    """Configuration for simulation behavior strategies."""

    RCNT_strategy: DriverChooseNextTaskStrategy

    TPU_strategy: TaskPopupStrategy

    TST_strategy: TaskServicingTimeStrategy

    def __init__(self) -> None:
        self.RCNT_strategy = DefaultRCNTStrategy()
        self.TPU_strategy = DefaultTPUStrategy()
        self.TST_strategy = DefaultTSTStrategy()

    def set_RCNT_strategy(self, strategy: DriverChooseNextTaskStrategy) -> None:
        """Set the driver choose next task strategy.

        Args:
            strategy: The strategy to use for driver task selection.

        Returns:
            None
        """
        self.RCNT_strategy = strategy

    def set_TPU_strategy(self, strategy: TaskPopupStrategy) -> None:
        """Set the task popup strategy.

        Args:
            strategy: The strategy to use for task popup behavior.

        Returns:
            None
        """
        self.TPU_strategy = strategy

    def set_TST_strategy(self, strategy: TaskServicingTimeStrategy) -> None:
        """Set the task service time strategy.

        Args:
            strategy: The strategy to determine task servicing time.

        Returns:
            None
        """
        self.TST_strategy = strategy
