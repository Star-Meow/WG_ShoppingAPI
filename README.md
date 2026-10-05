# 購物車結算計算 API(WisdomGarden Dev 面試題)

面試題核心:**給定購物車、促銷折扣與優惠券,算出消費者實際該付的金額**。

本專案將題目核心實作為一支**無狀態計算 API** `POST /api/calculate`——吃 JSON、吐金額。沒有資料庫、沒有持久層、沒有前端;促銷與優惠券都是**每次請求的輸入**,而非系統常駐資料。

> **為什麼是計算 API 而不是一整套電商網站?** 題目把促銷(`2015.11.11|0.7|電子`)與優惠券(`2016.3.2 1000 200`)都當成「跟結算請求一起傳進來的輸入」,題目目錄也**只列品類與商品名、沒有任何單價**(單價只出現在案例輸入行 `1*ipad:2399.00`)。所以系統只需算錢,不需要商品瀏覽頁、會員或資料庫。推理過程記錄在 [docs/decisions.md](docs/decisions.md) D6。

## 題目範例對應

| 題目案例 | 本專案對應 | 預期結果 |
| --- | --- | --- |
| Case A(`1*ipad:2399.00` 等 4 項 + 電子 0.7 折 + 滿千折二百) | `tests/fixtures/case-1.json` | `3083.60` ✅ |
| Case B(`3*蔬菜:5.98` + `8*餐巾紙:3.20`,無促銷無券) | `tests/fixtures/case-2.json` | `43.54` ✅ |

題目要求的「各種一般與例外情況」,另外以 6 組邊界案例覆蓋(見下方測試段落)。

## 計算規則

| # | 規則 |
| --- | --- |
| 1 | **促銷生效**:未指定日期或日期 = 交易日,**且**未指定品類或品類相符 |
| 2 | **促銷計算**:`lineTotal = qty × unitPrice × Π(rate) + Σ(effect)`;多張生效促銷的 `rate` 是**連乘** |
| 3 | **折價券過期**:交易日 > 到期日即失效,到期日當天有效 |
| 4 | **折價券門檻**:小計 < `minSpend` 即不生效(含等號);門檻跟**未四捨五入的小計**比 |
| 5 | **過期判斷優先於門檻判斷** |
| 6 | **折價券取值**:`effect` > `-discount` > `0` |
| 7 | **多張折價券**:依序套用於小計,`total = subtotal + Σ(已套用券 effect)` |
| 8 | **四捨五入**:只在最後 `total` 做,`ROUND_HALF_UP` 到小數 2 位;`subtotal` 忠實呈現計算過程 |
| 9 | **金額**:全程 `Decimal`,**嚴禁 float** |

> **關於「每次只能用一張優惠券」**:題目本文寫單張,但題目規格的情境需求包含多張折價券疊加。本專案採規格版:`coupons` 收陣列、依序套用。陣列本來就能只放一張,單張情境完全相容;若要改回單張,只需改 `case-6` 的預期值,API 不用動。

## API 規格

### Request `POST /api/calculate`

```json
{
  "date": "2015-11-11",
  "items": [
    {"name": "ipad", "category": "電子", "qty": 1, "unitPrice": "2399.00"}
  ],
  "promotions": [
    {"date": "2015-11-11", "category": "電子", "rate": "0.7", "effect": "-50"}
  ],
  "coupons": [
    {"expiryDate": "2016-03-02", "minSpend": "1000", "discount": "200", "effect": "-200"}
  ]
}
```

| 欄位 | 必填 | 說明 |
| --- | --- | --- |
| `date` | 是 | 交易日;支援 `YYYY-MM-DD` / `YYYY.MM.DD` / `YYYY/MM/DD` |
| `items` | 是 | 購物車明細,不得為空;`qty` 為正整數 |
| `items[].unitPrice` | 是 | 單價,**字串**;金額一律字串避免 JSON 數字還原成 float |
| `promotions` | 否 | 省略為空陣列;`date` / `category` 省略代表全適用 |
| `promotions[].rate` | 否 | 乘法(如 `0.7`) |
| `promotions[].effect` | 否 | 加法(如 `-50` 折扣或 `+50` 服務費) |
| `coupons` | 否 | 省略為空陣列;多張時依序套用 |
| `coupons[].discount` | 否 | 正數,套用時自動轉負 |
| `coupons[].effect` | 否 | 直接指定加減值;**取值優先序 `effect` > `-discount` > `0`** |

