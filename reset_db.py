from app.database import engine, Base
from app import models  # 確保所有 model 都被載入

print("⚠️  即將刪除所有資料表並重新建立...")

Base.metadata.drop_all(bind=engine)
print("✅ 舊資料表已刪除")

Base.metadata.create_all(bind=engine)
print("✅ 新資料表已建立完成")
print("   - users (id, username, password, name, role, gender, id_number, hire_date, birth_date, created_at)")
print("   - leave_records (id, user_id→users.id, type, start_date, end_date, hours, reason, status, reviewer, created_at, updated_at)")
