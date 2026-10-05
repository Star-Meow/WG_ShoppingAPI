# AGENTS.md

本檔案給進入此專案的任何人(或 AI agent)快速掌握:需要什麼框架與環境、完整需求清單,以及目前做到哪裡。詳細的架構與風格規則見 [docs/architecture.md](docs/architecture.md),業務規則的逐項說明見 [docs/requirements.md](docs/requirements.md),**評估過後不採用的方案與理由(為何不用 DB、為何不做登入等)見 [docs/decisions.md](docs/decisions.md)**。

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
| 測試 | pytest | 測試 HTTP 用 `TestClient`(依赖 httpx) |
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
├── docs/              # 需求與架構文件
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
└── tests/             # unit / api / fixtures
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

## 六、需求清單(業務規則)

### 結算主流程

1. **促銷折扣**:僅在結算日 = 促銷日期時生效,且只套用在對應品類。
2. **優惠券有效期**:結算日 ≤ 到期日即有效(含當天)。
3. **優惠券門檻**:以**促銷折扣後**金額判斷,≥ 門檻即成立。
4. **每次結算只能用一張優惠券**。
5. **金額**:一律 `Decimal`,最後四捨五入到小數 2 位。
6. **當前日期**:可由後台手動覆寫,也可切回系統真實日期。

### 待決定(列為待辦,未實作)

- 多張可用優惠券時,要「自動套用減額最大者」或「由使用者選擇」。**待確認後再補,不要自行假設。**

### 驗收測試案例

| 檔案 | 輸入摘要 | 預期輸出 |
| --- | --- | --- |
| `tests/fixtures/case_a.txt` | 電子品類 0.7 折促銷;ipad*1、顯示器*1、啤酒*12、麵包*5;優惠券門檻 1000 折 200 | `3083.60` |
| `tests/fixtures/case_b.txt` | 無促銷;蔬菜*3、餐巾紙*8;無優惠券 | `43.54` |

案例文字格式(未來 CLI parser 需解析):

- 第 1 段:促銷,`日期|折扣|品類`,例如 `2015.11.11|0.7|電子`
- 第 2 段:購物車明細,每行 `數量*商品:單價`,例如 `1*ipad:2399.00`
- 第 3 段:結算日,例如 `2015.11.11`
- 第 4 段:優惠券,`日期 門檻 折額`,例如 `2016.3.2 1000 200`
- 段落之間以空行分隔;無該段時為空行

### 商品目錄(MVP 預設值,之後可調整)

4 類 18 項:

| 品類 | 商品(單價) |
| --- | --- |
| 電子(5) | ipad 2399.00、iphone 5999.00、顯示器 1799.00、筆記型電腦 6999.00、鍵盤 349.00 |
| 食品(6) | 麵包 9.00、餅乾 12.00、蛋糕 45.00、牛肉 88.00、魚 36.00、蔬菜 5.98 |
| 日用品(4) | 餐巾紙 3.20、收納箱 59.00、咖啡杯 25.00、雨傘 39.00 |
| 酒類(3) | 啤酒 25.00、白酒 128.00、伏特加 168.00 |

## 七、功能盤點(前後端拆分,逐項勾選)

> 依架構分成「後端」與「前端」兩大類(測試獨立一類),逐項列出完成狀態。標註「空殼」者代表檔案已建但只有模組 docstring、尚無邏輯。

### 後端(api → services → domain)

#### 領域層 domain/

- [x] 商品目錄資料模型:`Category` 列舉(電子/食品/日用品/酒類)、`Product` 資料物件、`CATALOG`(4 類 18 項) — `domain/catalog.py`
- [x] 依品類分組商品:`products_by_category()`,回傳順序依照 `Category` 定義順序 — `domain/catalog.py`
- [x] 結算領域模型:`CartItem`、`Promotion`、`Coupon`、`Cart`(含 `subtotal()`)、`CheckoutInput` — `domain/models.py`
- [x] 領域錯誤類型:`CheckoutError` 家族(解析格式、未知商品、單價不一致、券不可用等),供 API 層對應 HTTP 狀態碼 — `domain/errors.py`
- [x] 金額規則:結算一律 `Decimal` 且四捨五入到小數 2 位(`round_to_two_places`) — `services/checkout.py`
- [x] 依名稱查商品:`find_product_by_name()`,供解析層取品類與權威單價 — `domain/catalog.py`

