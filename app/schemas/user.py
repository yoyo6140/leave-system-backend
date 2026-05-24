from pydantic import BaseModel


class UserOut(BaseModel):
    id:         int
    username:   str
    name:       str
    role:       str
    email:      str | None = None
    gender:     str | None = None
    id_number:  str | None = None
    hire_date:  str | None = None
    birth_date: str | None = None

    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    username:   str
    password:   str
    name:       str
    role:       str = "employee"
    email:      str | None = None
    gender:     str | None = None
    id_number:  str | None = None
    hire_date:  str | None = None
    birth_date: str | None = None

class UserUpdate(BaseModel):
    name:       str | None = None
    password:   str | None = None
    email:      str | None = None
    gender:     str | None = None
    id_number:  str | None = None
    hire_date:  str | None = None
    birth_date: str | None = None
