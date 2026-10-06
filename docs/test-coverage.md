# 測試涵蓋範圍清單

本檔案回答:「**測試程式涵蓋了哪些情境?想改數值時要怎麼改?**」。

測試的執行方式與缺口分析見 [test-checklist.md](test-checklist.md),業務規則見 [requirements.md](requirements.md)。

## 一、測試怎麼跑(一條指令)

```bash
pytest
```

- 測試框架:pytest,`pyproject.toml` 已設 `pythonpath = ["src"]` 與 `testpaths = ["tests"]`,所以在專案根目錄直接執行即可
- HTTP 測試用 FastAPI 的 `TestClient`,在行程內打 `/api/calculate`,**不啟動真的伺服器**
- 目前 62 項測試,執行時間約 0.5 秒

## 二、情境涵蓋矩陣

「✅」代表該情境有對應的測試;欄位意義見下方說明。

### 折扣(促銷 promotions)

| 情境 | fixture | 單元測試 | 說明 |
| --- | --- | --- | --- |
| 無促銷,取原價 | case-2、case-3、case-8 | ✅ | `qty × unitPrice` |
| 單一 rate 乘法折扣 | case-1、case-4~6、case-10 | ✅ | 如 `0.7` 打折 |
| **多個 rate 連乘** | case-10 | ✅ | `0.8 × 0.9 = 0.72`,**不是相加** |
| rate + effect 同時存在 | case-12 | ✅ | `qty × price × rate + effect` |
| effect 正數(加價/服務費) | case-7 | ✅ | 如 `+50` |
| effect 負數(折抵) | case-11、case-12 | ✅ | 如 `-10` |
| 促銷限定品類且符合 | case-1、case-6、case-10 | ✅ | `category` 相符才生效 |
| 促銷限定品類但**不符合** | case-4 | ✅ | 品類不符 → 不生效 |
| 促銷限定日期且符合 | case-1、case-6 | ✅ | `date` 相符才生效 |
| 促銷限定日期但**不符合** | case-5 | ✅ | 日期不符 → 不生效 |
| **日期符但品類不符** | case-4 | ✅ | 短路在品類判斷(見 `test_line_total_ignores_promotion_when_date_matches_but_category_does_not`) |
| **日期與品類皆不符** | — | ✅ | 任一條件不符即不生效 |
| 促銷不指定日期(全天生效) | case-7、case-12 | ✅ | `date` 省略代表不設限 |
| 促銷不指定品類(全品類生效) | case-7、case-10、case-12 | ✅ | `category` 省略代表不設限 |

### 折價券(coupons)

| 情境 | fixture | 單元測試 | 說明 |
| --- | --- | --- | --- |
| 無折價券 | case-4~8、case-10 無券 | ✅ | `couponResults` 為空陣列 |
| 單張券生效 | case-1、case-8 | ✅ | 達門檻且未過期 |
| **只生效一張(忽略後續券)** | case-6、case-10、case-12 | ✅ | 題目明定「每次結算只能用一張」,第二張以後無論有效與否都忽略 |
| 券未達 minSpend | case-2 | ✅ | reason = `below_min_spend` |
| 券已過期 | case-3 | ✅ | reason = `expired` |
| **過期優先於門檻判斷** | case-3 | ✅ | 同時過期且未達門檻 → 回報 `expired` |
| 到期日**當天**有效 | case-11 | ✅ | `expiryDate` 等於交易日仍可用 |
| minSpend **含等號** | case-11 | ✅ | 小計等於門檻時券生效 |
| minSpend 對**未四捨五入**小計判斷 | case-8 | ✅ | 用 `0.425` 而非 `0.43` 比對 |
| **discount 為正數自動轉負** | case-1、case-6 | ✅ | `discount: 200` → `-200` |
| **effect 優先於 discount** | case-11 | ✅ | 兩欄位並存時取 `effect`(API 層以真實 JSON 驗證) |
| 券 effect 為負值折抵 | case-11 | ✅ | `effect: -0.30` |
| 第一張未達門檻時,第二張不遞補 | — | ✅ | `test_apply_coupons_ignores_later_coupons_even_when_first_is_skipped` |
| 券不指定 expiryDate / minSpend | — | ✅ | 永不過期 / 永遠達標 |

### 日期

| 情境 | fixture | 單元測試 | 說明 |
| --- | --- | --- | --- |
| `YYYY-MM-DD` 格式 | case-1~8、case-10、case-11 | ✅ | 標準格式 |
| **`YYYY.MM.DD` 格式** | — | ✅ | `parse_date` 參數化測試 |
| **`YYYY/MM/DD` 格式** | case-12 | ✅ | fixture 與 API 層皆有 |
| **同一案例三格式結果一致** | — | ✅ | `test_calculate_runs_same_case_with_all_three_date_formats` |
| 不支援的日期格式 → 400 | — | ✅ | 如 `2015年11月11日` |
| 不可能的日期 → 400 | — | ✅ | 如 `2015-02-30`、`2015-13-01` |

### 金額精度與邊界

| 情境 | fixture | 單元測試 | 說明 |
| --- | --- | --- | --- |
| **float 精度誤差** | case-8 | ✅ | `0.1×3 + 0.125 = 0.425`,float 會算成 `0.42500000000000004` |
| **ROUND_HALF_UP 四捨五入** | case-8 | ✅ | `0.425 − 0.10 = 0.325` → `0.33`;float `round()` 給 `0.32` |
| subtotal 不四捨五入 | case-1、case-8、case-10 | ✅ | 忠實保留 `3283.600`、`0.425`、`7199.2800` |
| 高額金額 | case-3、case-10 | ✅ | `9999`、`5999` 等 |
| 小額金額 | case-8、case-11 | ✅ | `0.10`、`0.125`、`0.99` |
| 非數值單價 → 400 | — | ✅ | `unitPrice: "免費"` |

