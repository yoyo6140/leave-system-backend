from datetime import datetime
from typing import Any
from pydantic import BaseModel


class UserOut(BaseModel):
    id:         int
    username:   str
    name:       str
    role:       str
    email:      str
    gender:     str
    id_number:  str
    hire_date:  str
    birth_date: str
    is_active:  bool

    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    name:       str
    role:       str = "employee"
    email:      str
    gender:     str
    id_number:  str
    hire_date:  str
    birth_date: str

class UserUpdate(BaseModel):
    name:       str
    role:       str
    email:      str
    gender:     str
    id_number:  str
    hire_date:  str
    birth_date: str

class UserStatusUpdate(BaseModel):
    is_active: bool

class UserListData(BaseModel):
    total: int
    page:  int
    limit: int
    data:  list[UserOut]

class UserListResponse(BaseModel):
    success: bool = True
    data:    UserListData

class UserResponse(BaseModel):
    success: bool = True
    data:    UserOut

class UserLogOut(BaseModel):
    id:         str
    action:     str
    changes:    dict[str, Any] | None = None
    changed_by: int | None = None
    changed_at: datetime

    model_config = {"from_attributes": True}

class UserLogListResponse(BaseModel):
    success: bool = True
    data:    list[UserLogOut]
