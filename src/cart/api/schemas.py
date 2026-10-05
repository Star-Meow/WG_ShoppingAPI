"""API 層的資料結構(Pydantic schema)。

金額與日期欄位一律為字串:金額避免 JSON 數字還原成 float,日期由 service 解析。
欄名沿用規格的 camelCase。
"""

from pydantic import BaseModel, Field


class LineItemIn(BaseModel):
    """購物車項目:品名、品類、數量與單價。單價由請求帶入,不查目錄。"""

    name: str
    category: str
    qty: int = Field(gt=0, description="數量必須為正整數")
    unitPrice: str = Field(description="單價,字串以避免 float 誤差")


class PromotionIn(BaseModel):
    """促銷:乘法 rate 與加法 effect 可同時存在;date/category 省略代表全適用。"""

    date: str | None = None
    category: str | None = None
    rate: str | None = None
    effect: str | None = None


class CouponIn(BaseModel):
    """折價券:discount 為正數(自動轉負),effect 直接指定加減值。"""

    expiryDate: str | None = None
    minSpend: str | None = None
    discount: str | None = None
    effect: str | None = None


class CalculateRequest(BaseModel):
    """計算請求:交易日、購物車明細,以及可省略的促銷與折價券清單。"""

    date: str = Field(description="交易日,支援 YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD")
    items: list[LineItemIn] = Field(min_length=1, description="購物車明細不得為空")
    promotions: list[PromotionIn] = Field(default_factory=list)
    coupons: list[CouponIn] = Field(default_factory=list)


class CouponResultOut(BaseModel):
    """單張折價券的套用結果。reason 為 expired 或 below_min_spend,套用成功為 null。"""

    index: int
    applied: bool
    reason: str | None = None


class CalculateResultOut(BaseModel):
    """計算結果:subtotal 不四捨五入,total 四捨五入到小數 2 位。"""

    subtotal: str
    total: str
    couponResults: list[CouponResultOut]
