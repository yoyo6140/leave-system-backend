from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, LeaveRecord
from app.schemas import ok
from app.schemas.overview import OverviewResponse

router = APIRouter(prefix="/overview", tags=["overview"])

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
        "top_leave_hours": [
            {"user_id": 1, "name": "王小明", "hours": 80}
        ],
    },
}


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="管理員總覽",
    description="admin 限定。回傳待審核數、本月核准數、員工人數、待審核列表、年度請假時數排行（前五名）",
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
    if current_user.role not in ("admin", "sup_admin"):
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

    # 年度已核准時數排行（前五名）
    top_rows = (
        db.query(LeaveRecord.user_id, func.sum(LeaveRecord.hours).label("total_hours"))
        .filter(LeaveRecord.status == "已通過")
        .group_by(LeaveRecord.user_id)
        .order_by(func.sum(LeaveRecord.hours).desc())
        .limit(5)
        .all()
    )

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

    top_leave_hours = [
        {
            "user_id": uid,
            "name":    user_map.get(uid, f"#{uid}"),
            "hours":   int(total),
        }
        for uid, total in top_rows
    ]

    return ok({
        "pending_count":       len(pending_records),
        "approved_this_month": approved_this_month,
        "employee_count":      employee_count,
        "pending_list":        pending_list,
        "top_leave_hours":     top_leave_hours,
    })
