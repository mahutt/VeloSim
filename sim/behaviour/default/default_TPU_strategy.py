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

from sim.behaviour.station_behaviour.strategies.task_popup_strategy import (
    TaskPopupStrategy,
)
from sim.entities.BatterySwapTask import BatterySwapTask
from sim.entities.task_state import State
from typing import Dict, List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sim.entities.station import Station


class DefaultTPUStrategy(TaskPopupStrategy):
    """Default strategy for task popup at stations."""

    # {station_id: {time:[task_id, ...], ...}, ...}
    station_scheduled_tasks: Optional[Dict[int, Dict[int, List[int]]]] = None

    def check_for_new_task(self, station: "Station") -> List[BatterySwapTask]:
        """Check if a new task should popup at the station.

        Args:
            station: The station to check for new task popup.

        Returns:
            List of BatterySwapTask that have popped up.
        """

        # `env.now` can be int or float; cast to int to match scheduled keys
        sim_time = int(station.env.now)
        if self.station_scheduled_tasks is None:
            return []
        scheduled_times = self.station_scheduled_tasks.get(station.id, {})

        if not scheduled_times:
            return []

        tasks_at_current_time = scheduled_times.get(sim_time, [])

        if not tasks_at_current_time:
            return []

        pop_up_tasks: List[BatterySwapTask] = []

        for task_id in tasks_at_current_time:
            task = BatterySwapTask(
                task_id=task_id,
                station=station,
            )
            task.set_state(State.OPEN)
            task.has_updated = True
            pop_up_tasks.append(task)
        return pop_up_tasks
