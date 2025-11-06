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

from sim.behaviour.sim_behaviour import SimBehaviour
from sim.behaviour.resource_behaviour.resource_choose_next_task_strategy import (
    ResourceChooseNextTaskStrategy,
)

from sim.behaviour.station_behaviour.strategies.task_popup_strategy import (
    TaskPopupStrategy,
)
from typing import Self


class SimBehaviourBuilder:
    sim_behaviour: SimBehaviour

    def __init__(self) -> None:
        self.reset()

    def set_RCNT_strategy(self, strategy: ResourceChooseNextTaskStrategy) -> Self:
        self.sim_behaviour.set_RCNT_strategy(strategy)
        return self

    def set_TPU_strategy(self, strategy: TaskPopupStrategy) -> Self:
        self.sim_behaviour.set_TPU_strategy(strategy)
        return self

    def reset(self) -> None:
        self.sim_behaviour = SimBehaviour()

    def get_sim_behaviour(self) -> SimBehaviour:
        ret_sim_behaviour = self.sim_behaviour
        self.reset()
        return ret_sim_behaviour
