"""
建立 5 名員工假資料 + 請假紀錄
執行：python seed_employees.py
"""

import uuid
import bcrypt
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import User, LeaveRecord, LeaveStatusLog
from app.routers.users import next_employee_no, DEFAULT_PASSWORD

# 假別中文 -> leave_types.code（這份種子資料用中文比較好讀，實際存進去要轉成代碼）
LEAVE_TYPE_CODE_BY_NAME = {
    "特休": "annual",
    "病假": "sick",
    "事假": "personal",
    "婚假": "marriage",
    "喪假": "bereavement",
    "公假": "official",
    "其他": "other",
}

db = SessionLocal()

# ── 取得管理員（作為審核人）────────────────────────────────────────────────────
admin = db.query(User).filter(User.role.in_(("sup_admin", "admin"))).first()
if not admin:
    print("❌ 找不到管理員帳號，請先執行 seed_admin.py")
    db.close()
    exit(1)

# ── 員工資料 ──────────────────────────────────────────────────────────────────
EMPLOYEES = [
    {
        "key":        "chen_zhiming",
        "name":       "陳志明",
        "email":      "chen.zhiming@company.com",
        "gender":     "男",
        "id_number":  "A112345678",
        "hire_date":  "2021-03-15",   # 年資最久 ~5年
        "birth_date": "1988-05-20",
    },
    {
        "key":        "lin_meiling",
        "name":       "林美玲",
        "email":      "lin.meiling@company.com",
        "gender":     "女",
        "id_number":  "B223456789",
        "hire_date":  "2022-06-01",   # ~4年
        "birth_date": "1992-11-08",
    },
    {
        "key":        "huang_jianhong",
        "name":       "黃建宏",
        "email":      "huang.jianhong@company.com",
        "gender":     "男",
        "id_number":  "C134567890",
        "hire_date":  "2023-09-01",   # ~2年10個月
        "birth_date": "1990-07-14",
    },
    {
        "key":        "wang_yating",
        "name":       "王雅婷",
        "email":      "wang.yating@company.com",
        "gender":     "女",
        "id_number":  "D245678901",
        "hire_date":  "2024-04-15",   # ~2年2個月
        "birth_date": "1995-03-22",
    },
    {
        "key":        "zhang_yuxuan",
        "name":       "張宇軒",
        "email":      "zhang.yuxuan@company.com",
        "gender":     "男",
        "id_number":  "E156789012",
        "hire_date":  "2025-01-10",   # ~1年5個月
        "birth_date": "1998-09-30",
    },
]

