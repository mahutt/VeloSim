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

from typing import TYPE_CHECKING, Any
from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from back.database.session import Base
from back.models.scenario import JSONBCompatible

if TYPE_CHECKING:
    from .sim_instance import SimInstance


class SimKeyframe(Base):
    """Model to represent persisted simulation keyframes for replay purposes.

    Stores complete simulation state snapshots at regular intervals to enable
    replay and branching functionality. Keyframes are automatically deleted
    when the parent simulation instance is deleted.
    """

    __tablename__ = "sim_keyframes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    sim_instance_id: Mapped[int] = mapped_column(
        ForeignKey("sim_instances.id", ondelete="CASCADE"), nullable=False
    )

    sim_seconds_elapsed: Mapped[float] = mapped_column(nullable=False)
    """Simulation time in seconds when this keyframe was captured."""

    frame_data: Mapped[Any] = mapped_column(JSONBCompatible, nullable=False)
    """Complete frame payload as JSONB (PostgreSQL) or JSON text (SQLite)."""

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationship
    sim_instance: Mapped["SimInstance"] = relationship(
        "SimInstance", back_populates="keyframes"
    )

    # Composite index for efficient querying by simulation and time
    __table_args__ = (
        Index(
            "ix_sim_keyframes_instance_time",
            "sim_instance_id",
            "sim_seconds_elapsed",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SimKeyframe(id={self.id}, sim_instance_id={self.sim_instance_id}, "
            f"sim_seconds_elapsed={self.sim_seconds_elapsed:.2f})>"
        )
