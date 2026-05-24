from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .user import User


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id:         Mapped[str]           = mapped_column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:    Mapped[int]           = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type:       Mapped[str]           = mapped_column(SAEnum("特休", "病假", "事假", "婚假", "喪假", "公假", "其他", name="leave_type"), nullable=False)
    start_date: Mapped[str]           = mapped_column(String,  nullable=False)
    end_date:   Mapped[str]           = mapped_column(String,  nullable=False)
    hours:      Mapped[int]           = mapped_column(Integer, nullable=False)
    reason:     Mapped[str]           = mapped_column(String,  default="")
    status:     Mapped[str]           = mapped_column(SAEnum("待審核", "已通過", "已拒絕", name="leave_status"), nullable=False, default="待審核")
    reviewer:   Mapped[str | None]           = mapped_column(String,  nullable=True)
    created_at: Mapped[datetime]             = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime | None]      = mapped_column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped[User] = relationship("User", back_populates="leave_records")
