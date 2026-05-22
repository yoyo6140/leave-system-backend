from typing import Any, Optional
from pydantic import BaseModel


# ── 統一回應格式 ──────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str

class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    error: Optional[ErrorDetail] = None

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
    gender:     Optional[str] = None
    id_number:  Optional[str] = None
    hire_date:  Optional[str] = None
    birth_date: Optional[str] = None

    class Config:
        from_attributes = True


# ── Users ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username:   str
    password:   str
    name:       str
    role:       str = "employee"
    gender:     Optional[str] = None
    id_number:  Optional[str] = None
    hire_date:  Optional[str] = None
    birth_date: Optional[str] = None

class UserUpdate(BaseModel):
    name:       Optional[str] = None
    password:   Optional[str] = None
    gender:     Optional[str] = None
    id_number:  Optional[str] = None
    hire_date:  Optional[str] = None
    birth_date: Optional[str] = None


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
    username:   str
    type:       str
    start_date: str
    end_date:   str
    hours:      int
    reason:     str
    status:     str
    created_at: str

    class Config:
        from_attributes = True
