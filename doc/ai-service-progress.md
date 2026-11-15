# 第二階段 AI 助理 — 開發進度記錄

> 對應規格：`doc/spec/ai-service.md`。記錄每次 commit 做了什麼，方便回溯。

## fed2b6e — feat: 新增 kb_documents、kb_chunks model 與 pgvector migration

對應規格第 6 節開發步驟「2」。

**做了什麼**：
- `pip install pgvector`，補進 `requirements.txt`（同時補上原本缺的 `alembic`）
- 新增 `app/models/kb_document.py`（`KbDocument`）、`app/models/kb_chunk.py`（`KbChunk`），註冊進 `app/models/__init__.py`
- `alembic revision --autogenerate -m "新增 kb_documents、kb_chunks"` 產生 migration
- 手動修正 autogenerate 的產出：補上 `import pgvector.sqlalchemy`（autogenerate 沒自動加，否則會 `NameError`），在 `upgrade()` 最前面加 `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`
- `alembic upgrade head` 套用到 Supabase 資料庫
- 連線驗證：`pg_extension` 有 `vector`，`kb_documents`/`kb_chunks` 兩張表欄位都正確（`embedding` 顯示 `USER-DEFINED` 是 pgvector 自訂型別的正常顯示）

## 6bc6f81 — fix: kb_documents、kb_chunks 的 id 改用字串，避免跟 Pydantic str 驗證衝突

**問題**：`id`（及 `kb_chunks.document_id`）原本用 PostgreSQL 原生 `UUID(as_uuid=True)` 型別，SQLAlchemy 讀出來是 Python `uuid.UUID` 物件；但專案裡其他 model（如 `LeaveRecord.id`）的慣例是存成字串（`String` + `default=lambda: str(uuid.uuid4())`）。若 API schema 依照現有慣例寫 `id: str`，Pydantic v2 驗證 `uuid.UUID` 物件會直接報錯（`Input should be a valid string`），因為 Pydantic 不會自動把任意物件轉成字串。

**做了什麼**：
- 把 `KbDocument.id`、`KbChunk.id`、`KbChunk.document_id` 改成 `Mapped[str]` + `String` 欄位，跟 `LeaveRecord` 寫法一致
- `alembic revision --autogenerate` 產生型別變更的 migration；因為涉及外鍵、且表目前是空的，手動改成 `drop_table` + `create_table` 重建（而不是用 `alter_column`，避免 Postgres 的 UUID → String 隱式轉型問題）
- `alembic upgrade head` 套用，連線驗證兩張表的 `id`/`document_id` 都變成 `character varying`

另外補一支手動 migration（非 autogenerate，因為 Alembic 預設不比較外鍵的 `ondelete`）：`KbChunk.document_id` 的外鍵加上 `ondelete="CASCADE"`，刪除 `KbDocument` 時底下的 `KbChunk` 會自動一併刪除，不用在程式碼裡手動先刪子資料。

## 5e36643 — feat: 新增 kb_documents 的 CRUD API 骨架，上傳改為直接貼文字

對應規格第 6 節開發步驟「3」（部分）。

**設計決定**：上傳規章原本設計成檔案上傳（`multipart/form-data`），後來改成直接貼文字（JSON body：`{"title", "content"}`）。不用處理 PDF/docx 解析，admin 直接把規章文字貼進去即可，`source` 欄位固定存 `"manual"`。

**做了什麼**：
- 新增 `app/schemas/kb.py`：`KbDocumentOut`、`KbDocumentCreate`、`KbDocumentListData`、`KbDocumentListResponse`、`KbDocumentResponse`，註冊進 `app/schemas/__init__.py`
- 新增 `app/routers/kb.py`：`GET /kb/documents`（列表，所有角色可查）、`POST /kb/documents`（新增，admin 限定，`require_admin`）、`DELETE /kb/documents/{id}`（刪除，admin 限定），註冊進 `main.py`
- 本機用 Swagger UI（`/docs`）實測三支 API：新增成功回傳正確格式（`id` 是字串 UUID）、列表能撈到剛新增的資料、刪除成功且能正確觸發前面設定的 cascade

**分支**：`feature/kb-pgvector-migration`（已合併，PR #46）

