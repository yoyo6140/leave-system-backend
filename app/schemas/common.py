from typing import Any
from pydantic import BaseModel


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