#### 服務層 services/

- [x] 促銷折扣:僅在結算日 = 促銷日期時生效,且只套用在對應品類 — `services/checkout.py`
- [x] 優惠券有效期:結算日 ≤ 到期日即有效(含當天) — `services/checkout.py`
- [x] 優惠券門檻:以**促銷折扣後**金額判斷,≥ 門檻才成立 — `services/checkout.py`
- [x] 單張優惠券限制:每次結算只能一張(由 `CheckoutInput.coupon: Coupon | None` 於模型層強制) — `services/checkout.py`
- [ ] **待決定**:多張券可用時,自動套用減額最大者 or 由使用者選擇(確認後才實作,不假設)

#### 資料層 repository/

- [ ] JSON 讀寫:讀 `data/seed.json`、寫 `data/runtime.json`(domain 與 services 不得直接讀寫檔案) — `repository/json_store.py`(空殼)

#### API 層 api/

- [x] 商品瀏覽 API:`GET /api/products`,回傳 4 品類分組共 18 項,價格為字串 — `api/products.py`、`api/schemas.py`
- [x] 回傳格式轉換純函式:`build_category_groups()`,不經過 HTTP 也能測 — `api/products.py`
- [ ] 結算 API:接收購物車與優惠券 → 呼叫 service → 回傳金額 — `api/checkout.py`(空殼)
- [ ] 後台 API:商品目錄、促銷、優惠券管理 — `api/admin.py`(空殼)
- [ ] 後台 API:手動覆寫「當前日期」,可切回系統真實日期 — `api/admin.py`(空殼)
- [ ] 購物車 API:新增 / 修改 / 查詢購物車項目 — 尚未建立

#### 進入點與設定

- [x] FastAPI app 建立、API router 先註冊、靜態檔掛載在最後 — `main.py`
- [x] 路徑集中設定:web 目錄、`data/` 目錄(以 `pathlib` 依檔案位置推算) — `config.py`
- [ ] 「當前日期」由最外層決定並往內傳的機制(業務規則不得自行呼叫 `date.today()`) — 尚未實作

#### 命令列 cli/

- [x] 文字解析:案例字串 → `CheckoutInput`,只解析不計算金額;品類與單價由 `CATALOG` 查得 — `cli/parser.py`
- [x] CLI 入口:`python -m cart.cli <檔>...` 讀檔 → 解析 → 結算 → 印金額 — `cli/__main__.py`

### 前端(web/)

- [x] 頂部查詢框:輸入關鍵字即過濾目前頁面商品(依名稱不分大小寫比對,純前端不連後端) — `web/index.html`
- [x] 分類導引欄:查詢框下方的橫向分頁(全部 + 4 品類),點擊只顯示該品項,並清掉搜尋關鍵字 — `web/index.html`
- [x] 商品卡片:純 CSS 佔位圖(品類顏色 + 品名首字)、品名、單價 — `web/index.html`
- [x] 加入購物車按鈕:每張卡片一顆,點擊把目前數量加進購物車並顯示「已加入購物車:{品名} × {數量}」提示 — `web/index.html`
- [x] 數量調整元件:每張卡片上有 `- [數量] +`,最低 1,數量為 1 時停用減號鈕 — `web/index.html`
- [x] 右下角懸浮購物車鈕:`position: fixed` 固定於畫面右下角,附商品總數角標(0 時隱藏) — `web/index.html`
- [x] 購物籃畫面:點懸浮鈕展開,逐項顯示品名、單價 × 數量、該項小計與合計;空車顯示「購物車是空的」 — `web/index.html`
- [x] 前端購物車狀態:目前以 JS 物件存在記憶體,金額用整數分計算避免 float 誤差(見下方「購物車資料流向」) — `web/index.html`
- [x] 三種狀態處理:載入中 / 成功 / 失敗(失敗時附錯誤與排除方式);查無商品時顯示「查無符合的商品」 — `web/index.html`
- [x] 響應式版面:手機寬度可讀 — `web/index.html`
- [x] 可見的鍵盤 focus 樣式 — `web/index.html`
- [x] 無框架、免 build、資料以 `textContent` / 建立元素插入(不拼進 `innerHTML`) — `web/index.html`
- [ ] 後台管理頁:商品 / 促銷 / 優惠券管理與當前日期切換 — `web/admin.html`(空殼)
- [ ] 購物車頁面:修改 / 刪除已加入的商品(目前購物籃只能瀏覽,尚不能編輯) — 尚未建立
- [ ] 結算頁面:顯示促銷折扣後金額與最終金額 — 尚未建立
- [ ] 優惠券選擇介面 — 尚未建立(先等「待決定」項目定案)

