from fastapi import APIRouter, Depends, Query
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, LeaveRecord, LeaveStatusLog
from app.schemas import (
    LeaveCreate, LeaveUpdate, LeaveStatusUpdate, LeaveOut, LeaveStatusLogOut,
    LeaveListResponse, LeaveResponse, LeaveStatusLogListResponse,
    ok, fail,
)
from app.auth import get_current_user

router = APIRouter(prefix="/leaves", tags=["leave"])

VALID_TYPES    = {"特休", "病假", "事假", "婚假", "喪假", "公假", "其他"}
REVIEW_TARGETS = {"已通過", "已拒絕"}

_LEAVE_EXAMPLE = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": 1,
    "type": "特休",
    "start_date": "2024-07-01",
    "end_date": "2024-07-03",
    "hours": 16,
    "reason": "年度休假",
    "status": "待審核",
    "reviewer": None,
    "created_at": "2024-06-20T10:00:00",
    "updated_at": None,
}

_LOG_EXAMPLE = {
    "id": "log-uuid-example",
    "from_status": None,
    "to_status": "待審核",
    "changed_by": 1,
    "changed_at": "2024-06-20T10:00:00",
}


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
    status_filter: str | None = Query(default=None, alias="status", description="篩選狀態：待審核 / 已通過 / 已拒絕"),
    search: str = Query(default="", description="關鍵字搜尋請假原因；查詢全公司紀錄時（admin 且未加 mine）同時搜尋申請人姓名／帳號"),
    page:  int  = Query(default=1,     ge=1,        description="頁碼"),
    limit: int  = Query(default=10,    ge=1, le=500, description="每頁筆數"),
    mine:  bool = Query(default=False,               description="強制只查詢自己的紀錄，即使是 admin 也一樣（個人請假紀錄頁專用）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(LeaveRecord)

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
    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
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
    description="登入使用者為自己提交請假申請，初始狀態為「待審核」",
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
    if body.type not in VALID_TYPES:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_LEAVE_TYPE", f"假別必須為：{', '.join(VALID_TYPES)}"))
    if body.hours <= 0:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_HOURS", "時數必須大於 0"))

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
    db.add(LeaveStatusLog(leave_id=record.id, from_status=None, to_status="待審核", changed_by=current_user.id))
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 修改內容 ───────────────────────────────────────────────────────────────────

@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="修改請假內容",
    description="僅能修改狀態為「待審核」的自己的紀錄，admin 亦同，不可修改他人紀錄",
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
    if record.status != "待審核":
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_NOT_EDITABLE", "僅能修改狀態為「待審核」的請假申請"))

    if body.type not in VALID_TYPES:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_LEAVE_TYPE", f"假別必須為：{', '.join(VALID_TYPES)}"))
    if body.hours <= 0:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_HOURS", "時數必須大於 0"))

    record.type       = body.type
    record.start_date = body.start_date
    record.end_date   = body.end_date
    record.hours      = body.hours
    record.reason     = body.reason
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 審核狀態 ───────────────────────────────────────────────────────────────────

@router.patch(
    "/{id}/status",
    status_code=status.HTTP_200_OK,
    summary="審核請假申請",
    description="admin 限定，將「待審核」的申請核准或駁回；審核人自動帶入目前登入的 admin，不接受前端指定。已審核過的紀錄不可再變更，僅能由申請人重新提出新的紀錄",
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

    if body.status not in REVIEW_TARGETS:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_STATUS", f"狀態必須為：{', '.join(REVIEW_TARGETS)}"))

    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))
    if record.status != "待審核":
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_ALREADY_REVIEWED", "已審核過的申請不可再變更，請申請人重新提出新的紀錄"))

    old_status      = record.status
    record.status   = body.status
    record.reviewer = current_user.name
    db.add(LeaveStatusLog(leave_id=record.id, from_status=old_status, to_status=body.status, changed_by=current_user.id))
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
# 在 admin 審核之前，申請者想取消就把狀態改成「已取消」並保留紀錄（軟刪除），
# 不整筆砍掉——跟「拒絕」一樣是狀態變化，才留得住查核軌跡；
# 審核完成後（已通過／已拒絕）任何角色都不可再取消。

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="取消請假申請（軟刪除）",
    description=(
        "取消申請：狀態改為「已取消」並保留紀錄（不會真的刪除資料列），"
        "僅限狀態仍是「待審核」（尚未經 admin 審核）時可操作，"
        "審核完成後（已通過／已拒絕）任何角色都不可再取消。\n\n"
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

    # 不分身分：審核完成後就不可再取消，取消只能發生在待審核階段
    if record.status != "待審核":
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_NOT_DELETABLE", "僅能取消狀態為「待審核」的請假申請，審核完成後無法再取消"))

    old_status    = record.status
    record.status = "已取消"
    db.add(LeaveStatusLog(leave_id=record.id, from_status=old_status, to_status="已取消", changed_by=current_user.id))
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))
