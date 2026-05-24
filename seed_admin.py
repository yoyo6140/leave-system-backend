import bcrypt
from app.database import SessionLocal
from app.models import User

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1234"
ADMIN_NAME     = "系統管理員"
ADMIN_EMAIL    = "abc142536798@gmail.com"

db = SessionLocal()

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
    )
    db.add(admin)
    db.commit()
    print(f"Admin 帳號建立成功")
    print(f"   帳號：{ADMIN_USERNAME}")
    print(f"   密碼：{ADMIN_PASSWORD}")
    print(f"   姓名：{ADMIN_NAME}")

db.close()