### 測試 tests/

- [x] 目錄單元測試:品類數、商品總數、各品類數量 5/6/4/3、價格皆為 `Decimal` — `tests/unit/test_catalog.py`
- [x] builder 單元測試:直接測 `build_category_groups()`(不使用 `TestClient`),驗 4 組、18 項、價格字串、品類順序 — `tests/unit/test_products_builder.py`
- [x] 商品 API 測試:`GET /api/products` 與 `GET /` 經 `TestClient` — `tests/api/test_products_api.py`
- [x] 驗收案例 fixture:`case_a.txt`(預期 3083.60)、`case_b.txt`(預期 43.54) — `tests/fixtures/`
- [x] 結算規則單元測試:促銷生效/不生效、券過期/門檻/促銷後門檻、四捨五入(22 項) — `tests/unit/test_checkout.py`
- [x] 解析器單元測試:日期/促銷/明細/優惠券解析、錯誤案例(18 項) — `tests/unit/test_parser.py`
- [x] CLI 端對端測試:子程序執行 `python -m cart.cli`,印出預期金額與錯誤處理(5 項) — `tests/unit/test_cli.py`
- [x] 驗收案例端對端測試:讀 fixture → 解析 → 結算 → 比對 3083.60 / 43.54 — `tests/acceptance/test_cases.py`

### 完成度摘要

| 類別 | 已完成 | 總項目 |
| --- | --- | --- |
| 後端 | 15 | 22 |
| 前端 | 12 | 16 |
| 測試 | 8 | 8 |
| **合計** | **35** | **46** |

### 購物車資料流向(重要)

目前購物車狀態**只存在前端 JS 記憶體**(`cart` 物件),重新整理頁面就會清空。**尚未透過後端 API 儲存**。完整的方案評估(為何不用 DB、為何不做登入、資料職責分類)見 [docs/decisions.md](docs/decisions.md),以下只列對實作的直接影響:

- 後端購物車 API(`api/checkout.py`)仍是空殼,沒有可呼叫的 endpoint;`services/checkout.py` 已是純函式實作,API 只需薄薄接上一層。
- 依「目前以前端修正為主」的方向,先把互動做出來,不為了儲存而提前實作後端。
- 前端已把購物車操作集中在少數函式中(`addToCart`、`renderCartBadge`、`renderCartPanel`),日後後端 API 上市時,只要改這幾個函式內部去呼叫 API,卡片與面板的繪製邏輯都不用動。
- 金額計算使用整數「分」(`priceToCents` / `centsToText`),避免 float 小數誤差,與後端 `Decimal` 的精神一致。
- **金額的唯一信任來源是後端**:結算時後端只收商品名 + 數量,價格重取 `CATALOG`,不接受前端傳價(見 decisions.md D4)。

未來接後端時已定案的方向(decisions.md D3):以 session 為購物車錨點,session id 放 `httpOnly` cookie;待需會員功能時才考慮登入系統。

下一步建議順序:領域模型 → 結算服務 → CLI(已完成)→ 結算 API → 購物車 API → 後台 → 前端購物車與結算頁。每一層都先寫單元測試再實作。

## 八、Git 工作流

- 目前分支:`feature/project-skeleton`(已 commit 一次,尚未 push)
- 不得在 `main` / `master` 上修改;完成後只 commit,**不要 push、不要 merge**
- commit 前先跑 `pytest`,通過才 commit
- `main` 上有兩個 untracked 的題目來源檔(`WisdomGarden (Dev) 面試題目.pdf`、`request.md`),**不納入版本控管**
