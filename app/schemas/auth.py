from pydantic import BaseModel, EmailStr, Field
from .common import ErrorDetail


class LoginRequest(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str = Field(min_length=6, max_length=12)

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
