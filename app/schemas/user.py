from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    username:   str
    password:   str = Field(min_length=6, max_length=12)
    name:       str
    role:       str = "employee"
    email:      str
    gender:     str
    id_number:  str
    hire_date:  str
    birth_date: str

class UserUpdate(BaseModel):
    username:   str
    name:       str
    role:       str
    email:      str
    gender:     str
    id_number:  str
    hire_date:  str
    birth_date: str

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
