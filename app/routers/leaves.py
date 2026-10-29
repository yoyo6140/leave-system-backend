from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import User, LeaveRecord, LeaveStatusLog, LeaveType
from app.schemas import (
    LeaveCreate, LeaveUpdate, LeaveStatusUpdate, LeaveOut, LeaveStatusLogOut,
    LeaveListResponse, LeaveResponse, LeaveStatusLogListResponse,
    ok, fail,
)
from app.auth import get_current_user
from app.leave_quota import get_all_quotas, get_anniversary_year_start, get_anniversary_year_end, HOURS_PER_DAY

router = APIRouter(prefix="/leaves", tags=["leave"])

# 編輯/取消允許的來源狀態；通過/退回/銷假允許的 (來源狀態, 目標狀態) -> action
EDITABLE_STATUSES  = {"待審核", "已拒絕"}
STATUS_TRANSITIONS = {
    ("待審核", "已通過"): "approve",
    ("待審核", "已拒絕"): "reject",
    ("已通過", "已銷假"): "revoke",
}
NOTE_REQUIRED_STATUSES = {"已拒絕", "已銷假"}

_LEAVE_EXAMPLE = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": 1,
    "type": "annual",
    "start_date": "2024-07-01",
    "end_date": "2024-07-03",
    "hours": 16,
    "reason": "年度休假",
    "status": "待審核",
    "reviewer": None,
    "reviewed_at": None,
    "review_note": None,
    "created_at": "2024-06-20T10:00:00",
    "updated_at": None,
}

_LOG_EXAMPLE = {
    "id": "log-uuid-example",
    "from_status": None,
    "to_status": "待審核",
    "action": "create",
    "note": None,
    "changes": None,
    "changed_by": 1,
    "changed_at": "2024-06-20T10:00:00",
}


def _leave_query(db: Session):
    """共用：GET 查詢一律 eager load reviewer_user，避免每筆都多查一次"""
    return db.query(LeaveRecord).options(joinedload(LeaveRecord.reviewer_user))


def _get_leave_type(db: Session, code: str) -> LeaveType | None:
    return db.query(LeaveType).filter(LeaveType.code == code).first()


def _all_type_codes(db: Session) -> list[str]:
    return [c for (c,) in db.query(LeaveType.code).order_by(LeaveType.sort_order).all()]


def _validate_leave(
    body,
    leave_type: LeaveType,
    user: User,
    db: Session,
    exclude_id: str | None = None,
) -> tuple[str, str] | None:
    """
    共用驗證（規格第 7 節）。回傳 (error_code, message)；通過回傳 None。
    exclude_id：編輯「待審核」假單時排除自己這筆，避免跟自己的舊時數重複計算。
    """
    if not body.reason or not body.reason.strip():
        return ("MISSING_REASON", "請填寫請假理由")

    try:
        start = date.fromisoformat(body.start_date)
        end   = date.fromisoformat(body.end_date)
    except ValueError:
        return ("INVALID_DATE", "日期格式錯誤")

    if end < start:
        return ("INVALID_DATE_RANGE", "結束日期不可早於開始日期")

    if body.hours <= 0:
        return ("INVALID_HOURS", "時數必須大於 0")

    max_hours = ((end - start).days + 1) * HOURS_PER_DAY
    if body.hours > max_hours:
        return ("HOURS_EXCEED_RANGE", "時數不可超過日期區間天數 × 8")

    if leave_type.quota_type == "unlimited":
        return None  # 無上限假別不檢查額度與跨期間

    hire       = date.fromisoformat(user.hire_date)
    year_start = get_anniversary_year_start(hire, start)
    year_end   = get_anniversary_year_end(hire, year_start)

    if end > year_end:
        next_start = year_end + timedelta(days=1)
        return (
            "LEAVE_CROSS_PERIOD",
            f"此假單跨越 {year_end.isoformat()} 與 {next_start.isoformat()} 兩個年度，"
            f"請以 {year_end.isoformat()} 為界拆成兩張申請",
        )

    quota = get_all_quotas(user.hire_date, [leave_type], start)[0]
    if not quota["total_hours"]:
        return ("NO_LEAVE_QUOTA", f"尚無{leave_type.name}額度")

    next_anniversary = year_end + timedelta(days=1)
    used_query = db.query(func.sum(LeaveRecord.hours)).filter(
        LeaveRecord.user_id == user.id,
        LeaveRecord.type    == leave_type.code,
        LeaveRecord.status.in_(["待審核", "已通過"]),
        LeaveRecord.start_date >= year_start.isoformat(),
        LeaveRecord.start_date <  next_anniversary.isoformat(),
    )
    if exclude_id:
        used_query = used_query.filter(LeaveRecord.id != exclude_id)
    used      = used_query.scalar() or 0
    available = quota["total_hours"] - used

    if body.hours > available:
        return (
            "INSUFFICIENT_LEAVE_HOURS",
            f"{leave_type.name}可用 {available} 小時，不足申請的 {body.hours} 小時",
        )

    return None


