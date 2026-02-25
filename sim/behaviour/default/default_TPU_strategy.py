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
from sim.entities.battery_swap_task import BatterySwapTask
from sim.entities.task_state import State
from typing import Dict, List, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sim.entities.station import Station


class DefaultTPUStrategy(TaskPopupStrategy):
    """Default strategy for task popup at stations."""

    def __init__(self) -> None:
        """Initialize the DefaultTPUStrategy."""
        # {station_id: {time:[task_id, ...], ...}, ...}
        # Ideal for rapid lookup speed per station & time.
        self.station_scheduled_tasks: Dict[int, Dict[int, List[int]]] = {}

        # Ideal for speedy frame payload creation.
        # entries are discarded after emission.
        # Set of (station_id, time, task_id) tuples.
        self._scheduled_tasks_set: set = set()

    def set_station_scheduled_tasks(
        self, station_scheduled_tasks: Dict[int, Dict[int, List[int]]]
    ) -> None:
        """Set the station scheduled tasks.

        Args:
            station_scheduled_tasks: A Dict mapping station IDs to a
            dict mapping times to lists of task IDs.

        Returns:
            None
        """
        self.station_scheduled_tasks = station_scheduled_tasks
        self._build_scheduled_tasks_set()

    def get_station_scheduled_tasks(
        self,
    ) -> Optional[Dict[int, Dict[int, List[int]]]]:
        """Get the station scheduled tasks.

        Returns:
            A Dict mapping station IDs to a dict mapping times to lists of task IDs.
        """
        station_scheduled_tasks = self.station_scheduled_tasks
        return station_scheduled_tasks

    def get_scheduled_tasks(self) -> set:
        """Get the set of scheduled tasks that haven't been emitted yet.

        Returns:
            A set of (station_id, time, task_id) tuples.
        """
        task_set = self._scheduled_tasks_set
        return task_set

    def pop_scheduled_task(self, station_id: int, time: int, task_id: int) -> None:
        """Remove a scheduled task from the set after emission O(1).

        Args:
            station_id: The station ID.
            time: The scheduled time.
            task_id: The task ID.
        Returns:
            None
        """
        self._scheduled_tasks_set.discard((station_id, time, task_id))

    def check_for_new_task(self, station: "Station") -> List[BatterySwapTask]:
        """Check if a new task should popup at the station.

        Args:
            station: The station to check for new task popup.

        Returns:
            List of BatterySwapTask that have popped up.
        """

        # `env.now` can be int or float. cast to int to match scheduled keys
        sim_time = int(station.env.now)

        # Any scheduled tasks for this station ever?
        if not self.station_scheduled_tasks:
            return []

        scheduled_times = self.station_scheduled_tasks.get(station.id, {})
        if not scheduled_times:
            return []

        # Any scheduled tasks for this station at this time?
        tasks_at_current_time = scheduled_times.get(sim_time, [])
        if not tasks_at_current_time:
            return []

        pop_up_tasks: List[BatterySwapTask] = []

        for task_id in tasks_at_current_time:
            task = BatterySwapTask(
                task_id=task_id,
                station=station,
                spawn_time=sim_time,
            )
            task.set_state(State.OPEN)
            task.has_updated = True
            pop_up_tasks.append(task)
            self._scheduled_tasks_set.discard((station.id, sim_time, task_id))
        return pop_up_tasks

    def _build_scheduled_tasks_set(self) -> None:
        """Build the set of scheduled tasks from station_scheduled_tasks.

        This method is called after setting the station scheduled tasks.
        """
        self._scheduled_tasks_set = set()
        if not self.station_scheduled_tasks:
            return

        for station_id, times in self.station_scheduled_tasks.items():
            for time, task_ids in times.items():
                for task_id in task_ids:
                    self._scheduled_tasks_set.add((station_id, time, task_id))