### Response

```json
{
  "subtotal": "3283.600",
  "total": "3083.60",
  "couponResults": [{"index": 0, "applied": true, "reason": null}]
}
```

- `subtotal`:**不四捨五入**,忠實呈現計算過程
- `total`:四捨五入到小數 2 位
- `couponResults.reason`:只有 `expired`(交易日 > 到期日)、`below_min_spend`(小計 < 門檻)兩種,套用成功為 `null`

### 錯誤

| 狀態碼 | 情境 |
| --- | --- |
| **400** | 日期格式不支援或不可能日期、金額欄位不是數值(領域錯誤) |
| **422** | `items` 為空、`qty` 不是正整數、缺必填欄位(Pydantic 驗證) |

## 環境設定

### 1. 建立並啟用虛擬環境

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

### 2. 安裝依賴

```bash
pip install -r requirements-dev.txt   # 開發(含測試)
pip install -r requirements.txt       # 僅執行
```

依賴白名單只有 `fastapi`、`uvicorn`(執行)與 `pytest`、`httpx`(開發)。

## 啟動與使用

```bash
uvicorn cart.main:app --port 3000 --app-dir src
```

- 計算 API:<http://localhost:3000/api/calculate>(POST)
- API 文件:<http://localhost:3000/docs>

跑題目範例:

```bash
curl -X POST http://localhost:3000/api/calculate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/case-1.json
# {"subtotal":"3283.600","total":"3083.60","couponResults":[{"index":0,"applied":true,"reason":null}]}
```

## 測試

### 全套自動化測試

```bash
pytest
```

預期 **53 passed**。測試分兩層:

| 測試檔 | 項數 | 涵蓋內容 |
| --- | --- | --- |
| `tests/unit/test_date_parsing.py` | 8 | 三種日期格式、錯誤格式與不可能日期(2/13、2/30)、Decimal 精確值 |
| `tests/unit/test_calculator.py` | 13 | rate 套用 / 連乘、effect 加減、品類與日期不匹配、小計不四捨五入、Case A 端到端、精度案例 |
| `tests/unit/test_coupon.py` | 14 | discount 轉負、effect 優先、到期日當天有效、門檻含等號、過期優先於門檻、多券依序套用 |
| `tests/api/test_calculate_api.py` | 18 | 逐一讀 8 組 fixture 打 API 比對完整回應;三日期格式;400 / 422 錯誤 |

其他用法:

```bash
pytest tests/unit/test_calculator.py    # 單一檔
pytest -k coupon                        # 依關鍵字篩選
```

### 8 組驗收案例(`tests/fixtures/`)

前 2 組是題目給的 Case A / Case B,後 6 組覆蓋題目說的「其他情形」。可逐一打 API 比對:

```bash
uvicorn cart.main:app --port 3000 --app-dir src
curl -X POST http://localhost:3000/api/calculate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/case-8.json
```

| # | 情境 | 輸入摘要 | 預期 subtotal | 預期 total | couponResults |
| --- | --- | --- | --- | --- | --- |
| 1 | 基準案例(題目 Case A) | 電子 0.7 折;ipad×1、顯示器×1、啤酒×12、麵包×5;券折 200 門檻 1000 | `3283.600` | `3083.60` | `[{0,true,null}]` |
| 2 | 券未達門檻(題目 Case B) | 蔬菜×3、餐巾紙×8;券門檻 1000 | `43.54` | `43.54` | `[{0,false,"below_min_spend"}]` |
| 3 | 券已過期 | iphone×1 = 5999;券到期 2016-03-02,交易日 2016-04-01 | `5999.00` | `5999.00` | `[{0,false,"expired"}]` |
| 4 | 促銷品類不匹配 | 鍵盤×2(電子)= 698;促銷打在「日用品」0.7 折 | `698.00` | `698.00` | `[]` |
| 5 | 促銷日期不匹配 | 鍵盤×2(電子)= 698;促銷打電子 0.7 折但日期是 2015-12-25 | `698.00` | `698.00` | `[]` |
| 6 | 多張折價券疊加 | 筆電×1,電子 0.7 折 → 4899.300;兩張券各折 500、200 | `4899.300` | `4199.30` | `[{0,true,null},{1,true,null}]` |
| 7 | effect 正數(服務費) | 咖啡杯×2 = 50;全域促銷 `effect: +50` | `100.00` | `100.00` | `[]` |
| 8 | 浮點精度 + 四捨五入 | 餅乾×3×0.10、蛋糕×1×0.125 → 0.425;券門檻 0.40 折 0.10 | `0.425` | `0.33` | `[{0,true,null}]` |