def _diff_changes(record: LeaveRecord, body) -> dict | None:
    """編輯時紀錄變動的欄位：{field: [old, new]}，沒有變動回 None"""
    fields = ("type", "start_date", "end_date", "hours", "reason")
    changes = {}
    for f in fields:
        old_val = getattr(record, f)
        new_val = getattr(body, f)
        if old_val != new_val:
            changes[f] = [old_val, new_val]
    return changes or None


# ── 查詢列表 ───────────────────────────────────────────────────────────────────

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="查詢請假紀錄列表",
    description=(
        "預設：admin 可查所有人，員工只能查自己。支援狀態篩選、關鍵字搜尋與分頁。\n\n"
        "帶入 `mine=true` 時，無論角色一律強制只回傳登入者自己的紀錄"
        "（即使是 admin 也只看到自己的）——用於「個人請假紀錄」頁面，"
        "與 admin 專用的「員工請假紀錄／審核管理」查詢分開，避免混用。\n\n"
        "帶入 `search` 時比對請假原因；查詢全公司紀錄時（admin 且未加 `mine`）"
        "同時比對申請人姓名／帳號。"
    ),
    response_model=LeaveListResponse,
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
                            "data": [_LEAVE_EXAMPLE],
                        },
                    }
                }
            },
        },
    },
)
def get_leaves(
    status_filter: str | None = Query(default=None, alias="status", description="篩選狀態：待審核 / 已通過 / 已拒絕 / 已取消 / 已銷假"),
    search: str = Query(default="", description="關鍵字搜尋請假原因；查詢全公司紀錄時（admin 且未加 mine）同時搜尋申請人姓名／帳號"),
    page:  int  = Query(default=1,     ge=1,        description="頁碼"),
    limit: int  = Query(default=10,    ge=1, le=500, description="每頁筆數"),
    mine:  bool = Query(default=False,               description="強制只查詢自己的紀錄，即使是 admin 也一樣（個人請假紀錄頁專用）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _leave_query(db)

    query_all_users = not mine and current_user.role == "admin"
    if not query_all_users:
        query = query.filter(LeaveRecord.user_id == current_user.id)

    if status_filter:
        query = query.filter(LeaveRecord.status == status_filter)

    if search:
        conditions = [LeaveRecord.reason.contains(search)]
        if query_all_users:
            query = query.join(User, LeaveRecord.user_id == User.id)
            conditions.append(User.name.contains(search))
            conditions.append(User.username.contains(search))
        query = query.filter(or_(*conditions))

    query = query.order_by(LeaveRecord.created_at.desc())

    total = query.count()
    records = query.offset((page - 1) * limit).limit(limit).all()

    return ok({
        "total": total,
        "page":  page,
        "limit": limit,
        "data":  [LeaveOut.model_validate(r) for r in records],
    })


# ── 查詢單筆 ───────────────────────────────────────────────────────────────────

@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="查詢單筆請假紀錄",
    description="admin 可查任何人，員工只能查自己的",
    response_model=LeaveResponse,
    responses={
        200: {
            "description": "查詢成功",
            "content": {
                "application/json": {
                    "example": {"success": True, "data": _LEAVE_EXAMPLE}
                }
            },
        },
    },
)
def get_leave(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _leave_query(db).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))
    if current_user.role != "admin" and record.user_id != current_user.id:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "無權限查看此紀錄"))
    return ok(LeaveOut.model_validate(record))


