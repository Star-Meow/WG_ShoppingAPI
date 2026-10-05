# 架構與程式風格

> 「**評估過後決定不做**」的決策與理由,記在 [decisions.md](decisions.md),此處只列始終適用的原則。

## 資料職責分類(事實 / 規則 / 衍生值)

判斷「什麼可以暫存、什麼不可以」的依據:把資料分成三類,**衍生值絕不暫存**。

| 類別 | 定義 | 範例 | 處理方式 |
| --- | --- | --- | --- |
| **事實** | 使用者的選擇,本身不會推導出別的 | 購物車裡有 ipad × 2 | 由請求帶入(系統不保存) |
| **規則** | 折扣與判斷條件,是計算的**輸入** | 電子品類 0.7 折、折價券門檻 1000 折 200 | 由請求帶入(系統不保存) |
| **衍生值** | 從事實 + 規則算出的數字 | 小計、折扣金額、合計 | **每次現場重算,不落地** |

理由:同一份事實配上不同日期或促銷,結果就不同。系統是**無狀態**的,事實與規則都是請求輸入,算完即丟;不存在可過期的暫存值。題目要求「日期由參數傳入、業務規則寫成純函式」,此形態天然滿足。

## 分層與依賴方向

```
api  →  services  →  domain
```

- `domain/`:領域資料與業務規則。**不得 import FastAPI 或任何 web 模組**,也不讀寫檔案。
- `services/`:業務流程(計算、日期解析),組合 domain 的規則;同樣不讀寫檔案。
- `api/`:HTTP 介面。保持極薄,只做「接收 → 呼叫 service → 回傳」;
  schema(Pydantic)與 router 只能出現在此層。

依賴方向一律由外往內,**domain 不認識外層**。無 `repository/`、無 `web/`、無 `cli/`(見 [decisions.md](decisions.md) D6)。

## 設計原則

- 金額一律使用 `Decimal`,API 輸出為字串,**不得使用 float**。
- **價格與品類由請求 JSON 帶入**,後端不查目錄。詳見 [decisions.md](decisions.md) D6。
- 「交易日」由請求帶入並往內傳,**任何函式不得自行呼叫 `date.today()`**。
- 業務規則寫成**純函式**:相同輸入必得相同輸出,不讀檔、不讀系統時間、不用全域狀態。
- 不提前建立用不到的 base class、interface、factory。
- 資料物件只負責存放資料,業務邏輯寫在獨立函式中。

## 可讀性規則(全專案適用)

判斷標準:**一行程式碼,讀者能不能一眼看懂?需要停下來拆解,就改寫成明確的 for / if。**

### 可以使用

- 單層、單純轉換的 comprehension,例如 `names = [p.name for p in products]`
- `Enum`、type hints、f-string
- `@dataclass` 或手寫 `__init__` 的資料物件宣告
- FastAPI 的 `@router.post` decorator 與 Pydantic schema(僅 `api/` 層)

### 不要使用

1. comprehension 同時包含「過濾」與「轉換」,或兩層以上的 for / if
2. 巢狀三元運算式(`a if x else b if y else c`),改用 if / elif / else
3. 一行串接多個動作(如 `sorted(filter(map(...)))`),改用具名變數逐步承接
4. lambda 內含邏輯判斷,改用具名函式
5. 海象運算子 `:=`、`functools.reduce`,改用明確迴圈
6. `__getattr__`、metaclass、自訂 decorator 等隱含行為的寫法

### 以具名函式包裝邏輯

- 需要判斷、過濾、累加、轉換時,寫成獨立函式,再由上層呼叫
- 函式名稱用「動詞 + 受詞」,例如 `calculate_line_total`、`is_coupon_expired`
- 每個函式只做一件事
- 函式必須對應一個業務概念,**不要為了拆而拆**,不建立只是轉呼叫的空包裝
- 上層函式只負責依序呼叫下層函式,不混入細節判斷

範例:

```python
def calculate_line_total(item: LineItem, promotions: list[Promotion],
                         transaction_date: date) -> Decimal:
    applicable = collect_applicable_promotions(promotions, item.category, transaction_date)
    rate_product = calculate_rate_product(applicable)
    effect_sum = calculate_effect_sum(applicable)
    return Decimal(item.quantity) * item.unit_price * rate_product + effect_sum
```
