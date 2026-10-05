# P0 結算引擎驗收報告

**範圍**:題目核心「給定購物車與促銷資訊,算出結算金額」,即 P0 的結算引擎與 CLI 介面。
**驗收日期**:2026-10-05
**測試環境**:Python 3.10.11、pytest 9.1.1、Windows + Git Bash,虛擬環境 `.venv`

---

## 一、驗收結論

| 項目 | 結果 |
| --- | --- |
| `pytest` 全套測試 | **59 passed**(0 failed) |
| Case A(`tests/fixtures/case_a.txt`) | **3083.60** ✅ 與題目預期一致 |
| Case B(`tests/fixtures/case_b.txt`) | **43.54** ✅ 與題目預期一致 |
| CLI 介面 `python -m cart.cli` | 兩案各印出一行金額,exit code 0 |

題目指定的文字驗收案例已可透過 CLI 實際跑出預期金額,計算引擎、解析器、CLI 三層全部有單元測試覆蓋。

---

## 二、Case A / Case B 計算過程(引擎實際行為)

### Case A:電子品類 0.7 折促銷 + 門檻 1000 折 200 的優惠券

| 明細 | 品類 | 原價小計 | 促銷後 |
| --- | --- | --- | --- |
| ipad × 1 | 電子 | 2399.00 | 2399.00 × 0.7 = 1679.30 |
| 顯示器 × 1 | 電子 | 1799.00 | 1799.00 × 0.7 = 1259.30 |
| 啤酒 × 12 | 酒類 | 300.00 | 300.00(無促銷) |
| 麵包 × 5 | 食品 | 45.00 | 45.00(無促銷) |

1. 促銷只套用電子品類(規則 1):電子合計 4198.00 × 0.7 = 2938.60
2. 促銷後金額 = 2938.60 + 300.00 + 45.00 = **3283.60**
3. 優惠券門檻以促銷後金額判斷(規則 3):3283.60 ≥ 1000,成立
4. 3283.60 − 200 = **3083.60**(四捨五入到小數 2 位,規則 5)

### Case B:無促銷、無優惠券

- 蔬菜 3 × 5.98 = 17.94、餐巾紙 8 × 3.20 = 25.60
- 無促銷套用、無優惠券:17.94 + 25.60 = **43.54**

---

## 三、各功能實作方式與效果

### 1. 領域模型 `src/cart/domain/models.py`

不可變的 `dataclass(frozen=True)` 資料物件,只存放資料、不讀檔、不認識外層:

| 物件 | 內容 | 實作重點 |
| --- | --- | --- |
| `CartItem` | 品名、品類、單價、數量 | 品類由目錄查得,不由文字輸入決定 |
| `Promotion` | 促銷日期、折扣、品類 | 折扣為 `Decimal`(0.7 = 打 7 折) |
| `Coupon` | 到期日、門檻、折額 | 三者皆為外部傳入 |
| `Cart` | 項目清單 | 唯一行為:`subtotal()` 算未折扣小計 |
| `CheckoutInput` | 購物車、促銷清單、結算日、優惠券 | **「每次只能用一張優惠券」由型別 `coupon: Coupon \| None` 直接強制**,不是靠執行期檢查 |

金額一律 `Decimal`、日期一律 `datetime.date`,兩者皆由外部傳入,符合「日期由參數傳入、不自行呼叫 `date.today()`」的規範。

### 2. 領域錯誤 `src/cart/domain/errors.py`

`CheckoutError` 為共同基底,API 層可對應 HTTP 狀態碼、CLI 層統一捕捉印出:

| 錯誤 | 意義 | 觸發位置 |
| --- | --- | --- |
| `ParseError` | 案例文字格式不符(欄位缺失、段落數不對、多張券) | `cli/parser.py` |
| `UnknownProductError` | 購物車出現目錄以外的商品 | `cli/parser.py` |
| `PriceMismatchError` | 文字單價與目錄不一致(價格必須由目錄重取) | `cli/parser.py` |
| `CouponNotApplicableError` | 券過期或未達門檻 | 供 API 層後續使用 |

### 3. 結算服務 `src/cart/services/checkout.py`

全部是**純函式**,相同輸入必得相同輸出,不讀檔、不讀系統時間。函式命名為「動詞 + 受詞」,上層只依序呼叫下層:

```
calculate_checkout(input)                      ← 唯一對外入口
 ├─ calculate_promoted_subtotal(cart, promos, date)
 │    └─ calculate_promoted_item_subtotal(item, promos, date)
 │         ├─ calculate_item_subtotal(item)
 │         └─ find_active_promotion(promos, category, date)
 │                └─ is_promotion_active(promo, date)
 ├─ calculate_coupon_discount(coupon, promoted_subtotal, date)
 │    └─ is_coupon_applicable(coupon, promoted_subtotal, date)
 │         ├─ is_coupon_expired(coupon, date)
 │         └─ is_coupon_threshold_met(coupon, amount)
 └─ round_to_two_places(promoted_subtotal - coupon_discount)
```

對應的業務規則:

1. **促銷折扣**:`is_promotion_active` 只有「結算日 == 促銷日期」才生效;`find_active_promotion` 再比對品類,只套用在對應品類。
2. **優惠券有效期**:`is_coupon_expired` 採「結算日 > 到期日才算過期」,到期日當天仍有效。
3. **優惠券門檻**:`calculate_promoted_subtotal` 先算出促銷後金額,`is_coupon_threshold_met` 才以此金額判斷(含門檻值本身)。
4. **單張限制**:由 `CheckoutInput` 型別強制,解析器遇到兩張券時拋 `ParseError`。
5. **金額**:`round_to_two_places` 用 `ROUND_HALF_UP` 四捨五入到小數 2 位(測試驗證 `100.005 → 100.01`、`100.004 → 100.00`)。