### 輸入驗證

| 情境 | 單元測試 | 說明 |
| --- | --- | --- |
| qty 非正整數 → 422 | ✅ | Pydantic 層 `Field(gt=0)` |
| items 為空 → 422 | ✅ | Pydantic 層 `min_length=1` |
| promotions / coupons 可省略 | ✅ | 預設為空陣列 |

## 三、Fixture 案例一览

`tests/fixtures/case-N.json` 是純請求 payload,API 測試逐一讀取並比對完整回應。

| # | 情境 | 預期 subtotal | 預期 total | couponResults |
| --- | --- | --- | --- | --- |
| 1 | 基準案例(原 Case A):電子 0.7 折 + 券折 200 | `3283.600` | `3083.60` | `[{0, true, null}]` |
| 2 | 券未達 minSpend(原 Case B) | `43.54` | `43.54` | `[{0, false, "below_min_spend"}]` |
| 3 | 券已過期 | `5999.00` | `5999.00` | `[{0, false, "expired"}]` |
| 4 | 促銷品類不匹配 | `698.00` | `698.00` | `[]` |
| 5 | 促銷日期不匹配 | `698.00` | `698.00` | `[]` |
| 6 | 只用第一張券(每次只能用一張) | `4899.300` | `4399.30` | `[{0, true, null}]` |
| 7 | effect 正數(服務費 +50) | `100.00` | `100.00` | `[]` |
| 8 | 浮點精度 + 四捨五入 | `0.425` | `0.33` | `[{0, true, null}]` |
| 10 | 多 rate 連乘(0.8 × 0.9)+ 高額,第二張券被忽略 | `7199.2800` | `6699.28` | `[{0, true, null}]` |
| 11 | 券 effect 優先於 discount + 到期日當天 + 門檻含等號 | `0.99` | `0.69` | `[{0, true, null}]` |
| 12 | 斜線日期 + 自由品類 + 促銷連乘折抵 + 只評估第一張券 | `80.3500` | `60.35` | `[{0, true, null}]` |

> case-9 刻意略過,保留編號空隙以便未來插入新案例。

## 四、想改單價或額度,怎麼改?

所有案例的數值都是**純 JSON**,直接編輯 fixture 檔即可,不用碰 Python。三步驟:

### 步驟 1:改 fixture

例如想把 case-1 的 ipad 單價從 `2399.00` 改成 `2999.00`:

```json
// tests/fixtures/case-1.json
{"name": "ipad", "category": "電子", "qty": 1, "unitPrice": "2999.00"}
```

可改的欄位:

| 想改的東西 | 改哪裡 | 範例 |
| --- | --- | --- |
| 品項單價 | `items[].unitPrice` | `"2399.00"` → `"2999.00"` |
| 品項數量 | `items[].qty` | `1` → `3` |
| 品項品類 | `items[].category` | `"電子"` → `"生活用品類"` |
| 促銷折扣率 | `promotions[].rate` | `"0.7"` → `"0.5"` |
| 促銷折抵額 | `promotions[].effect` | `"-50"` → `"-100"` |
| 券門檻 | `coupons[].minSpend` | `"1000"` → `"500"` |
| 券折扣額 | `coupons[].discount` | `"200"` → `"300"` |
| 券到期日 | `coupons[].expiryDate` | `"2016-03-02"` → `"2017-01-01"` |
| 交易日 | `date`(最外層) | `"2015-11-11"` → `"2015/11/11"` |

### 步驟 2:重算期望值

```bash
python tools/recompute_expected.py
```

會印出所有案例的最新期望值(Python 字典格式),直接貼回 `tests/api/test_calculate_api.py` 的 `CASE_EXPECTATIONS`。

> **注意**:這支工具只是「把現況算出來」。貼回去之前請先判斷新數字**符不符合預期**——測試的價值在於斷言「已知正確的答案」,不是「程式現在的輸出」。若改了數值後結果變了,先確認是規格本該如此,還是程式有 bug。

### 步驟 3:跑測試

```bash
pytest
```

### 替代方案:不想改期望表

如果只是想**臨時實驗**、不動到測試,可以複製一份新檔案再跑單一案例:

```bash
cp tests/fixtures/case-1.json tests/fixtures/case-99.json
# 編輯 case-99.json...
pytest tests/api/test_calculate_api.py -k case-99    # 需先在 CASE_EXPECTATIONS 補該檔期望值
```

或啟動伺服器用 curl:

```bash
uvicorn cart.main:app --port 3000 --app-dir src
curl -X POST http://localhost:3000/api/calculate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/case-1.json
```

## 五、新增情境的步驟

1. 建立 `tests/fixtures/case-N.json`(避開已用過的編號)
2. 執行 `python tools/recompute_expected.py`,取得新檔的期望值
3. **人工確認**期望值正確後,貼入 `tests/api/test_calculate_api.py` 的 `CASE_EXPECTATIONS`
4. 若是新規則(不是既有組合),在 `tests/unit/` 補單元測試
5. `pytest` 全綠
6. 更新本檔案的情境矩陣與 [test-checklist.md](test-checklist.md)

## 六、覆蓋缺口(刻意不測或尚未測)

| 缺口 | 原因 |
| --- | --- |
| 效能/壓力測試 | MVP 階段不需要;計算為純函式,無 I/O 瓶頸 |
| 多張券的門檻互動 | 已改為單券規則(D7),此互動不存在,無需測試 |
| 前端 UI | 系統無前端,不適用 |
| 資料庫 / 持久層 | 系統無狀態,不適用 |
