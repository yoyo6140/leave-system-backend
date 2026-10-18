# 請假系統後端 API 規格書

## 目錄

1. [概述](#概述)
2. [通用規範](#通用規範)
3. [認證機制](#認證機制)
4. [API 端點](#api-端點)
   - [系統](#系統)
   - [認證 /auth](#認證-auth)
   - [員工管理 /user /users](#員工管理-user--users)
   - [請假紀錄 /leaves](#請假紀錄-leaves)
5. [資料模型](#資料模型)
6. [錯誤碼一覽](#錯誤碼一覽)

---

## 概述

| 項目 | 說明 |
|------|------|
| 框架 | FastAPI |
| 認證方式 | JWT Bearer Token（HS256） |
| 資料格式 | JSON |
| 基礎路徑 | `http://localhost:8000` |
| 互動文件 | `/docs`（Swagger UI）、`/redoc`（ReDoc） |

---

## 通用規範

### 請求 Header

需要登入的端點一律在 Header 帶入：

```
Authorization: Bearer <token>
```

### 成功回應格式

```json
{
  "success": true,
  "data": { ... }
}
```

### 失敗回應格式

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "說明文字"
  }
}
```

### 分頁參數

支援分頁的端點均接受以下 Query 參數：

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `page` | integer | `1` | 頁碼（≥1） |
| `limit` | integer | `10` | 每頁筆數（1–100） |

分頁回應格式：

```json
{
  "success": true,
  "data": {
    "total": 50,
    "page": 1,
    "limit": 10,
    "data": [ ... ]
  }
}
```

---

## 認證機制

- Token 類型：JWT（JSON Web Token）
- 簽章演算法：HS256
- Payload 欄位：`sub`（使用者 ID）、`role`、`exp`
- 預設有效期限：480 分鐘（可透過環境變數 `JWT_EXPIRE_MINUTES` 調整）
- Token 失效或格式錯誤時回傳 `401 Unauthorized`

### httpOnly Cookie

登入後 token 以 `Set-Cookie` 寫入瀏覽器，**JavaScript 無法讀取**，防止 XSS 竊取。

| Cookie 屬性 | 值 | 說明 |
|-------------|-----|------|
| `httpOnly` | `true` | JS 不可存取 |
| `samesite` | `lax` | 防 CSRF，允許一般導頁帶上 cookie |
| `secure` | 由 `COOKIE_SECURE` 決定 | 正式環境設 `true`，僅 HTTPS 傳送 |
| `max_age` | 同 JWT 有效期 | 瀏覽器自動到期清除 |

`get_current_user` 讀取順序：**cookie → Authorization Bearer header**（後者供 Swagger UI 使用）。

---

## API 端點

### 系統

#### `GET /`

服務健康檢查。

- **權限**：公開
- **成功回應** `200`：

```json
{
  "success": true,
  "data": "請假系統 API 運行中"
}
```

---

### 認證 `/auth`

#### `POST /auth/login`

使用帳號密碼登入，取得 JWT Token。

- **權限**：公開

**請求 Body：**

```json
{
  "username": "admin",
  "password": "admin1234"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `username` | string | 是 | 帳號 |
| `password` | string | 是 | 明文密碼 |

**成功回應** `200`：

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

**失敗回應** `401`：

```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "帳號或密碼錯誤"
  }
}
```

---

#### `POST /auth/token`

OAuth2 Password Flow，供 Swagger UI「Authorize」按鈕使用，不列入一般業務流程。

- **權限**：公開
- **請求格式**：`application/x-www-form-urlencoded`（`username`、`password`）
- **成功回應**：`{ "access_token": "<jwt>", "token_type": "bearer" }`

---

#### `POST /auth/forgot-password`

申請密碼重設。若信箱存在，系統寄出含 token 的重設連結（30 分鐘有效）。為防止帳號枚舉攻擊，無論信箱是否存在，回應格式相同。

- **權限**：公開

**請求 Body：**

```json
{ "email": "user@example.com" }
```

**成功回應** `200`：

```json
{
  "success": true,
  "data": { "message": "若此信箱已註冊，您將收到密碼重設信件" }
}
```

---

#### `POST /auth/reset-password`

使用信箱收到的 token 設定新密碼。Token 使用後立即失效。

- **權限**：公開

**請求 Body：**

```json
{
  "token": "<reset-token>",
  "new_password": "newPassword123"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `token` | string | 是 | 信箱收到的重設 token |
| `new_password` | string | 是 | 新密碼（明文，儲存時自動 bcrypt 雜湊） |

**成功回應** `200`：

```json
{
  "success": true,
  "data": { "message": "密碼已成功重設，請重新登入" }
}
```

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 400 | `INVALID_TOKEN` | token 不存在或已被使用 |
| 400 | `TOKEN_EXPIRED` | token 已過期（超過 30 分鐘） |

---

#### `POST /auth/logout`

登出，清除 httpOnly cookie。

- **權限**：公開

**成功回應** `200`：

```json
{ "success": true, "data": { "message": "已登出" } }
```

---

#### `GET /auth/me`

取得目前登入使用者的資料。

- **權限**：需登入

**成功回應** `200`：

```json
{
  "id": 1,
  "username": "admin",
  "name": "系統管理員",
  "role": "admin",
  "email": "admin@example.com",
  "gender": "男",
  "id_number": "A123456789",
  "hire_date": "2020-01-01",
  "birth_date": "1990-01-01"
}
```

---

### 員工管理 `/user` & `/users`

#### `GET /users`

查詢員工列表，支援關鍵字搜尋與分頁。

- **權限**：`admin`

**Query 參數：**

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `search` | string | `""` | 依姓名或帳號模糊搜尋 |
| `page` | integer | `1` | 頁碼 |
| `limit` | integer | `10` | 每頁筆數（最大 100） |

**成功回應** `200`：

```json
{
  "success": true,
  "data": {
    "total": 3,
    "page": 1,
    "limit": 10,
    "data": [
      {
        "id": 1,
        "username": "admin",
        "name": "系統管理員",
        "role": "admin",
        "email": "admin@example.com",
        "gender": "男",
        "id_number": "A123456789",
        "hire_date": "2020-01-01",
        "birth_date": "1990-01-01"
      }
    ]
  }
}
```

---

#### `POST /user`

新增一位員工帳號。

- **權限**：`admin`

**請求 Body：**

```json
{
  "username": "emp001",
  "password": "password123",
  "name": "王小明",
  "role": "employee",
  "email": "emp001@example.com",
  "gender": "男",
  "id_number": "A123456789",
  "hire_date": "2024-01-01",
  "birth_date": "1990-05-15"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `username` | string | 是 | 帳號（唯一） |
| `password` | string | 是 | 明文密碼（儲存時自動 bcrypt 雜湊） |
| `name` | string | 是 | 姓名 |
| `role` | string | 否 | `admin` / `employee`，預設 `employee` |
| `email` | string | 是 | 電子郵件（唯一） |
| `gender` | string | 是 | `男` / `女` |
| `id_number` | string | 是 | 身分證字號（唯一，長度 10） |
| `hire_date` | string | 是 | 到職日，格式 `YYYY-MM-DD` |
| `birth_date` | string | 是 | 生日，格式 `YYYY-MM-DD` |

**成功回應** `201`：回傳新建立的 `UserOut` 物件（同 `/auth/me` 格式，不含密碼）

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 409 | `USERNAME_EXISTS` | 帳號已存在 |
| 409 | `EMAIL_EXISTS` | 信箱已被使用 |
| 409 | `ID_NUMBER_EXISTS` | 身分證號碼已存在 |

---

#### `GET /user/{id}`

查詢單一員工資料。

- **權限**：`admin`
- **路徑參數**：`id`（integer）— 員工 ID

**成功回應** `200`：回傳 `UserOut` 物件

**失敗回應** `404`：`USER_NOT_FOUND`

---

#### `PUT /user/{id}`

更新員工資料（不含密碼）。

- **權限**：`admin`
- **路徑參數**：`id`（integer）— 員工 ID

**請求 Body：**

```json
{
  "username": "emp001",
  "name": "王小明",
  "role": "employee",
  "email": "emp001@example.com",
  "gender": "男",
  "id_number": "A123456789",
  "hire_date": "2024-01-01",
  "birth_date": "1990-05-15"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `username` | string | 是 | 帳號 |
| `name` | string | 是 | 姓名 |
| `role` | string | 是 | `admin` / `employee` |
| `email` | string | 是 | 電子郵件 |
| `gender` | string | 是 | `男` / `女` |
| `id_number` | string | 是 | 身分證字號 |
| `hire_date` | string | 是 | 到職日 `YYYY-MM-DD` |
| `birth_date` | string | 是 | 生日 `YYYY-MM-DD` |

**成功回應** `200`：回傳更新後的 `UserOut` 物件

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 404 | `USER_NOT_FOUND` | 找不到使用者 |
| 409 | `EMAIL_EXISTS` | 信箱已被其他帳號使用 |
| 409 | `ID_NUMBER_EXISTS` | 身分證號碼已被其他帳號使用 |
| 409 | `USERNAME_EXISTS` | 帳號已被其他人使用 |

---

#### `DELETE /user/{id}`

刪除員工帳號。

- **權限**：`admin`
- **路徑參數**：`id`（integer）— 員工 ID

**成功回應** `200`：

```json
{
  "success": true,
  "data": { "message": "員工帳號已刪除" }
}
```

**失敗回應** `404`：`USER_NOT_FOUND`

---

### 請假紀錄 `/leaves`

#### `GET /leaves`

查詢請假紀錄列表，支援狀態篩選、關鍵字搜尋與分頁。預設 Admin 可查所有人的紀錄；一般員工只能查自己的。

帶入 `mine=true` 時，無論角色一律強制只回傳登入者自己的紀錄（即使是 admin 也只看到自己的）。
用於「個人請假紀錄」頁面，與 admin 專用的「員工請假紀錄／審核管理」查詢分開，避免混用。

帶入 `search` 時比對請假原因（`reason`）；查詢全公司紀錄時（admin 且未加 `mine`）
同時比對申請人姓名（`name`）與帳號（`username`）。

- **權限**：需登入

**Query 參數：**

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `status` | string | — | 篩選狀態：`待審核` / `已通過` / `已拒絕` |
| `search` | string | — | 關鍵字搜尋原因；admin 查全公司時一併搜尋申請人姓名／帳號 |
| `page` | integer | `1` | 頁碼 |
| `limit` | integer | `10` | 每頁筆數（最大 100） |
| `mine` | boolean | `false` | `true` 時強制只查自己的紀錄，即使是 admin 也一樣 |

**成功回應** `200`：

```json
{
  "success": true,
  "data": {
    "total": 5,
    "page": 1,
    "limit": 10,
    "data": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": 2,
        "type": "特休",
        "start_date": "2024-07-01",
        "end_date": "2024-07-03",
        "hours": 24,
        "reason": "出遊",
        "status": "待審核",
        "reviewer": null,
        "created_at": "2024-06-20T08:00:00Z",
        "updated_at": null
      }
    ]
  }
}
```

---

#### `GET /leaves/{id}`

查詢單筆請假紀錄。Admin 可查任何人；員工只能查自己的。

- **權限**：需登入
- **路徑參數**：`id`（string / UUID）

**成功回應** `200`：

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 2,
    "type": "特休",
    "start_date": "2024-07-01",
    "end_date": "2024-07-03",
    "hours": 24,
    "reason": "出遊",
    "status": "待審核",
    "reviewer": null,
    "created_at": "2024-06-20T08:00:00Z",
    "updated_at": null
  }
}
```

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 404 | `LEAVE_NOT_FOUND` | 找不到請假紀錄 |
| 403 | `FORBIDDEN` | 無權限查看此紀錄 |

---

#### `POST /leaves`

新增請假申請，初始狀態為「待審核」。

- **權限**：需登入（為自己建立）

**請求 Body：**

```json
{
  "type": "特休",
  "start_date": "2024-07-01",
  "end_date": "2024-07-03",
  "hours": 24,
  "reason": "出遊"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `type` | string | 是 | `特休` / `病假` / `事假` / `婚假` / `喪假` / `公假` / `其他` |
| `start_date` | string | 是 | 開始日（`YYYY-MM-DD`） |
| `end_date` | string | 是 | 結束日（`YYYY-MM-DD`） |
| `hours` | integer | 是 | 時數（需 > 0） |
| `reason` | string | 否 | 事由，預設空字串 |

**成功回應** `201`：回傳新建立的 `LeaveOut` 物件（同上）

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 422 | `INVALID_LEAVE_TYPE` | 假別不在允許清單內 |
| 422 | `INVALID_HOURS` | 時數必須大於 0 |

---

#### `PUT /leaves/{id}`

修改請假申請內容。僅能修改狀態為「待審核」的自己的申請，Admin 亦同，不可修改他人紀錄。

- **權限**：需登入
- **路徑參數**：`id`（string / UUID）

**請求 Body：**（欄位與 POST 相同，無 `reason` 預設值，所有欄位皆必填）

```json
{
  "type": "病假",
  "start_date": "2024-07-01",
  "end_date": "2024-07-02",
  "hours": 16,
  "reason": "感冒"
}
```

**成功回應** `200`：回傳更新後的 `LeaveOut` 物件

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 404 | `LEAVE_NOT_FOUND` | 找不到請假紀錄 |
| 403 | `FORBIDDEN` | 無權限修改此紀錄 |
| 409 | `LEAVE_NOT_EDITABLE` | 僅能修改「待審核」狀態的申請 |
| 422 | `INVALID_LEAVE_TYPE` | 假別不在允許清單內 |
| 422 | `INVALID_HOURS` | 時數必須大於 0 |

---

#### `PATCH /leaves/{id}/status`

審核請假申請，將「待審核」的申請核准或駁回。`reviewer` 由後端自動帶入目前登入的 admin 姓名，
不接受前端指定。已審核過的申請（已通過／已拒絕／已取消）不可再變更狀態，僅能由申請人重新提出新的紀錄；
admin 可審核自己提出的申請。

- **權限**：`admin`
- **路徑參數**：`id`（string / UUID）

**請求 Body：**

```json
{
  "status": "已通過"
}
```

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `status` | string | 是 | `已通過` / `已拒絕` |

**成功回應** `200`：回傳更新後的 `LeaveOut` 物件（`reviewer` 為後端自動帶入的審核人姓名）

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 403 | `FORBIDDEN` | 僅 admin 可審核 |
| 404 | `LEAVE_NOT_FOUND` | 找不到請假紀錄 |
| 409 | `LEAVE_ALREADY_REVIEWED` | 已審核過的申請不可再變更，請申請人重新提出新的紀錄 |
| 422 | `INVALID_STATUS` | 狀態值不合法（僅接受 `已通過` / `已拒絕`） |

---

#### `GET /leaves/{id}/status-logs`

查詢單筆請假的狀態變更歷史，依時間升序排列。Admin 可查任何人；員工只能查自己的。

- **權限**：需登入
- **路徑參數**：`id`（string / UUID）

**成功回應** `200`：

```json
{
  "success": true,
  "data": [
    {
      "id": "log-uuid-1",
      "from_status": null,
      "to_status": "待審核",
      "changed_by": 2,
      "changed_at": "2024-06-20T08:00:00Z"
    },
    {
      "id": "log-uuid-2",
      "from_status": "待審核",
      "to_status": "已通過",
      "changed_by": 1,
      "changed_at": "2024-06-21T10:30:00Z"
    },
    {
      "id": "log-uuid-3",
      "from_status": "已通過",
      "to_status": "已取消",
      "changed_by": 2,
      "changed_at": "2024-06-22T14:00:00Z"
    }
  ]
}
```

> `from_status` 為 `null` 代表這是建立申請時的初始狀態紀錄。

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 404 | `LEAVE_NOT_FOUND` | 找不到請假紀錄 |
| 403 | `FORBIDDEN` | 無權限查看此紀錄 |

---

#### `DELETE /leaves/{id}` — 取消請假申請（軟刪除）

流程是申請者送出 → admin 審核（通過／拒絕）。**取消申請＝狀態改為「已取消」，保留紀錄**
（不會真的刪除資料列，跟「拒絕」一樣是狀態變化，才留得住查核軌跡），
僅限狀態仍是「待審核」（尚未經 admin 審核）時可操作；
審核完成後（已通過／已拒絕）**任何角色都不可再取消**。

僅能取消自己的申請，Admin 亦同，不可取消他人申請；同樣限「待審核」。

> 舊版曾規劃另一支 `PATCH /leaves/{id}/cancel`，與實際流程不符（允許在「已通過」後還能取消）
> 已移除；也曾短暫改成整筆硬刪除，後改回軟刪除以保留稽核紀錄。取消一律用這支 `DELETE`。

- **權限**：需登入
- **路徑參數**：`id`（string / UUID）

**成功回應** `200`：回傳更新後的 `LeaveOut` 物件（`status` 變為 `已取消`）

```json
{
  "success": true,
  "data": { "id": "550e8400-e29b-41d4-a716-446655440000", "status": "已取消", "...": "..." }
}
```

**失敗回應：**

| HTTP | 錯誤碼 | 說明 |
|------|--------|------|
| 404 | `LEAVE_NOT_FOUND` | 找不到請假紀錄 |
| 403 | `FORBIDDEN` | 無權限取消此紀錄 |
| 409 | `LEAVE_NOT_DELETABLE` | 僅能取消「待審核」狀態的申請，審核完成後無法再取消 |

---

## 資料模型

### `users` 資料表

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| `id` | integer | PK、Auto Increment | 主鍵 |
| `username` | string | Unique、Not Null、Index | 帳號 |
| `password` | string | Not Null | bcrypt 雜湊密碼 |
| `name` | string | Not Null | 姓名 |
| `role` | enum | Not Null、預設 `employee` | `admin` / `employee` |
| `email` | string | Unique、Not Null | 電子郵件 |
| `is_verified` | boolean | Not Null、預設 `false` | 是否已驗證 |
| `gender` | enum | Not Null | `男` / `女` |
| `id_number` | string(10) | Unique、Not Null | 身分證字號 |
| `hire_date` | string | Not Null | 到職日（`YYYY-MM-DD`） |
| `birth_date` | string | Not Null | 生日（`YYYY-MM-DD`） |
| `created_at` | datetime (tz) | 預設 UTC now | 建立時間 |

### `leave_records` 資料表

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| `id` | string (UUID) | PK | 主鍵（UUID v4） |
| `user_id` | integer | FK → `users.id`、Not Null、Index | 所屬員工 |
| `type` | enum | Not Null | `特休` / `病假` / `事假` / `婚假` / `喪假` / `公假` / `其他` |
| `start_date` | string | Not Null | 請假開始日（`YYYY-MM-DD`） |
| `end_date` | string | Not Null | 請假結束日（`YYYY-MM-DD`） |
| `hours` | integer | Not Null | 請假時數 |
| `reason` | string | 預設 `""` | 請假事由 |
| `status` | enum | Not Null、預設 `待審核` | `待審核` / `已通過` / `已拒絕` |
| `reviewer` | string | Nullable | 審核人姓名 |
| `created_at` | datetime (tz) | 預設 UTC now | 建立時間 |
| `updated_at` | datetime (tz) | Nullable、on update UTC now | 最後更新時間 |

### `leave_status_logs` 資料表

每次狀態變動插入一筆，完整保留歷史軌跡。

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| `id` | string (UUID) | PK | 主鍵 |
| `leave_id` | string (UUID) | FK → `leave_records.id`、Index | 對應的請假紀錄 |
| `from_status` | string | Nullable | 變更前的狀態（建立時為 null） |
| `to_status` | string | Not Null | 變更後的狀態 |
| `changed_by` | integer | FK → `users.id`、Not Null | 操作者 |
| `changed_at` | datetime (tz) | 預設 UTC now | 變更時間 |

---

## 錯誤碼一覽

| 錯誤碼 | HTTP | 說明 |
|--------|------|------|
| `INVALID_CREDENTIALS` | 401 | 帳號或密碼錯誤 |
| `INVALID_TOKEN` | 400 | 重設 token 不存在或已被使用 |
| `TOKEN_EXPIRED` | 400 | 重設 token 已過期 |
| `USERNAME_EXISTS` | 409 | 帳號已存在或已被其他人使用 |
| `EMAIL_EXISTS` | 409 | 信箱已被使用 |
| `ID_NUMBER_EXISTS` | 409 | 身分證號碼已存在 |
| `USER_NOT_FOUND` | 404 | 找不到指定使用者 |
| `LEAVE_NOT_FOUND` | 404 | 找不到請假紀錄 |
| `LEAVE_NOT_EDITABLE` | 409 | 僅能修改「待審核」狀態的申請 |
| `LEAVE_NOT_DELETABLE` | 409 | 僅能取消（刪除）「待審核」狀態的申請，審核完成後無法再取消 |
| `INVALID_LEAVE_TYPE` | 422 | 假別不在允許清單內 |
| `INVALID_HOURS` | 422 | 時數必須大於 0 |
| `INVALID_STATUS` | 422 | 狀態值不合法 |
| `FORBIDDEN` | 403 | 無權限執行此操作 |
