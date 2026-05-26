from fastapi import APIRouter, Depends, Query
from fastapi import status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, LeaveRecord
from app.schemas import LeaveOut, ok
from app.auth import get_current_user

router = APIRouter(prefix="/leaves", tags=["leave"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="查詢請假紀錄",
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
