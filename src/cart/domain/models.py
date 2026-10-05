"""結算領域模型:一次計算請求的資料物件。

資料物件只負責存放資料,業務邏輯寫在 services/calculator.py。
金額一律使用 Decimal、日期使用 datetime.date,兩者皆由外部傳入。
品類為自由字串,不由目錄約束(規格允許任意品類,如「生活用品類」)。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class LineItem:
    """購物車內的單一商品項目,單價由請求 JSON 帶入。"""

    name: str
    category: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class Promotion:
    """促銷:可對指定日期與品類的商品打折或加減金額。

    rate 為乘法(如 0.7),effect 為加法(如 -50 或 +50),兩者可同時存在;
    date 與 category 省略(None)代表不設限,對所有品項生效。
    """

    date: date | None
    category: str | None
    rate: Decimal | None
    effect: Decimal | None


@dataclass(frozen=True)
class Coupon:
    """折價券:有效期內且達到小計門檻時,折抵或加減固定金額。

    discount 為正數、套用時自動轉負;effect 直接指定加減值。
    取值優先序為 effect > -discount > 0,三者皆可省略。
    """

    expiry_date: date | None
    min_spend: Decimal | None
    discount: Decimal | None
    effect: Decimal | None


@dataclass(frozen=True)
class CaseInput:
    """一次計算的完整輸入:交易日、購物車、促銷清單與折價券清單。"""

    date: date
    items: list[LineItem]
    promotions: list[Promotion]
    coupons: list[Coupon]


@dataclass(frozen=True)
class CouponResult:
    """單張折價券的套用結果,供呼叫端判斷是否生效與不生效原因。

    reason 只有兩種:expired(交易日超過到期日)、below_min_spend(小計未達門檻);
    成功套用時為 None。
    """

    index: int
    applied: bool
    reason: str | None


@dataclass(frozen=True)
class CalculationResult:
    """計算結果:促銷後小計、最終金額與每張折價券的套用結果。

    subtotal 不四捨五入以忠實呈現計算過程,total 才四捨五入到小數 2 位。
    """

    subtotal: Decimal
    total: Decimal
    coupon_results: list[CouponResult]
