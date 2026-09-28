import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import bcrypt
from app.database import get_db
from app.models import User, PasswordResetToken
from app.schemas import (
    LoginRequest, LoginResponse, LoginErrorResponse, SuccessResponse,
    UserOut, ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
    ok, fail,
)
from app.auth import verify_password, create_token, get_current_user
from app.email import send_reset_password_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", include_in_schema=False)
def swagger_token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="帳號已停用")
    token = create_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="使用者登入",
    description="登入成功後回傳 Bearer Token，前端存入 localStorage 並於後續請求帶上 Authorization header",
    response_model=LoginResponse,
    responses={
        401: {"model": LoginErrorResponse},
        403: {"model": LoginErrorResponse, "description": "帳號已停用"},
    },
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()

    if not user or not verify_password(body.password, user.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=fail("INVALID_CREDENTIALS", "帳號或密碼錯誤")
        )

    if not user.is_active:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=fail("ACCOUNT_DISABLED", "帳號已停用")
        )

    token = create_token({"sub": str(user.id), "role": user.role})

    return {"success": True, "data": {"token": token}}


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="登出",
    description="登出，前端應自行清除 localStorage 中的 token",
    response_model=SuccessResponse,
    responses={
        200: {
            "description": "登出成功",
            "content": {"application/json": {"example": {"success": True}}},
        },
    },
)
def logout():
    return {"success": True}


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserOut,
    summary="取得目前登入的使用者資料",
    responses={
        200: {
            "description": "目前登入的使用者",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "john_doe",
                        "name": "John Doe",
                        "role": "employee",
                        "email": "john@example.com",
                        "gender": "male",
                        "id_number": "A123456789",
                        "hire_date": "2020-01-01",
                        "birth_date": "1990-05-15",
                    }
                }
            },
        },
    },
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="申請密碼重設",
    description="輸入信箱，若帳號存在則寄出重設連結（連結 30 分鐘內有效）",
    response_model=MessageResponse,
    responses={
        200: {
            "description": "申請已受理（無論信箱是否存在均回傳相同訊息）",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {"message": "若此信箱已註冊，您將收到密碼重設信件"},
                    }
                }
            },
        },
    },
)
async def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    # 無論信箱是否存在或帳號是否停用，都回傳相同訊息，避免帳號枚舉攻擊
    if user and user.is_active:
        # 刪除該使用者舊有的未使用 token
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()

        token      = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at))
        db.commit()

        try:
            await send_reset_password_email(to=user.email, token=token)
        except Exception:
            pass  # SMTP 未設定或失敗時不中斷，避免洩漏帳號是否存在

    return ok({"message": "若此信箱已註冊，您將收到密碼重設信件"})


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="重設密碼",
    description="使用信箱收到的 token 設定新密碼",
    response_model=MessageResponse,
    responses={
        200: {
            "description": "密碼重設成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {"message": "密碼已成功重設，請重新登入"},
                    }
                }
            },
        },
    },
)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token == body.token).first()

    if not record:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=fail("INVALID_TOKEN", "無效的重設連結"))

    if datetime.now(timezone.utc) > record.expires_at:
        db.delete(record)
        db.commit()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=fail("TOKEN_EXPIRED", "重設連結已過期，請重新申請"))

    user = db.query(User).filter(User.id == record.user_id).first()
    user.password = bcrypt.hashpw(body.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    db.delete(record)
    db.commit()

    return ok({"message": "密碼已成功重設，請重新登入"})
