"""
建立 7 種假別（leave_types 表）
執行：python seed_leave_types.py
"""

from app.database import SessionLocal
from app.models import LeaveType

LEAVE_TYPES = [
    # code,          name,  quota_type,  quota_hours, sort_order
    ("annual",      "特休", "seniority", None, 1),
    ("sick",        "病假", "fixed",     240,  2),
    ("personal",    "事假", "fixed",     112,  3),
    ("marriage",    "婚假", "unlimited", None, 4),
    ("bereavement", "喪假", "unlimited", None, 5),
    ("official",    "公假", "unlimited", None, 6),
    ("other",       "其他", "unlimited", None, 7),
]

db = SessionLocal()

existing_codes = {code for (code,) in db.query(LeaveType.code).all()}
created = 0
for code, name, quota_type, quota_hours, sort_order in LEAVE_TYPES:
    if code in existing_codes:
        continue
    db.add(LeaveType(
        code=code, name=name, quota_type=quota_type,
        quota_hours=quota_hours, sort_order=sort_order,
    ))
    created += 1

db.commit()
print(f"假別建立完成，新增 {created} 筆（略過 {len(LEAVE_TYPES) - created} 筆已存在）")

db.close()