**案例 8 是精度分辨測試**:全程 `Decimal` 讓小計精確為 `0.425`。float 算 `0.1×3 + 0.125` 會得 `0.42500000000000004`,且 `0.425` 的 double 表示略小於真值,使 Python `round(0.425, 2)` 給 **0.42** 而非 `ROUND_HALF_UP` 的 **0.43**——這類金額計算必須用 `Decimal` 才貼合十進位真值。

**案例 1 計算過程**:

```
ipad    1 × 2399.00 × 0.7 = 1679.300    (電子,促銷生效)
顯示器   1 × 1799.00 × 0.7 = 1259.300    (電子,促銷生效)
啤酒    12 × 25.00       =  300.00       (酒類,無促銷)
麵包     5 × 9.00        =   45.00       (食品,無促銷)
----------------------------------------
subtotal                 = 3283.600      (不四捨五入)
3283.600 ≥ 門檻 1000,未過期 → − 200
total                    = 3083.60       (四捨五入到 2 位)
```

## 目錄結構

```
WG_ShoppingWeb/
├── README.md                          # 本檔:題目對應、API 規格、測試方式
├── AGENTS.md                          # 環境與程式風格規則(給進入專案的人)
├── docs/                              # 詳細文件
│   ├── requirements.md                #   完整業務規則與案例
│   ├── feature-checklist.md           #   實作進度
│   ├── test-checklist.md              #   測試涵蓋與缺口
│   ├── architecture.md                #   分層、依賴方向、風格規則
│   ├── decisions.md                   #   評估過後不採用的方案與理由
│   └── acceptance-report.md           #   實測紀錄
├── src/cart/
│   ├── main.py                        # FastAPI 進入點(只註冊 calculate + 400 handler)
│   ├── domain/                        # 領域層:模型、錯誤(不 import 任何 web 模組)
│   │   ├── models.py                  #   LineItem / Promotion / Coupon / CaseInput / 結果
│   │   └── errors.py                  #   CalculationError 家族
│   ├── services/                      # 服務層:純函式,不讀檔、不讀系統時間
│   │   ├── calculator.py              #   促銷判斷、lineTotal、小計、券套用、總額
│   │   └── date_parsing.py            #   日期三格式解析、Decimal 解析
│   └── api/                           # API 層:極薄,只做「接收 → 呼叫 service → 回傳」
│       ├── schemas.py                 #   Pydantic 請求/回應模型(camelCase)
│       └── calculate.py               #   /api/calculate router
└── tests/
    ├── unit/                          # 單元測試(計算引擎、日期解析、券)
    ├── api/                           # API 測試(TestClient)
    └── fixtures/case-1.json ~ case-8.json
```

**依賴方向:`api → services → domain`;`domain` 不得 import FastAPI 或任何 web 模組。**

- `domain/`:領域資料,不讀寫檔案、不認識外層。
- `services/`:業務規則,全部是**純函式**(相同輸入必得相同輸出),日期一律由參數傳入,不自行呼叫 `date.today()`。
- `api/`:HTTP 介面,Pydantic schema 只出現在此層。

## 設計決策摘要

| 決策 | 理由 |
| --- | --- |
| **不用 DB** | 題目把促銷與券當成每次請求的輸入參數,系統從不查詢「某日期當時生效的促銷」,版本回溯與查詢能力用不到([decisions.md](docs/decisions.md) D1) |
| **價格由請求帶入** | 題目目錄只列品類與商品名,**沒有單價**;單價只能來自輸入。品類也改為自由字串,可容納目錄以外的品項(D6) |
| **不做登入 / 會員** | 題目完全未涉及,且會帶入整套安全表面(D3) |
| **不做前端** | 題目核心是結算計算;題目目錄無單價,做商品頁也無從定價(D6) |
| **無狀態** | 每次請求獨立計算,算完即丟;衍生值絕不暫存([architecture.md](docs/architecture.md)) |

完整推理與「什麼情況下會翻轉」見 [docs/decisions.md](docs/decisions.md)。
