from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .user import User


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id:         Mapped[int]      = mapped_column(Integer,  primary_key=True, autoincrement=True)
    user_id:    Mapped[int]      = mapped_column(Integer,  ForeignKey("users.id"), nullable=False, index=True)
    token:      Mapped[str]      = mapped_column(String,   unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped[User] = relationship("User")
