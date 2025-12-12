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
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from back.database.session import Base

if TYPE_CHECKING:
    from .station_task import StationTask
    from .sim_instance import SimInstance


class Station(Base):
    """Station model for bike sharing stations."""

    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sim_instance_id: Mapped[int] = mapped_column(
        ForeignKey("sim_instances.id"), nullable=False
    )
    sim_instance: Mapped["SimInstance"] = relationship(
        "SimInstance", back_populates="stations"
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    tasks: Mapped[List["StationTask"]] = relationship(
        "StationTask", back_populates="station"
    )

    def __repr__(self) -> str:
        return (
            f"<Station(id={self.id}, name='{self.name}', "
            f"position=[{self.longitude}, {self.latitude}])>"
        )

    @property
    def position(self) -> list[float]:
        """Get position as [longitude, latitude] to match sim model.

        Returns:
            list[float]: Position as [longitude, latitude].
        """
        return [self.longitude, self.latitude]

    @position.setter
    def position(self, pos: list[float]) -> None:
        """Set position from [longitude, latitude] list.

        Args:
            pos: Position as [longitude, latitude].

        Returns:
            None
        """
        if len(pos) != 2:
            raise ValueError("Position must be [longitude, latitude]")
        self.longitude = pos[0]
        self.latitude = pos[1]