## ed7ee76 — feat: 新增 app/ai/client.py，封裝呼叫 Modal embedding API 的介面

對應規格第 6 節開發步驟「3」（部分）。

**做了什麼**：
- `pip install httpx`，補進 `requirements.txt`
- `.env` 補 `EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`（對應 `leave-system-inference` 的 embedding endpoint 與 key），`.env.example` 補對應佔位版本
- 新增 `app/ai/__init__.py`、`app/ai/client.py`：`embed(texts, kind)` 函式，`kind="query"`/`"passage"` 對應 Modal 那邊的前綴邏輯，`timeout=30` 預留冷啟動時間
- 本機測試：`load_dotenv()` 後 import 該模組確認環境變數有讀到（過程中發現 `.env` 裡網址太長複製貼上時斷行，導致 `python-dotenv` 解析警告，已修正）

**分支**：`feature/ai-embedding-modal`

## 86085a7 — feat: 串接切段與 embedding，POST /kb/documents 完整寫入 kb_chunks

對應規格第 6 節開發步驟「3」。

**做了什麼**：
- 新增 `app/ai/ingest.py`：`split_into_chunks(text, max_chars, overlap)`，先按空行分段，過長段落用固定長度＋重疊切開
- `kb.py` 新增 `_process_document(document_id, content)` 背景任務：切段 → 呼叫 `embed(chunks, kind="passage")` → 寫入 `KbChunk`（含 `embedding_model`）→ 文件狀態改 `ready`；失敗則狀態改 `failed` 並記錄 `error_message`
- `create_document` 改成呼叫 `background_tasks.add_task(_process_document, ...)`
- 實測：用 Swagger UI 建立含兩段文字的規章，確認 `kb_chunks` 正確寫入 2 筆、`vector_dims(embedding) = 1024`
- 過程中踩到一個坑：`.env` 的 `EMBEDDING_BASE_URL` 不小心把測試用的 `Invoke-RestMethod -Uri "..."` 指令本身也複製貼進去了，導致 `httpx` 報「URL 缺少協定」；清乾淨後重試立刻成功

## 2b9ddba — feat: 補上 kb_documents 的 content 欄位與 retry API

**問題**：`KbDocument` 沒有存原始文字，`POST /kb/documents/{id}/retry`（規格第 5 節）需要重新切段向量化時，沒有原文可用。

**做了什麼**：
- `KbDocument` 新增 `content: Mapped[str]`（`NOT NULL`）欄位
- `alembic revision --autogenerate` 產生 migration；因為表裡已有測試資料，`NOT NULL` 欄位加不進去，先清空測試資料再套用
- `create_document` 新增時把 `body.content` 一併存進這個欄位
- 新增 `POST /kb/documents/{id}/retry`：只允許 `status == "failed"` 的文件重試，把狀態改回 `processing`、清空 `error_message`，用 `document.content`（從資料庫讀回原文，不是 request body）重新丟進 `_process_document`
- 過程中踩到環境變數殘留的坑：本機某個 PowerShell session 曾經手動設過 `$env:DATABASE_URL`，導致 `.env` 換了新密碼後 `alembic` 仍連線失敗（`python-dotenv` 預設不覆蓋已存在的環境變數），重開一個新終端機才解決
- 實測：Modal 沒啟動時建立的文件正確顯示 `status: "failed"`，`error_message` 是 Modal 回的 404（`modal serve` 的網址在服務關閉後會失效）；retry 的程式邏輯已確認無語法錯誤，實際重試成功的流程留待之後需要時再測

**還沒做**（規格第 6 節後續步驟）：
- 檔案型別/大小限制（目前完全沒限制，之後要補）
- 步驟 4、5：檢索邏輯（`app/ai/retrieval.py`）與測試問題集
- 步驟 7：`/chat` 改接 Modal、移除 Gemini
- `PUT /kb/documents/{id}`（規格第 5 節）
- `leave-system-inference` 那邊：dev/prod 分環境、分 key（目前只有一組 dev 用的 secret）
- 待確認：`modal serve` 目前只適合本機開發期間使用，等這些功能都穩定後要考慮換成 `modal deploy` 正式部署，不然每次重開終端機／關機都要重啟
