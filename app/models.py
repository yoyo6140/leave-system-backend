import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum
from app.database import Base


class User(Base):
    __tablename__ = "users"

    username  = Column(String, primary_key=True, index=True)
    password  = Column(String, nullable=False)
    name      = Column(String, nullable=False)
    role      = Column(SAEnum("admin", "employee", name="user_role"), nullable=False, default="employee")
    gender    = Column(SAEnum("男", "女", name="gender"), nullable=True)
    id_number = Column(String(10), nullable=True)
    hire_date = Column(String, nullable=True)
    birth_date= Column(String, nullable=True)
    created_at= Column(DateTime, default=datetime.utcnow)


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username   = Column(String, nullable=False, index=True)
    type       = Column(SAEnum("特休","病假","事假","婚假","喪假","公假","其他", name="leave_type"), nullable=False)
    start_date = Column(String, nullable=False)
    end_date   = Column(String, nullable=False)
    hours      = Column(Integer, nullable=False)
    reason     = Column(String, default="")
    status     = Column(SAEnum("待審核","已通過","已拒絕", name="leave_status"), nullable=False, default="待審核")
    created_at = Column(DateTime, default=datetime.utcnow)
