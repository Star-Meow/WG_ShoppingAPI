"""計算 API:接收購物車與促銷/折價券 JSON,呼叫計算引擎後回傳金額。

API 層保持極薄,只做「接收 → 呼叫 service → 回傳」,不放業務判斷。
金額與日期由請求 JSON 帶入,不查目錄、不讀系統時間。
"""

from fastapi import APIRouter

from cart.api.schemas import (
    CalculateRequest,
    CalculateResultOut,
    CouponResultOut,
)
from cart.domain.models import (
    CaseInput,
    Coupon,
    LineItem,
    Promotion,
)
from cart.services.calculator import calculate
from cart.services.date_parsing import parse_date, parse_decimal

router = APIRouter(prefix="/api", tags=["calculate"])


def build_line_item(item) -> LineItem:
    """把 API 層的品項轉成領域物件;單價由請求帶入。"""
    return LineItem(
        name=item.name,
        category=item.category,
        quantity=item.qty,
        unit_price=parse_decimal(item.unitPrice, "品項單價"),
    )


def build_promotion(promotion) -> Promotion:
    """把 API 層的促銷轉成領域物件;日期與金額為空則保留 None。"""
    return Promotion(
        date=parse_date(promotion.date) if promotion.date is not None else None,
        category=promotion.category,
        rate=parse_decimal(promotion.rate, "促銷 rate")
        if promotion.rate is not None
        else None,
        effect=parse_decimal(promotion.effect, "促銷 effect")
        if promotion.effect is not None
        else None,
    )


def build_coupon(coupon) -> Coupon:
    """把 API 層的折價券轉成領域物件;discount 為正數,原樣保留待套用時轉負。"""
    return Coupon(
        expiry_date=parse_date(coupon.expiryDate)
        if coupon.expiryDate is not None
        else None,
        min_spend=parse_decimal(coupon.minSpend, "折價券 minSpend")
        if coupon.minSpend is not None
        else None,
        discount=parse_decimal(coupon.discount, "折價券 discount")
        if coupon.discount is not None
        else None,
        effect=parse_decimal(coupon.effect, "折價券 effect")
        if coupon.effect is not None
        else None,
    )


def build_case_input(request: CalculateRequest) -> CaseInput:
    """把完整請求轉成一次計算所需的領域輸入。"""
    return CaseInput(
        date=parse_date(request.date),
        items=[build_line_item(item) for item in request.items],
        promotions=[build_promotion(p) for p in request.promotions],
        coupons=[build_coupon(c) for c in request.coupons],
    )


def to_coupon_result_out(result) -> CouponResultOut:
    """把領域的折價券結果轉成 API 回傳格式。"""
    return CouponResultOut(
        index=result.index, applied=result.applied, reason=result.reason
    )


@router.post("/calculate")
def calculate_total(request: CalculateRequest) -> CalculateResultOut:
    """依促銷與折價券計算最終金額;先促銷後折價券,最後四捨五入到小數 2 位。"""
    result = calculate(build_case_input(request))
    return CalculateResultOut(
        subtotal=str(result.subtotal),
        total=str(result.total),
        couponResults=[to_coupon_result_out(r) for r in result.coupon_results],
    )
