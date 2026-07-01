# 忘記密碼功能說明

## 整體流程

```
用戶輸入信箱
    │
    ▼
POST /auth/forgot-password
    │
    ├─ 找不到此信箱 ──► 回傳相同成功訊息（不透露帳號是否存在）
    │
    └─ 找到用戶
           │
           ├─ 刪除舊 token（避免同一用戶有多個有效 token）
           ├─ 產生新 token，寫入 password_reset_tokens 資料表
           ├─ 寄出重設連結信件
           └─ 回傳成功訊息

用戶點擊信件連結（帶有 token）
    │
    ▼
POST /auth/reset-password
    │
    ├─ token 不存在 ──► 400 無效的重設連結
    ├─ token 已過期 ──► 400 重設連結已過期，請重新申請
    └─ 驗證通過
           │
           ├─ 更新用戶密碼（bcrypt 雜湊）
           ├─ 刪除已使用的 token（一次性，防止重複使用）
           └─ 回傳成功訊息
```

---

## Token 如何驗證過期

### 1. 資料表結構（`password_reset_tokens`）

```python
class PasswordResetToken(Base):
    id:         int      # 主鍵
    user_id:    int      # 關聯用戶
    token:      str      # 隨機字串（unique）
    expires_at: datetime # 到期時間（含時區）
    created_at: datetime # 建立時間
```

`expires_at` 在產生 token 時設定為**當下 UTC 時間 + 30 分鐘**：

```python
expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
```

---

### 2. 驗證邏輯（`app/routers/auth.py`）

```python
def reset_password(body: ResetPasswordRequest, db: Session):
    # 步驟一：查詢 token 是否存在
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == body.token
    ).first()

    if not record:
        return 400  # 無效的重設連結

    # 步驟二：比較目前時間與 expires_at
    if datetime.now(timezone.utc) > record.expires_at:
        db.delete(record)   # 過期的 token 直接從 DB 刪除
        db.commit()
        return 400  # 重設連結已過期，請重新申請

    # 步驟三：token 有效，更新密碼
    user = db.query(User).filter(User.id == record.user_id).first()
    user.password = bcrypt.hashpw(
        body.new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    db.delete(record)  # token 使用後立即刪除（一次性）
    db.commit()

    return 200  # 密碼已成功重設
```

**關鍵判斷：**

```python
datetime.now(timezone.utc) > record.expires_at
```

兩邊都是含時區（UTC）的 datetime，直接比較大小：
- 目前時間 > 到期時間 → **已過期**
- 目前時間 ≤ 到期時間 → **有效**

---

## Token 的安全設計

| 機制 | 說明 |
|------|------|
| `secrets.token_urlsafe(32)` | 產生 43 個字元的隨機 URL 安全字串，無法預測 |
| `unique=True` | DB 欄位唯一，防止重複 token |
| 30 分鐘有效期 | 限制攻擊者可利用的時間窗口 |
| 一次性使用 | 使用後立即從 DB 刪除，無法重複使用 |
| 舊 token 覆蓋 | 申請新 token 時，先刪除同一用戶的舊 token |
| 不透露帳號是否存在 | 無論信箱有沒有註冊，都回傳相同訊息 |
| 過期 token 主動清除 | 驗證時發現過期即刪除，避免 DB 累積無效資料 |

---

## 信件內容

重設連結格式：

```
{FRONTEND_URL}/reset-password?token={token}
```

範例：

```
http://localhost:3001/reset-password?token=xK9mP2qRtYvNwBjLcAeZdFgHsUiOkXnM3p7Q
```

前端的 `/reset-password` 頁面讀取 URL 中的 `?token=` 參數，送出新密碼時一併帶給後端驗證。

---

## SMTP 設定（`.env`）

```env
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=應用程式密碼（16 碼，非 Gmail 登入密碼）
MAIL_FROM=your@gmail.com
MAIL_FROM_NAME=請假系統
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
FRONTEND_URL=http://localhost:3001
```

> Gmail 需要使用**應用程式密碼**，設定路徑：Google 帳號 → 安全性 → 兩步驟驗證 → 應用程式密碼
