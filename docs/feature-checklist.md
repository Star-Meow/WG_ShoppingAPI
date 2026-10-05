# 功能盤點(實作進度)

本檔案回答「**哪些功能已實作、哪些還沒**」。需求本身見 [requirements.md](requirements.md),測試涵蓋範圍見 [test-checklist.md](test-checklist.md)。

## 一、完成度摘要

題目核心「依促銷與折價券算出結算金額」**已 100% 做完**,形態為一支無狀態計算 API `POST /api/calculate`(見 [decisions.md](decisions.md) D6)。

| 類別 | 已完成 | 總項目 | 完成率 |
| --- | --- | --- | --- |
| 後端 | 12 | 12 | 100% |
| 測試 | 8 | 8 | 100% |
| **合計** | **20** | **20** | **100%** |

> **歷史**:本專案曾包含商品瀏覽頁、獨立結帳頁、CLI 文字解析、JSON 持久層與後台管理空殼。重讀題目後確認題目核心只需「把案例資料餵進系統算出金額」,這些屬於範圍外的加值功能,已在 D6 全數移除。舊版盤點與其理由保留在 git 歷史。

## 二、後端盤點(api → services → domain)

### 領域層 `domain/`

- [x] 計算領域模型:`LineItem`、`Promotion`(rate + effect,可省略 date / category)、`Coupon`、`CaseInput`、`CalculationResult`、`CouponResult` — `domain/models.py`
- [x] 領域錯誤類型:`CalculationError` 家族(日期格式、數量、金額、空購物車),供 API 層對應 HTTP 400 — `domain/errors.py`
- [x] 品類為自由字串,不由固定目錄約束 — `domain/models.py`

### 服務層 `services/`

- [x] 日期解析:支援 `YYYY-MM-DD` / `YYYY.MM.DD` / `YYYY/MM/DD` 三格式,不合法格式拋 `DateFormatError` — `services/date_parsing.py`
- [x] 促銷生效判斷:未指定日期或日期相符,**且**未指定品類或品類相符 — `services/calculator.py`
- [x] 促銷計算:`lineTotal = qty × unitPrice × Π(rate) + Σ(effect)` — `services/calculator.py`
- [x] 折價券過期判斷:交易日 > 到期日即失效,到期日當天有效;無到期日永不失效 — `services/calculator.py`
- [x] 折價券門檻判斷:小計 < minSpend 即不生效(含等號);無門檻永遠達標 — `services/calculator.py`
- [x] 折價券取值優先序:`effect` > `-discount` > `0` — `services/calculator.py`
- [x] 多張折價券依序套用,過期判斷優先於門檻判斷 — `services/calculator.py`
- [x] 金額規則:全程 `Decimal`,`total` 最後四捨五入到小數 2 位(`ROUND_HALF_UP`),`subtotal` 不四捨五入 — `services/calculator.py`

### API 層 `api/`

- [x] 計算 API:`POST /api/calculate` 收交易日期、品項(含單價與品類)、促銷、折價券,回傳 `subtotal` / `total` / `couponResults` — `api/calculate.py`、`api/schemas.py`
- [x] 領域錯誤統一轉 HTTP 400;結構錯誤由 Pydantic 擋成 422 — `main.py`、`api/schemas.py`

### 進入點

- [x] FastAPI app 建立,只註冊計算 router — `main.py`

## 三、測試案例盤點

8 組 JSON 案例位於 `tests/fixtures/`,API 測試逐一讀取打 API 比對:

| # | 情境 | 預期 total |
| --- | --- | --- |
| 1 | 基準案例(原 Case A) | `3083.60` |
| 2 | 折價券未達 minSpend(原 Case B) | `43.54` |
| 3 | 折價券已過期 | `5999.00` |
| 4 | 促銷品類不匹配 | `698.00` |
| 5 | 促銷日期不匹配 | `698.00` |
| 6 | 多張折價券疊加 | `4199.30` |
| 7 | effect 為正數(服務費) | `100.00` |
| 8 | 浮點數精度 + 四捨五入 | `0.33` |

案例 8 是精度分辨測試:全程 `Decimal` 讓 subtotal 精確為 **0.425**、折價券後 `ROUND_HALF_UP` 給 **0.33**。float 算小計會得 `0.42500000000000004`,且 `0.425` 的 double 表示略小於真值,使 `round(0.425, 2)` 給 **0.42** 而非 0.43。

## 四、不做的功能(範圍外)

以下都是題目未要求、屬於加值範圍,目前**刻意不做**(理由見 [decisions.md](decisions.md) D6):

| 功能 | 為何不做 |
| --- | --- |
| 商品瀏覽頁 / 結帳頁等前端 | 題目核心是計算邏輯;前端屬追加項,需求端已明示「先不重做」 |
| 後台管理(商品 / 促銷 / 折價券 CRUD) | 促銷與券是每次請求的輸入參數,不是常駐實體;做 CRUD 會把系統從無狀態變成有狀態 |
| 購物車持久化 / 後端購物車 API | 系統無狀態,購物車明細由請求帶入,不需要保存 |
| 登入 / 會員 | 題目完全未涉及,且會帶入整套安全表面 |
| CLI 文字案例解析 | 案例改用 JSON 直接餵 API,不再需要文字解析中介層 |
| 資料庫 | 無持久化需求,JSON 檔也不需要(見 D1 → D6) |
