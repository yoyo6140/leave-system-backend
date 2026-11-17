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

**還沒做**（規格第 6 節後續步驟，截至 `2b9ddba`）：
- 檔案型別/大小限制（目前完全沒限制，之後要補）
- 步驟 4、5：檢索邏輯（`app/ai/retrieval.py`）與測試問題集
- 步驟 7：`/chat` 改接 Modal、移除 Gemini
- `PUT /kb/documents/{id}`（規格第 5 節）
- `leave-system-inference` 那邊：dev/prod 分環境、分 key（目前只有一組 dev 用的 secret）
- 待確認：`modal serve` 目前只適合本機開發期間使用，等這些功能都穩定後要考慮換成 `modal deploy` 正式部署，不然每次重開終端機／關機都要重啟

## f9d3535 — feat: 新增 app/ai/retrieval.py，實作向量檢索 search 函式

對應規格第 6 節開發步驟「4」。

**做了什麼**：
- 新增 `search(db, query, top_k=5)`：問題向量化（`kind="query"`）後，用 pgvector 的 `cosine_distance` 排序取出前 k 個 `kb_chunks`
- 新增 `app/ai/test_retrieval.py` 手動測試腳本，驗證「特休有幾天」能撈到對應段落

## 0a3509a — feat: 新增 PUT /kb/documents/{id}，修改規章後僅在內容變動時重新向量化

對應規格第 5 節。

**做了什麼**：
- 新增 `KbDocumentUpdate` schema，`title`/`content` 皆可選填更新
- `update_document`：只有 `content` 實際變動（跟資料庫原值比較）才清空舊 `kb_chunks`、`status` 改回 `processing`、重新向量化；單改 `title` 不觸發，省資源
- 踩的坑：比較「content 是否變動」要寫在覆蓋欄位**之前**，不然 `document.content` 已經被蓋成新值，永遠比不出差異

## 8da97f8 + ba0ef0f — feat: kb_documents 新增 type 欄位，依文件類型採用不同切段邏輯（router 接線另開一個 commit）

不在規格書原始設計內，開發過程中討論後新增，並補寫進 `doc/spec/ai-service.md`。

**做了什麼**：
- `KbDocument` 新增 `type`（`rule`／`raw`／`letter`，預設 `rule`）
- `split_into_chunks` 依 `doc_type` 分派：`rule` 沿用現有空行分段邏輯，`raw` 依「第 X 條」為界切（正則需處理「第 1 條」這種數字前後有空格的格式），`letter` 整篇不切
- 抽出 `_split_long_text` 共用函式，三種類型切出的候選段落統一做超長保護（`max_chars=500`/`overlap=50`），解決 `letter` 原本完全沒長度保護的問題
- `_process_document`／`create_document`／`update_document`／`retry_document` 都接上 `doc_type`；`update_document` 的 `needs_revectorize` 也納入 `type` 是否變動
- alembic migration 新增 `type` 欄位（先清空 `kb_documents` 測試資料，沒有加 `server_default`）
- 新增 `app/ai/test_ingest.py` 手動測試三種切法，含超長內容驗證

**踩的坑**：`type` 覆蓋欄位的順序一開始寫反了（跟 `content` 一樣的錯：先覆蓋再比較，導致 `needs_revectorize` 永遠判斷不出 `type` 變了），修正後統一在比較完才覆蓋。

**還沒做**（截至本節）：
- `type` 功能還沒經過完整流程實測——只單獨測過 `split_into_chunks`（`test_ingest.py`），沒有真的用 Swagger UI 跑過 `POST /kb/documents` 帶 `type="raw"`/`"letter"`，確認背景任務產出的 `kb_chunks` 正確
- `create_document`/`update_document` 沒有驗證 `body.type` 是否為 `rule`/`raw`/`letter` 合法值，打錯字串會被存進去、切段時悄悄當成 `rule` 處理
- `leave-system-inference`：已 `modal deploy` 正式部署（固定 prod 網址），決定先不做 dev/prod 分環境、不分 key（共用同一組 `embedding-api-key`），之後真的需要再補
- Render 環境變數：`EMBEDDING_BASE_URL`/`EMBEDDING_API_KEY` 還沒補進 `render.yaml` 或 Render 後台——Modal prod 網址已經有了，這件事已經解鎖，可以回來處理
- 規格第 6 節步驟 5：準備 20~30 題檢索測試問題集，驗證正確段落有沒有落在前 5 名

