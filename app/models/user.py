from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .leave_record import LeaveRecord


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]      = mapped_column(Integer,    primary_key=True, autoincrement=True)
    username:   Mapped[str]      = mapped_column(String,     unique=True, nullable=False, index=True)
    password:   Mapped[str]      = mapped_column(String,     nullable=False)
    name:       Mapped[str]      = mapped_column(String,     nullable=False)
    role:       Mapped[str]      = mapped_column(SAEnum("admin", "employee", name="user_role"), nullable=False, default="employee")
    email:      Mapped[str] = mapped_column(String,     unique=True, nullable=True)
    is_verified: Mapped[bool]      = mapped_column(default=False, nullable=False)
    gender:     Mapped[str] = mapped_column(SAEnum("男", "女", name="gender"), nullable=True)
    id_number:  Mapped[str] = mapped_column(String(10), unique=True, nullable=True)
    hire_date:  Mapped[str] = mapped_column(String,     nullable=True)
    birth_date: Mapped[str] = mapped_column(String,     nullable=True)
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    leave_records: Mapped[list[LeaveRecord]] = relationship("LeaveRecord", back_populates="user")
