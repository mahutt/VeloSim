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

from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from back.models import StationTaskType, TaskStatus
from back.database.session import Base

if TYPE_CHECKING:
    from .station import Station
    from .resource import Resource
    from .sim_instance import SimInstance


class StationTask(Base):
    """Model to represent tasks that must be done to a specific bike (as opposed to
    tasks to maintain the station itself).
    """

    __tablename__ = "station_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sim_instance_id: Mapped[int] = mapped_column(
        ForeignKey("sim_instances.id"), nullable=False
    )
    sim_instance: Mapped["SimInstance"] = relationship(
        "SimInstance", back_populates="tasks"
    )

    type: Mapped[StationTaskType] = mapped_column(Enum(StationTaskType), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), nullable=False, default=TaskStatus.OPEN
    )
    date_created: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    date_updated: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    station_id: Mapped[int] = mapped_column(ForeignKey("stations.id"), nullable=False)
    station: Mapped["Station"] = relationship("Station", back_populates="tasks")
    resource_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("resources.id", ondelete="SET NULL"), nullable=True
    )
    resource: Mapped[Optional["Resource"]] = relationship(
        "Resource", back_populates="tasks"
    )

    def __repr__(self) -> str:
        return (
            f"<StationTask(id={self.id}, type={self.type}, status={self.status}, "
            f"station_id={self.station_id}, resource_id={self.resource_id}, "
            f"sim_instance_id={self.sim_instance_id}, "
            f"date_created={self.date_created}, date_updated={self.date_updated})>"
        )
