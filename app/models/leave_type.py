from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class LeaveType(Base):
    __tablename__ = "leave_types"

    code:   Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    quota_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quota_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)