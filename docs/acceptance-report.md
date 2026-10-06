# 結算系統驗收報告

**範圍**:題目核心「給定購物車、促銷與折價券,算出最終結算金額」——一支無狀態計算 API `POST /api/calculate`。
**驗收日期**:2026-10-06
**測試環境**:Python 3.10.11、pytest 9.1.1、Windows + Git Bash,虛擬環境 `.venv`

---

## 一、驗收結論

| 項目 | 結果 |
| --- | --- |
| `pytest` 全套測試 | **53 passed**(0 failed) |
| 8 組案例 `curl` 實測 | **8/8 吻合**(subtotal / total / couponResults 三欄全對) |
| 基準案例 case-1(原 Case A) | total **3083.60** ✅ 與題目預期一致 |
| case-2(原 Case B) | total **43.54** ✅ 與題目預期一致 |
| 精度分辨案例 case-8 | subtotal **0.425**、total **0.33** ✅ float 算小計會得 0.42500000000000004,`round(0.425,2)` 更給 0.42 |
| 錯誤處理 | 日期格式錯 → 400;`qty ≤ 0` / 空車 → 422 |

題目指定的驗收路徑已由「文字案例 + CLI」改為「JSON + API」(見 [decisions.md](decisions.md) D6),`curl` 打 API 即是驗收,不再經過解析器或 CLI 中介層。

---

## 二、8 組案例實測結果

啟動方式:`uvicorn cart.main:app --port 3000 --app-dir src`,再對每組 fixture 發:

```bash
curl -X POST http://localhost:3000/api/calculate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/case-N.json
```

| # | 情境 | 預期 subtotal | 實際 subtotal | 預期 total | 實際 total | couponResults | 結果 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 基準案例(原 Case A) | `3283.600` | `3283.600` | `3083.60` | `3083.60` | `[{0,true,null}]` | ✅ |
| 2 | 券未達 minSpend(原 Case B) | `43.54` | `43.54` | `43.54` | `43.54` | `[{0,false,"below_min_spend"}]` | ✅ |
| 3 | 券已過期 | `5999.00` | `5999.00` | `5999.00` | `5999.00` | `[{0,false,"expired"}]` | ✅ |
| 4 | 促銷品類不匹配 | `698.00` | `698.00` | `698.00` | `698.00` | `[]` | ✅ |
| 5 | 促銷日期不匹配 | `698.00` | `698.00` | `698.00` | `698.00` | `[]` | ✅ |
| 6 | 只用第一張券(每次只能用一張) | `4899.300` | `4899.300` | `4399.30` | `4399.30` | `[{0,true,null}]` | ✅ |
| 7 | effect 為正數(服務費) | `100.00` | `100.00` | `100.00` | `100.00` | `[]` | ✅ |
| 8 | 浮點精度 + 四捨五入 | `0.425` | `0.425` | `0.33` | `0.33` | `[{0,true,null}]` | ✅ |

完整回應(case-1 為例):

```json
{"subtotal":"3283.600","total":"3083.60","couponResults":[{"index":0,"applied":true,"reason":null}]}
```

### 計算過程

**case-1(基準案例)**——電子品類 0.7 折 + 門檻 1000 折 200:

| 明細 | 品類 | 原價 | 促銷後 |
| --- | --- | --- | --- |
| ipad × 1 | 電子 | 2399.00 | 2399.00 × 0.7 = 1679.300 |
| 顯示器 × 1 | 電子 | 1799.00 | 1799.00 × 0.7 = 1259.300 |
| 啤酒 × 12 | 酒類 | 300.00 | 300.00(無促銷) |
| 麵包 × 5 | 食品 | 45.00 | 45.00(無促銷) |

subtotal = 1679.300 + 1259.300 + 300.00 + 45.00 = **3283.600**(不四捨五入)
3283.600 ≥ 門檻 1000 且未過期 → 3283.600 − 200 = **3083.60**

**case-2**——蔬菜 3 × 5.98 = 17.94、餐巾紙 8 × 3.20 = 25.60,subtotal = **43.54** < 門檻 1000 → 券不生效,total = **43.54**。

**case-3**——iphone 5999.00,交易日 2016-04-01 > 到期日 2016-03-02 → `expired`,total = **5999.00**。

**case-4 / case-5**——鍵盤 2 × 349.00 = 698.00。case-4 促銷打在「日用品」但品項是「電子」(品類不符);case-5 促銷日期 2015-12-25 ≠ 交易日 2015-11-11(日期不符)。兩者促銷都不生效,total 皆 **698.00**。

**case-6(每次只能用一張)**——筆電 6999.00 × 0.7 = **4899.300**;傳了兩張券(各折 500、200),但題目明定每次結算只能用一張,只套用第一張 → 4899.300 − 500 = **4399.30**,第二張忽略不計。

**case-7**——咖啡杯 2 × 25.00 = 50.00,促銷未指定 date / category(全適用)且帶 `effect: 50` → 50.00 + 50 = **100.00**。

