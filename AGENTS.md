# AGENTS.md

本檔案給進入此專案的任何人(或 AI agent)快速掌握:**要什麼框架與環境、程式碼怎麼寫、怎麼執行**。

需求清單、實作進度、測試清單各自獨立成檔,不放在本檔案,避免一次讀太多:

| 想知道的東西 | 看哪裡 |
| --- | --- |
| 業務規則、驗收案例、商品目錄、待決定事項 | [docs/requirements.md](docs/requirements.md) |
| 哪些功能已實作、哪些還沒、下一步順序 | [docs/feature-checklist.md](docs/feature-checklist.md) |
| 測了什麼、測試覆蓋的缺口 | [docs/test-checklist.md](docs/test-checklist.md) |
| 分層依賴、模組職責 | [docs/architecture.md](docs/architecture.md) |
| 評估過後不採用的方案與理由(為何不用 DB、為何不做登入等) | [docs/decisions.md](docs/decisions.md) |
| 各功能的實作方式與瀏覽器實測紀錄 | [docs/acceptance-report.md](docs/acceptance-report.md) |

## 一、專案概述

電商購物車結算系統(WisdomGarden Dev 面試題 MVP)。消費者選好商品後,系統依「促銷折扣」與「優惠券」算出最終結算金額。

評分重點:**clean code、物件導向(不過度設計)、自動化單元測試**。

## 二、技術棧與框架

| 項目 | 選擇 | 說明 |
| --- | --- | --- |
| Python | 3.10+ | 使用 `list[X]` 等 type hint 語法 |
| 後端 | FastAPI | 由 uvicorn 執行;程式碼中**不需要** `import uvicorn` |
| 伺服器 | uvicorn | 啟動指令:`uvicorn cart.main:app --reload --app-dir src` |
| 前端 | 純 HTML + 原生 JavaScript(`fetch`) | **禁止** Vue / React / Alpine.js,**禁止** npm / build |
| 資料驗證 | Pydantic | schema 只能出現在 `api/` 層 |
| 金額 | `Decimal` | **嚴禁 float**;API 輸出為字串,最後四捨五入到小數 2 位 |
| 測試 | pytest | 測試 HTTP 用 `TestClient`(依賴 httpx) |
| 套件管理 | pip + venv | 套件**只裝在 `.venv` 內**,不得裝到系統 Python |

依賴白名單(只允許下列套件):

- 執行:`fastapi`、`uvicorn`
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
uvicorn cart.main:app --reload --app-dir src
```

- 商品瀏覽頁:<http://127.0.0.1:8000/>
- API 文件:<http://127.0.0.1:8000/docs>
- 商品 API:<http://127.0.0.1:8000/api/products>

### 執行測試

```bash
pytest
```

### 跑驗收案例(CLI)

```bash
python -m cart.cli tests/fixtures/case_a.txt tests/fixtures/case_b.txt
# 需在 src 在路徑上的環境執行,例如 PYTHONPATH=src,或從安裝了此套件的 venv 執行
```

輸出每個案例一行的結算金額,case_a 為 `3083.60`、case_b 為 `43.54`。

## 四、目錄結構與分層

```
shopping_cart/
├── docs/              # 文件(requirements / feature-checklist / test-checklist / architecture / decisions / acceptance-report)
├── data/              # 資料檔(seed.json;runtime.json 執行時產生,已 gitignore)
├── src/cart/
│   ├── main.py        # FastAPI 進入點
│   ├── config.py      # 路徑設定(以檔案位置推算,不依賴工作目錄)
│   ├── domain/        # 領域層:目錄、模型、錯誤
│   ├── services/      # 服務層:結算流程
│   ├── repository/    # 檔案讀寫(唯一碰檔案的地方)
│   ├── api/           # API 層:schema、router(極薄)
│   ├── cli/           # 命令列工具與文字解析
│   └── web/           # 前端靜態檔
└── tests/             # unit / api / acceptance / fixtures
```

**依賴方向:`api → services → domain`;`domain` 不得 import FastAPI 或任何 web 模組。**

- `domain/`:領域資料與業務規則,不讀寫檔案、不認識外層。
- `services/`:業務流程(結算),組合 domain 規則,不讀寫檔案。
- `repository/`:唯一讀寫檔案的地方。
- `api/`:HTTP 介面,只做「接收 → 呼叫 service → 回傳」。
- `cli/parser.py`:文字解析,只做「字串 → 資料物件」,**不計算金額**。

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
- **日期由參數傳入**:任何函式不得自行呼叫 `date.today()`,「今天」由最外層決定後往內傳
- I/O 與規則分離:`domain/`、`services/` 不讀寫檔案
- 需要儲存或日期的類別,在建構時從外部傳入
- PEP 8,所有函式標註參數與回傳型別
- 不提前建立用不到的 base class、interface、factory

### 前端

- 拆成小函式(取資料、組畫面、顯示錯誤各一個),使用 `async / await`,不用 `.then()` 串接長邏輯
- 插入資料時用 `textContent` 或建立元素,**不把資料直接拼進 `innerHTML`**
- 載入中 / 成功 / 失敗三種狀態都要處理

## 六、現況摘要

題目核心「依促銷與優惠券算出結算金額」**已完整實作並通過驗收案例**(case_a `3083.60`、case_b `43.54`,`pytest` 74 passed)。

尚未實作的部分集中在**後台管理**與**購物車持久化**,兩者都是題目未要求的加值範圍。完整清單(8 項,含各項現況與為何未做)與建議順序見 [docs/feature-checklist.md](docs/feature-checklist.md)。

購物車目前只存在前端 JS 記憶體,重整頁面即清空;**金額的唯一信任來源是後端**,結算時後端只收商品名 + 數量,價格重取 `CATALOG`(見 [docs/decisions.md](docs/decisions.md) D4)。

## 七、Git 工作流

- 目前分支:`feature/project-skeleton`(已 commit 5 次,尚未 push)
- 不得在 `main` / `master` 上修改;完成後只 commit,**不要 push、不要 merge**
- commit 前先跑 `pytest`,通過才 commit
- 題目來源檔(`WisdomGarden (Dev) 面試題目.pdf`、`request.md`、`classHTML.md`、`productHTML.md`)為 untracked,**不納入版本控管**