# AGENTS.md

本檔案給進入此專案的任何人(或 AI agent)快速掌握:**要什麼框架與環境、程式碼怎麼寫、怎麼執行**。

需求清單、實作進度、測試清單各自獨立成檔,不放在本檔案,避免一次讀太多:

| 想知道的東西 | 看哪裡 |
| --- | --- |
| 業務規則、API 規格、驗收案例 | [docs/requirements.md](docs/requirements.md) |
| 哪些功能已實作、哪些還沒、下一步順序 | [docs/feature-checklist.md](docs/feature-checklist.md) |
| 測了什麼、測試覆蓋的缺口 | [docs/test-checklist.md](docs/test-checklist.md) |
| 測試涵蓋哪些情境、想改數值時怎麼改 | [docs/test-coverage.md](docs/test-coverage.md) |
| 分層依賴、模組職責 | [docs/architecture.md](docs/architecture.md) |
| 評估過後不採用的方案與理由(為何不用 DB、為何不做登入等) | [docs/decisions.md](docs/decisions.md) |
| 各功能的實作方式與 API 實測紀錄 | [docs/acceptance-report.md](docs/acceptance-report.md) |

## 一、專案概述

電商購物車結算系統(WisdomGarden Dev 面試題 MVP)。消費者選好商品後,系統依「促銷折扣」與「優惠券」算出最終結算金額。

評分重點:**clean code、物件導向(不過度設計)、自動化單元測試**。

## 二、技術棧與框架

| 項目 | 選擇 | 說明 |
| --- | --- | --- |
| Python | 3.10+ | 使用 `list[X]` 等 type hint 語法 |
| 後端 | FastAPI | 由 uvicorn 執行;程式碼中**不需要** `import uvicorn` |
| 伺服器 | uvicorn | 啟動指令:`uvicorn cart.main:app --port 3000 --app-dir src` |
| 資料驗證 | Pydantic | schema 只能出現在 `api/` 層 |
| 金額 | `Decimal` | **嚴禁 float**;API 輸出為字串,`total` 四捨五入到小數 2 位 |
| 測試 | pytest | 測試 HTTP 用 `TestClient`(依賴 httpx) |
| 套件管理 | pip + venv | 套件**只裝在 `.venv` 內**,不得裝到系統 Python |

依賴白名單(只允許下列套件):

- 執行:`fastapi`、`uvicorn`、`pydantic`
- 開發:`pytest`、`httpx`

**不建立 Makefile、不建立 GitHub Actions。**

## 三、環境設定與常用指令

### 建立並啟用虛擬環境

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 安裝依賴

```bash
pip install -r requirements-dev.txt   # 開發(含測試)
pip install -r requirements.txt       # 僅執行
```

### 啟動伺服器

```bash
uvicorn cart.main:app --port 3000 --app-dir src
```

- 計算 API:<http://localhost:3000/api/calculate>(POST)
- API 文件:<http://localhost:3000/docs>

### 執行測試

```bash
pytest
```

### 跑測試案例

```bash
curl -X POST http://localhost:3000/api/calculate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/case-1.json
```

`tests/fixtures/case-1.json` 為基準案例(原 Case A),預期 `total` 為 `3083.60`;`case-2.json` 為 Case B,預期 `43.54`;`case-3` ~ `case-8` 為邊界情境,見 [docs/requirements.md](docs/requirements.md)。

## 四、目錄結構與分層

```
shopping_cart/
├── docs/              # 文件(requirements / feature-checklist / test-checklist / architecture / decisions)
├── src/cart/
│   ├── main.py                  # FastAPI 進入點
│   ├── domain/                  # 領域層:模型、錯誤
│   ├── services/                # 服務層:日期解析、計算引擎
│   └── api/                     # API 層:schema、calculate router(極薄)
└── tests/             # unit / api / fixtures
```

**依賴方向:`api → services → domain`;`domain` 不得 import FastAPI 或任何 web 模組。**

- `domain/`:領域資料與業務規則,不讀寫檔案、不認識外層。
- `services/`:業務流程(計算),組合 domain 規則,不讀寫檔案。
- `api/`:HTTP 介面,只做「接收 → 呼叫 service → 回傳」。

整個系統**無狀態**:沒有資料庫、沒有持久層、沒有前端,促銷與折價券都是每次請求的輸入而非常駐資料。

## 五、程式風格規則(全專案適用)

### 可讀性優先,不要把迴圈濃縮成難讀的一行

判斷標準:**一行程式碼,讀者能不能一眼看懂?需要停下來拆解,就改寫成明確的 for / if。**

**禁止**:

1. comprehension 同時包含「過濾」與「轉換」,或兩層以上的 for / if
2. 巢狀三元運算式(`a if x else b if y else c`),改用 if / elif / else
3. 一行串接多個動作(如 `sorted(filter(map(...)))`),改用具名變數逐步承接
4. lambda 內含邏輯判斷,改用具名函式
5. 海象運算子 `:=`、`functools.reduce`,改用明確迴圈
6. `__getattr__`、metaclass、自訂 decorator 等隱含行為

**允許**:單層單純轉換的 comprehension(如 `names = [p.name for p in products]`)、`Enum`、type hints、f-string。

### 以具名函式包裝邏輯

- 需要判斷、過濾、累加、轉換時,寫成獨立函式,再由上層呼叫
- 函式命名用「動詞 + 受詞」,例如 `calculate_item_subtotal`、`is_coupon_expired`
- 每個函式只做一件事;必須對應一個業務概念,**不為了拆而拆**,不建立只是轉呼叫的空包裝
- 上層函式只負責依序呼叫下層函式,不混入細節判斷

### 解耦,利於單元測試

- 業務規則寫成**純函式**:相同輸入必得相同輸出,不讀檔、不讀系統時間、不用全域狀態
- **日期由參數傳入**:任何函式不得自行呼叫 `date.today()`,「交易日」由請求帶進來
- I/O 與規則分離:`domain/`、`services/` 不讀寫檔案
- PEP 8,所有函式標註參數與回傳型別
- 不提前建立用不到的 base class、interface、factory

## 六、現況摘要

題目核心「依促銷與折價券算出結算金額」**已完整實作**,形態為一支無狀態計算 API:`POST /api/calculate`。基準案例 case-1(原 Case A) `total` 為 `3083.60`、case-2(原 Case B)為 `43.54`,`pytest` 62 passed,並以 curl 逐案例實測全數吻合。

規格要點(完整版見 [docs/requirements.md](docs/requirements.md)):促銷有乘法 `rate` 與加法 `effect`、可限 `date`/`category`;**折價券每次結算只能用一張**(題目原文,只評估陣列第一張),欄位為 `minSpend` / `expiryDate` / `discount` / `effect`;**價格由請求 JSON 帶入**,不查目錄(見 [docs/decisions.md](docs/decisions.md) D6、D7)。

## 七、Git 工作流

- 目前分支:`feature/project-skeleton`(已 commit 5 次,尚未 push)
- 不得在 `main` / `master` 上修改;完成後只 commit,**不要 push、不要 merge**
- commit 前先跑 `pytest`,通過才 commit
- 題目來源檔(`WisdomGarden (Dev) 面試題目.pdf`、`request.md`、`classHTML.md`、`productHTML.md`)為 untracked,**不納入版本控管**