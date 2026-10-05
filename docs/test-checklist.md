# 測試清單

本檔案回答「**測了什麼、還缺什麼測試**」。需求規則見 [requirements.md](requirements.md),實作進度見 [feature-checklist.md](feature-checklist.md)。

## 一、總覽

| 項目 | 數值 |
| --- | --- |
| 測試總數 | **53**(全數通過) |
| 測試檔數 | 4 |
| 執行方式 | `pytest`(需在 `.venv` 內) |
| 執行時間 | 約 0.6 秒 |
| 測試分層 | unit(35)/ api(18) |

> HTTP 測試用 FastAPI 的 `TestClient`(依賴 `httpx`),不啟動真的伺服器。

## 二、測試檔清單

### 單元測試 `tests/unit/`

| 檔案 | 項數 | 涵蓋內容 | 對應需求規則 |
| --- | --- | --- | --- |
| `test_date_parsing.py` | 8 | 三種日期分隔格式正確解析;不支援格式與不可能日期(2/13、2/30)拒絕;Decimal 精確值;非數值拒絕 | 規則 9、API 日期格式 |
| `test_calculator.py` | 13 | 逐項:無促銷原價、rate 套用、品類不匹配、日期不匹配、多 rate 連乘、rate + effect 並存、無日期促銷任意天生效;小計不四捨五入;Case A 端到端;`ROUND_HALF_UP`;精度案例 `0.425 → 0.43`(float `round` 給 0.42) | 規則 1、2、7、8 |
| `test_coupon.py` | 14 | discount 轉負;effect 優先於 discount;effect 正數(服務費);無欄位為 0;到期日當天有效、隔天失效;無到期日永不失效;門檻含等號;門檻對未四捨五入小計判斷;過期優先於門檻;多券依序套用;混用券部分生效;空清單 | 規則 3、4、5、6、7 |

### API 測試 `tests/api/`

| 檔案 | 項數 | 涵蓋內容 | 對應需求規則 |
| --- | --- | --- | --- |
| `test_calculate_api.py` | 18 | 逐一讀 8 組 `case-N.json` 打 API 比對完整回應;三日期格式都接受;日期格式錯 400;qty 非 positive 422;空車 422;非數值單價 400;promotions / coupons 預設空陣列 | 全部規則 |

### 測試資料 `tests/fixtures/`

| 檔案 | 情境 | 預期 total |
| --- | --- | --- |
| `case-1.json` | 基準案例(原 Case A) | `3083.60` |
| `case-2.json` | 折價券未達 minSpend(原 Case B) | `43.54` |
| `case-3.json` | 折價券已過期 | `5999.00` |
| `case-4.json` | 促銷品類不匹配 | `698.00` |
| `case-5.json` | 促銷日期不匹配 | `698.00` |
| `case-6.json` | 多張折價券疊加 | `4199.30` |
| `case-7.json` | effect 為正數(服務費) | `100.00` |
| `case-8.json` | 浮點數精度 + 四捨五入 | `0.33` |

案例的完整輸入與計算過程見 [requirements.md](requirements.md) 第四節。

## 三、關鍵回歸測試

這幾項直接對應最容易出錯的規則,改動計算邏輯後務必確認它們仍然通過:

| 測試 | 保護的規則 | 情境 |
| --- | --- | --- |
| `test_calculator_precision_avoids_float_error` | 規則 8、9 | `0.1×3 + 0.125 = 0.425` 精確無誤;float 算成 `0.42500000000000004`,`round(0.425, 2)` 更給 `0.42` 而非 `ROUND_HALF_UP` 的 `0.43` |
| `test_apply_coupon_marks_expired_before_threshold` | 規則 5 | 同時過期且未達門檻時,reason 必須是 `expired` 而非 `below_min_spend` |
| `test_line_total_multiplies_multiple_matching_rates` | 規則 2 | 兩張生效促銷的 rate 是**連乘**(`0.7 × 0.8`),不是相加 |
| `test_calculate_case_a_end_to_end` | 規則 1、2、7 | 基準案例的 `3083.60`,任何一條規則走偏都會變號 |
| `test_min_spend_includes_the_threshold` | 規則 4 | 小計**等於**門檻時券必須生效 |

## 四、測試覆蓋的缺口

| 缺口 | 影響 | 建議 |
| --- | --- | --- |
| 促銷同時指定 date 且 category 的「日期符但品類不符」組合 | 有各自單獨覆蓋(date-only / category-only),但未測兩條件同時存在時的短路行為 | 補一項 `date` 相符 + `category` 不符的 line total 斷言 |
| `effect` 與 `discount` 同時存在的折價券 | 規則 6 的優先序只在單元測試以 `resolve_coupon_effect` 覆蓋,未在 API 層以真實 JSON 跑過 | 補一組 fixture 兩欄位並存,斷言取 `effect` |
| 多張券中「第 1 張生效使小計跌破第 2 張門檻」的相關性 | 目前多張券的門檻都對**同一個 subtotal** 判斷(規格明定),未測此互動是否被誤解為逐張重算 | 若未來改規格,需先補此測試再改 |

## 五、怎麼跑

```bash
# 全套
pytest                                  # 預期 53 passed

# 單一檔
pytest tests/unit/test_calculator.py

# 依關鍵字篩選
pytest -k coupon

# 啟動伺服器跑案例(對照 requirements.md 的預期值)
uvicorn cart.main:app --port 3000 --app-dir src
curl -X POST http://localhost:3000/api/calculate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/case-1.json
# 預期輸出:{"subtotal":"3283.600","total":"3083.60","couponResults":[{"index":0,"applied":true,"reason":null}]}
```
