# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

FastAPI + SQLAlchemy 2.x 的請假系統後端（單一部門內部使用）。前端是另一個 repo（`yoyo6140/leave-system-frontend`，Next.js，部署於 Vercel），後端以 Docker 部署在 Render（設定見 `render.yaml`）。程式內的訊息、註解、文件都用繁體中文。

## 常用指令

```bash
# 本機開發（需先在 .env 設定 DATABASE_URL，例如 sqlite:///./leave_system.db）
pip install -r requirements.txt
uvicorn main:app --reload            # http://127.0.0.1:8000/docs 是 Swagger UI

# Docker（API + PostgreSQL 16）
docker compose up --build
docker compose exec api python seed_admin.py
docker compose exec api python seed_leave_types.py

# 開發用腳本
python seed_admin.py                 # 建立 admin / admin1234
python seed_leave_types.py           # 建立 7 種假別（leave_types 表）
python seed_employees.py             # 建立測試員工（需先跑過上面兩支）
python reset_db.py                   # 刪除並重建所有資料表（會清空資料）

# Alembic migration（alembic 沒有列在 requirements.txt，要另外安裝）
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

目前沒有測試套件，也沒有 linter 設定。

`alembic/versions/` 目前是空的：還沒有正式部署過，所有 schema 都直接寫在 model 裡由 `create_all()` 建立，沒有舊資料要轉換，所以把之前幾支 migration 都刪了。`leave_types` 的 7 筆種子資料無法靠 `create_all()` 塞進去（它只建表結構、不塞資料），所以另外寫了 `seed_leave_types.py`。**等到正式環境真的有資料之後，之後的欄位變更才需要重新開始寫 Alembic migration**（見下方「啟動流程」）。

## 架構重點

- **啟動流程**：`main.py` 的 lifespan 會執行 `Base.metadata.create_all()`，所以新的資料表會自動建立；**但已存在資料表的欄位變更不會自動套用**，要寫 Alembic migration（`alembic/versions/`）。`alembic/env.py` 會讀 `.env` 的 `DATABASE_URL` 並 import `app.models` 取得 metadata。
- **新增 model** 時要加進 `app/models/__init__.py`，否則 `create_all` 和 Alembic 都抓不到。
- **統一回應格式**：成功是 `{"success": true, "data": ...}`，失敗是 `{"success": false, "error": {"code", "message"}}`，分頁資料是 `{total, page, limit, data}`。路由用 `app/schemas/common.py` 的 `ok()` / `fail()` 組回應；業務錯誤一律寫成 `return JSONResponse(status_code=..., content=fail("ERROR_CODE", "訊息"))`，並使用專屬錯誤碼。`main.py` 的全域 handler 會把 `HTTPException` 轉成 `HTTP_ERROR`、驗證錯誤轉成 `VALIDATION_ERROR`、未捕捉的例外轉成 `INTERNAL_ERROR`。`/chat` 是例外，直接回傳 `{reply}`。
- **認證**：`app/auth.py` 的 `get_current_user` 先讀 `access_token` cookie，再讀 `Authorization: Bearer`；JWT 的 `sub` 是 user id。停用（`is_active=False`）的帳號一律回 401。管理員專用端點使用 `app/routers/users.py` 的 `require_admin`；`leaves.py` 則在函式內檢查 `current_user.role`。
- **請假狀態機**（`app/routers/leaves.py`，五個狀態）：`待審核` →（admin）`已通過` / `已拒絕`；`已拒絕` → 申請人編輯同一張後自動重送回 `待審核`（action=`resubmit`，重新預扣）；`已通過` →（admin，必填 `review_note`）`已銷假`；`待審核`／`已拒絕` → 申請人可取消為 `已取消`（軟刪除）。`reviewer` 由後端從 JWT 帶入（`reviewer_id` FK → users，API 輸出姓名，不接受前端指定）。所有會改變狀態的端點都用「`WHERE id=... AND status=舊狀態`」的條件式 UPDATE，受影響筆數為 0 就回 409（處理競態）。**每次狀態變更都要寫一筆 `LeaveStatusLog`**（含 `action`/`note`/`changes`）。
- **假單驗證**（`app/routers/leaves.py` 的 `_validate_leave`，新增、編輯、退回重送共用）：必填理由、日期順序、時數 >0、時數 ≤ 區間天數×8；有額度的假別（`quota_type` 非 `unlimited`）才檢查「不跨額度期間」跟「可用時數足夠」。
- **列表權限**：`GET /leaves` 的 admin 預設查看全公司；帶 `mine=true` 時強制只回傳自己的紀錄（個人頁面使用）。員工只能看自己的。
- **假別額度**（`app/leave_quota.py` + `app/models/leave_type.py`）：假別存在 `leave_types` 表（`code`/`name`/`quota_type`/`quota_hours`/`sort_order`），不寫死在程式裡。`quota_type` 為 `seniority`（特休，依勞基法第 38 條年資計算）/`fixed`（病假、事假，固定時數）/`unlimited`（婚假、喪假、公假、其他，由審核人自行判斷）。1 天 = 8 小時；年度以**到職週年日**為基準（有處理 2/29）。`app/routers/quota.py` 會加總週年度內 `待審核` + `已通過`（送出即預扣，見第 5 節）的時數，算出已用和剩餘時數。
- **AI 對話**：`app/routers/chat.py` 用 Gemini（`GEMINI_API_KEY`），沒有設定時回 503。
- **忘記密碼**：`app/email.py`（fastapi-mail，`MAIL_*` 環境變數）加上 `PasswordResetToken` model，重設連結會指向 `FRONTEND_URL`。
- **CORS** 白名單寫死在 `main.py` 的 `ALLOWED_ORIGINS`，新增前端網域時要改這裡。

## 規格文件

`doc/spec/` 底下是**目標規格**。實作或修改功能前，一律以規格為準；規格裡的「新增」「變更」標記代表和現況不同的地方。規格和程式碼衝突時，先告知使用者再動手。`doc/api-spec.md` 是 API 說明文件。

第 12 節「與現況的差異」列的待辦裡，已完成：#2 假別代碼（中文 → 英文代碼）、#9 婚假/喪假改無上限、#1 預扣（待審核也算已佔用）、#10 特休額度改讀 `leave_types`、#4 退回重送、#5 銷假。尚未處理：#3 sup_admin 角色、#6 帳號自動編號、#7 修改密碼 API、#12 `user_logs`，這幾項多數需要前後端一起改。

- 第一階段核心功能：doc/spec/leaves-system.md
- 第二階段 AI 助理（用 Modal 自架模型取代 Gemini）：doc/spec/ai-service.md
