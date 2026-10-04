# 架構與程式風格

> 「**評估過後決定不做**」的決策與理由,記在 [decisions.md](decisions.md),此處只列始終適用的原則。

## 資料職責分類(事實 / 規則 / 衍生值)

判斷「什麼可以暫存、什麼不可以」的依據:把資料分成三類,**衍生值絕不暫存**。

| 類別 | 定義 | 範例 | 處理方式 |
| --- | --- | --- | --- |
| **事實** | 使用者或系統的選擇,本身不會推導出別的 | 購物車裡有 ipad × 2、session 識別 | 可以暫存 |
| **規則** | 折扣與判斷條件,是計算的**輸入** | 電子品類 0.7 折、優惠券門檻 1000 折 200 | 走定義好的來源(seed / runtime),**不暫存** |
| **衍生值** | 從事實 + 規則算出的數字 | 小計、折扣金額、合計 | **每次現場重算,不落地** |

理由:同一份事實配上不同日期或促銷,結果就不同。把算好的合計存起來,一旦「當前日期」被後台覆寫,暫存的數字立刻是錯的。題目要求「日期由參數傳入、業務規則寫成純函式」,正是確保每次結算從輸入重算。

對應到分層:

```
暫存層      → 只放事實(購物車品項、session 識別)
設定來源    → 放規則(seed / runtime.json:目錄、促銷、優惠券、日期覆寫)
計算層      → 衍生值,每次從上兩層現場算,不落地
```

把促銷與優惠券跟購物車一起塞暫存,等於把「世界長怎樣」和「使用者做了什麼」混在同一層。持久層的選擇(為何不用 DB)見 [decisions.md](decisions.md) D1。

## 分層與依賴方向

```
api  →  services  →  domain
 │         │
 └→ repository(檔案讀寫)
```

- `domain/`:領域資料與業務規則。**不得 import FastAPI 或任何 web 模組**,也不讀寫檔案。
- `services/`:業務流程(結算),組合 domain 的規則;同樣不讀寫檔案。
- `repository/`:**唯一讀寫檔案的地方**(seed.json、runtime.json)。
- `api/`:HTTP 介面。保持極薄,只做「接收 → 呼叫 service → 回傳」;
  schema(Pydantic)與 router 只能出現在此層。
- `cli/`:命令列。文字解析只在 `cli/parser.py`,且只做「字串 → 資料物件」,不計算金額。
- `web/`:前端靜態檔,純 HTML + 原生 JavaScript,不需 build。

依賴方向一律由外往內,**domain 不認識外層**。

## 設計原則

- 金額一律使用 `Decimal`,API 輸出為字串,**不得使用 float**。
- **金額的唯一信任來源是後端**:結算時後端只收「商品名 + 數量」,價格由後端查 `CATALOG` 重取;前端的金額僅供顯示。詳見 [decisions.md](decisions.md) D4。
- 「今天」由最外層決定後往內傳,**任何函式不得自行呼叫 `date.today()`**。
- 需要儲存或日期的類別,在建構時從外部傳入,不在內部直接建立。
- 業務規則寫成**純函式**:相同輸入必得相同輸出,不讀檔、不讀系統時間、不用全域狀態。
- 不提前建立用不到的 base class、interface、factory。
- 資料物件只負責存放資料,業務邏輯寫在獨立函式中。

## 可讀性規則(全專案適用)

判斷標準:**一行程式碼,讀者能不能一眼看懂?需要停下來拆解,就改寫成明確的 for / if。**

### 可以使用

- 單層、單純轉換的 comprehension,例如 `names = [p.name for p in products]`
- `Enum`、type hints、f-string
- `@dataclass` 或手寫 `__init__` 的資料物件宣告
- FastAPI 的 `@router.get` decorator 與 Pydantic schema(僅 `api/` 層)

### 不要使用

1. comprehension 同時包含「過濾」與「轉換」,或兩層以上的 for / if
2. 巢狀三元運算式(`a if x else b if y else c`),改用 if / elif / else
3. 一行串接多個動作(如 `sorted(filter(map(...)))`),改用具名變數逐步承接
4. lambda 內含邏輯判斷,改用具名函式
5. 海象運算子 `:=`、`functools.reduce`,改用明確迴圈
6. `__getattr__`、metaclass、自訂 decorator 等隱含行為的寫法

### 以具名函式包裝邏輯

- 需要判斷、過濾、累加、轉換時,寫成獨立函式,再由上層呼叫
- 函式名稱用「動詞 + 受詞」,例如 `calculate_item_subtotal`、`is_coupon_expired`
- 每個函式只做一件事
- 函式必須對應一個業務概念,**不要為了拆而拆**,不建立只是轉呼叫的空包裝
- 上層函式只負責依序呼叫下層函式,不混入細節判斷

範例:

```python
def calculate_item_subtotal(price: Decimal, quantity: int) -> Decimal:
    return price * quantity


def calculate_cart_subtotal(items: list[CartItem]) -> Decimal:
    total = Decimal("0")
    for item in items:
        subtotal = calculate_item_subtotal(item.price, item.quantity)
        total = total + subtotal
    return total
```

## 前端

- 純 HTML + 原生 JavaScript(`fetch`),不使用 Vue / React / Alpine.js,不需 npm / build
- 拆成小函式(取資料、組畫面、顯示錯誤各一個),使用 `async / await`
- 插入資料時用 `textContent` 或建立元素,不把資料直接拼進 `innerHTML`
