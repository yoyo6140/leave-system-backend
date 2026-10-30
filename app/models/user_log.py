from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .user import User


class UserLog(Base):
    __tablename__ = "user_logs"

    id:         Mapped[str]      = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action:     Mapped[str]      = mapped_column(String(20), nullable=False)  # create/update/deactivate/activate/change_password/reset_password/update_hire_date/update_role
    changes:    Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # {field: [old, new]}；密碼、身分證字號只記 "已修改"
    changed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)  # 操作人；忘記密碼重設時為本人
    changed_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user:    Mapped[User]       = relationship("User", foreign_keys=[user_id])
    changer: Mapped[User | None] = relationship("User", foreign_keys=[changed_by])


def log_user_action(
    db,
    *,
    user_id: int,
    action: str,
    changed_by: int | None,
    changes: dict[str, Any] | None = None,
) -> None:
    """統一寫入 user_logs，只 add() 不 commit()，跟著呼叫端原本的 transaction 一起送出。"""
    db.add(UserLog(user_id=user_id, action=action, changes=changes, changed_by=changed_by))
