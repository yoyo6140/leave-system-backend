from datetime import datetime
from typing import Any
from pydantic import BaseModel


# ── 統一回應格式 ──────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str

class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    error: ErrorDetail | None = None

def ok(data: Any = None) -> dict:
    return {"success": True, "data": data}

def fail(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    username:   str
    name:       str
    role:       str
    gender:     str | None = None
    id_number:  str | None = None
    hire_date:  str | None = None
    birth_date: str | None = None

    model_config = {"from_attributes": True}


# ── Users ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username:   str
    password:   str
    name:       str
    role:       str = "employee"
    gender:     str | None = None
    id_number:  str | None = None
    hire_date:  str | None = None
    birth_date: str | None = None

class UserUpdate(BaseModel):
    name:       str | None = None
    password:   str | None = None
    gender:     str | None = None
    id_number:  str | None = None
    hire_date:  str | None = None
    birth_date: str | None = None


# ── Leave Records ─────────────────────────────────────────────────────────────

class LeaveCreate(BaseModel):
    type:       str
    start_date: str
    end_date:   str
    hours:      int
    reason:     str = ""

class LeaveStatusUpdate(BaseModel):
    status: str

class LeaveOut(BaseModel):
    id:         str
    user_id:    int
    type:       str
    start_date: str
    end_date:   str
    hours:      int
    reason:     str
    status:     str
    reviewer:   str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
