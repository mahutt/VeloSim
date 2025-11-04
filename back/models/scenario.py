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

from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, Dialect, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator, TypeEngine
from back.database.session import Base

if TYPE_CHECKING:
    from .user import User


class JSONBCompatible(TypeDecorator[Any]):
    """Use PostgreSQL JSONB if available, otherwise fallback to Text (SQLite)."""

    impl = Text  # fallback for SQLite

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(
        self, value: Optional[Any], dialect: Dialect
    ) -> Optional[Any]:
        return value

    def process_result_value(
        self, value: Optional[Any], dialect: Dialect
    ) -> Optional[Any]:
        return value


class Scenario(Base):
    """Model to represent user-created simulation scenarios."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # JSONB for Postgres, Text fallback for SQLite
    content: Mapped[Any] = mapped_column(JSONBCompatible, nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    date_created: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    date_updated: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="scenarios")

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, name='{self.name}', user_id={self.user_id})>"
