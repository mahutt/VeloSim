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
from .position import Position


class Resource:
    # @TODO: add attribute for route once Route entity is implemented
    def __init__(
        self,
        env: simpy.Environment,
        resource_id: int,
        position: Position,  # [longitude, latitude]
        task_list: (
            list[int] | None
        ) = None,  # TODO: change from list of task_id (int) to list of Task entities
    ) -> None:
        self.env = env
        self.id = resource_id
        self.position = position
        self.task_list = task_list if task_list is not None else []
        self.has_updated = False  # flag to track if a resource was updated

        # starting the process for periodic resource operations
        self.action = env.process(self.run())

    def get_resource_position(self) -> Position:
        return self.position

    def set_resource_position(self, position: Position) -> None:
        self.position = position

    # TODO: use Task entity instead of task_id once implemented
    def assign_task(self, task_id: int) -> None:
        self.task_list.append(task_id)

    # TODO: use Task entity instead of task_id once implemented
    def unassign_task(self, task_id: int) -> None:
        if task_id in self.task_list:
            self.task_list.remove(task_id)

    def service_task(self, task_id: int) -> None:
        # @TODO: serviceTask has to update the status/current state of the task
        # e.g. task status complete, or task current state closed
        # this would require the Task entity to be implemented
        self.unassign_task(task_id)

    def get_task_count(self) -> int:
        return len(self.task_list)

    def get_task_list(self) -> list[int]:
        return self.task_list

    def clear_update(self) -> None:
        self.has_updated = False

    # continous process that runs throughout the simulation
    def run(self):  # type: ignore[no-untyped-def]
        while True:
            # @TODO: replace with actual periodic logic
            yield self.env.timeout(1)
