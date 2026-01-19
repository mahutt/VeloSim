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
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from back.database.session import Base
from back.models.scenario import JSONBCompatible

if TYPE_CHECKING:
    from .sim_instance import SimInstance


class SimFrame(Base):
    """Model to represent persisted simulation frames for replay purposes.

    Stores both keyframes (complete state snapshots) and diff frames
    (incremental updates) to enable full replay, seek, and branching
    functionality. Frames are automatically deleted when the parent
    simulation instance is deleted.

    The unique constraint on (sim_instance_id, seq_number) ensures
    idempotent writes, allowing safe retry of frame persistence operations.
    """

    __tablename__ = "sim_frames"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    sim_instance_id: Mapped[int] = mapped_column(
        ForeignKey("sim_instances.id", ondelete="CASCADE"), nullable=False
    )

    seq_number: Mapped[int] = mapped_column(nullable=False)
    """Frame sequence number, unique per simulation instance.

    Used for ordering and idempotency.
    """

    sim_seconds_elapsed: Mapped[float] = mapped_column(nullable=False)
    """Simulation time in seconds when this frame was captured."""

    frame_data: Mapped[Any] = mapped_column(JSONBCompatible, nullable=False)
    """Complete frame payload as JSONB (PostgreSQL) or JSON text (SQLite)."""

    is_key: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """True if keyframe (complete state), False if diff frame (incremental)."""

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationship
    sim_instance: Mapped["SimInstance"] = relationship(
        "SimInstance", back_populates="frames"
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint for idempotent writes
        UniqueConstraint(
            "sim_instance_id", "seq_number", name="uq_sim_frames_instance_seq"
        ),
        # Composite index for time-based queries (seek operations)
        Index(
            "ix_sim_frames_instance_time",
            "sim_instance_id",
            "sim_seconds_elapsed",
        ),
        # Index for querying keyframes specifically
        Index("ix_sim_frames_is_key", "sim_instance_id", "is_key"),
        # Index for querying by creation time
        Index("ix_sim_frames_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        frame_type = "keyframe" if self.is_key else "diff"
        return (
            f"<SimFrame(id={self.id}, sim_instance_id={self.sim_instance_id}, "
            f"seq={self.seq_number}, time={self.sim_seconds_elapsed:.2f}, "
            f"type={frame_type})>"
        )
