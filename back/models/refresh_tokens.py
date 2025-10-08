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

import secrets
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from back.database.session import Base

if TYPE_CHECKING:
    from .user import User


def generate_token_id() -> str:
    return secrets.token_urlsafe(16)


class RefreshToken(Base):
    """Model to represent refresh tokens that have been issued to the user (sessions).
    This will happen automatically on login, and may also happen manually if the user
    creates one to be used with an unattended API client.
    """

    __tablename__ = "refresh_tokens"

    # Need some entropy in this identifier to include in JWTs - 16 bytes base64url
    id: Mapped[str] = mapped_column(
        String(22), primary_key=True, default=generate_token_id, index=True
    )
    user_agent: Mapped[str] = mapped_column(String(512))
    creation_ip: Mapped[str] = mapped_column(String(40))
    token_name: Mapped[str] = mapped_column(String(100))

    date_created: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    date_updated: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    # The expiry date will be used in issuing JWTs
    date_expires: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return (
            f"<RefreshToken(id={self.id}, user_agent={self.user_agent}, "
            f"creation_ip={self.creation_ip}, date_created={self.date_created}, "
            f"date_updated={self.date_updated}, user_id={self.user_id})>"
        )
