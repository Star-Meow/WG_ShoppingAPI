"""結算領域模型:購物車、購物車項目、促銷與優惠券的資料物件。

資料物件只負責存放資料,業務邏輯寫在 services/checkout.py。
金額一律使用 Decimal,日期使用 datetime.date,兩者皆由外部傳入。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from cart.domain.catalog import Category


@dataclass(frozen=True)
class CartItem:
    """購物車內的單一商品項目。"""

    name: str
    category: Category
    unit_price: Decimal
    quantity: int


@dataclass(frozen=True)
class Promotion:
    """促銷折扣:在促銷日期當天,對指定品類的商品打折。"""

    date: date
    discount: Decimal
    category: Category
    name: str = ""


@dataclass(frozen=True)
class Coupon:
    """優惠券:有效期內且金額達門檻時,折抵固定金額。

    id 與 name 是給前台與 API 使用的識別與顯示文字,不參與金額計算;
    從測試案例文字解析出來的券沒有這兩個欄位(維持空字串)。
    """

    expiry_date: date
    threshold: Decimal
    discount: Decimal
    id: str = ""
    name: str = ""


@dataclass(frozen=True)
class Cart:
    """購物車:持有顧客選購的全部項目。"""

    items: list[CartItem]

    def subtotal(self) -> Decimal:
        """購物車的未折扣小計。"""
        total = Decimal("0")
        for item in self.items:
            total = total + item.unit_price * item.quantity
        return total


@dataclass(frozen=True)
class CheckoutInput:
    """一次結算的完整輸入:購物車、促銷清單、結算日與(最多一張)優惠券。"""

    cart: Cart
    promotions: list[Promotion]
    checkout_date: date
    coupon: Coupon | None = None


@dataclass(frozen=True)
class CheckoutResult:
    """結算明細:把計算過程的每一步金額都暴露出來,供前端逐項顯示。

    優惠券折抵可能因過期或未達門檻而不成立,此時 discount 為 0、
    coupon_status 說明原因;applied_coupon 記錄實際套用的券。
    """

    original_subtotal: Decimal
    promoted_subtotal: Decimal
    coupon_discount: Decimal
    total: Decimal
    coupon_status: str
    applied_coupon: Coupon | None
    applied_promotions: list[Promotion]
