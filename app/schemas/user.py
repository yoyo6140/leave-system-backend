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

    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    username:   str
    password:   str
    name:       str
    role:       str = "employee"
    email:      str
    gender:     str
    id_number:  str
    hire_date:  str
    birth_date: str

class UserUpdate(BaseModel):
    name:       str
    password:   str
    email:      str
    gender:     str
    id_number:  str
    hire_date:  str
    birth_date: str
