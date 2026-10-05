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


@dataclass(frozen=True)
class Coupon:
    """優惠券:有效期內且金額達門檻時,折抵固定金額。"""

    expiry_date: date
    threshold: Decimal
    discount: Decimal


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
