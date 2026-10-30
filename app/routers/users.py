import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, PasswordResetToken, UserLog
from app.models.user import employee_no_seq
from app.models.user_log import log_user_action
from app.auth import get_current_user
from app.schemas import (
    UserCreate, UserOut, UserUpdate, UserStatusUpdate, UserListResponse, UserResponse,
    UserLogOut, UserLogListResponse, ok, fail,
)

# 修改這些欄位時，一般的 "update" 紀錄就寫入新舊值；id_number 只記「已修改」（規格第 8 節）
MASKED_FIELDS = {"id_number"}

router = APIRouter(tags=["user"])

DEFAULT_PASSWORD = "6666666"
MANAGER_ROLES    = ("sup_admin", "admin")  # 可以管理 employee 帳號、審核假單的角色

_USER_EXAMPLE = {
    "id": 1,
    "username": "A0001",
    "name": "John Doe",
    "role": "employee",
    "email": "john@example.com",
    "gender": "男",
    "id_number": "A123456789",
    "hire_date": "2020-01-01",
    "birth_date": "1990-05-15",
    "is_active": True,
}


def require_admin(current_user=Depends(get_current_user)):
    """admin、sup_admin 都算「管理端」，可以呼叫這些帳號管理 API；
    admin 跟 sup_admin 之間更細的權限差異（能不能動到其他管理員帳號、改角色/受雇日期）
    在各自路由裡另外檢查。"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")
    return current_user


def next_employee_no(db: Session) -> str:
    n = db.execute(select(employee_no_seq.next_value())).scalar()
    return f"A{n:04d}"


# ── 列表 ───────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    status_code=status.HTTP_200_OK,
    summary="查詢員工列表",
    description="admin 限定，支援以姓名、帳號、身分證字號搜尋與分頁",
    response_model=UserListResponse,
    responses={
        200: {
            "description": "查詢成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "total": 1,
                            "page": 1,
                            "limit": 10,
                            "data": [_USER_EXAMPLE],
                        },
                    }
                }
            },
        },
    },
)
def get_users(
    search: str = Query(default="", description="搜尋姓名、帳號或身分證字號（身分證字號不分大小寫）"),
    page: int   = Query(default=1,  ge=1, description="頁碼"),
    limit: int  = Query(default=10, ge=1, le=500, description="每頁筆數"),
    include_inactive: bool = Query(default=False, description="是否包含已停用的帳號"),
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    query = db.query(User)
    if not include_inactive:
        query = query.filter(User.is_active.is_(True))
    if search:
        query = query.filter(
            User.name.contains(search)
            | User.username.contains(search)
            | User.id_number.icontains(search)
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
    response_model=UserResponse,
    summary="新增員工",
    description="admin 限定，新增一位員工帳號",
    responses={
        201: {
            "description": "新增成功",
            "content": {"application/json": {"example": {"success": True, "data": _USER_EXAMPLE}}},
        },
    },
)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if body.role not in ("employee", "admin", "sup_admin"):
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_ROLE", "角色必須為 sup_admin／admin／employee"))
    if body.role != "employee" and current_user.role != "sup_admin":
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "僅 sup_admin 可建立 admin 或 sup_admin 帳號"))
    if db.query(User).filter(User.email == body.email).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("EMAIL_EXISTS", "信箱已被使用"))
    if db.query(User).filter(User.id_number == body.id_number).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("ID_NUMBER_EXISTS", "身分證號碼已存在"))

    hashed = bcrypt.hashpw(DEFAULT_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(
        username    = next_employee_no(db),
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
    db.flush()  # 取得 user.id
    log_user_action(db, user_id=user.id, action="create", changed_by=current_user.id)
    db.commit()
    db.refresh(user)
    return ok(UserOut.model_validate(user))


@router.get(
    "/user/{id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="查詢員工資料",
    description="admin 限定，查詢一位員工的資料",
    responses={
        200: {
            "description": "查詢成功",
            "content": {"application/json": {"example": {"success": True, "data": _USER_EXAMPLE}}},
        },
    },
)
def get_user(
    id: int,
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("USER_NOT_FOUND", "找不到使用者"))
    return ok(UserOut.model_validate(user))


@router.put(
    "/user/{id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="更新員工資料",
    description="admin 限定，更新一位員工的資料",
    responses={
        200: {
            "description": "更新成功",
            "content": {"application/json": {"example": {"success": True, "data": _USER_EXAMPLE}}},
        },
    },
)
def update_user(
    id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("USER_NOT_FOUND", "找不到使用者"))

    # admin 不能管理 admin／sup_admin 帳號（含自己），只有 sup_admin 可以
    if current_user.role != "sup_admin" and user.role in MANAGER_ROLES:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "僅 sup_admin 可管理管理員帳號"))

    if body.role not in ("employee", "admin", "sup_admin"):
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_ROLE", "角色必須為 sup_admin／admin／employee"))

    # 角色、受雇日期僅 sup_admin 可改；admin 呼叫時若嘗試變更一律 403
    if current_user.role != "sup_admin" and (body.role != user.role or body.hire_date != user.hire_date):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "僅 sup_admin 可修改角色或受雇日期"))

    if db.query(User).filter(User.email == body.email, User.id != id).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("EMAIL_EXISTS", "信箱已被使用"))
    if db.query(User).filter(User.id_number == body.id_number, User.id != id).first():
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("ID_NUMBER_EXISTS", "身分證號碼已存在"))

    # 一般欄位（name/email/gender/id_number/birth_date）的異動記成一筆 "update"；
    # role、hire_date 各自是獨立的 action（規格的 user_logs.action 列舉值）
    general_changes = {}
    for field in ("name", "email", "gender", "id_number", "birth_date"):
        old_val, new_val = getattr(user, field), getattr(body, field)
        if old_val != new_val:
            general_changes[field] = "已修改" if field in MASKED_FIELDS else [old_val, new_val]

    if body.role != user.role:
        log_user_action(db, user_id=user.id, action="update_role", changed_by=current_user.id, changes={"role": [user.role, body.role]})
    if body.hire_date != user.hire_date:
        log_user_action(db, user_id=user.id, action="update_hire_date", changed_by=current_user.id, changes={"hire_date": [user.hire_date, body.hire_date]})
    if general_changes:
        log_user_action(db, user_id=user.id, action="update", changed_by=current_user.id, changes=general_changes)

    user.name       = body.name
    user.role       = body.role
    user.email      = body.email
    user.gender     = body.gender
    user.id_number  = body.id_number
    user.hire_date  = body.hire_date
    user.birth_date = body.birth_date
    db.commit()
    db.refresh(user)
    return ok(UserOut.model_validate(user))


@router.patch(
    "/user/{id}/status",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="啟用／停用員工帳號",
    description="admin 限定。停用後該員工無法登入，已發出的 token 也會失效；請假紀錄完整保留。admin 不可停用自己",
    responses={
        200: {
            "description": "更新成功",
            "content": {"application/json": {"example": {"success": True, "data": {**_USER_EXAMPLE, "is_active": False}}}},
        },
    },
)
def update_user_status(
    id: int,
    body: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("USER_NOT_FOUND", "找不到使用者"))
    if user.id == current_user.id and not body.is_active:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=fail("CANNOT_DEACTIVATE_SELF", "不可停用自己的帳號"))

    # admin 不能啟用／停用 admin／sup_admin 帳號，只有 sup_admin 可以
    if current_user.role != "sup_admin" and user.role in MANAGER_ROLES:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "僅 sup_admin 可管理管理員帳號"))

    # 系統至少保留一個啟用中的 sup_admin，不能停用最後一個
    if user.role == "sup_admin" and not body.is_active:
        other_active_sup_admins = (
            db.query(User)
            .filter(User.role == "sup_admin", User.is_active.is_(True), User.id != user.id)
            .count()
        )
        if other_active_sup_admins == 0:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=fail("LAST_SUP_ADMIN", "系統至少要保留一個啟用中的 sup_admin"))

    user.is_active = body.is_active
    if not body.is_active:
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == id).delete()
    log_user_action(
        db, user_id=user.id,
        action="activate" if body.is_active else "deactivate",
        changed_by=current_user.id,
    )
    db.commit()
    db.refresh(user)
    return ok(UserOut.model_validate(user))


@router.get(
    "/user/{id}/logs",
    status_code=status.HTTP_200_OK,
    response_model=UserLogListResponse,
    summary="查詢帳號異動紀錄",
    description="admin、sup_admin 限定。查詢一個帳號的建立、修改、停用、啟用、密碼變更等歷史紀錄",
    responses={
        200: {
            "description": "查詢成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "id": "log-uuid-example",
                                "action": "create",
                                "changes": None,
                                "changed_by": 1,
                                "changed_at": "2024-06-20T10:00:00",
                            }
                        ],
                    }
                }
            },
        },
    },
)
def get_user_logs(
    id: int,
    db: Session = Depends(get_db),
    _: User     = Depends(require_admin),
):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("USER_NOT_FOUND", "找不到使用者"))

    logs = db.query(UserLog).filter(UserLog.user_id == id).order_by(UserLog.changed_at).all()
    return ok([UserLogOut.model_validate(l) for l in logs])