# ── 新增 ───────────────────────────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="新增請假申請",
    description="登入使用者為自己提交請假申請，初始狀態為「待審核」，送出即預扣額度",
    response_model=LeaveResponse,
    responses={
        201: {
            "description": "申請建立成功",
            "content": {
                "application/json": {
                    "example": {"success": True, "data": _LEAVE_EXAMPLE}
                }
            },
        },
    },
)
def create_leave(
    body: LeaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_type = _get_leave_type(db, body.type)
    if not leave_type:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_LEAVE_TYPE", f"假別必須為：{', '.join(_all_type_codes(db))}"))

    error = _validate_leave(body, leave_type, current_user, db)
    if error:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail(*error))

    record = LeaveRecord(
        user_id    = current_user.id,
        type       = body.type,
        start_date = body.start_date,
        end_date   = body.end_date,
        hours      = body.hours,
        reason     = body.reason,
    )
    db.add(record)
    db.flush()  # 取得 record.id，尚未 commit
    db.add(LeaveStatusLog(leave_id=record.id, from_status=None, to_status="待審核", changed_by=current_user.id, action="create"))
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 修改內容（待審核：編輯；已拒絕：編輯即重送）────────────────────────────────

@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="修改請假內容",
    description="僅能修改自己狀態為「待審核」或「已拒絕」的紀錄；「已拒絕」的假單儲存後自動回到「待審核」並重新預扣",
    response_model=LeaveResponse,
    responses={
        200: {
            "description": "修改成功",
            "content": {
                "application/json": {
                    "example": {"success": True, "data": _LEAVE_EXAMPLE}
                }
            },
        },
    },
)
def update_leave(
    id: str,
    body: LeaveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))

    if record.user_id != current_user.id:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "無權限修改此紀錄"))
    if record.status not in EDITABLE_STATUSES:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_NOT_EDITABLE", "僅能修改狀態為「待審核」或「已拒絕」的請假申請"))

    leave_type = _get_leave_type(db, body.type)
    if not leave_type:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_LEAVE_TYPE", f"假別必須為：{', '.join(_all_type_codes(db))}"))

    old_status = record.status
    # 「待審核」編輯時，自己這筆原本的時數已經算在已佔用額度裡，驗證新時數要先排除自己
    exclude_id = record.id if old_status == "待審核" else None
    error = _validate_leave(body, leave_type, current_user, db, exclude_id=exclude_id)
    if error:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail(*error))

    changes = _diff_changes(record, body)
    action  = "resubmit" if old_status == "已拒絕" else "update"

    # 條件更新：只有「狀態還是我讀到時的那個狀態」才會真的更新，避免跟其他請求競態
    updated_rows = (
        db.query(LeaveRecord)
        .filter(LeaveRecord.id == id, LeaveRecord.status == old_status)
        .update({
            "type":       body.type,
            "start_date": body.start_date,
            "end_date":   body.end_date,
            "hours":      body.hours,
            "reason":     body.reason,
            "status":     "待審核",
        })
    )
    if not updated_rows:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_STATUS_CHANGED", "狀態已變更，請重新整理"))

    db.add(LeaveStatusLog(
        leave_id=id, from_status=old_status, to_status="待審核",
        changed_by=current_user.id, action=action, changes=changes,
    ))
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 審核狀態（通過／退回／銷假）─────────────────────────────────────────────────

