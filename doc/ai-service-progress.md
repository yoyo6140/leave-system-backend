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

**分支**：`feature/kb-pgvector-migration`，尚未 push

**還沒做**（規格第 6 節後續步驟）：
- 步驟 3：規章上傳 API（`POST /kb/documents`），背景任務自動切段、向量化
- 步驟 4、5：檢索邏輯（`app/ai/retrieval.py`）與測試問題集
- 步驟 7：`/chat` 改接 Modal、移除 Gemini
- `leave-system-inference` 那邊：dev/prod 分環境、分 key（目前只有一組 dev 用的 secret）
