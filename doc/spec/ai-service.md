# 請假系統規格書（第二階段：AI 助理）
 
Oct 29, 2026 · @yoyo
 
> 第一階段核心功能見 `specs/leaves-system-spec.md`。本階段在第一階段上線後才開始，2-B 假單查詢會用到第一階段的權限與額度邏輯。
 
 
## 1. 目標與範圍
 
> **2026-11-24 決策變更**：原規格打算用自架於 Modal 的對話模型（Gemma 4 E4B-it，vLLM）**完全取代** Gemini。實際部署測試後（見 `leave-system-inference/docs/vLLMWhy.md`），發現 L4 GPU 常要排隊等待可用容量（實測遇過數分鐘到十幾分鐘不等），且常駐成本不低（約 $575/月），對一個低流量的單一部門內部系統不划算，穩定性也不適合用來展示。**決定改用混合架構**：embedding（向量化）維持自架在 Modal（`multilingual-e5-large-instruct`，從未出現過穩定性問題，T4 GPU 成本低），**對話生成改回使用 Gemini**（原本後端已有的整合），但接上 RAG 檢索結果（相關規章段落），而不是像第一階段 Gemini `/chat` 那樣沒有檢索依據。以下內文提到「Modal 的對話模型」「Gemma 4」「vLLM」之處，均為已評估但未採用的方案，保留供參考，實際採用的是本節這個決策。
 
以自架於 Modal 的 embedding 模型 + pgvector 檢索 + Gemini 生成回答，取代第一階段沒有檢索依據的 Gemini `/chat`，分兩個子階段上線：
 
| 子階段 | 功能 | 作法 |
| --- | --- | --- |
| 2-A 規章問答 | 回答勞基法、公司規章相關問題，並附上引用段落 | RAG：規章切段 → 向量化存 pgvector → 提問時檢索相關段落，組進 prompt 交給 Gemini |
| 2-B 假單查詢 | 查自己的可用時數、假單狀態 | tool calling：Gemini 原生支援 function calling，模型呼叫後端工具，工具直接使用第一階段的 service 函式 |
 
- **繼續使用 `GEMINI_API_KEY`**（跟原本的決定相反，不移除）
- 對話不留紀錄，只存在前端 state
- 用 system prompt 限制回答範圍在請假與規章相關問題
## 2. 權限
 
| 動作 | sup\_admin | admin | employee |
| --- | --- | --- | --- |
| 使用 AI 助理 | 可 | 可 | 可 |
| 管理規章文件（上傳、修改、刪除、重試） | 可 | 可 | 不可 |
| 假單查詢工具的資料範圍 | 所有人 | 所有人 | 僅自己 |
 
- 工具一律以目前登入者身分執行，不接受模型傳入 `user_id`；查詢範圍與核心規格書第 2 節相同
- `/ai-analysis` 頁面改為所有角色都看得到
## 3. 架構
 
```
前端 ──► 後端 FastAPI ──┬─► Modal（leave-system-inference，僅 embedding）
                        │     └─ embedding 模型（multilingual-e5-large-instruct）
                        ├─► Gemini API（對話生成，2-A 附檢索段落、2-B 用 function calling）
                        └─► PostgreSQL + pgvector（kb_documents、kb_chunks）
```
 
**模型選擇**
 
基於資安考量，不使用 Qwen 系列模型（含 Qwen3-Embedding）。
 
| 用途 | 模型 | 授權 | 備註 |
| --- | --- | --- | --- |
| 對話（2-A、2-B 共用） | Gemini（透過 `GEMINI_API_KEY`） | Google 商用 API | 原生支援 function calling；無需自架、無冷啟動問題；一個模型同時處理規章問答與工具呼叫 |
| Embedding | intfloat/multilingual-e5-large-instruct（自架於 Modal，L4） | MIT | 1024 維、支援 100 種語言；從實測結果看穩定、成本低，繼續沿用 |
 
**已評估但未採用**（見本節開頭的決策變更說明，細節記錄在 `leave-system-inference/docs/vLLMWhy.md`）：

