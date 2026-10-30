from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .user import User
    from .leave_status_log import LeaveStatusLog


class LeaveRecord(Base):
    __tablename__ = "leave_records"
    __table_args__ = (
        # 查詢可用時數（依 user_id/type/status/start_date 加總）用的複合索引
        Index("ix_leave_records_quota_lookup", "user_id", "type", "status", "start_date"),
    )

    id:          Mapped[str]           = mapped_column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:     Mapped[int]           = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type:        Mapped[str]           = mapped_column(String(20), ForeignKey("leave_types.code"), nullable=False)
    start_date:  Mapped[str]           = mapped_column(String,  nullable=False)
    end_date:    Mapped[str]           = mapped_column(String,  nullable=False)
    hours:       Mapped[int]           = mapped_column(Integer, nullable=False)
    reason:      Mapped[str]           = mapped_column(String,  nullable=False)
    status:      Mapped[str]           = mapped_column(SAEnum("待審核", "已通過", "已拒絕", "已取消", "已銷假", name="leave_status"), nullable=False, default="待審核")
    reviewer_id: Mapped[int | None]           = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None]      = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None]           = mapped_column(String,  nullable=True)
    created_at:  Mapped[datetime]             = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:  Mapped[datetime | None]      = mapped_column(DateTime(timezone=True), nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    user:         Mapped[User]                  = relationship("User", foreign_keys=[user_id], back_populates="leave_records")
    reviewer_user: Mapped[User | None]          = relationship("User", foreign_keys=[reviewer_id])
    status_logs:  Mapped[list[LeaveStatusLog]] = relationship("LeaveStatusLog", back_populates="leave", order_by="LeaveStatusLog.changed_at")

    @property
    def reviewer(self) -> str | None:
        """API 的 reviewer 欄位輸出姓名，不是 user id（規格第 9 節）"""
        return self.reviewer_user.name if self.reviewer_user else None
