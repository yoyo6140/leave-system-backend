from fastapi import APIRouter, Depends, Query
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, LeaveRecord
from app.schemas import LeaveCreate, LeaveUpdate, LeaveStatusUpdate, LeaveOut, ok, fail
from app.auth import get_current_user

router = APIRouter(prefix="/leaves", tags=["leave"])

VALID_TYPES    = {"特休", "病假", "事假", "婚假", "喪假", "公假", "其他"}
VALID_STATUSES = {"待審核", "已通過", "已拒絕", "已取消"}


# ── 查詢列表 ───────────────────────────────────────────────────────────────────

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="查詢請假紀錄列表",
    description="admin 可查所有人，員工只能查自己。支援狀態篩選與分頁",
)
def get_leaves(
    status_filter: str | None = Query(default=None, alias="status", description="篩選狀態：待審核 / 已通過 / 已拒絕"),
    page:  int = Query(default=1,  ge=1,        description="頁碼"),
    limit: int = Query(default=10, ge=1, le=100, description="每頁筆數"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(LeaveRecord)

    if current_user.role != "admin":
        query = query.filter(LeaveRecord.user_id == current_user.id)

    if status_filter:
        query = query.filter(LeaveRecord.status == status_filter)

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
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 修改內容 ───────────────────────────────────────────────────────────────────

@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="修改請假內容",
    description="員工只能修改狀態為「待審核」的自己的紀錄；admin 可修改任何紀錄",
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

    if current_user.role != "admin":
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
    description="admin 限定，更新請假狀態（已通過 / 已拒絕）",
)
def update_leave_status(
    id: str,
    body: LeaveStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "僅 admin 可審核請假"))

    if body.status not in VALID_STATUSES:
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=fail("INVALID_STATUS", f"狀態必須為：{', '.join(VALID_STATUSES)}"))

    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))

    record.status   = body.status
    record.reviewer = body.reviewer
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 取消 ───────────────────────────────────────────────────────────────────────

@router.patch(
    "/{id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="取消請假申請",
    description="員工可取消自己「待審核」或「已通過」的申請；admin 可取消任何紀錄",
)
def cancel_leave(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))

    if current_user.role != "admin":
        if record.user_id != current_user.id:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "無權限取消此紀錄"))
        if record.status not in {"待審核", "已通過"}:
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_NOT_CANCELABLE", "僅能取消「待審核」或「已通過」的請假申請"))

    if record.status == "已取消":
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_ALREADY_CANCELLED", "此請假申請已取消"))

    record.status = "已取消"
    db.commit()
    db.refresh(record)
    return ok(LeaveOut.model_validate(record))


# ── 刪除 ───────────────────────────────────────────────────────────────────────

@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="刪除請假申請",
    description="員工只能刪除狀態為「待審核」的自己的申請；admin 可刪除任何紀錄",
)
def delete_leave(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(LeaveRecord).filter(LeaveRecord.id == id).first()
    if not record:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=fail("LEAVE_NOT_FOUND", "找不到請假紀錄"))

    if current_user.role != "admin":
        if record.user_id != current_user.id:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=fail("FORBIDDEN", "無權限刪除此紀錄"))
        if record.status != "待審核":
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=fail("LEAVE_NOT_DELETABLE", "僅能刪除狀態為「待審核」的請假申請"))

    db.delete(record)
    db.commit()
    return ok({"message": "請假紀錄已刪除"})
