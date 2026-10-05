"""計算引擎:依促銷與折價券算出最終金額。

所有函式皆為純函式:不讀檔、不讀系統時間、不使用全域狀態,
交易日一律由參數傳入。金額全程使用 Decimal,只在最後 total 四捨五入。

計算流程:
    逐項 lineTotal = qty × unitPrice × Π(rate) + Σ(effect)
    subtotal      = Σ(lineTotal)
    total         = subtotal + Σ(已套用券 effect),最後四捨五入到小數 2 位
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from cart.domain.models import (
    CalculationResult,
    CaseInput,
    Coupon,
    CouponResult,
    LineItem,
    Promotion,
)

TWO_PLACES = Decimal("0.01")

REASON_EXPIRED = "expired"
REASON_BELOW_MIN_SPEND = "below_min_spend"


def round_to_two_places(amount: Decimal) -> Decimal:
    """金額四捨五入到小數 2 位。"""
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def is_promotion_applicable(
    promotion: Promotion,
    item_category: str,
    transaction_date: date,
) -> bool:
    """促銷生效條件:未指定日期或日期相符,且未指定品類或品類相符。"""
    if promotion.date is not None and promotion.date != transaction_date:
        return False
    if promotion.category is not None and promotion.category != item_category:
        return False
    return True


def collect_applicable_promotions(
    promotions: list[Promotion],
    item_category: str,
    transaction_date: date,
) -> list[Promotion]:
    """找出對某品項生效的促銷清單。"""
    applicable = []
    for promotion in promotions:
        if is_promotion_applicable(promotion, item_category, transaction_date):
            applicable.append(promotion)
    return applicable


def calculate_rate_product(applicable_promotions: list[Promotion]) -> Decimal:
    """套用乘法促銷的連乘積;無促銷時為 1(不影響原價)。"""
    rate_product = Decimal("1")
    for promotion in applicable_promotions:
        if promotion.rate is not None:
            rate_product = rate_product * promotion.rate
    return rate_product


def calculate_effect_sum(applicable_promotions: list[Promotion]) -> Decimal:
    """套用加法促銷的總和;無促銷時為 0。"""
    effect_sum = Decimal("0")
    for promotion in applicable_promotions:
        if promotion.effect is not None:
            effect_sum = effect_sum + promotion.effect
    return effect_sum


def calculate_line_total(
    item: LineItem,
    promotions: list[Promotion],
    transaction_date: date,
) -> Decimal:
    """單一品項的金額:數量 × 單價 × Π(rate) + Σ(effect)。"""
    applicable = collect_applicable_promotions(
        promotions, item.category, transaction_date
    )
    rate_product = calculate_rate_product(applicable)
    effect_sum = calculate_effect_sum(applicable)
    return Decimal(item.quantity) * item.unit_price * rate_product + effect_sum


def calculate_subtotal(
    items: list[LineItem],
    promotions: list[Promotion],
    transaction_date: date,
) -> Decimal:
    """所有品項加總,即折價券套用前的小計;不四捨五入。"""
    subtotal = Decimal("0")
    for item in items:
        subtotal = subtotal + calculate_line_total(item, promotions, transaction_date)
    return subtotal


def resolve_coupon_effect(coupon: Coupon) -> Decimal:
    """折價券的實際加減值:effect 優先,其次 -discount,皆無則 0。"""
    if coupon.effect is not None:
        return coupon.effect
    if coupon.discount is not None:
        return Decimal("0") - coupon.discount
    return Decimal("0")


def is_coupon_expired(coupon: Coupon, transaction_date: date) -> bool:
    """交易日超過到期日即失效;到期日當天仍有效。無到期日則永不失效。"""
    if coupon.expiry_date is None:
        return False
    return transaction_date > coupon.expiry_date


def is_coupon_below_min_spend(coupon: Coupon, subtotal: Decimal) -> bool:
    """小計未達門檻;門檻含等號(>=)。無門檻則永遠達標。"""
    if coupon.min_spend is None:
        return False
    return subtotal < coupon.min_spend


def apply_coupon(
    coupon: Coupon,
    index: int,
    subtotal: Decimal,
    transaction_date: date,
) -> CouponResult:
    """判斷單張折價券是否生效。過期判斷優先於門檻判斷。"""
    if is_coupon_expired(coupon, transaction_date):
        return CouponResult(index=index, applied=False, reason=REASON_EXPIRED)
    if is_coupon_below_min_spend(coupon, subtotal):
        return CouponResult(
            index=index, applied=False, reason=REASON_BELOW_MIN_SPEND
        )
    return CouponResult(index=index, applied=True, reason=None)


def apply_coupons(
    coupons: list[Coupon],
    subtotal: Decimal,
    transaction_date: date,
) -> tuple[Decimal, list[CouponResult]]:
    """依序套用所有折價券於小計,回傳(加減總和, 每張券的套用結果)。"""
    coupon_effect_sum = Decimal("0")
    results = []
    for index, coupon in enumerate(coupons):
        result = apply_coupon(coupon, index, subtotal, transaction_date)
        results.append(result)
        if result.applied:
            coupon_effect_sum = coupon_effect_sum + resolve_coupon_effect(coupon)
    return coupon_effect_sum, results


def calculate(input_data: CaseInput) -> CalculationResult:
    """計算最終金額:先促銷後折價券,只在最後四捨五入。"""
    subtotal = calculate_subtotal(
        input_data.items, input_data.promotions, input_data.date
    )
    coupon_effect_sum, coupon_results = apply_coupons(
        input_data.coupons, subtotal, input_data.date
    )
    total = round_to_two_places(subtotal + coupon_effect_sum)
    return CalculationResult(
        subtotal=subtotal,
        total=total,
        coupon_results=coupon_results,
    )