# ── 請假紀錄（key 對應 EMPLOYEES 的 "key"，純內部索引，不是真正的帳號）──────────
# status: 已通過 / 已拒絕 / 待審核 / 已取消
LEAVE_RECORDS: dict[str, list[dict]] = {
    "chen_zhiming": [
        {"type": "特休", "start": "2021-05-03", "end": "2021-05-07", "hours": 40, "status": "已通過", "reason": "家庭旅遊"},
        {"type": "病假", "start": "2021-09-15", "end": "2021-09-15", "hours": 8,  "status": "已通過", "reason": "感冒就醫"},
        {"type": "事假", "start": "2022-01-03", "end": "2022-01-03", "hours": 8,  "status": "已通過", "reason": "處理私事"},
        {"type": "特休", "start": "2022-08-15", "end": "2022-08-19", "hours": 40, "status": "已通過", "reason": "出國旅遊"},
        {"type": "病假", "start": "2022-11-21", "end": "2022-11-22", "hours": 16, "status": "已通過", "reason": "腸胃炎"},
        {"type": "特休", "start": "2023-02-06", "end": "2023-02-10", "hours": 40, "status": "已通過", "reason": "春節延假"},
        {"type": "事假", "start": "2023-06-05", "end": "2023-06-05", "hours": 8,  "status": "已通過", "reason": "辦理文件"},
        {"type": "特休", "start": "2024-01-22", "end": "2024-01-26", "hours": 40, "status": "已通過", "reason": "年假"},
        {"type": "病假", "start": "2024-04-08", "end": "2024-04-08", "hours": 8,  "status": "已拒絕", "reason": "身體不適"},
        {"type": "公假", "start": "2024-09-10", "end": "2024-09-10", "hours": 8,  "status": "已通過", "reason": "教育訓練"},
        {"type": "特休", "start": "2025-03-03", "end": "2025-03-07", "hours": 40, "status": "已通過", "reason": "出遊"},
        {"type": "事假", "start": "2026-06-15", "end": "2026-06-15", "hours": 8,  "status": "待審核", "reason": "家人就醫陪同"},
    ],
    "lin_meiling": [
        {"type": "特休", "start": "2022-09-05", "end": "2022-09-09", "hours": 40, "status": "已通過", "reason": "休假"},
        {"type": "事假", "start": "2022-12-26", "end": "2022-12-26", "hours": 8,  "status": "已通過", "reason": "搬家"},
        {"type": "病假", "start": "2023-03-20", "end": "2023-03-20", "hours": 8,  "status": "已通過", "reason": "頭痛就醫"},
        {"type": "特休", "start": "2023-07-17", "end": "2023-07-21", "hours": 40, "status": "已通過", "reason": "暑假旅遊"},
        {"type": "婚假", "start": "2023-10-09", "end": "2023-10-18", "hours": 64, "status": "已通過", "reason": "結婚"},
        {"type": "事假", "start": "2024-02-19", "end": "2024-02-19", "hours": 8,  "status": "已通過", "reason": "個人事務"},
        {"type": "特休", "start": "2024-06-17", "end": "2024-06-21", "hours": 40, "status": "已通過", "reason": "家庭旅遊"},
        {"type": "病假", "start": "2024-11-11", "end": "2024-11-12", "hours": 16, "status": "已通過", "reason": "流感休養"},
        {"type": "特休", "start": "2025-05-05", "end": "2025-05-09", "hours": 40, "status": "已拒絕", "reason": "旅遊"},
        {"type": "事假", "start": "2026-06-08", "end": "2026-06-08", "hours": 8,  "status": "待審核", "reason": "處理行政事務"},
    ],
    "huang_jianhong": [
        {"type": "特休", "start": "2023-12-25", "end": "2023-12-29", "hours": 40, "status": "已通過", "reason": "耶誕跨年"},
        {"type": "病假", "start": "2024-02-26", "end": "2024-02-26", "hours": 8,  "status": "已通過", "reason": "發燒就醫"},
        {"type": "事假", "start": "2024-05-20", "end": "2024-05-20", "hours": 8,  "status": "已通過", "reason": "辦理證件"},
        {"type": "特休", "start": "2024-08-12", "end": "2024-08-16", "hours": 40, "status": "已通過", "reason": "暑假"},
        {"type": "病假", "start": "2024-11-04", "end": "2024-11-05", "hours": 16, "status": "已通過", "reason": "扭傷休養"},
        {"type": "特休", "start": "2025-01-20", "end": "2025-01-24", "hours": 40, "status": "已通過", "reason": "農曆年前連假"},
        {"type": "公假", "start": "2025-09-03", "end": "2025-09-03", "hours": 8,  "status": "已通過", "reason": "消防演習"},
        {"type": "事假", "start": "2026-05-04", "end": "2026-05-04", "hours": 8,  "status": "待審核", "reason": "私人事宜"},
    ],
    "wang_yating": [
        {"type": "特休", "start": "2024-08-26", "end": "2024-08-30", "hours": 40, "status": "已通過", "reason": "休假"},
        {"type": "病假", "start": "2024-10-14", "end": "2024-10-14", "hours": 8,  "status": "已通過", "reason": "婦科回診"},
        {"type": "事假", "start": "2025-01-06", "end": "2025-01-06", "hours": 8,  "status": "已通過", "reason": "行政事務"},
        {"type": "特休", "start": "2025-04-07", "end": "2025-04-11", "hours": 40, "status": "已通過", "reason": "清明連假"},
        {"type": "其他", "start": "2025-11-17", "end": "2025-11-17", "hours": 8,  "status": "已取消", "reason": "個人規劃調整"},
        {"type": "事假", "start": "2026-06-22", "end": "2026-06-22", "hours": 8,  "status": "待審核", "reason": "家庭事務"},
    ],
    "zhang_yuxuan": [
        {"type": "病假", "start": "2025-03-17", "end": "2025-03-17", "hours": 8,  "status": "已通過", "reason": "急性腸胃炎"},
        {"type": "事假", "start": "2025-07-07", "end": "2025-07-07", "hours": 8,  "status": "已通過", "reason": "辦理個人事務"},
        {"type": "特休", "start": "2026-01-20", "end": "2026-01-24", "hours": 40, "status": "已通過", "reason": "農曆年連假"},
        {"type": "病假", "start": "2026-06-01", "end": "2026-06-01", "hours": 8,  "status": "待審核", "reason": "身體不適"},
    ],
}


