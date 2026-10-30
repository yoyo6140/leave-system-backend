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
