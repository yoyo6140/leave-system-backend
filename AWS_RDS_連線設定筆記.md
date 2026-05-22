# AWS RDS PostgreSQL 連線設定筆記

## 前置條件
- 已建立 AWS RDS PostgreSQL 資料庫
- 已有 FastAPI 後端專案
- 本機已安裝 Python、pip

---

## 概念說明

### 連線流程
```
你的電腦
  → Internet Gateway（大門）
    → VPC（私人網路空間）
      → Security Group（保全，檢查是否放行）
        → RDS 資料庫（目的地）
```

| 名詞 | 說明 |
|------|------|
| VPC | AWS 給你的私人網路空間，資料庫住在裡面，預設外部連不進來 |
| Internet Gateway | VPC 的大門，沒有它外部就無法存取 |
| Route Table | 流量走向規則，決定外部流量要透過哪個大門進來 |
| Security Group | 資料庫前的保全，控制哪些 IP 和 Port 可以連進來 |
| Publicly Accessible | RDS 自己的開關，要設成 Yes 才允許外部連線 |

---

## 設定步驟

### 步驟一：修改 RDS 為公開可存取

1. AWS Console → 搜尋 **RDS** → **Databases**
2. 點進你的資料庫（例如 `database-leaves`）
3. 右上角點 **Modify**
4. 往下捲找到 **Connectivity** 區塊
5. **Publicly accessible** → 改成 **Yes**
6. 拉到最下面 → **Continue**
7. 選 **Apply immediately**
8. 點 **Modify DB instance**

> 儲存後 RDS 會進入 Modifying 狀態，Modify 按鈕暫時變灰，等幾分鐘即可恢復正常。

---

### 步驟二：確認 Internet Gateway 已附加到 VPC

1. AWS Console → 搜尋 **VPC**
2. 左側選單點 **Internet gateways**
3. 確認有一筆 State 是 **Attached**，且 VPC ID 對應你 RDS 所在的 VPC

> 如果沒有，需要：
> 1. 點 **Create internet gateway** → 取名 → 建立
> 2. 建立後點 **Actions → Attach to VPC** → 選你的 VPC → Attach

---

### 步驟三：設定 Route Table 讓外部流量可進入

1. VPC 左側選單點 **Route tables**
2. 找到你 VPC 對應的 Route Table（Main = **Yes** 的那筆）
3. 點進去 → 下方選 **Routes** 分頁
4. 確認有以下這筆路由（如果沒有就點 **Edit routes → Add route** 新增）：

| Destination | Target | Status |
|-------------|--------|--------|
| 0.0.0.0/0 | igw-xxxxxxxxx（你的 Internet Gateway） | Active |
| 172.31.0.0/16 | local | Active |

5. 儲存 → **Save changes**

---

### 步驟四：Security Group 開放 5432 Port

1. AWS Console → 搜尋 **EC2**
2. 左側選單點 **Security Groups**
3. 找到 RDS 使用的 Security Group（通常名稱是 **default**）
4. 點進去 → **Inbound rules** 分頁 → **Edit inbound rules**
5. 若有舊的 PostgreSQL 規則先點 **Delete** 刪掉
6. 點 **Add rule** 新增：

| 欄位 | 設定值 |
|------|--------|
| Type | PostgreSQL |
| Protocol | TCP（自動） |
| Port range | 5432（自動） |
| Source | My IP（AWS 會自動帶入你的 IP，例如 219.85.41.113/32） |

7. 點 **Save rules**

---

## 後端專案設定

### 安裝套件
```powershell
cd C:\Users\User\Desktop\leave-system-backend
pip install -r requirements.txt
```

### .env 檔案
```
DATABASE_URL=postgresql://使用者名稱:密碼@RDS端點:5432/資料庫名稱
```

範例：
```
DATABASE_URL=postgresql://postgres:F129143455@database-leaves.ckvescy2i09y.us-east-1.rds.amazonaws.com:5432/postgres
```

### 啟動伺服器測試連線
```powershell
uvicorn main:app --reload
```

### 連線成功的訊息
```
[OK] 資料庫連線成功
INFO:     Application startup complete.
```

---

## 注意事項

- **My IP 限制**：Security Group 設定 My IP 代表只有你目前的網路 IP 可以連線。若換了網路（換地點、重新撥號），IP 會改變，需要重新更新 Security Group 的 Inbound rule。
- **RDS Proxy**：選用功能，不需要設定，跳過即可。
- **Internet Gateway 每個 VPC 只能附加一個**，不需要重複建立。

---

## 啟動指令說明

| 指令 / 訊息 | 說明 |
|-------------|------|
| `uvicorn main:app --reload` | 啟動後端伺服器，自動偵測程式碼變更並重啟 |
| `http://127.0.0.1:8000` | 伺服器跑在本機 8000 port，可用瀏覽器打開測試 |
| `Started reloader process` | 監視檔案變化的程序 |
| `Started server process` | 實際跑 API 的程序 |
| `Waiting for application startup` | 正在執行 startup() 初始化函式 |
| `[OK] 資料庫連線成功` | test_connection() 執行完畢，資料庫連線正常 |
| `Application startup complete` | 伺服器完全就緒，API 可以使用 |





