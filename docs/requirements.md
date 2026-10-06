# 需求清單

本檔案是本專案的**需求來源**:業務規則、API 規格、測試案例。

- 想查「做到哪裡」→ [feature-checklist.md](feature-checklist.md)
- 想查「測了什麼」→ [test-checklist.md](test-checklist.md)
- 想查「為何這樣設計 / 為何不那樣」→ [decisions.md](decisions.md)

## 一、系統形態

一支**無狀態計算 API**:`POST /api/calculate`。消費者選好商品後,連同促銷與折價券一起送進來,系統算出最終結算金額。系統不保存任何資料:沒有資料庫、沒有持久層、沒有前端,促銷與折價券都是**每次請求的輸入**而非常駐資料。

## 二、API 規格

### Request

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
| `date` | 是 | 交易日,支援 `YYYY-MM-DD` / `YYYY.MM.DD` / `YYYY/MM/DD` |
| `items` | 是 | 購物車明細,不得為空;`qty` 為正整數 |
| `items[].unitPrice` | 是 | 單價,**字串**,由請求帶入(不查目錄) |
| `promotions` | 否 | 省略為空陣列 |
| `promotions[].date` / `category` | 否 | 省略代表不設限,對所有品項生效 |
| `promotions[].rate` | 否 | 乘法,如 `0.7` |
| `promotions[].effect` | 否 | 加法,如 `-50`(折扣)或 `+50`(服務費) |
| `coupons` | 否 | 省略為空陣列;**每次結算只能用一張**,只評估陣列第一張,其餘忽略 |
| `coupons[].discount` | 否 | 正數,套用時自動轉負 |
| `coupons[].effect` | 否 | 直接指定加減值;**取值優先序:`effect` > `-discount` > `0`** |

金額欄位一律是**字串**,避免 JSON 數字還原成 float。

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
- `couponResults`:**只有第一張券**的套用結果(其餘不回報)。`reason` 只有 `expired` / `below_min_spend` 兩種,套用成功為 `null`

### 錯誤

| 狀態码 | 情境 |
| --- | --- |
| 400 | 日期格式不支援、金額欄位不是數值(領域錯誤) |
| 422 | 結構錯誤:`items` 為空、`qty` 不是正整數、缺必填欄位(Pydantic 驗證) |

## 三、業務規則

| # | 規則 | 實作位置 |
| --- | --- | --- |
| 1 | **促銷生效**:未指定日期或日期 = 交易日,**且**未指定品類或品類相符 | `services/calculator.py::is_promotion_applicable` |
| 2 | **促銷計算**:`lineTotal = qty × unitPrice × Π(rate) + Σ(effect)` | `services/calculator.py::calculate_line_total` |
| 3 | **折價券過期**:交易日 > 到期日即失效,到期日當天有效;未指定到期日永不失效 | `services/calculator.py::is_coupon_expired` |
| 4 | **折價券門檻**:小計 < minSpend 即不生效,含等號;未指定門檻永遠達標 | `services/calculator.py::is_coupon_below_min_spend` |
| 5 | **過期判斷優先於門檻判斷** | `services/calculator.py::apply_coupon` |
| 6 | **折價券取值**:`effect` > `-discount` > `0` | `services/calculator.py::resolve_coupon_effect` |
| 7 | **單張折價券**:**每次結算只能用一張**(題目原文),只評估陣列第一張,`total = subtotal + 已套用券 effect` | `services/calculator.py::apply_coupons` |
| 8 | **四捨五入**:只在最後 `total` 做,`ROUND_HALF_UP` 到小數 2 位 | `services/calculator.py::round_to_two_places` |
| 9 | **金額**:全程 `Decimal`,`subtotal` 不四捨五入 | 全專案 |
| 10 | **品類**:自由字串,不由固定目錄約束 | `domain/models.py` |

## 四、測試案例

案例檔為 `tests/fixtures/case-N.json`(純 request payload),API 測試逐一讀取比對。

| 檔案 | 情境 | 預期 subtotal | 預期 total | couponResults |
| --- | --- | --- | --- | --- |
| `case-1.json` | 基準案例(原 Case A) | `3283.600` | `3083.60` | `[{0, true, null}]` |
| `case-2.json` | 折價券未達 minSpend(原 Case B) | `43.54` | `43.54` | `[{0, false, "below_min_spend"}]` |
| `case-3.json` | 折價券已過期 | `5999.00` | `5999.00` | `[{0, false, "expired"}]` |
| `case-4.json` | 促銷品類不匹配 | `698.00` | `698.00` | `[]` |
| `case-5.json` | 促銷日期不匹配 | `698.00` | `698.00` | `[]` |
| `case-6.json` | 第二張券被忽略(每次只能用一張) | `4899.300` | `4399.30` | `[{0, true, null}]` |
| `case-7.json` | effect 為正數(服務費) | `100.00` | `100.00` | `[]` |
| `case-8.json` | 浮點數精度 + 四捨五入 | `0.425` | `0.33` | `[{0, true, null}]` |
| `case-10.json` | 多 rate 連乘 + 高額,第二張券被忽略 | `7199.2800` | `6699.28` | `[{0, true, null}]` |
| `case-11.json` | 券 effect 優先 + 到期日當天 + 門檻含等號 | `0.99` | `0.69` | `[{0, true, null}]` |
| `case-12.json` | 斜線日期 + 自由品類 + 促銷折抵 + 過期券 | `80.3500` | `60.35` | `[{0, true, null}]` |

### 基準案例計算過程(case-1)

- 電子品類 0.7 折:ipad 2399.00 × 0.7 = 1679.300、顯示器 1799.00 × 0.7 = 1259.300
- 其他品類不打折:啤酒 12 × 25.00 = 300.00、麵包 5 × 9.00 = 45.00
- subtotal = 1679.300 + 1259.300 + 300.00 + 45.00 = **3283.600**
- 折價券(3283.600 ≥ 門檻 1000,未過期):3283.600 − 200 = **3083.60**

### 精度案例(case-8)為何是分辨性測試

- 餅乾 3 × 0.10 = 0.30、蛋糕 1 × 0.125 = 0.125,subtotal = **0.425**(達門檻 0.40)
- 折價券 0.425 − 0.10 = **0.325**,`ROUND_HALF_UP` 到 2 位 = **0.33**
- **真正的分辨點在 subtotal 本身**:float 算 `0.1 × 3 + 0.125` 得 `0.42500000000000004`而非精確的 0.425;`0.425` 的 double 表示又略小於真值,使 `round(0.425, 2)` 得 **0.42** 而非 Decimal `ROUND_HALF_UP` 的 **0.43**。全程 `Decimal` 才能保證小計與四捨五入都貼合十進位真值。

## 五、歷史:與原始題目輸入格式的對應

原始題目用文字案例,本規格改用 JSON,欄位對應如下:

| 原始格式 | JSON 對應 |
| --- | --- |
| `2015.11.11\|0.7\|電子` | `{"date": "2015.11.11", "category": "電子", "rate": "0.7"}` |
| `1*ipad:2399.00` | `{"name": "ipad", "category": "電子", "qty": 1, "unitPrice": "2399.00"}` |
| `2015.11.11`(結算日) | `date` |
| `2016.3.2 1000 200` | `{"expiryDate": "2016.3.2", "minSpend": "1000", "discount": "200"}` |

品類欄位在原始題目由目錄隱含提供(商品 → 品類對照),本規格改為**每個品項明確攜帶 `category`**,因此可容納題目目錄以外的品項(如「生活用品類」)。
