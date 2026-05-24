from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse, LoginErrorResponse, ok, fail
from app.auth import verify_password, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", include_in_schema=False)
def swagger_token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤")
    token = create_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.post(
    "/login", 
    status_code=status.HTTP_200_OK,
    summary="使用者登入",
    description="使用者登入後，返回 JWT Token 與 使用者資料",
    response_model=LoginResponse,
    responses={401: {"model": LoginErrorResponse}},
    )
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()

    if not user or not verify_password(body.password, user.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=fail("INVALID_CREDENTIALS", "帳號或密碼錯誤")
        )

    token = create_token({"sub": str(user.id), "role": user.role})

    return ok({
        "token": token,
        "user": {
            "id":       user.id,
            "username": user.username,
            "name":     user.name,
            "role":     user.role,
        }
    })

