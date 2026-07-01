# 請假系統後端 API

基於 **FastAPI** 的請假系統後端，提供使用者認證（JWT）、員工帳號管理與請假紀錄查詢。資料庫使用 **SQLAlchemy**，支援 SQLite（本機開發）與 PostgreSQL（Docker / 正式環境）。

## 技術棧

| 項目 | 說明 |
|------|------|
| 框架 | FastAPI |
| 伺服器 | Uvicorn |
| ORM | SQLAlchemy 2.x |
| 資料庫 | SQLite / PostgreSQL（`psycopg2-binary`） |
| 認證 | JWT（`python-jose`）+ bcrypt 密碼雜湊 |

## 專案結構

```
leave-system-backend/
├── main.py                 # 應用程式進入點、路由註冊
├── app/
│   ├── auth.py             # JWT、密碼驗證、get_current_user
│   ├── database.py         # 資料庫連線、Session、Base
│   ├── models/             # User、LeaveRecord 等資料表
│   ├── routers/
│   │   ├── auth.py         # 登入、token、me API
│   │   ├── users.py        # 員工帳號 CRUD API
│   │   └── leaves.py       # 請假紀錄查詢 API
│   └── schemas/            # Pydantic 請求／回應模型
├── seed_admin.py           # 建立預設管理員帳號
├── reset_db.py             # 刪除並重建所有資料表（開發用）
├── docker-compose.yml      # API + PostgreSQL
├── Dockerfile
├── requirements.txt
└── .env.example
```

## 環境變數

複製範例檔並依需求修改：

```bash
cp .env.example .env
```

| 變數 | 必填 | 說明 | 預設值 |
|------|------|------|--------|
| `DATABASE_URL` | 是 | SQLAlchemy 連線字串 | — |
| `JWT_SECRET` | 否 | JWT 簽章金鑰 | `change-me` |
| `JWT_EXPIRE_MINUTES` | 否 | Token 有效分鐘數 | `480` |

**本機開發（SQLite）範例：**

```env
DATABASE_URL=sqlite:///./leave_system.db
JWT_SECRET=your-secret-key-change-this
JWT_EXPIRE_MINUTES=480
```

**Docker（由 `docker-compose.yml` 自動覆蓋）：**

```env
DATABASE_URL=postgresql://leave_user:leave_pass@db:5432/leave_system
```

> 若使用 AWS RDS，請參考 [`AWS_RDS_連線設定筆記.md`](./AWS_RDS_連線設定筆記.md)。

## 本機啟動

### 1. 安裝依賴

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. 設定 `.env`

至少設定 `DATABASE_URL`（見上方）。

### 3. 啟動 API

```bash
uvicorn main:app --reload
```

啟動時會自動建立資料表並測試資料庫連線。

| 網址 | 說明 |
|------|------|
| http://127.0.0.1:8000/ | 健康檢查 |
| http://127.0.0.1:8000/docs | Swagger UI |
| http://127.0.0.1:8000/redoc | ReDoc |

### 4. 建立管理員帳號（選用）

```bash
python seed_admin.py
```

預設會建立（若尚不存在）：

| 欄位 | 值 |
|------|-----|
| 帳號 | `admin` |
| 密碼 | `admin1234` |
| 角色 | `admin` |

## Docker 啟動

需已安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

```bash
docker compose up --build
```

背景執行：

```bash
docker compose up --build -d
```

| 服務 | 說明 | 埠號 |
|------|------|------|
| `api` | FastAPI（含 `--reload`） | 8000 |
| `db` | PostgreSQL 16 | 5432 |

常用指令：

```bash
docker compose ps          # 查看狀態
docker compose logs api -f # 查看 API 日誌
docker compose down        # 停止服務
docker compose down -v     # 停止並刪除資料庫 volume
```

Docker 啟動後，在容器內建立管理員：

```bash
docker compose exec api python seed_admin.py
```

## API 一覽

所有需登入的端點請在 Header 帶入：

```
Authorization: Bearer <token>
```

### 系統

| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| `GET` | `/` | 服務狀態 | 公開 |

### 認證 (`/auth`)

| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| `POST` | `/auth/login` | 登入，回傳 JWT 與使用者資訊 | 公開 |
| `POST` | `/auth/token` | Swagger「Authorize」用（OAuth2 表單） | 公開 |
| `GET`  | `/auth/me`    | 取得目前登入的使用者資料 | 需登入 |

**登入請求範例：**

```json
POST /auth/login
{
  "username": "admin",
  "password": "admin1234"
}
```

**成功回應：**

```json
{
  "success": true,
  "data": {
    "token": "<jwt>",
    "user": {
      "id": 1,
      "username": "admin",
      "name": "系統管理員",
      "role": "admin"
    }
  }
}
```

### 員工 (`/user`、`/users`)

| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| `GET`    | `/users`      | 查詢員工列表（支援搜尋與分頁） | `admin` |
| `POST`   | `/user`       | 新增員工帳號 | `admin` |
| `GET`    | `/user/{id}`  | 查詢單一員工資料 | `admin` |
| `PUT`    | `/user/{id}`  | 更新員工資料 | `admin` |
| `DELETE` | `/user/{id}`  | 刪除員工帳號 | `admin` |

**新增員工請求範例：**

```json
POST /user
{
  "username": "emp001",
  "password": "password123",
  "name": "王小明",
  "role": "employee",
  "email": "emp@example.com",
  "gender": "男",
  "id_number": "A123456789",
  "hire_date": "2024-01-01",
  "birth_date": "1990-05-15"
}
```

### 請假紀錄 (`/leaves`)

| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| `GET` | `/leaves` | 查詢請假紀錄（admin 可查所有人，員工只能查自己） | 需登入 |

**Query 參數：**

| 參數 | 說明 | 預設 |
|------|------|------|
| `status` | 篩選狀態：`待審核` / `已通過` / `已拒絕` | — |
| `page` | 頁碼（≥1） | `1` |
| `limit` | 每頁筆數（1–100） | `10` |

**成功回應：**

```json
{
  "success": true,
  "data": {
    "total": 20,
    "page": 1,
    "limit": 10,
    "data": [ { ... } ]
  }
}
```

### 錯誤碼一覽

| 錯誤碼 | HTTP | 說明 |
|--------|------|------|
| `INVALID_CREDENTIALS` | 401 | 登入帳密錯誤 |
| `USERNAME_EXISTS` | 409 | 帳號已存在 |
| `EMAIL_EXISTS` | 409 | 信箱已被使用 |
| `ID_NUMBER_EXISTS` | 409 | 身分證號碼已存在 |
| `USER_NOT_FOUND` | 404 | 找不到使用者 |

## 資料模型

啟動時會透過 `Base.metadata.create_all()` 自動建立資料表。

### `users`

| 欄位 | 說明 |
|------|------|
| `id` | 主鍵 |
| `username` | 帳號（唯一） |
| `password` | bcrypt 雜湊密碼 |
| `name` | 姓名 |
| `role` | `admin` / `employee` |
| `email` | 電子郵件（可為空） |
| `is_verified` | 是否已驗證 |
| `gender` | `男` / `女` |
| `id_number` | 身分證字號 |
| `hire_date` / `birth_date` | 到職日、生日 |
| `created_at` | 建立時間 |

### `leave_records`

| 欄位 | 說明 |
|------|------|
| `id` | UUID 主鍵 |
| `user_id` | 關聯 `users.id` |
| `type` | 特休、病假、事假、婚假、喪假、公假、其他 |
| `start_date` / `end_date` | 請假區間 |
| `hours` | 時數 |
| `reason` | 事由 |
| `status` | 待審核、已通過、已拒絕 |
| `reviewer` | 審核人 |
| `created_at` / `updated_at` | 建立／更新時間 |

## 開發用腳本

| 腳本 | 說明 |
|------|------|
| `python seed_admin.py` | 建立預設 `admin` 帳號 |
| `python reset_db.py` | **刪除所有資料表並重建**（會清空資料，僅限開發） |

## 回應格式

成功：

```json
{ "success": true, "data": { ... } }
```

失敗：

```json
{
  "success": false,
  "error": { "code": "ERROR_CODE", "message": "說明文字" }
}
```
