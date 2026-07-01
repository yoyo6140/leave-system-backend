import bcrypt
from sqlalchemy import text
from app.database import engine, Base, SessionLocal
from app import models  # 確保所有 model 都被載入
from app.models import User

print("⚠️  即將刪除所有資料表並重新建立...")

# 刪除所有資料表
Base.metadata.drop_all(bind=engine)
print("✅ 舊資料表已刪除")

# PostgreSQL 自訂 ENUM 不隨資料表自動刪除，需手動清除
ENUM_TYPES = ["user_role", "gender", "leave_type", "leave_status"]
with engine.connect() as conn:
    for enum_name in ENUM_TYPES:
        conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
    conn.commit()
print("✅ 舊 ENUM 型態已刪除")

# 重新建立所有資料表
Base.metadata.create_all(bind=engine)
print("✅ 新資料表已建立完成")
print("   - users")
print("   - leave_records")
print("   - leave_status_logs")
print("   - password_reset_tokens")
print("   - email_verifications")

# 建立 admin 帳號
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1234"
ADMIN_NAME     = "系統管理員"
ADMIN_EMAIL    = "abc142536798@gmail.com"

db = SessionLocal()
try:
    existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if existing:
        print(f"帳號 [{ADMIN_USERNAME}] 已存在，略過")
    else:
        hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        admin = User(
            username    = ADMIN_USERNAME,
            password    = hashed,
            name        = ADMIN_NAME,
            role        = "admin",
            email       = ADMIN_EMAIL,
            is_verified = True,
            gender      = "男",
            id_number   = "A000000000",
            hire_date   = "2020-01-01",
            birth_date  = "1990-01-01",
        )
        db.add(admin)
        db.commit()
        print("✅ Admin 帳號建立成功")
        print(f"   帳號：{ADMIN_USERNAME}")
        print(f"   密碼：{ADMIN_PASSWORD}")
        print(f"   姓名：{ADMIN_NAME}")
finally:
    db.close()
