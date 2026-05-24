from pydantic import BaseModel
from .common import ErrorDetail


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginUserOut(BaseModel):
    id:       int
    username: str
    name:     str
    role:     str

class LoginData(BaseModel):
    token: str
    user:  LoginUserOut

class LoginResponse(BaseModel):
    success: bool = True
    data:    LoginData

class LoginErrorResponse(BaseModel):
    success: bool = False
    error:   ErrorDetail