@router.patch(
    "/{id}/status",
    status_code=status.HTTP_200_OK,
    summary="審核或銷假",
    description=(
        "admin 限定。「待審核」可通過或退回；「已通過」可銷假。"
        "審核人自動帶入目前登入的 admin，不接受前端指定。"
        "退回、銷假時 `review_note` 必填。"
    ),
    response_model=LeaveResponse,
    responses={
        200: {
            "description": "審核成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {**_LEAVE_EXAMPLE, "status": "已通過", "reviewer": "admin"},
                    }
                }
            },
        },
    },
)
def update_leave_status(
    id: str,
    body: LeaveStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "僅 admin 可審核請假"))

    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))

    old_status = record.status
    action = STATUS_TRANSITIONS.get((old_status, body.status))
    if action is None:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_STATUS", f"不允許從「{old_status}」變更為「{body.status}」"))

    if body.status in NOTE_REQUIRED_STATUSES and not (body.review_note and body.review_note.strip()):
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("MISSING_REVIEW_NOTE", "退回或銷假必須填寫理由"))

    now = datetime.now(timezone.utc)
    updated_rows = (
        db.query(LeaveRecord)
        .filter(LeaveRecord.id == id, LeaveRecord.status == old_status)
        .update({
            "status":      body.status,
            "reviewer_id": current_user.id,
            "reviewed_at": now,
            "review_note": body.review_note,
        })
    )
    if not updated_rows:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_STATUS_CHANGED", "狀態已變更，請重新整理"))

    db.add(LeaveStatusLog(
        leave_id=id, from_status=old_status, to_status=body.status,
        changed_by=current_user.id, action=action, note=body.review_note,
    ))
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 狀態歷史 ──────────────────────────────────────────────────────────────────

@router.get(
    "/{id}/status-logs",
    status_code=status.HTTP_200_OK,
    summary="查詢請假狀態變更歷史",
    description="admin 可查任何紀錄；員工只能查自己的",
    response_model=LeaveStatusLogListResponse,
    responses={
        200: {
            "description": "查詢成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [_LOG_EXAMPLE],
                    }
                }
            },
        },
    },
)
def get_leave_status_logs(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))
    if current_user.role != "admin" and record.user_id != current_user.id:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "無權限查看此紀錄"))

    logs = db.query(LeaveStatusLog).filter(LeaveStatusLog.leave_id == id).order_by(LeaveStatusLog.changed_at).all()
    return ok([LeaveStatusLogOut.model_validate(l) for l in logs])


# ── 取消（軟刪除）─────────────────────────────────────────────────────────────
# 流程：申請者送出 → admin 審核（通過／拒絕）。
# 「待審核」或「已拒絕」都可以取消：狀態改成「已取消」並保留紀錄（軟刪除），
# 不整筆砍掉——跟「拒絕」一樣是狀態變化，才留得住查核軌跡；
# 審核完成（已通過／已銷假）後任何角色都不可再取消。

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="取消請假申請（軟刪除）",
    description=(
        "取消申請：狀態改為「已取消」並保留紀錄（不會真的刪除資料列），"
        "僅限狀態為「待審核」或「已拒絕」時可操作，"
        "審核通過（已通過／已銷假）後任何角色都不可再取消。\n\n"
        "僅能取消自己的申請，admin 亦同，不可取消他人申請。"
    ),
    response_model=LeaveResponse,
    responses={
        200: {
            "description": "取消成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {**_LEAVE_EXAMPLE, "status": "已取消"},
                    }
                }
            },
        },
    },
)
def delete_leave(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))

    if record.user_id != current_user.id:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "無權限取消此紀錄"))

    old_status = record.status
    if old_status not in EDITABLE_STATUSES:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_NOT_DELETABLE", "僅能取消狀態為「待審核」或「已拒絕」的請假申請，審核通過後無法再取消"))

    updated_rows = (
        db.query(LeaveRecord)
        .filter(LeaveRecord.id == id, LeaveRecord.status == old_status)
        .update({"status": "已取消"})
    )
    if not updated_rows:
        db.rollback()
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_STATUS_CHANGED", "狀態已變更，請重新整理"))

    db.add(LeaveStatusLog(leave_id=id, from_status=old_status, to_status="已取消", changed_by=current_user.id, action="cancel"))
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))
