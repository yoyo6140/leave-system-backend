from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Integer

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .user import User


class KbDocument(Base):
    __tablename__ = "kb_documents"

    id:            Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title:         Mapped[str]       = mapped_column(String(200), nullable=False)
    content:       Mapped[str] = mapped_column(String, nullable=False)
    source:        Mapped[str]       = mapped_column(String(500), nullable=False)
    status:        Mapped[str]       = mapped_column(String(20), nullable=False, default="processing")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    uploaded_by:   Mapped[int]       = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:    Mapped[datetime]  = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    uploader: Mapped[User] = relationship("User")