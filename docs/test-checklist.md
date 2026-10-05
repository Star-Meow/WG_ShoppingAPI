# 測試清單

本檔案回答「**測了什麼、還缺什麼測試**」。需求規則見 [requirements.md](requirements.md),實作進度見 [feature-checklist.md](feature-checklist.md),各功能的實作方式說明見 [acceptance-report.md](acceptance-report.md)。

## 一、總覽

| 項目 | 數值 |
| --- | --- |
| 測試總數 | **74**(全數通過) |
| 測試檔數 | 9 |
| 執行方式 | `pytest`(需在 `.venv` 內) |
| 執行時間 | 約 3 秒 |
| 測試分層 | unit(60)/ api(12)/ acceptance(2) |

> HTTP 測試用 FastAPI 的 `TestClient`(依賴 `httpx`),不啟動真的伺服器。

## 二、測試檔清單

### 單元測試 `tests/unit/`

| 檔案 | 項數 | 涵蓋內容 | 對應需求規則 |
| --- | --- | --- | --- |
| `test_catalog.py` | 4 | 目錄 4 品類 18 項、各品類數量 5/6/4/3、價格皆為 `Decimal` | 需求五(商品目錄) |
| `test_checkout.py` | 22 | 促銷生效/不生效/跨品類、券過期/到期日當天/門檻上下緣、門檻以促銷後金額判斷、四捨五入、Case A/B 完整結算 | 規則 1、2、3、5 |
| `test_checkout_result.py` | 7 | `build_checkout_result` 的原價合計、促銷折抵、券折抵明細、券三狀態、已套用的促銷與券名稱 | 規則 1、3 |
| `test_parser.py` | 18 | 日期/促銷/明細/優惠券解析;錯誤案例:未知商品、單價不一致、數量為 0、缺結算日、空車、多張券 | 需求四(案例格式)、規則 4 |
| `test_products_builder.py` | 4 | `build_category_groups()` 的 4 組、18 項、價格字串、品類順序(不使用 `TestClient`) | — |
| `test_cli.py` | 5 | 子程序執行 `python -m cart.cli`:印金額、多檔、用法提示、缺檔、格式錯誤 | — |

### API 測試 `tests/api/`

| 檔案 | 項數 | 涵蓋內容 | 對應需求規則 |
| --- | --- | --- | --- |
| `test_products_api.py` | 4 | `GET /api/products` 與 `GET /` 經 `TestClient` | — |
| `test_checkout_api.py` | 8 | `GET /api/coupons`;`POST /api/checkout`:無券原價、促銷日期生效、券折抵、過期券、未達門檻、未知商品 400、未知券 400;並驗證 `runtime.json` 日期覆寫會讓促銷自動生效 | 規則 1、3、6 |

### 驗收測試 `tests/acceptance/`

| 檔案 | 項數 | 涵蓋內容 |
| --- | --- | --- |
| `test_cases.py` | 2 | 讀真實 fixture 檔 → 解析 → 結算 → 比對 `3083.60` / `43.54` |

### 測試資料 `tests/fixtures/`

| 檔案 | 內容 | 預期 |
| --- | --- | --- |
| `case_a.txt` | 電子品類 0.7 折促銷 + 門檻 1000 折 200 的券 | `3083.60` |
| `case_b.txt` | 無促銷、無券 | `43.54` |

案例的完整輸入與計算過程見 [requirements.md](requirements.md) 第四節。

## 三、關鍵回歸測試

這幾項直接對應最容易出錯的規則,改動結算邏輯後務必確認它們仍然通過:

| 測試 | 保護的規則 | 情境 |
| --- | --- | --- |
| `test_coupon_threshold_is_judged_after_promotion_discount` | 規則 3 | 原價過門檻但促銷後未過,券**不得**折抵 |
| `test_checkout_rounds_half_up_to_two_places` | 規則 5 | `29.985 → 29.99`(`ROUND_HALF_UP`) |
| `test_promotion_is_active_only_on_its_date` | 規則 1 | 促銷前一天與後一天皆不生效 |

## 四、測試覆蓋的缺口

| 缺口 | 影響 | 建議 |
| --- | --- | --- |
| 後台 API 與 `web/admin.html` | 無測試 | 兩者都還是空殼,實作時才需要補 |
| `save_current_date(None)` 清除覆寫值的行為 | 目前只在 `test_checkout_api.py` 的 fixture 清理中呼叫,**沒有獨立斷言** | 開日期覆寫 endpoint 時,補一組「設定 / 覆寫 / 清除」三態測試 |
| 前端 JS | 無自動化測試 | 專案規範禁止 npm / build,目前靠瀏覽器實測驗證(見 [acceptance-report.md](acceptance-report.md) 第五節) |
| 多券擇優 | 無測試 | 待業務定案後才會有 |

## 五、怎麼跑

```bash
# 全套
pytest                                  # 預期 74 passed

# 單一檔
pytest tests/unit/test_checkout.py

# 依關鍵字篩選
pytest -k coupon

# 驗收案例的 CLI 輸出(不經 pytest,直接看結果)
PYTHONPATH=src python -m cart.cli tests/fixtures/case_a.txt tests/fixtures/case_b.txt
# 預期輸出:
# 3083.60
# 43.54
```