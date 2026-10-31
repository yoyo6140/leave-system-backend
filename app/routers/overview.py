from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, LeaveRecord
from app.schemas import ok
from app.schemas.overview import OverviewResponse, MonthlyLeaveStatsResponse

router = APIRouter(prefix="/overview", tags=["overview"])

MANAGER_ROLES = ("admin", "sup_admin")

_EXAMPLE = {
    "success": True,
    "data": {
        "pending_count": 3,
        "approved_this_month": 5,
        "employee_count": 10,
        "pending_list": [
            {
                "id": "abc123",
                "user_id": 1,
                "user_name": "王小明",
                "type": "annual",
                "hours": 8,
                "start_date": "2024-07-01",
                "end_date": "2024-07-01",
                "created_at": "2024-06-20T10:00:00+00:00",
            }
        ],
    },
}

_MONTHLY_EXAMPLE = {
    "success": True,
    "data": {
        "year": 2026,
        "months": [{"month": m, "count": 0} for m in range(1, 13)],
    },
}


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="管理員總覽",
    description="admin 限定。回傳待審核數、本月核准數、員工人數、待審核列表",
    response_model=OverviewResponse,
    responses={
        200: {
            "description": "查詢成功",
            "content": {"application/json": {"example": _EXAMPLE}},
        },
    },
)
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")

    now = date.today()
    month_start_dt = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 待審核列表（全部，前端決定顯示幾筆）
    pending_records = (
        db.query(LeaveRecord)
        .filter(LeaveRecord.status == "待審核")
        .order_by(LeaveRecord.created_at.desc())
        .all()
    )

    # 本月已核准數
    approved_this_month = (
        db.query(LeaveRecord)
        .filter(
            LeaveRecord.status == "已通過",
            LeaveRecord.created_at >= month_start_dt,
        )
        .count()
    )

    # 員工人數
    employee_count = db.query(User).filter(User.role == "employee", User.is_active.is_(True)).count()

    # 使用者 id → name 對照表
    user_map: dict[int, str] = {u.id: u.name for u in db.query(User).all()}

    pending_list = [
        {
            "id":         r.id,
            "user_id":    r.user_id,
            "user_name":  user_map.get(r.user_id, f"#{r.user_id}"),
            "type":       r.type,
            "hours":      r.hours,
            "start_date": r.start_date,
            "end_date":   r.end_date,
            "created_at": r.created_at.isoformat(),
        }
        for r in pending_records
    ]

    return ok({
        "pending_count":       len(pending_records),
        "approved_this_month": approved_this_month,
        "employee_count":      employee_count,
        "pending_list":        pending_list,
    })


# ── 每月請假次數統計（獨立 API，可依年度篩選，不跟上面的總覽綁在一起）─────────────

@router.get(
    "/leave-count-monthly",
    status_code=status.HTTP_200_OK,
    summary="每月請假次數統計",
    description=(
        "admin、sup_admin 限定。依指定年度（預設今年），回傳 1~12 月各月"
        "已通過的請假次數，讓管理者看出哪個月是請假尖峰。\n\n"
        "每張假單依 `start_date` 歸屬到當月計一次，跟額度期間的歸屬規則一致。"
    ),
    response_model=MonthlyLeaveStatsResponse,
    responses={
        200: {
            "description": "查詢成功",
            "content": {"application/json": {"example": _MONTHLY_EXAMPLE}},
        },
    },
)
def get_leave_count_monthly(
    year: int = Query(default=None, description="要查詢的年度，預設今年"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="權限不足")

    target_year = year or date.today().year

    records = (
        db.query(LeaveRecord.start_date)
        .filter(
            LeaveRecord.status == "已通過",
            LeaveRecord.start_date.like(f"{target_year}-%"),
        )
        .all()
    )

    count_by_month: list[int] = [0] * 12
    for (start_date,) in records:
        month_index = int(start_date[5:7]) - 1
        count_by_month[month_index] += 1

    months = [{"month": m + 1, "count": count_by_month[m]} for m in range(12)]

    return ok({"year": target_year, "months": months})