**case-8(精度分辨案例)**——餅乾 3 × 0.10 = 0.30、蛋糕 1 × 0.125 = 0.125,subtotal = **0.425**(達門檻 0.40);0.425 − 0.10 = 0.325,`ROUND_HALF_UP` 到 2 位 = **0.33**。
分辨點在 subtotal 本身:float 算 `0.1 × 3 + 0.125` 得 `0.42500000000000004` 而非精確 0.425,且 `0.425` 的 double 表示略小於真值,使 `round(0.425, 2)` 得 **0.42** 而非 Decimal 的 **0.43**;全程 `Decimal` 才能保證小計與四捨五入都貼合十進位真值。

---

## 三、錯誤處理實測

| 輸入 | 狀態碼 | 結果 |
| --- | --- | --- |
| `date` = `"2015/13/45"`(不合法日期) | **400** | `{"detail":"無效的日期格式: 2015/13/45"}`(領域錯誤) |
| `qty` = 0 | **422** | Pydantic 驗證 `Input should be greater than 0` |
| `items` = `[]` | **422** | Pydantic 驗證 `List should have at least 1 item` |
| `date` = `"2015.11.11"` / `"2015/11/11"` | **200** | 三種分隔格式皆接受 |

400 與 422 的分工依規格:日期格式與金額數值屬領域錯誤(400),結構性驗證交給 Pydantic(422)。

---

## 四、各功能實作方式

### 1. 領域模型 `src/cart/domain/models.py`

不可變的 `dataclass(frozen=True)` 資料物件,只存放資料、不讀檔、不認識外層:

| 物件 | 內容 | 實作重點 |
| --- | --- | --- |
| `LineItem` | 品名、品類、數量、單價 | 品類為**自由字串**,不由固定目錄約束 |
| `Promotion` | 日期、品類、rate、effect | `date` / `category` 可為 `None`,代表不設限 |
| `Coupon` | 到期日、門檻、折額、effect | 四者皆可為 `None`;`discount` 為正數,套用時才轉負 |
| `CaseInput` | 交易日、品項、促銷清單、折價券清單 | 折價券是**清單**,但每次結算**只評估第一張**(題目規則) |
| `CalculationResult` / `CouponResult` | 計算結果 | `reason` 只有 `expired` / `below_min_spend` / `null` |

金額一律 `Decimal`、日期一律 `datetime.date`,兩者皆由請求帶入,符合「日期由參數傳入、不自行呼叫 `date.today()`」的規範。

### 2. 領域錯誤 `src/cart/domain/errors.py`

`CalculationError` 為共同基底,`main.py` 統一攔截轉成 HTTP 400:

| 錯誤 | 意義 | 觸發位置 |
| --- | --- | --- |
| `DateFormatError` | 日期格式不支援或不可能(如 2/30) | `services/date_parsing.py` |
| `InvalidDecimalError` | 金額欄位不是數值 | `services/date_parsing.py` |

### 3. 日期解析 `src/cart/services/date_parsing.py`

`parse_date` 接受 `YYYY-MM-DD` / `YYYY.MM.DD` / `YYYY/MM/DD` 三種分隔格式,其他格式或不可能日期(2/13、2/30)拋 `DateFormatError`;`parse_decimal` 把字串轉 `Decimal` 並拒絕非數值。兩者皆為純函式,不讀系統時間。

### 4. 計算引擎 `src/cart/services/calculator.py`

全部是**純函式**,相同輸入必得相同輸出,不讀檔、不讀系統時間。函式命名為「動詞 + 受詞」,上層只依序呼叫下層:

```
calculate(input)                                   ← 唯一對外入口
 ├─ calculate_subtotal(items, promos, date)
 │    └─ calculate_line_total(item, promos, date)
 │         ├─ collect_applicable_promotions(promos, category, date)
 │         │    └─ is_promotion_applicable(promo, category, date)
 │         ├─ calculate_rate_product(applicable)      ← Π(rate)
 │         └─ calculate_effect_sum(applicable)        ← Σ(effect)
 ├─ apply_coupons(coupons, subtotal, date)
 │    └─ apply_coupon(coupon, index, subtotal, date)
 │         ├─ is_coupon_expired(coupon, date)         ← 過期優先
 │         └─ is_coupon_below_min_spend(coupon, subtotal)
 │    └─ resolve_coupon_effect(coupon)                ← effect > -discount > 0
 └─ round_to_two_places(subtotal + coupon_effect_sum)
```

對應的業務規則(規則編號見 [requirements.md](requirements.md)):

