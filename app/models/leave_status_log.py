from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .user import User
    from .leave_record import LeaveRecord


class LeaveStatusLog(Base):
    __tablename__ = "leave_status_logs"

    id:          Mapped[str]      = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    leave_id:    Mapped[str]      = mapped_column(String, ForeignKey("leave_records.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)   # 建立時為 None
    to_status:   Mapped[str]      = mapped_column(String, nullable=False)
    action:      Mapped[str | None] = mapped_column(String(20), nullable=True)  # create/update/resubmit/approve/reject/cancel/revoke
    note:        Mapped[str | None] = mapped_column(String, nullable=True)      # 退回、銷假理由
    changes:     Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # {field: [old, new]}
    changed_by:  Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    leave:      Mapped[LeaveRecord] = relationship("LeaveRecord", back_populates="status_logs")
    changer:    Mapped[User]        = relationship("User")
