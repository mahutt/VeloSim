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

from typing import TYPE_CHECKING, List
from sqlalchemy import Enum, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .resource_type import ResourceType
from .task_status import TaskStatus
from back.database.session import Base

if TYPE_CHECKING:
    from .station_task import StationTask
    from .sim_instance import SimInstance


class Resource(Base):
    """
    Model representing an assignable unit in the simulation.
    """

    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sim_instance_id: Mapped[int] = mapped_column(
        ForeignKey("sim_instances.id"), nullable=False
    )
    sim_instance: Mapped["SimInstance"] = relationship(
        "SimInstance", back_populates="resources"
    )

    type: Mapped[ResourceType] = mapped_column(Enum(ResourceType), nullable=False)
    date_created: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    date_updated: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    route_start_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    route_start_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    route_end_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    route_end_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    tasks: Mapped[List["StationTask"]] = relationship(
        "StationTask",
        back_populates="resource",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Resource(id={self.id}, type={self.type}, "
            f"position={self.position}, "
            f"route={self.route}, "
            f"tasks={[task.id for task in self.tasks]}, "
            f"date_created={self.date_created}, "
            f"date_updated={self.date_updated})>"
        )

    @property
    def position(self) -> list[float]:
        """Get current position as [longitude, latitude] to match sim model.

        Returns:
            list[float]: Current position as [longitude, latitude].
        """
        return [self.longitude, self.latitude]

    @position.setter
    def position(self, pos: list[float]) -> None:
        """Set current position from [longitude, latitude] list.

        Args:
            pos: Position as [longitude, latitude].

        Returns:
            None
        """
        if len(pos) != 2:
            raise ValueError("Position must be in the form [longitude, latitude]")
        self.longitude = pos[0]
        self.latitude = pos[1]

    @property
    def route(self) -> List[List[float]]:
        """Get current route as [[start_long, start_lat], [end_long, end_lat]].

        Returns:
            List[List[float]]: Route as [[start_long, start_lat], [end_long, end_lat]].
        """
        return [
            [self.route_start_longitude, self.route_start_latitude],
            [self.route_end_longitude, self.route_end_latitude],
        ]

    @route.setter
    def route(self, route_pos: List[List[float]]) -> None:
        """Set route from [[start_long, start_lat], [end_long, end_lat]] list.

        Args:
            route_pos: Route as [[start_long, start_lat], [end_long, end_lat]].

        Returns:
            None
        """
        if len(route_pos) != 2 or any(len(p) != 2 for p in route_pos):
            raise ValueError(
                "Route must be [[start_long, start_lat], [end_long, end_lat]]"
            )
        (self.route_start_longitude, self.route_start_latitude), (
            self.route_end_longitude,
            self.route_end_latitude,
        ) = route_pos

    def assign_task(self, task: "StationTask") -> None:
        """Assign a task to this resource (on the precondition that it is open).

        Args:
            task: The station task to assign.

        Returns:
            None
        """
        if task is None:
            raise ValueError("Cannot assign a null task.")
        if task in self.tasks:
            raise ValueError(f"Task {task.id} is already assigned to this resource.")
        if not task.status.is_open:
            raise ValueError(
                f"Task {task.id} has status {task.status.value} and cannot be assigned."
            )
        if task.sim_instance_id != self.sim_instance_id:
            raise ValueError(
                f"Task {task.id} belongs to a different simulation than this resource."
            )
        self.tasks.append(task)
        task.resource = self
        task.status = TaskStatus.ASSIGNED

    def unassign_task(self, task: "StationTask") -> None:
        """Unassign a task from this resource.

        Args:
            task: The station task to unassign.

        Returns:
            None
        """
        if task is None:
            raise ValueError("Cannot unassign a null task.")
        if task not in self.tasks:
            raise ValueError(f"Task {task.id} is not assigned to this resource.")
        self.tasks.remove(task)
        task.resource = None
        task.status = TaskStatus.OPEN

    def service_task(self, task: "StationTask") -> None:
        """Mark a task as closed and remove it from this resource.

        Args:
            task: The station task to service.

        Returns:
            None
        """
        if task is None:
            raise ValueError("Cannot service a null task.")
        if task not in self.tasks:
            raise ValueError(
                f"Task {task.id} is not assigned to this resource "
                "and cannot be serviced."
            )
        self.tasks.remove(task)
        task.resource = None
        task.status = TaskStatus.CLOSED

    def get_task_count(self) -> int:
        """Return the number of tasks currently assigned to the resource.

        Returns:
            int: Number of tasks assigned.
        """
        return len(self.tasks)

    def get_task_list(self) -> List["StationTask"]:
        """Return a list of all tasks currently assigned.

        Returns:
            List[StationTask]: List of assigned tasks.
        """
        return list(self.tasks)