### 4. 案例文字解析 `src/cart/cli/parser.py`

只做「字串 → 資料物件」,不算金額。`parse_case_text()` 把整份文字切成三個段落(促銷 / 購物車 / 結算日與優惠券),再逐行交給 `parse_promotion_line`、`parse_cart_line`、`parse_coupon_line`、`parse_date`。

**價格信任來源(D4)**:明細行的品類與單價一律由 `CATALOG` 經 `find_product_by_name()` 查得;案例文字所載的單價只做一致性檢查,不一致時拋 `PriceMismatchError`。這讓「攻擊者改掉輸入文字的單價就能低價結帳」的路徑被擋住。

格式錯誤都會明確報出,而非靜默吞掉:日期格式不對、品類不存在、數量非正整數、商品不在目錄、段落數不足、!物車為空、多張優惠券等。

### 5. CLI 入口 `src/cart/cli/__main__.py`

```bash
PYTHONPATH=src python -m cart.cli tests/fixtures/case_a.txt tests/fixtures/case_b.txt
```

- 每個案例檔印出一行金額(case_a → `3083.60`、case_b → `43.54`)
- 無參數時印用法、exit code 2
- 讀檔失敗或解析/結算錯誤印到 stderr、exit code 1;其餘案例仍會繼續處理
- 本模組是外層介面(與 `main.py` 同層),只負責讀檔與印出,解析與計算都在可單測的模組內

---

## 四、自動化測試清單

共 59 項測試,全數通過:

| 測試檔 | 項數 | 涵蓋內容 |
| --- | --- | --- |
| `tests/unit/test_checkout.py` | 22 | 促銷生效/不生效/跨品類、券過期/到期日當天/門檻上下緣、門檻以促銷後金額判斷、四捨五入、Case A/B 完整結算 |
| `tests/unit/test_parser.py` | 18 | 日期/促銷/明細/優惠券解析、未知商品、單價不一致、數量為 0、缺結算日、空車、多張券 |
| `tests/unit/test_cli.py` | 5 | 子程序執行 CLI:印金額、多檔、用法、缺檔、格式錯誤 |
| `tests/acceptance/test_cases.py` | 2 | 讀真實 fixture 檔 → 解析 → 結算 → 比對 3083.60 / 43.54 |
| `tests/unit/test_catalog.py` | 4 | 目錄 4 品類 18 項、價格皆 `Decimal` |
| `tests/unit/test_products_builder.py` | 4 | `build_category_groups()` 輸出格式 |
| `tests/api/test_products_api.py` | 4 | `GET /api/products`、`GET /` 經 `TestClient` |

其中直接驗證題目規則的關鍵測試:

- `test_coupon_threshold_is_judged_after_promotion_discount`:原價過門檻但促銷後未過時,券不得折抵(規則 3 的回歸保護)
- `test_checkout_rounds_half_up_to_two_places`:`9.995 × 3 = 29.985 → 29.99`
- `test_promotion_is_active_only_on_its_date`:促銷前一天與後一天皆不生效

---

## 五、關於 DB 的評估

本次未導入資料庫,理由記錄於 [docs/decisions.md](decisions.md) D1:

- 題目把促銷與優惠券當成**每次結算一起傳進來的輸入參數**(如 `case_a.txt` 中的 `2015.11.11|0.7|電子`),而非被系統查詢的常駐實體。系統從不問「某日期當時生效的是哪幾檔促銷」,版本回溯與查詢能力在 MVP 裡不會被用到。
- 依賴白名單只有 `fastapi`、`uvicorn`、`pytest`、`httpx`;為幾個欄位付出 schema 定義與測試隔離的成本屬過度設計。
- 換 DB 的成本接近零:`repository/` 是唯一讀寫檔案的地方,`domain` 與 `services` 不碰檔案,將來換成 `db_store.py` 時領域層與服務層一行都不用改。

**翻轉條件**(滿足任一項即導入):後台需要對促銷/優惠券做 CRUD、需要回溯某日期當時的促銷、多人並發寫入、審計軌跡、跨表查詢或報表。

---

## 六、尚未實作與已知限制

| 項目 | 狀態 | 說明 |
| --- | --- | --- |
| 多張券的擇優策略 | **待決定** | 題目說「每次只能用一張」但未定義多張可用時如何選。目前不假設,待確認後再補;現階段由 `CheckoutInput.coupon` 型別強制單張 |
| 「當前日期」後台覆寫 | 未實作 | 結算函式已接受日期參數,只要外層傳入覆寫值即可生效;後台 API 尚未建立 |
| 結算 API / 購物車 API | 未實作 | `services/checkout.py` 已是純函式,API 層接上一層即可 |
| 持久層 `repository/json_store.py` | 未實作 | `data/seed.json` 仍為 `{}`;結算目前不依賴它 |
| 前端結算頁 / 優惠券選擇介面 | 未實作 | 依賴上述後端項目 |
| 前端頁面視覺驗收 | 本次未異動 | 商品瀏覽頁本次未修改,僅後端與 CLI 有變更,無視覺回歸需求;日後前端有變更時需以截圖驗收(本環境無法輸入圖像,改以文字斷言與 DOM 檢查為主,視覺檢查留待可輸入圖像的環境補上) |

---

## 七、重現方式

```bash
# 1. 建立並啟用虛擬環境(已存在可略過)
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
# source .venv/bin/activate         # macOS / Linux

# 2. 安裝依賴
pip install -r requirements-dev.txt

# 3. 跑全套測試
pytest                              # 預期 59 passed

# 4. 跑題目驗收案例
PYTHONPATH=src python -m cart.cli tests/fixtures/case_a.txt tests/fixtures/case_b.txt
# 預期輸出:
# 3083.60
# 43.54
```