1. **促銷生效**(規則 1):`is_promotion_applicable` 要求「日期未指定或相符」且「品類未指定或相符」。
2. **促銷計算**(規則 2):`lineTotal = qty × unitPrice × Π(rate) + Σ(effect)`,多張生效促銷的 rate 是**連乘**。
3. **券過期**(規則 3):交易日 **>** 到期日才算過期,到期日當天有效。
4. **券門檻**(規則 4):小計 **<** minSpend 才不生效,含等號;門檻一律跟**未四捨五入的 subtotal** 比。
5. **過期優先於門檻**(規則 5):`apply_coupon` 先判過期,兩者皆成立時 reason 為 `expired`。
6. **券取值**(規則 6):`effect` > `-discount` > `0`。
7. **四捨五入**(規則 8):只在最後 `total` 做,`ROUND_HALF_UP` 到小數 2 位;`subtotal` 忠實呈現計算過程(如 `3283.600`、`4899.300`)。

### 5. 計算 API `src/cart/api/calculate.py`、`api/schemas.py`

維持「接收 → 呼叫 service → 回傳」的薄度:

- `POST /api/calculate`:收 `{date, items, promotions, coupons}`,回 `{subtotal, total, couponResults}`。
- schema 層用 Pydantic,欄名直接用 JSON 的 camelCase(`unitPrice` / `expiryDate` / `minSpend`),金額一律字串、`qty` 限定正整數、`items` 不得為空。
- `build_case_input()` 組裝領域物件,促銷與折價券的空欄位保留 `None`;計算全部在 `calculator.py`,API 層不放任何業務判斷。

### 6. 應用進入點 `src/cart/main.py`

只註冊 `/api/calculate` 一個 router,並註冊 `CalculationError` 的例外處理器轉成 400。無狀態:不存資料、不讀檔、不碰系統時間。

---

## 五、自動化測試

共 53 項測試,全數通過(明細見 [test-checklist.md](test-checklist.md)):

| 測試檔 | 項數 | 涵蓋內容 |
| --- | --- | --- |
| `tests/unit/test_date_parsing.py` | 8 | 三種日期格式、錯誤格式與不可能日期、Decimal 精確值 |
| `tests/unit/test_calculator.py` | 13 | rate 套用 / 連乘、effect 加減、品類與日期不匹配、小計不四捨五入、Case A 端到端、精度案例 |
| `tests/unit/test_coupon.py` | 14 | discount 轉負、effect 優先、到期日當天有效、門檻含等號、過期優先於門檻、只評估第一張券 |
| `tests/api/test_calculate_api.py` | 18 | 逐一讀 8 組 fixture 打 API 比對完整回應;三日期格式;400 / 422 錯誤 |

其中直接驗證題目規則的關鍵測試:

- `test_calculator_precision_avoids_float_error`:`0.1×3 + 0.125 = 0.425` 精確無誤;float 會算成 `0.42500000000000004`,`round(0.425, 2)` 更因 double 表示偏小而給 **0.42**
- `test_apply_coupon_marks_expired_before_threshold`:同時過期且未達門檻時,reason 必須是 `expired`
- `test_line_total_multiplies_multiple_matching_rates`:兩張生效促銷的 rate 是連乘(`0.7 × 0.8`),不是相加
- `test_calculate_case_a_end_to_end`:基準案例的 `3083.60`,任何一條規則走偏都會變號

---

## 六、關於 DB 的評估

未導入資料庫,理由記錄於 [decisions.md](decisions.md) D1 / D6:

- 題目把促銷與折價券當成**每次請求一起傳進來的輸入參數**,而非被系統查詢的常駐實體;系統無狀態,從不問「某日期當時生效的是哪幾檔促銷」。
- 依賴白名單只有 `fastapi`、`uvicorn`、`pytest`、`httpx`;為幾個欄位付出 schema 定義與測試隔離的成本屬過度設計。
- 現在連持久層都移除了(D6):`domain` 與 `services` 是純函式、不碰檔案,將來需要持久化時,接點在 API 層的組裝方式,計算引擎一行都不用改。

---

## 七、已知限制

| 項目 | 狀態 | 說明 |
| --- | --- | --- |
| 無前端 | 不做(範圍外) | 題目核心是結算計算;前端屬追加項,本規格不涵蓋 |
| 多張券的門檻判斷基準 | 依規格定案 | 每張券都對**同一個原始 subtotal** 判斷,而非逐張重算;若改規格需先補測試再改 |
| 無持久層、無登入 | 不做(範圍外) | 見 D1 / D3 / D6;系統無狀態,每次請求獨立 |

---

## 八、重現方式

```bash
# 1. 建立並啟用虛擬環境(已存在可略過)
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
# source .venv/bin/activate         # macOS / Linux

# 2. 安裝依賴
pip install -r requirements-dev.txt

# 3. 跑全套測試
pytest                              # 預期 53 passed

# 4. 啟動伺服器,跑 8 組驗收案例
uvicorn cart.main:app --port 3000 --app-dir src
curl -X POST http://localhost:3000/api/calculate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/case-1.json
# 預期輸出:{"subtotal":"3283.600","total":"3083.60","couponResults":[{"index":0,"applied":true,"reason":null}]}
```
