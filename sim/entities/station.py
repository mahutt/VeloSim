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
import uuid
from sim.behaviour.sim_behaviour import SimBehaviour
from .BatterySwapTask import BatterySwapTask
from typing import TYPE_CHECKING

# to avoid circular imports
if TYPE_CHECKING:  # pragma: no cover
    from .task import Task
    from .position import Position


class Station:

    def __init__(
        self,
        env: simpy.Environment,
        station_id: int,
        name: str,
        position: "Position",  # [longitude, latitude]
        tasks: list["Task"] | None = None,
    ) -> None:
        self.env = env
        self.id = station_id
        self.name = name
        self.position = position
        self.tasks = (
            tasks if tasks is not None else []
        )  # list of tasks assigned to a given station
        self.has_updated = False
        self.pop_up_tasks: list["Task"] = []

    def add_task(self, task: "Task") -> None:
        self.tasks.append(task)
        task.set_station(self)

    def add_pop_up_task(self, task: "Task") -> None:
        self.pop_up_tasks.append(task)
        self.has_updated = True

    def remove_task(self, task: "Task") -> None:
        if task in self.tasks:
            self.tasks.remove(task)

    def get_task_count(self) -> int:
        return len(self.tasks)

    def get_station_position(self) -> "Position":
        return self.position

    def set_behaviour(self, behaviour: SimBehaviour) -> None:
        # Store behaviour consistently under 'behaviour'
        self.behaviour = behaviour

    def check_for_new_task(self) -> None:
        # Use the behaviour reference set via set_behaviour
        has_new_task = False
        if hasattr(self, "behaviour") and hasattr(self.behaviour, "TPU_strategy"):
            has_new_task = self.behaviour.TPU_strategy.check_for_new_task(self)

        if has_new_task:

            # TEMPORARY ID SOLUTION FOR TESTING
            task_id = uuid.uuid4().int % 1_000_000_000
            # Ensure BatterySwapTask is instantiated with the current env
            # and station
            task = BatterySwapTask(env=self.env, task_id=task_id, station=self)
            self.add_task(task)
            self.add_pop_up_task(task)

    def clear_update(self) -> None:
        self.has_updated = False

    # continous process that runs throughout the simulation
    def run(self):  # type: ignore[no-untyped-def]
        # Yield once at the start to ensure behaviour is set
        yield self.env.timeout(1)

        # TODO: replace with periodic operations
        while True:
            self.check_for_new_task()
            yield self.env.timeout(1)