> [Image #2] 我在這
  ⎿  [Image #2]

● 確認了，Internet access gateway: Disabled 就是問題所在。我們來一步一步修正。

  ---
  第一步：先修改 RDS 設定（讓它公開可存取）

  你現在就在對的頁面，點右上角的 Modify 按鈕。

  進去後往下捲找到 Connectivity 區塊 → Publicly accessible → 改成 Yes → 拉到最下面 Continue → 選 Apply immediately → Modify DB
  instance

  完成後回來告訴我，我再引導你去 VPC 設定 Internet Gateway。

✻ Cogitated for 13s

> [Image #3] 這裡?
  ⎿  [Image #3]

● 對，就是這個區塊，但要繼續往下捲，找到 Public access 選項（在 Certificate authority 下面），把它改成 Yes / Publicly accessible。

✻ Cogitated for 6s

> 改好了

● 好，現在去設定 VPC Internet Gateway。

  ---
  第二步：建立 Internet Gateway

  1. 在 AWS Console 上方搜尋欄輸入 VPC → 點進去
  2. 左側選單找 Internet gateways
  3. 右上角點 Create internet gateway
  4. Name 隨便取（例如 leave-igw）→ Create internet gateway
  5. 建立完成後，點 Actions → Attach to VPC
  6. 選 vpc-04dc8beb280f93b0f（就是你 RDS 用的那個）→ Attach internet gateway

  完成後告訴我，再做第三步 Route Table。

✻ Sautéed for 8s

> 為何那個modify 我剛才儲存之後  返回上一頁 按鈕變成disable

● 那是正常現象。RDS 在套用修改時會進入 Modifying 狀態，這時 Modify 按鈕會暫時變灰，等幾分鐘就會恢復。

  不影響操作，你可以繼續做第二步 Internet Gateway 的設定。做好了嗎？

✻ Brewed for 11s

> Internet gateway settings
  Name tag
  Creates a tag with a key of 'Name' and a value that you specify.  這個取名? 下面那個tags-option是啥

● Name 就填 leave-igw 就好。

  下面那個 Tags - optional 不用管，直接跳過，點 Create internet gateway 即可。

✻ Cooked for 3s

> [Image #4]
  ⎿  [Image #4]

● 你的 VPC 已經有一個 Internet Gateway 了（第一筆，State: Attached，連到 vpc-04dc8beb280f93b0f）。

  你新建的 leave-igw 用不到，可以選它 → Actions → Delete internet gateway 刪掉。

  ---
  現在問題只剩 Route Table 沒設定。

  左側點 Route tables → 下一步我引導你。

✻ Baked for 18s

> 好了 下一步

● 第三步：設定 Route Table

  1. 左側點 Route tables
  2. 找到 VPC ID 是 vpc-04dc8beb280f93b0f 的那筆（可能有多筆，找 Main = Yes 的那條）
  3. 點進去 → 下方選 Routes 分頁 → Edit routes
  4. 點 Add route：
    - Destination：0.0.0.0/0
    - Target：選 Internet Gateway → 選 igw-0784e86ac703c576c
  5. Save changes

  完成後告訴我，再做最後一步 Security Group。

✻ Churned for 8s

> [Image #5]
  ⎿  [Image #5]

● 只有一筆，Main = Yes，就是它。點 rtb-0bbc455537b527ddd 進去。

✻ Baked for 5s

> 好了 下一步

● 點進去後，下方點 Routes 分頁，然後點 Edit routes，截圖給我看現在有哪些路由。

✻ Crunched for 4s

> [Image #6]
  ⎿  [Image #6]

● Route Table 已經有 0.0.0.0/0 → igw-0784e86ac703c576c 而且是 Active，不需要再改。

  ---
  第四步：Security Group 開放 5432 port

  1. AWS Console 搜尋 EC2 → 左側 Security Groups
  2. 找到 RDS 用的 Security Group（名稱是 default）
  3. 點進去 → Inbound rules 分頁 → Edit inbound rules
  4. Add rule：
    - Type：PostgreSQL
    - Source：My IP（AWS 會自動填你目前的 IP）
  5. Save rules

  完成後告訴我，我們就可以測試連線了。

✻ Crunched for 9s

> [Image #7]
  ⎿  [Image #7]

● 這個錯誤是因為那筆規則原本是用 Security Group 當 source，不能直接改成 IP。

  解法：

  1. 點那筆規則右側的 Delete 刪掉它
  2. 點 Add rule 新增一筆：
    - Type：PostgreSQL
    - Source：My IP（會自動帶入 219.85.41.113/32）
  3. Save rules

✻ Cogitated for 14s

> 下一步

● 現在測試連線。在你的終端機輸入：

  cd C:\Users\User\Desktop\leave-system-backend
  uvicorn main:app --reload

  看到什麼訊息告訴我。
