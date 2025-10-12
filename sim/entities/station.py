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

        # starting the process for periodic station operations
        self.action = env.process(self.run())

    def add_task(self, task: "Task") -> None:
        self.tasks.append(task)
        task.set_station(self)

    def remove_task(self, task: "Task") -> None:
        if task in self.tasks:
            self.tasks.remove(task)

    def get_task_count(self) -> int:
        return len(self.tasks)

    def get_station_position(self) -> "Position":
        return self.position

    # continous process that runs throughout the simulation
    def run(self):  # type: ignore[no-untyped-def]
        # TODO: replace with periodic operations
        while True:
            yield self.env.timeout(1)
