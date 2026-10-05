"""結算 API:接收購物車與優惠券代號,呼叫結算服務後回傳金額明細。

API 層保持極薄,只做「接收 → 呼叫 service → 回傳」,不放業務判斷。
金額由後端依 CATALOG 重取後計算,不接受前端傳價(decisions.md D4)。
"""

from datetime import date

from fastapi import APIRouter

from cart.api.schemas import (
    CheckoutItemIn,
    CheckoutRequest,
    CheckoutResultOut,
    CouponOptionOut,
    CouponOptionsRequest,
    CouponOut,
)
from cart.domain.catalog import find_product_by_name
from cart.domain.errors import UnknownCouponError, UnknownProductError
from cart.domain.models import Cart, CartItem, CheckoutInput
from cart.repository import json_store
from cart.services.checkout import (
    build_checkout_result,
    calculate_promoted_subtotal,
    collect_coupon_options,
)

router = APIRouter(prefix="/api", tags=["checkout"])


def resolve_current_date() -> date:
    """決定「今天」:後台有覆寫就用覆寫值,否則用系統真實日期。

    業務規則不得自行呼叫 date.today(),由這裡(最外層)決定後往內傳。
    """
    overridden = json_store.load_current_date()
    if overridden is not None:
        return overridden
    return date.today()


def build_cart(items: list[CheckoutItemIn]) -> Cart:
    """把前端傳來的明細轉成領域購物車;單價一律由 CATALOG 重取。"""
    cart_items = []
    for item in items:
        product = find_product_by_name(item.name)
        if product is None:
            raise UnknownProductError(f"購物車出現目錄以外的商品:「{item.name}」")
        cart_items.append(
            CartItem(
                name=product.name,
                category=product.category,
                unit_price=product.price,
                quantity=item.quantity,
            )
        )
    return Cart(items=cart_items)


def to_coupon_out(coupon) -> CouponOut:
    """把領域優惠券轉成 API 回傳格式。"""
    return CouponOut(
        id=coupon.id,
        name=coupon.name,
        expiry_date=coupon.expiry_date.isoformat(),
        threshold=str(coupon.threshold),
        discount=str(coupon.discount),
    )


def to_coupon_option_out(option) -> CouponOptionOut:
    """把領域的單張券可選狀態轉成 API 回傳格式。"""
    coupon = option.coupon
    return CouponOptionOut(
        id=coupon.id,
        name=coupon.name,
        expiry_date=coupon.expiry_date.isoformat(),
        threshold=str(coupon.threshold),
        discount=str(coupon.discount),
        status=option.status,
    )


@router.get("/coupons")
def list_coupons() -> list[CouponOut]:
    """列出目前可選的優惠券(前端用來顯示選單,是否可用由結算結果判斷)。"""
    coupons = json_store.load_coupons()
    return [to_coupon_out(coupon) for coupon in coupons]


@router.post("/checkout/coupon-options")
def list_coupon_options(request: CouponOptionsRequest) -> list[CouponOptionOut]:
    """依目前購物車列出每張優惠券的可用狀態,供結帳頁顯示可點選的券清單。

    門檻以促銷折扣後的金額判斷(業務規則 3),金額與狀態一律由後端計算。
    """
    cart = build_cart(request.items)
    checkout_date = resolve_current_date()
    promoted_subtotal = calculate_promoted_subtotal(
        cart, json_store.load_promotions(), checkout_date
    )
    options = collect_coupon_options(
        json_store.load_coupons(), promoted_subtotal, checkout_date
    )
    return [to_coupon_option_out(option) for option in options]


@router.post("/checkout")
def checkout(request: CheckoutRequest) -> CheckoutResultOut:
    """結算購物車:先套促銷再扣優惠券,回傳逐項金額明細。"""
    cart = build_cart(request.items)

    coupon = None
    if request.coupon_id is not None:
        coupon = json_store.find_coupon_by_id(request.coupon_id)
        if coupon is None:
            raise UnknownCouponError(f"未知的優惠券代號:「{request.coupon_id}」")

    input_data = CheckoutInput(
        cart=cart,
        promotions=json_store.load_promotions(),
        checkout_date=resolve_current_date(),
        coupon=coupon,
    )
    result = build_checkout_result(input_data)

    applied_coupon_name = None
    if result.applied_coupon is not None:
        applied_coupon_name = result.applied_coupon.name
    applied_promotion_names = [
        promotion.name for promotion in result.applied_promotions
    ]

    return CheckoutResultOut(
        original_subtotal=str(result.original_subtotal),
        promoted_subtotal=str(result.promoted_subtotal),
        coupon_discount=str(result.coupon_discount),
        total=str(result.total),
        coupon_status=result.coupon_status,
        applied_coupon_name=applied_coupon_name,
        applied_promotion_names=applied_promotion_names,
    )
