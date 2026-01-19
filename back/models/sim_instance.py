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

from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from back.database.session import Base
from back.models.scenario import JSONBCompatible

if TYPE_CHECKING:
    from .user import User
    from .sim_frame import SimFrame


class SimInstance(Base):
    """Model to represent sim instances.

    This model will be more fleshed out once we know more about how sims will run.
    """

    __tablename__ = "sim_instances"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # UUID for external identification (matches simulator UUID)
    uuid: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, unique=True, index=True
    )

    date_created: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    date_updated: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="sim_instances")

    # Original scenario payload to enable consistent restarts
    scenario_payload: Mapped[Optional[Any]] = mapped_column(
        JSONBCompatible, nullable=True
    )

    # User-provided name for the simulation instance
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # True for all new instances with full frame persistence, False for legacy instances
    playback_capable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # For branched simulations: FK to parent sim instance
    parent_sim_instance_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sim_instances.id", ondelete="SET NULL"), nullable=True
    )

    # For branched simulations: seq_number of keyframe this sim branched from
    branch_keyframe_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    frames: Mapped[List["SimFrame"]] = relationship(
        "SimFrame", back_populates="sim_instance", cascade="all, delete-orphan"
    )

    # Self-referential relationship for branching
    parent_sim_instance: Mapped[Optional["SimInstance"]] = relationship(
        "SimInstance",
        remote_side="SimInstance.id",
        foreign_keys=[parent_sim_instance_id],
        backref="child_sim_instances",
    )

    def __repr__(self) -> str:
        return f"<SimInstance(id={self.id}, user_id={self.user_id}, name={self.name})>"
