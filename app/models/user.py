from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum, Sequence, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .leave_record import LeaveRecord

# 員工編號序號（A0001 起）。掛在 Base.metadata 上，create_all() 會連它一起建出來；
# 停用帳號不會回收編號，序號本身天生就滿足這個規則（只會前進，不會重複）。
employee_no_seq = Sequence("employee_no_seq", start=1, metadata=Base.metadata)


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]      = mapped_column(Integer,    primary_key=True, autoincrement=True)
    username:   Mapped[str]      = mapped_column(String,     unique=True, nullable=False, index=True)
    password:   Mapped[str]      = mapped_column(String,     nullable=False)
    name:       Mapped[str]      = mapped_column(String,     nullable=False)
    role:       Mapped[str]      = mapped_column(SAEnum("sup_admin", "admin", "employee", name="user_role"), nullable=False, default="employee")
    email:      Mapped[str] = mapped_column(String,     unique=True, nullable=False)
    is_verified: Mapped[bool]      = mapped_column(default=False, nullable=False)
    is_active:  Mapped[bool]       = mapped_column(default=True, server_default=text("true"), nullable=False)
    gender:     Mapped[str] = mapped_column(SAEnum("男", "女", name="gender"), nullable=False)
    id_number:  Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    hire_date:  Mapped[str] = mapped_column(String,     nullable=False)
    birth_date: Mapped[str] = mapped_column(String,     nullable=False)
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    leave_records: Mapped[list[LeaveRecord]] = relationship(
        "LeaveRecord", foreign_keys="LeaveRecord.user_id", back_populates="user"
    )
