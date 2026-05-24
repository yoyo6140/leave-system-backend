import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.schemas import UserCreate, UserOut, ok, fail

user_router  = APIRouter(prefix="/user",  tags=["user"])
users_router = APIRouter(prefix="/users", tags=["users"])


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")
    return current_user


# ── /user 單筆操作 ─────────────────────────────────────────────────────────────

@user_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="新增員工",
    description="admin 限定，新增一位員工帳號",
    response_model=UserOut,
)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == body.username).first():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=fail("USERNAME_EXISTS", "帳號已存在"),
        )

    if db.query(User).filter(User.email == body.email).first():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=fail("EMAIL_EXISTS", "信箱已被使用"),
        )

    if db.query(User).filter(User.id_number == body.id_number).first():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=fail("ID_NUMBER_EXISTS", "身分證號碼已存在"),
        )

    hashed = bcrypt.hashpw(body.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = User(
        username    = body.username,
        password    = hashed,
        name        = body.name,
        role        = body.role,
        email       = body.email,
        gender      = body.gender,
        id_number   = body.id_number,
        hire_date   = body.hire_date,
        birth_date  = body.birth_date,
        is_verified = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ── /users 列表操作 ────────────────────────────────────────────────────────────

# 之後新增查詢列表 API
