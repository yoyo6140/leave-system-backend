from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from .leave_record import LeaveRecord


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]           = mapped_column(Integer,    primary_key=True, autoincrement=True)
    username:   Mapped[str]           = mapped_column(String,     unique=True, nullable=False, index=True)
    password:   Mapped[str]           = mapped_column(String,     nullable=False)
    name:       Mapped[str]           = mapped_column(String,     nullable=False)
    role:       Mapped[str]           = mapped_column(SAEnum("admin", "employee", name="user_role"), nullable=False, default="employee")
    gender:     Mapped[Optional[str]] = mapped_column(SAEnum("男", "女", name="gender"), nullable=True)
    id_number:  Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    hire_date:  Mapped[Optional[str]] = mapped_column(String,     nullable=True)
    birth_date: Mapped[Optional[str]] = mapped_column(String,     nullable=True)
    created_at: Mapped[datetime]      = mapped_column(DateTime,   default=datetime.utcnow)

    leave_records: Mapped[list["LeaveRecord"]] = relationship("LeaveRecord", back_populates="user")