| 用途 | 模型 | 授權 | GPU | 未採用原因 |
| --- | --- | --- | --- | --- |
| 對話 | Gemma 4 E4B-it（vLLM） | Apache 2.0 | L4 | 實測可運作、繁中回答流暢，但 L4 GPU 常需排隊等待容量，且常駐成本高（約 $575/月），對低流量內部系統不划算 |
| 對話候選 | Gemma-3-TAIDE-12b-Chat-2602 | TAIDE 授權 + Gemma 使用條款（gated） | L40S | 因對話模型整體方向改用 Gemini，未進行到步驟 6.5 的品質比較 |
 
- Embedding 模型只從官方 Hugging Face 組織下載（`intfloat/`），並固定 revision（commit hash），避免載入被替換的權重
- system prompt／system instruction 必須要求「使用繁體中文（台灣用語）回答，只根據提供的規章段落回答」
**部署與設定**
 
- Embedding 推論服務放在獨立 repo `leave-system-inference`，無狀態、沒有資料庫；向量的讀寫都由後端負責
- 後端新增 `app/ai/`：`client.py`（embedding 呼叫介面）、`ingest.py`（切段與向量化）、`retrieval.py`（pgvector 檢索）、`tools.py`（2-B 工具，供 Gemini function calling 使用）
- 後端依賴環境變數：`EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`（Modal embedding 服務）、`GEMINI_API_KEY`（對話生成）
- 驗證：Modal embedding 服務自行產生 API key 存為 Modal Secret，endpoint 檢查 key；後端以環境變數保存同一組 key，不存資料庫、不給前端
- Embedding 冷啟動：Modal 縮到 0 台時第一次請求較慢；Gemini 無此問題，不需要前端顯示「助理啟動中」這類提示
- CI：`leave-system-inference` 的 pipeline 以 `MODAL_TOKEN_ID`、`MODAL_TOKEN_SECRET` 執行 `modal deploy`（僅限 embedding 服務）
## 4. 資料表
 
| 表 | 欄位 | 說明 |
| --- | --- | --- |
| `kb_documents` | `id` UUID PK、`title`、`source`、`type`（`rule`／`raw`／`letter`，預設 `rule`）、`status`（`processing`／`ready`／`failed`）、`error_message`、`uploaded_by` FK、`created_at`、`updated_at` | 規章文件 |
| `kb_chunks` | `id` UUID PK、`document_id` FK、`chunk_index`、`content`、`embedding vector(1024)`、`embedding_model` | 段落與向量；1024 維對應 multilingual-e5-large-instruct |
 
- 需在 PostgreSQL 啟用 `CREATE EXTENSION vector`（本機 Docker 改用 `pgvector/pgvector` image）
- 上傳或修改規章後以 FastAPI BackgroundTasks 自動切段、向量化；失敗時 `status` 為 `failed`
- `embedding_model` 用於換模型時找出需要重新向量化的段落；換成維度不同的模型（例如 EmbeddingGemma）時，`embedding` 欄位要一併 migration
- multilingual-e5 系列需加前綴：規章段落用 `passage: `，使用者問題用 `query: `（instruct 版的查詢端改用模型卡指定的指令格式）
- **`type` 決定切段策略**（新增，`app/ai/ingest.py` 依 `type` 分派）：
  - `rule`（公司規章，預設）：沿用現有邏輯，先按空行分段，過長段落用固定長度（`max_chars=500`）＋重疊（`overlap=50`）二次切
  - `raw`（法條）：依「第 X 條」為分界切，一條一個 chunk；單條內容超過 `max_chars` 才二次切
  - `letter`（函文／公文）：整篇不切，一份文件一個 chunk（公文通常上下文相依、篇幅短）
  - 這三種切段規則目前是草案，待步驟 5 的檢索測試集跑過後再確認是否需要調整
## 5. API
 
| 方法 | 路徑 | 說明 | 狀態 |
| --- | --- | --- | --- |
| POST | `/chat` | AI 對話，所有角色可用 | 變更：接上 RAG 檢索結果，改用 Gemini 生成回答、開放所有角色 |
| GET | `/kb/documents` | 規章列表 | 新增 |
| POST | `/kb/documents` | 上傳規章，需帶 `type`（`rule`／`raw`／`letter`），回傳時 `status` 為 `processing` | 新增 |
| PUT | `/kb/documents/{id}` | 修改規章，`title`／`content`／`type` 皆可選填更新 | 新增 |
| DELETE | `/kb/documents/{id}` | 刪除規章與其段落 | 新增 |
| POST | `/kb/documents/{id}/retry` | 重新向量化失敗的文件 | 新增 |
 
