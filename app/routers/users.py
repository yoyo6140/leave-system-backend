import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.schemas import UserCreate, UserOut, UserUpdate, ok, fail

router = APIRouter(tags=["user"])


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")
    return current_user


# ── 列表 ───────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    status_code=status.HTTP_200_OK,
    summary="查詢員工列表",
    description="admin 限定，支援搜尋與分頁",
)
def get_users(
    search: str = Query(default="", description="搜尋姓名或帳號"),
    page: int   = Query(default=1,  ge=1, description="頁碼"),
    limit: int  = Query(default=10, ge=1, le=100, description="每頁筆數"),
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    query = db.query(User)
    if search:
        query = query.filter(
            User.name.contains(search) | User.username.contains(search)
        )
    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()
    return ok({
        "total": total,
        "page":  page,
        "limit": limit,
        "data":  [UserOut.model_validate(u) for u in users],
    })


# ── 單筆 CRUD ──────────────────────────────────────────────────────────────────

@router.post(
    "/user",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
    summary="新增員工",
    description="admin 限定，新增一位員工帳號",
)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    if db.query(User).filter(User.username == body.username).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("USERNAME_EXISTS", "帳號已存在"))
    if db.query(User).filter(User.email == body.email).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("EMAIL_EXISTS", "信箱已被使用"))
    if db.query(User).filter(User.id_number == body.id_number).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("ID_NUMBER_EXISTS", "身分證號碼已存在"))

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


@router.get(
    "/user/{id}",
    status_code=status.HTTP_200_OK,
    response_model=UserOut,
    summary="查詢員工資料",
    description="admin 限定，查詢一位員工的資料",
)
def get_user(
    id: int,
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("USER_NOT_FOUND", "找不到使用者"))
    return user


@router.put(
    "/user/{id}",
    status_code=status.HTTP_200_OK,
    response_model=UserOut,
    summary="更新員工資料",
    description="admin 限定，更新一位員工的資料",
)
def update_user(
    id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("USER_NOT_FOUND", "找不到使用者"))
    if db.query(User).filter(User.email == body.email, User.id != id).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("EMAIL_EXISTS", "信箱已被使用"))
    if db.query(User).filter(User.id_number == body.id_number, User.id != id).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("ID_NUMBER_EXISTS", "身分證號碼已存在"))
    if db.query(User).filter(User.username == body.username, User.id != id).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("USERNAME_EXISTS", "帳號已被使用"))

    user.username   = body.username
    user.name       = body.name
    user.role       = body.role
    user.email      = body.email
    user.gender     = body.gender
    user.id_number  = body.id_number
    user.hire_date  = body.hire_date
    user.birth_date = body.birth_date
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/user/{id}",
    status_code=status.HTTP_200_OK,
    summary="刪除員工帳號",
    description="admin 限定，刪除一位員工的帳號",
)
def delete_user(
    id: int,
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("USER_NOT_FOUND", "找不到使用者"))
    db.delete(user)
    db.commit()
    return ok({"message": "員工帳號已刪除"})