## cf4c4e3 — feat: embed() 依 Modal 的 MAX_BATCH 限制自動分批呼叫

**問題**：`app/ai/client.py` 的 `embed()` 原本一次把所有 chunk 送給 Modal，但 `leave-system-inference` 的 `embedding_app.py` 限制 `MAX_BATCH=64`，超過會收到 422。上傳完整法規全文（勞基法 86 條，切完接近或超過 64 個 chunk）會直接失敗。

**做了什麼**：
- `embed()` 改成用 `range(0, len(texts), BATCH_SIZE)` 把 `texts` 切成每批 ≤64 筆，逐批呼叫 Modal，用 `embeddings.extend(...)` 依序接起來，確保跟原始 chunk 順序一致（後面 `_process_document` 要靠順序 `zip(chunks, embeddings)` 配對）
- 考慮過直接調大 Modal 那邊的 `MAX_BATCH`，但那只是把上限往後移、沒解決根本問題，而且要重新 `modal deploy` 動到剛穩定的 prod，所以選擇在 backend 端做分批

## （本次未附 commit hash，待補）— 驗證 type="raw" 完整流程，補齊規格步驟 5 測試集

**背景**：為了用真實資料測試 `type="raw"` 跟檢索品質，從全國法規資料庫複製勞動基準法全文（86 條），過程中踩了不少坑：

1. **Swagger UI 貼多行文字會 JSON decode error**：直接在 JSON 輸入框貼有換行的全文，換行沒轉義導致格式壞掉。改寫 `app/ai/upload_law.py`：讀本機 `.txt` 檔、呼叫 `/auth/login` 拿 token、用 `httpx` 的 `json=` 參數自動處理轉義，繞過手動編輯 JSON 的問題。
2. **`EMBEDDING_BASE_URL` 指向過期的 `modal serve` 網址**：忘記 `.env` 改完要重啟 `uvicorn`（`client.py` 的環境變數是模組載入時讀一次，不會自動重讀），Docker 版本則是「容器啟動時」讀 `env_file`，改完 `.env` 也要重新 `docker compose up` 才會生效。
3. **`raw` 切段正則把條文內文裡提到的條號也當成切點**：原正則 `第[一二三四五六七八九十0-9]+條` 沒限定位置，導致「第三十六條所定之例假…」這種**內文引用**（中文數字、無空格、非行首）被誤判成新條文開頭，把第 39 條切碎。改成 `r'(?=^第\s*\d+\s*條)'` 搭配 `flags=re.MULTILINE`，限定「只有在行首、且為阿拉伯數字」才算切點，修好後第 39 條維持完整一段。
   - **已知殘留限制**：帶橫線的增訂條文（如「第 9-1 條」）不符合 `\d+\s*條`（中間多了 `-1`），不會被獨立切開，會黏在前一條尾巴——測試後發現這不影響檢索（內容還在，只是切得比較粗），先不處理。

**做了什麼**：
- 新增 `app/ai/upload_law.py`（一次性上傳工具腳本）
- 修正 `app/ai/ingest.py` 的 `raw` 切段正則
- 新增 `app/ai/test_retrieval_suite.py`：25 題測試問題（對應規格第 6 節步驟 5），每題驗證預期條號有沒有出現在 `top_5` 結果裡，印出命中率跟未命中清單
- 實測結果：**25/25 全過，`top_5` 命中率 100%**（含 3 題故意測「帶橫線條文」的邊界情況）
- 規格第 6 節步驟 5 完成，檢索品質已驗證，可以進入步驟 6（部署 Gemma 4）