**`PUT /kb/documents/{id}` 細節**
 
- admin 限定（`require_admin`）
- Request body：`{ title?, content?, type? }`，三者皆可選填，缺的欄位沿用原值
- `content` 或 `type` 有變動才重新向量化：清空該文件底下所有 `kb_chunks`、`status` 改回 `processing`、`error_message` 清空，背景任務依（可能更新後的）`type` 重新切段、呼叫 embedding
- 只改 `title` 不觸發重新向量化（不影響向量內容，省資源）
- Response 格式同 `KbDocumentResponse`
 
**`/chat` 格式**（維持非統一格式）
 
- Request：`{ messages: [{ role: "user" | "model", content }] }`，維持現有前端格式，後端轉成 Gemini 需要的格式（`model` → `assistant`／Gemini 對應的角色名稱）
- Response：`{ reply, sources: [{ document_id, title, chunk_index }] }`，`sources` 為新增（檢索到的段落，不是 Gemini 自己提供的，是後端組 prompt 前就知道的）
- 2-B 的工具呼叫（Gemini function calling）在後端完成，前端只會收到最後的 `reply`
## 6. 開發步驟
 
| 順序 | 做什麼 | 完成的判斷標準 |
| --- | --- | --- |
| 1 | 建 `leave-system-inference` repo，部署 multilingual-e5-large-instruct 並加 key 驗證 | curl 帶 key 拿得到 1024 維向量，不帶 key 被拒 |
| 2 | 後端 migration：pgvector、`kb_documents`、`kb_chunks` | 本機與 Render 的資料庫都能建立 |
| 3 | 規章上傳 API 與自動向量化 | 上傳後 `kb_chunks` 有資料，`status` 變 `ready` |
| 4 | 檢索：問題 → 向量 → 找前 k 段 | 不接模型，直接檢查段落是否正確 |
| 5 | 準備 20～30 題測試問題 | 大部分題目的正確段落在前 5 名 |
| 6 | ~~部署 Gemma 4 E4B（vLLM，L4）~~ | **已評估，未採用**——實測可運作，但 GPU 排隊與常駐成本不划算，詳見第 1、3 節決策變更 |
| 6.5 | ~~比較 Gemma 4 E4B、Gemma 4 12B、TAIDE 的繁中回答品質~~ | **跳過**——對話模型改用 Gemini，不需要比較自架模型 |
| 7 | 後端 `/chat` 改接「檢索 + Gemini」，附 `sources` | 回答附引用段落；embedding 繼續用 Modal，對話用 Gemini（不移除） |
| 8 | 前端：所有角色可進入、顯示引用來源、冷啟動提示；規章管理頁；改寫 `docs/ai-chat.md`、`docs/sdd/10-ai-analysis.md`（含 Bearer JWT） | 2-A 完成 |
| 9 | 2-B：定義工具（查可用時數、查假單），用 Gemini 的 function calling | 「我特休還剩多少」回答正確 |
| 10 | 2-B：工具呼叫迴圈設最多輪數 | 不會無限呼叫 |
 
## 7. 測試案例
 
| 分類 | 案例 | 預期結果 |
| --- | --- | --- |
| 驗證 | Modal endpoint 不帶 key | 401 |
| 向量化 | 上傳規章 | `status` 由 `processing` 變 `ready` |
| 向量化 | embedding 服務失敗 | `status` 為 `failed`，可重試 |
| 檢索 | 「到職滿 2 年特休幾天」 | 引用特休年資表段落，答 10 天 |
| 範圍 | 問與請假無關的問題 | 婉拒回答 |
| 語言 | 所有測試問題的回答 | 繁體中文、台灣用語，不含簡體字 |
| 權限 | employee 上傳規章 | 403 |
| 權限 | 員工問「A0002 請了幾天假」 | 查不到他人資料 |
| 工具 | 員工問「我特休還剩多少」 | 與 `/leave-quota/me` 結果一致 |
 
## 8. 不在第二階段範圍
 
- AI 對話紀錄保存
- 由 AI 代替使用者送出、取消假單（工具只能查詢）
- 與其他專案共用推論服務