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

查詢請假紀錄，支援狀態篩選與分頁。Admin 可查所有人的紀錄；一般員工只能查自己的。

- **權限**：需登入

**Query 參數：**

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `status` | string | — | 篩選狀態：`待審核` / `已通過` / `已拒絕` |
| `page` | integer | `1` | 頁碼 |
| `limit` | integer | `10` | 每頁筆數（最大 100） |

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

---

## 錯誤碼一覽

| 錯誤碼 | HTTP | 說明 |
|--------|------|------|
| `INVALID_CREDENTIALS` | 401 | 帳號或密碼錯誤 |
| `USERNAME_EXISTS` | 409 | 帳號已存在或已被其他人使用 |
| `EMAIL_EXISTS` | 409 | 信箱已被使用 |
| `ID_NUMBER_EXISTS` | 409 | 身分證號碼已存在 |
| `USER_NOT_FOUND` | 404 | 找不到指定使用者 |
