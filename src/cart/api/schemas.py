"""API 層的回傳資料結構(Pydantic schema)。"""

from pydantic import BaseModel


class ProductOut(BaseModel):
    """回傳給前端的單一商品,價格固定為字串以避免 float 誤差。"""

    name: str
    price: str


class CategoryGroupOut(BaseModel):
    """回傳給前端的單一品類分組。"""

    category: str
    products: list[ProductOut]


class CouponOut(BaseModel):
    """回傳給前端的單張優惠券,金額與日期皆為字串。"""

    id: str
    name: str
    expiry_date: str
    threshold: str
    discount: str


class CouponOptionOut(BaseModel):
    """回傳給前端的單張優惠券與其在目前購物車下的可用狀態。

    status 由後端依促銷後金額與結算日判斷:usable / expired / below_threshold。
    """

    id: str
    name: str
    expiry_date: str
    threshold: str
    discount: str
    status: str


class CheckoutItemIn(BaseModel):
    """前端送來的購物車項目;只收商品名與數量,不收價格(見 decisions.md D4)。"""

    name: str
    quantity: int


class CheckoutRequest(BaseModel):
    """結算請求:購物車明細與(可選的)本次優惠券代號。"""

    items: list[CheckoutItemIn]
    coupon_id: str | None = None


class CouponOptionsRequest(BaseModel):
    """優惠券可選清單請求:只收購物車明細,用來判斷每張券的門檻狀態。"""

    items: list[CheckoutItemIn]


class CheckoutResultOut(BaseModel):
    """結算結果明細:把計算過程逐項回傳,供結帳頁顯示。"""

    original_subtotal: str
    promoted_subtotal: str
    coupon_discount: str
    total: str
    coupon_status: str
    applied_coupon_name: str | None
    applied_promotion_names: list[str]
