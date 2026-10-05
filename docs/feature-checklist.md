# 功能盤點(實作進度)

本檔案回答「**哪些功能已實作、哪些還沒**」。需求本身見 [requirements.md](requirements.md),測試涵蓋範圍見 [test-checklist.md](test-checklist.md)。

標註「空殼」者代表檔案已建但只有 docstring 或佔位文字、尚無邏輯。

## 一、完成度摘要

| 類別 | 已完成 | 總項目 | 完成率 |
| --- | --- | --- | --- |
| 後端 | 19 | 22 | 86% |
| 前端 | 15 | 17 | 88% |
| 測試 | 10 | 10 | 100% |
| **合計** | **44** | **49** | **90%** |

**題目核心要求(促銷 + 優惠券算結算金額)已 100% 做完並通過驗收案例。** 未完成的部分全部集中在「後台管理」與「購物車持久化」這兩塊範圍外的加值功能。

## 二、後端盤點(api → services → domain)

### 領域層 `domain/`

- [x] 商品目錄資料模型:`Category` 列舉(電子/食品/日用品/酒類)、`Product` 資料物件、`CATALOG`(4 類 18 項) — `domain/catalog.py`
- [x] 依品類分組商品:`products_by_category()`,回傳順序依照 `Category` 定義順序 — `domain/catalog.py`
- [x] 結算領域模型:`CartItem`、`Promotion`、`Coupon`、`Cart`(含 `subtotal()`)、`CheckoutInput` — `domain/models.py`
- [x] 領域錯誤類型:`CheckoutError` 家族(解析格式、未知商品、單價不一致、券不可用等),供 API 層對應 HTTP 狀態碼 — `domain/errors.py`
- [x] 金額規則:結算一律 `Decimal` 且四捨五入到小數 2 位(`round_to_two_places`) — `services/checkout.py`
- [x] 依名稱查商品:`find_product_by_name()`,供解析層取品類與權威單價 — `domain/catalog.py`

### 服務層 `services/`

- [x] 促銷折扣:僅在結算日 = 促銷日期時生效,且只套用在對應品類 — `services/checkout.py`
- [x] 優惠券有效期:結算日 ≤ 到期日即有效(含當天) — `services/checkout.py`
- [x] 優惠券門檻:以**促銷折扣後**金額判斷,≥ 門檻才成立 — `services/checkout.py`
- [x] 單張優惠券限制:每次結算只能一張(由 `CheckoutInput.coupon: Coupon | None` 於模型層強制) — `services/checkout.py`
- [ ] **待決定**:多張券可用時,自動套用減額最大者 or 由使用者選擇(確認後才實作,不假設)

### 資料層 `repository/`

- [x] JSON 讀取:從 `data/seed.json` 讀促銷與優惠券、依 id 查券;`data/runtime.json` 讀寫「當前日期」覆寫 — `repository/json_store.py`
- [ ] JSON 寫入:把後台異動(目錄/促銷/優惠券)寫回 `seed.json` — **尚未實作**。`json_store.py` 目前只有讀取函式與 `save_current_date()`,`seed.json` 完全唯讀

### API 層 `api/`

- [x] 商品瀏覽 API:`GET /api/products`,回傳 4 品類分組共 18 項,價格為字串 — `api/products.py`、`api/schemas.py`
- [x] 回傳格式轉換純函式:`build_category_groups()`,不經過 HTTP 也能測 — `api/products.py`
- [x] 結算 API:`POST /api/checkout` 收商品名+數量與券 id,回傳逐項金額明細;`GET /api/coupons` 列出可選優惠券 — `api/checkout.py`、`api/schemas.py`
- [x] 結算金額由後端依 `CATALOG` 重取單價計算,不接受前端傳價(decisions.md D4) — `api/checkout.py`、`services/checkout.py`
- [ ] 後台 API:商品目錄、促銷、優惠券管理 — `api/admin.py`(**空殼**,只有 docstring,未在 `main.py` 註冊 router)
- [ ] 後台 API:手動覆寫「當前日期」,可切回系統真實日期 — `api/admin.py`(**空殼**;`save_current_date()` 已備妥但沒有任何 endpoint 呼叫它,目前只能手改檔案)
- [ ] 購物車 API:新增 / 修改 / 查詢購物車項目 — **尚未建立任何檔案**

### 進入點與設定

- [x] FastAPI app 建立、API router 先註冊、靜態檔掛載在最後 — `main.py`
- [x] 路徑集中設定:web 目錄、`data/` 目錄(以 `pathlib` 依檔案位置推算) — `config.py`
- [x] 「當前日期」由最外層決定並往內傳:API 層讀 `runtime.json` 覆寫值,無覆寫才用 `date.today()`,service 不碰系統時間 — `api/checkout.py`、`repository/json_store.py`

### 命令列 `cli/`

- [x] 文字解析:案例字串 → `CheckoutInput`,只解析不計算金額;品類與單價由 `CATALOG` 查得 — `cli/parser.py`
- [x] CLI 入口:`python -m cart.cli <檔>...` 讀檔 → 解析 → 結算 → 印金額 — `cli/__main__.py`

## 三、前端盤點(`web/`)

