# 結算系統驗收報告

**範圍**:題目核心「給定購物車與促銷資訊,算出結算金額」——P0 結算引擎與 CLI 介面,以及其後加入的結算 API 與獨立結帳頁。
**驗收日期**:2026-10-05(初版);2026-10-06 更新(優惠券改為可點選清單,新增券可選狀態 API)
**測試環境**:Python 3.10.11、pytest 9.1.1、Windows + Git Bash,虛擬環境 `.venv`

---

## 一、驗收結論

| 項目 | 結果 |
| --- | --- |
| `pytest` 全套測試 | **85 passed**(0 failed) |
| Case A(`tests/fixtures/case_a.txt`) | **3083.60** ✅ 與題目預期一致 |
| Case B(`tests/fixtures/case_b.txt`) | **43.54** ✅ 與題目預期一致 |
| CLI 介面 `python -m cart.cli` | 兩案各印出一行金額,exit code 0 |
| 結算 API `POST /api/checkout` | ✅ 回傳逐項金額明細,金額由後端計算 |
| 券可選狀態 API `POST /api/checkout/coupon-options` | ✅ 依購物車回傳每張券可使用/已過期/未達門檻 |
| 獨立結帳頁(瀏覽器實測) | ✅ 可用券可點選、選中即時重算、不可用券標灰附原因、結帳清空購物車 |

題目指定的文字驗收案例已可透過 CLI 實際跑出預期金額;網頁端也已有完整的結帳頁,金額全部由後端 `Decimal` 計算後回傳,前端只負責顯示。

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

### 6. 結算 API `src/cart/api/checkout.py`、`src/cart/repository/json_store.py`

兩個 endpoint,都保持「接收 → 呼叫 service → 回傳」的薄度:

- `GET /api/coupons`:從 `data/seed.json` 讀出可選優惠券,回傳 id / 名稱 / 門檻 / 折額 / 到期日(皆字串)。
- `POST /api/checkout`:收 `{items:[{name, quantity}], coupon_id?}`,回傳逐項明細——原價合計、促銷後金額、券折抵、結算金額、券狀態、實際套用的促銷與券名稱。

**價格由後端重取(D4)**:`build_cart()` 只拿前端傳來的商品名,單價與品類一律由 `CATALOG` 經 `find_product_by_name()` 查得;前端傳的價格完全不使用。未知商品回 400。

**「當前日期」由最外層決定(規則 6)**:`resolve_current_date()` 先讀 `data/runtime.json` 的覆寫值,沒有才用 `date.today()`;service 層不碰系統時間。把日期覆寫成促銷日期,該促銷就會在結算時自動生效(下面第五節實測)。

**券三狀態**:`usable` / `expired` / `below_threshold`,由 `checkout_coupon_status()` 依「促銷後金額 vs 門檻」與「結算日 vs 到期日」判斷;不可用時折抵 0 且不視為已套用,但仍把原因告訴前端。

### 7. 獨立結帳頁 `src/cart/web/index.html`

點懸浮購物車鈕後**整頁切換**到結帳頁(不是彈出面板),版面是左明細 / 右結帳欄:

- **左側**:逐項顯示品名、單價 × 數量、該項小計;空車顯示「購物車是空的,請先回到目錄挑選商品」並停用結帳鈕。
- **右側結帳欄**:**可點選的優惠券清單**(「不使用優惠券」+ `POST /api/checkout/coupon-options` 回傳的每張券)、金額明細(原價合計 / 各促銷折抵 / 券折抵 / 結算金額)、確認結帳鈕。
- **只有能用的券可以點**:狀態由後端依「促銷後金額 vs 門檻」與「結算日 vs 到期日」判斷,可使用的券可點選(選中後高亮並即時重算),不可用的券停用、標灰,並直接在卡片上寫明原因(「已過期,本次結算無法使用」或「未達門檻:需促銷後金額滿 N 元」),不必點了才知道。
- 確認結帳後顯示「結帳完成,結算金額 X 元」、清空購物車、角標歸 0。
- 三種狀態都處理:計算中、成功、失敗(附錯誤與排除方式);資料一律用 `textContent` / 建立元素插入,不拼 `innerHTML`;760px 以下結帳欄改為直排。

---

## 四、自動化測試清單

共 85 項測試,全數通過:

| 測試檔 | 項數 | 涵蓋內容 |
| --- | --- | --- |
| `tests/unit/test_checkout.py` | 22 | 促銷生效/不生效/跨品類、券過期/到期日當天/門檻上下緣、門檻以促銷後金額判斷、四捨五入、Case A/B 完整結算 |
| `tests/unit/test_checkout_result.py` | 7 | `build_checkout_result`:原價/促銷後/券折抵明細、券三狀態、已套用促銷與券 |
| `tests/unit/test_coupon_options.py` | 7 | `collect_coupon_options`:可使用/已過期/未達門檻、門檻以促銷後金額判斷、多券混合狀態、保留券參考、空清單 |
| `tests/unit/test_parser.py` | 18 | 日期/促銷/明細/優惠券解析、未知商品、單價不一致、數量為 0、缺結算日、空車、多張券 |
| `tests/unit/test_cli.py` | 5 | 子程序執行 CLI:印金額、多檔、用法、缺檔、格式錯誤 |
| `tests/acceptance/test_cases.py` | 2 | 讀真實 fixture 檔 → 解析 → 結算 → 比對 3083.60 / 43.54 |
| `tests/api/test_checkout_api.py` | 12 | `GET /api/coupons`;`POST /api/checkout` 全情境;`POST /api/checkout/coupon-options` 的狀態判斷與 400 錯誤 |
| `tests/unit/test_catalog.py` | 4 | 目錄 4 品類 18 項、價格皆 `Decimal` |
| `tests/unit/test_products_builder.py` | 4 | `build_category_groups()` 輸出格式 |
| `tests/api/test_products_api.py` | 4 | `GET /api/products`、`GET /` 經 `TestClient` |

其中直接驗證題目規則的關鍵測試:

- `test_coupon_threshold_is_judged_after_promotion_discount`:原價過門檻但促銷後未過時,券不得折抵(規則 3 的回歸保護)
- `test_checkout_rounds_half_up_to_two_places`:`9.995 × 3 = 29.985 → 29.99`
- `test_promotion_is_active_only_on_its_date`:促銷前一天與後一天皆不生效

---

## 五、結帳頁瀏覽器實測(2026-10-05)

以 ZCode In-app Browser 打開 `http://127.0.0.1:8001/`,實際操作全流程:

| 步驟 | 操作 | 實際結果 |
| --- | --- | --- |
| 1 | 載入目錄頁 | 18 項商品、4 品類分頁全部渲染;載入中狀態先出現後被取代 |
| 2 | 加入 ipad×1、顯示器×1、啤酒×12、麵包×5,點懸浮鈕 | 結帳頁整頁切換;左側四項明細正確,右側原價合計 **4543.00**,角標 19 |
| 3 | 優惠券選「滿三千折五百」 | 明細出現「優惠券:滿三千折五百 −500.00」,結算金額 **4043.00** |
| 4 | 改選過期券「端午滿千折五十」 | 出現警示「優惠券已過期,本次結算未折抵」,折抵消失,金額退回 4543.00 |
| 5 | 改回「不使用優惠券」 | 結算金額 **4543.00**,無折抵項 |
| 6 | 把當前日期覆寫到 2026-11-11(`runtime.json`),再選「滿千折百」 | **促銷自動生效**:「促銷:雙 11 電子品類 7 折 −1259.40」+「優惠券:滿千折百 −100.00」,結算金額 **3183.60** |
| 7 | 點「確認結帳」 | 顯示「結帳完成,結算金額 3183.60 元」、購物車清空、角標歸 0、結帳鈕停用 |

步驟 6 證實了需求描述的行為:**預先寫好的促銷(聖誕節、雙 11)在「當前日期」被調到促銷日期時自動生效**,不需要重啟或改程式碼,因為促銷是否生效本來就只看「結算日 == 促銷日期」。

步驟 6 的算式對拍:電子品類原價 (2399.00 + 1799.00) × 0.7 = 2938.60,其他品類 300.00 + 45.00 = 345.00,促銷後 3283.60,折 100 → **3183.60** ✅

## 五之一、可點選優惠券清單實測(2026-10-06)

優惠券從下拉改成可點選清單後,以 ZCode In-app Browser 打開 `http://127.0.0.1:8000/` 重新實測:

| 步驟 | 操作 | 實際結果 |
| --- | --- | --- |
| 1 | 加入 ipad×1、顯示器×1、啤酒×1、麵包×1,點懸浮鈕 | 結帳頁列出 5 張卡片:「不使用」+ 4 張券;「滿百折十」「滿千折百」「滿三千折五百」標「可使用」可點,「端午滿千折五十(已過期)」**停用並標灰**,直接寫明「已過期,本次結算無法使用」 |
| 2 | 點「滿千折百」 | 該卡高亮(`aria-pressed` 正確切換),明細出現「優惠券:滿千折百 −100.00」,結算金額 **4132.00**(原價 4232.00 − 100) |
| 3 | 把當前日期覆寫到 2026-11-11 後重進結帳頁 | **促銷自動生效**:「促銷:雙 11 電子品類 7 折 −1259.40」;「滿三千折五百」當場**由可使用轉為停用**,原因「未達門檻:需促銷後金額滿 3000 元」(促銷後 2972.60 < 3000),全程不必點錯才知道 |
| 4 | 點「確認結帳」 | 顯示「結帳完成,結算金額 2872.60 元」、購物車清空、券清單縮回只剩「不使用優惠券」、結帳鈕停用 |

步驟 3 是這次改動的核心價值:**券能不能用,在點之前就由後端算好並直接呈現在卡片上**,「門檻以促銷後金額判斷」(規則 3)的效力也即時反映在清單上,而不是選了才跳警示。

---

## 六、關於 DB 的評估

未導入資料庫,理由記錄於 [docs/decisions.md](decisions.md) D1:

- 題目把促銷與優惠券當成**每次結算一起傳進來的輸入參數**(如 `case_a.txt` 中的 `2015.11.11|0.7|電子`),而非被系統查詢的常駐實體。系統從不問「某日期當時生效的是哪幾檔促銷」,版本回溯與查詢能力在 MVP 裡不會被用到。
- 依賴白名單只有 `fastapi`、`uvicorn`、`pytest`、`httpx`;為幾個欄位付出 schema 定義與測試隔離的成本屬過度設計。
- 換 DB 的成本接近零:`repository/` 是唯一讀寫檔案的地方,`domain` 與 `services` 不碰檔案,將來換成 `db_store.py` 時領域層與服務層一行都不用改。

**翻轉條件**(滿足任一項即導入):後台需要對促銷/優惠券做 CRUD、需要回溯某日期當時的促銷、多人並發寫入、審計軌跡、跨表查詢或報表。

---

## 七、尚未實作與已知限制

| 項目 | 狀態 | 說明 |
| --- | --- | --- |
| 後台發放優惠券 / 促銷管理 | **暫緩** | 評估過「券原因、名稱、圖片、折扣效果 + 日期驅動促銷」這組需求;它會翻轉 D1(促銷與券從輸入參數變成常駐實體),並逼出「同日促銷重疊」「全館促銷」「多券擇優」三個待定案的业务決策。决定先做結帳頁,此功能待定案後再動 |
| 多張券的擇優策略 | **待決定** | 題目說「每次只能用一張」但未定義多張可用時如何選。目前結帳頁把可用的券全部列出由使用者點選(即「由使用者選擇」路線);若要改「自動套用減額最大者」需在 service 加一個擇優函式 |
| 「當前日期」後台 API | 讀寫機制已備妥 | `repository/json_store.py` 已能讀寫 `runtime.json` 覆寫值(第五節步驟 6 實測生效),但 `api/admin.py` 的 endpoint 尚未開,目前只能改檔案 |
| 後端購物車 API | 未實作 | 購物車仍只存前端 JS 記憶體,重整頁面即清空;日後接 D3 的 session 方案 |
| 前端購物車編輯頁 | 未實作 | 結帳頁目前只能瀏覽明細,不能修改 / 刪除品項 |
| 前端頁面視覺驗收 | 部分受限 | 結帳頁以瀏覽器實測驗證了互動與金額(第五節);但本環境無法輸入圖像,版面與配色的視覺檢查只能靠 DOM 結構與文字內容,無法做像素級比對,留待可輸入圖像的環境補上 |

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
pytest                              # 預期 85 passed

# 4. 跑題目驗收案例
PYTHONPATH=src python -m cart.cli tests/fixtures/case_a.txt tests/fixtures/case_b.txt
# 預期輸出:
# 3083.60
# 43.54

# 5. 啟動伺服器,用瀏覽器開 http://127.0.0.1:8000/ 使用結帳頁
uvicorn cart.main:app --reload --app-dir src
```
