"""結算服務:依促銷折扣與優惠券計算最終金額。

所有函式皆為純函式:不讀檔、不讀系統時間、不使用全域狀態,
結算日期一律由參數傳入。金額使用 Decimal,最後四捨五入到小數 2 位。
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from cart.domain.catalog import Category
from cart.domain.models import (
    Cart,
    CartItem,
    CheckoutInput,
    CheckoutResult,
    Coupon,
    Promotion,
)

TWO_PLACES = Decimal("0.01")

COUPON_STATUS_USABLE = "usable"
COUPON_STATUS_EXPIRED = "expired"
COUPON_STATUS_BELOW_THRESHOLD = "below_threshold"


def round_to_two_places(amount: Decimal) -> Decimal:
    """金額四捨五入到小數 2 位。"""
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def is_promotion_active(promotion: Promotion, checkout_date: date) -> bool:
    """促銷僅在結算日等於促銷日期時生效。"""
    return promotion.date == checkout_date


def find_active_promotion(
    promotions: list[Promotion],
    category: Category,
    checkout_date: date,
) -> Promotion | None:
    """找出對應品類且在結算日生效的促銷;沒有則回傳 None。"""
    for promotion in promotions:
        if not is_promotion_active(promotion, checkout_date):
            continue
        if promotion.category != category:
            continue
        return promotion
    return None


def calculate_item_subtotal(item: CartItem) -> Decimal:
    """單一項目的原價小計。"""
    return item.unit_price * item.quantity


def calculate_promoted_item_subtotal(
    item: CartItem,
    promotions: list[Promotion],
    checkout_date: date,
) -> Decimal:
    """單一項目套用促銷後的小計;無適用促銷時回傳原價。"""
    subtotal = calculate_item_subtotal(item)
    promotion = find_active_promotion(promotions, item.category, checkout_date)
    if promotion is None:
        return subtotal
    return subtotal * promotion.discount


def calculate_promoted_subtotal(
    cart: Cart,
    promotions: list[Promotion],
    checkout_date: date,
) -> Decimal:
    """整車套用促銷後的小計,作為優惠券門檻的判斷基準。"""
    total = Decimal("0")
    for item in cart.items:
        subtotal = calculate_promoted_item_subtotal(item, promotions, checkout_date)
        total = total + subtotal
    return total


def is_coupon_expired(coupon: Coupon, checkout_date: date) -> bool:
    """優惠券在結算日之後到期即過期;到期日當天仍有效。"""
    return checkout_date > coupon.expiry_date


def is_coupon_threshold_met(coupon: Coupon, amount: Decimal) -> bool:
    """促銷折扣後金額達門檻(含)即成立。"""
    return amount >= coupon.threshold


def is_coupon_applicable(
    coupon: Coupon,
    promoted_subtotal: Decimal,
    checkout_date: date,
) -> bool:
    """優惠券可用:未過期且達門檻。"""
    if is_coupon_expired(coupon, checkout_date):
        return False
    if not is_coupon_threshold_met(coupon, promoted_subtotal):
        return False
    return True


def calculate_coupon_discount(
    coupon: Coupon | None,
    promoted_subtotal: Decimal,
    checkout_date: date,
) -> Decimal:
    """計算優惠券折抵金額;無券或不可用時折抵 0。每次結算最多一張。"""
    if coupon is None:
        return Decimal("0")
    if not is_coupon_applicable(coupon, promoted_subtotal, checkout_date):
        return Decimal("0")
    return coupon.discount


def calculate_checkout(input_data: CheckoutInput) -> Decimal:
    """計算最終結算金額:先套促銷,再以促銷後金額判斷優惠券門檻。"""
    promoted_subtotal = calculate_promoted_subtotal(
        input_data.cart,
        input_data.promotions,
        input_data.checkout_date,
    )
    coupon_discount = calculate_coupon_discount(
        input_data.coupon,
        promoted_subtotal,
        input_data.checkout_date,
    )
    return round_to_two_places(promoted_subtotal - coupon_discount)


def checkout_coupon_status(
    coupon: Coupon | None,
    promoted_subtotal: Decimal,
    checkout_date: date,
) -> str:
    """判斷券在目前的促銷後金額與結算日下屬於哪種狀態。

    前端依此顯示「可使用 / 已過期 / 未達門檻」;無券時固定為可使用(折抵 0)。
    """
    if coupon is None:
        return COUPON_STATUS_USABLE
    if is_coupon_expired(coupon, checkout_date):
        return COUPON_STATUS_EXPIRED
    if not is_coupon_threshold_met(coupon, promoted_subtotal):
        return COUPON_STATUS_BELOW_THRESHOLD
    return COUPON_STATUS_USABLE


def collect_applied_promotions(
    cart: Cart,
    promotions: list[Promotion],
    checkout_date: date,
) -> list[Promotion]:
    """列出本次結算實際生效的促銷(供明細顯示),依購物車品項順序。"""
    applied: list[Promotion] = []
    for item in cart.items:
        promotion = find_active_promotion(promotions, item.category, checkout_date)
        if promotion is not None and promotion not in applied:
            applied.append(promotion)
    return applied


def build_checkout_result(input_data: CheckoutInput) -> CheckoutResult:
    """計算結算明細:原價、促銷後金額、券折抵與最終金額,一次算完不重算。"""
    original_subtotal = input_data.cart.subtotal()
    promoted_subtotal = calculate_promoted_subtotal(
        input_data.cart,
        input_data.promotions,
        input_data.checkout_date,
    )
    status = checkout_coupon_status(
        input_data.coupon, promoted_subtotal, input_data.checkout_date
    )
    coupon_discount = calculate_coupon_discount(
        input_data.coupon,
        promoted_subtotal,
        input_data.checkout_date,
    )
    total = round_to_two_places(promoted_subtotal - coupon_discount)
    applied_coupon = input_data.coupon if coupon_discount > 0 else None
    applied_promotions = collect_applied_promotions(
        input_data.cart, input_data.promotions, input_data.checkout_date
    )
    return CheckoutResult(
        original_subtotal=round_to_two_places(original_subtotal),
        promoted_subtotal=round_to_two_places(promoted_subtotal),
        coupon_discount=round_to_two_places(coupon_discount),
        total=total,
        coupon_status=status,
        applied_coupon=applied_coupon,
        applied_promotions=applied_promotions,
    )