- [x] 頂部查詢框:輸入關鍵字即過濾目前頁面商品(依名稱不分大小寫比對,純前端不連後端) — `web/index.html`
- [x] 分類導引欄:查詢框下方的橫向分頁(全部 + 4 品類),點擊只顯示該品項,並清掉搜尋關鍵字 — `web/index.html`
- [x] 商品卡片:純 CSS 佔位圖(品類顏色 + 品名首字)、品名、單價 — `web/index.html`
- [x] 加入購物車按鈕:每張卡片一顆,點擊把目前數量加進購物車並顯示「已加入購物車:{品名} × {數量}」提示 — `web/index.html`
- [x] 數量調整元件:每張卡片上有 `- [數量] +`,最低 1,數量為 1 時停用減號鈕 — `web/index.html`
- [x] 右下角懸浮購物車鈕:`position: fixed` 固定於畫面右下角,附商品總數角標(0 時隱藏) — `web/index.html`
- [x] 前端購物車狀態:目前以 JS 物件存在記憶體,金額用整數分計算避免 float 小數誤差(見第五節) — `web/index.html`
- [x] 三種狀態處理:載入中 / 成功 / 失敗(失敗時附錯誤與排除方式);查無商品時顯示「查無符合的商品」 — `web/index.html`
- [x] 響應式版面:手機寬度可讀 — `web/index.html`
- [x] 可見的鍵盤 focus 樣式 — `web/index.html`
- [x] 無框架、免 build、資料以 `textContent` / 建立元素插入(不拼進 `innerHTML`) — `web/index.html`
- [x] **獨立結帳頁**:點懸浮鈕整頁切換,左側購物車明細、右側結帳欄(優惠券下拉 + 逐項金額 + 確認結帳);空車顯示提示並停用結帳鈕 — `web/index.html`
- [x] **優惠券選擇介面**:`GET /api/coupons` 載入券清單,選擇後即時重算並顯示券狀態(可使用 / 已過期 / 未達門檻) — `web/index.html`
- [x] **結算金額明細**:原價合計、促銷折扣(附促銷名稱)、優惠券折抵、最終結算金額,全部由 `POST /api/checkout` 回傳 — `web/index.html`
- [ ] 後台管理頁:商品 / 促銷 / 優惠券管理與當前日期切換 — `web/admin.html`(**空殼**,12 行佔位頁,沒有任何 JS)
- [ ] 購物車頁面:修改 / 刪除已加入的商品(目前結帳頁只能瀏覽,尚不能編輯) — **尚未建立**

> 舊的購物籃下拉面板已移除,改由獨立結帳頁取代。

## 四、未實作功能總表

依「離題目核心多遠」排序。第一組是題目沒要求、純屬加分;第二、三組是需求文件提到但明確標為暫緩的。

| # | 功能 | 範圍 | 現況 | 為何未做 |
| --- | --- | --- | --- | --- |
| 1 | 多券擇優策略 | 待定案 | 未實作 | 題目未定義「多張可用券怎麼選」,兩種做法會產出不同結果,不宜自行假設 |
| 2 | 「當前日期」後台 endpoint | 小 | 底層已備妥,只差 API | `save_current_date()` 存在但無呼叫端;開一個 `PUT /api/admin/current-date` 即可,成本最低 |
| 3 | 後台管理 API(商品/促銷/優惠券 CRUD) | 中 | `api/admin.py` 空殼 | 會把促銷與券從「每次結算的輸入參數」翻轉成「常駐實體」,推翻 D1,且連帶逼出「同日促銷重疊」「全館促銷」「多券擇優」三個未定的業務決策 |
| 4 | `seed.json` 寫入 | 中 | 未實作 | 依附於第 3 項 |
| 5 | 後台管理頁 | 中 | `web/admin.html` 空殼 | 依附於第 3 項 |
| 6 | 後端購物車 API | 中 | 尚未建立 | 目前購物車只在記憶體,重整即清空。方向已定案(decisions.md D3:session + `httpOnly` cookie) |
| 7 | 前端購物車編輯頁(改數量/刪除) | 小 | 尚未建立 | 依附於第 6 項;但在純前端也能先做,不一定要等 API |
| 8 | 像素級視覺驗收 | 小 | 受環境限制 | 結帳頁已用瀏覽器實測互動與金額,但本環境無法比對截圖 |

## 五、購物車資料流向(重要)

目前購物車狀態**只存在前端 JS 記憶體**(`cart` 物件),重新整理頁面就會清空。**尚未透過後端 API 儲存**。完整的方案評估(為何不用 DB、為何不做登入、資料職責分類)見 [decisions.md](decisions.md) D1 / D3,以下只列對實作的直接影響:

- 後端結算 API(`POST /api/checkout`、`GET /api/coupons`)已實作,但**購物車本身**仍只存前端記憶體,沒有後端購物車 API。
- 前端已把購物車操作集中在少數函式中(`addToCart`、`renderCartBadge`、`renderCheckoutItems`),日後接後端購物車 API 時,只要改這幾個函式內部去呼叫 API,明細與結帳欄的繪製邏輯都不用動。
- 金額計算使用整數「分」(`priceToCents` / `centsToText`),避免 float 小數誤差,與後端 `Decimal` 的精神一致。
- **金額的唯一信任來源是後端**:結算時後端只收商品名 + 數量,價格重取 `CATALOG`,不接受前端傳價(見 decisions.md D4)。

## 六、建議的下一步順序

1. **多券擇優定案** — 先做業務決定,再寫 code。定了之後 `services/` 加一個擇優函式 + 前端下拉複選或自動推薦。
2. **「當前日期」後台 endpoint** — 最小成本補完需求規則 6,一個 endpoint 就能讓後台日期切換不必手改檔案。
3. **後端購物車 API** — 依 decisions.md D3 走 session + `httpOnly` cookie,讓重整頁面購物車不消失。
4. **前端購物車編輯頁** — 結帳頁加上改數量 / 刪除品項。
5. **後台管理頁與 seed 寫入** — 最後做,因為它會推翻 D1 且牽涉多個未定的業務決策。

每一層都先寫單元測試再實作,順序與分層理由見 [architecture.md](architecture.md)。