def make_dt(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)


def add_status_logs(leave: LeaveRecord, employee: User):
    """依最終狀態補上 status log"""
    # 建立時的初始紀錄
    db.add(LeaveStatusLog(
        id=str(uuid.uuid4()),
        leave_id=leave.id,
        from_status=None,
        to_status="待審核",
        changed_by=employee.id,
        changed_at=make_dt(leave.start_date),
    ))

    if leave.status in ("已通過", "已拒絕"):
        db.add(LeaveStatusLog(
            id=str(uuid.uuid4()),
            leave_id=leave.id,
            from_status="待審核",
            to_status=leave.status,
            changed_by=admin.id,
            changed_at=make_dt(leave.start_date),
        ))
    elif leave.status == "已取消":
        db.add(LeaveStatusLog(
            id=str(uuid.uuid4()),
            leave_id=leave.id,
            from_status="待審核",
            to_status="已取消",
            changed_by=employee.id,
            changed_at=make_dt(leave.start_date),
        ))


# ── 建立員工與請假紀錄 ────────────────────────────────────────────────────────
for emp_data in EMPLOYEES:
    existing = db.query(User).filter(User.id_number == emp_data["id_number"]).first()
    if existing:
        print(f"⚠️  [{emp_data['name']}] 已存在，略過")
        continue

    # 帳號一律自動編號（A0001 起）、預設密碼一律 6666666，跟 POST /user 的規則一致
    hashed = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()
    employee = User(
        username    = next_employee_no(db),
        password    = hashed,
        name        = emp_data["name"],
        role        = "employee",
        email       = emp_data["email"],
        is_verified = True,
        gender      = emp_data["gender"],
        id_number   = emp_data["id_number"],
        hire_date   = emp_data["hire_date"],
        birth_date  = emp_data["birth_date"],
    )
    db.add(employee)
    db.flush()  # 取得 employee.id

    records = LEAVE_RECORDS.get(emp_data["key"], [])
    for r in records:
        reviewer_id = admin.id if r["status"] in ("已通過", "已拒絕") else None
        leave = LeaveRecord(
            id          = str(uuid.uuid4()),
            user_id     = employee.id,
            type        = LEAVE_TYPE_CODE_BY_NAME[r["type"]],
            start_date  = r["start"],
            end_date    = r["end"],
            hours       = r["hours"],
            reason      = r.get("reason", ""),
            status      = r["status"],
            reviewer_id = reviewer_id,
            created_at  = make_dt(r["start"]),
        )
        db.add(leave)
        db.flush()
        add_status_logs(leave, employee)

    print(f"✅ {employee.name}（{employee.username}）+ {len(records)} 筆請假紀錄")

db.commit()
print("\n✅ 所有員工與請假資料建立完成")
print(f"   預設密碼：{DEFAULT_PASSWORD}")
db.close()
