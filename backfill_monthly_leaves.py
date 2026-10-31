"""
補齊今年 1~11 月的請假紀錄：該月目前完全沒有假單的話，補 3~4 筆「待審核」假單
（用現有員工，不檢查額度，純粹讓每個月都有資料可以測試月份統計／狀態篩選）。
執行：python backfill_monthly_leaves.py
"""

import uuid
from calendar import monthrange
from datetime import date, datetime, timezone

from app.database import SessionLocal
from app.models import LeaveRecord, LeaveStatusLog, User

db = SessionLocal()

YEAR = date.today().year

employees = db.query(User).filter(User.role == "employee").order_by(User.id).all()
if not employees:
    print("❌ 找不到員工帳號，請先執行 seed_employees.py")
    db.close()
    exit(1)

# 假別代碼輪流用，搭配對應的請假理由
TYPE_CYCLE = [
    ("annual", "個人休假"),
    ("sick", "身體不適就醫"),
    ("personal", "處理私事"),
    ("other", "其他事務"),
]

DAYS_IN_MONTH_SLOTS = [5, 12, 19, 26]  # 最多 4 筆時各自的日期


def make_dt(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


created_total = 0

for month in range(1, 12):
    existing = (
        db.query(LeaveRecord)
        .filter(LeaveRecord.start_date.like(f"{YEAR}-{month:02d}-%"))
        .count()
    )
    if existing > 0:
        print(f"⏭️  {YEAR}-{month:02d} 已有 {existing} 筆，略過")
        continue

    count = 3 if month % 2 == 0 else 4
    last_day = monthrange(YEAR, month)[1]

    for i in range(count):
        day = min(DAYS_IN_MONTH_SLOTS[i], last_day)
        start = date(YEAR, month, day)
        employee = employees[(month + i) % len(employees)]
        type_code, reason = TYPE_CYCLE[(month + i) % len(TYPE_CYCLE)]

        leave = LeaveRecord(
            id=str(uuid.uuid4()),
            user_id=employee.id,
            type=type_code,
            start_date=start.isoformat(),
            end_date=start.isoformat(),
            hours=8,
            reason=reason,
            status="待審核",
            created_at=make_dt(start),
        )
        db.add(leave)
        db.flush()  # 取得 leave.id

        db.add(LeaveStatusLog(
            id=str(uuid.uuid4()),
            leave_id=leave.id,
            from_status=None,
            to_status="待審核",
            action="create",
            changed_by=employee.id,
            changed_at=make_dt(start),
        ))
        created_total += 1

    print(f"✅ {YEAR}-{month:02d} 原本 0 筆，補了 {count} 筆待審核假單")

db.commit()
print(f"\n✅ 完成，共新增 {created_total} 筆待審核假單")
db.close()
