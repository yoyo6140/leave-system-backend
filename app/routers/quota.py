from datetime import date, timedelta
from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, LeaveRecord, LeaveType
from app.auth import get_current_user
from app.leave_quota import get_all_quotas, get_anniversary_year_start, get_anniversary_year_end
from app.schemas import LeaveQuotaResponse, ok, fail

router = APIRouter(prefix="/leave-quota", tags=["leave-quota"])

_QUOTA_EXAMPLE = {
    "success": True,
    "data": {
        "user_id": 1,
        "username": "john_doe",
        "name": "John Doe",
        "as_of": "2024-06-30",
        "year_start": "2024-03-15",
        "year_end": "2025-03-14",
        "quotas": [
            {"type": "annual", "total_days": 14, "total_hours": 112, "used_hours": 16, "remaining_hours": 96, "note": "年資 4 年"},
            {"type": "sick", "total_days": 30, "total_hours": 240, "used_hours": 0, "remaining_hours": 240, "note": None},
            {"type": "personal", "total_days": 14, "total_hours": 112, "used_hours": 8, "remaining_hours": 104, "note": None},
            {"type": "marriage", "total_days": None, "total_hours": None, "used_hours": 0, "remaining_hours": None, "note": "無上限"},
            {"type": "bereavement", "total_days": None, "total_hours": None, "used_hours": 0, "remaining_hours": None, "note": "無上限"},
            {"type": "official", "total_days": None, "total_hours": None, "used_hours": 0, "remaining_hours": None, "note": "無上限"},
            {"type": "other", "total_days": None, "total_hours": None, "used_hours": 0, "remaining_hours": None, "note": "無上限"},
        ],
    },
}


def _build_quota(user: User, as_of: date, db: Session) -> dict:
    hire = date.fromisoformat(user.hire_date)
    year_start = get_anniversary_year_start(hire, as_of)
    year_end   = get_anniversary_year_end(hire, year_start)

    # 下一個週年日（作為查詢的排他上界）
    next_anniversary = year_end + timedelta(days=1)

    leave_types = db.query(LeaveType).order_by(LeaveType.sort_order).all()
    quotas = get_all_quotas(user.hire_date, leave_types, as_of)

    # 撈該週年度內狀態為「待審核」或「已通過」的假單，依假別加總時數
    # 送出即預扣：待審核的時數也算已佔用（規格第 5 節）
    used_rows = (
        db.query(LeaveRecord.type, func.sum(LeaveRecord.hours))
        .filter(
            LeaveRecord.user_id == user.id,
            LeaveRecord.status.in_(["待審核", "已通過"]),
            LeaveRecord.start_date >= year_start.isoformat(),
            LeaveRecord.start_date <  next_anniversary.isoformat(),
        )
        .group_by(LeaveRecord.type)
        .all()
    )
    used_map = {t: h for t, h in used_rows}

    for q in quotas:
        used_h = used_map.get(q["type"], 0)
        q["used_hours"]      = used_h
        q["remaining_hours"] = (q["total_hours"] - used_h) if q["total_hours"] is not None else None

    return {
        "user_id":    user.id,
        "username":   user.username,
        "name":       user.name,
        "as_of":      as_of.isoformat(),
        "year_start": year_start.isoformat(),
        "year_end":   year_end.isoformat(),
        "quotas":     quotas,
    }


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="查詢自己的假別額度",
    description="依勞基法及到職週年度計算額度，並扣除本週年度內已通過的請假時數",
    response_model=LeaveQuotaResponse,
    responses={
        200: {
            "description": "查詢成功",
            "content": {"application/json": {"example": _QUOTA_EXAMPLE}},
        },
    },
)
def get_my_quota(
    as_of: date = Query(default=None, description="計算基準日，預設為今天"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_date = as_of or date.today()
    return ok(_build_quota(current_user, target_date, db))


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="查詢指定員工的假別額度",
    description="admin 限定，依勞基法及到職週年度計算，並扣除本週年度內已通過的請假時數",
    response_model=LeaveQuotaResponse,
    responses={
        200: {
            "description": "查詢成功",
            "content": {"application/json": {"example": _QUOTA_EXAMPLE}},
        },
    },
)
def get_user_quota(
    user_id: int,
    as_of: date = Query(default=None, description="計算基準日，預設為今天"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=fail("FORBIDDEN", "僅 admin 可查詢其他員工的假別額度"),
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=fail("USER_NOT_FOUND", "找不到使用者"),
        )

    target_date = as_of or date.today()
    return ok(_build_quota(user, target_date, db))
