"""結算明細的單元測試:build_checkout_result 與券狀態判斷。

直接測 services/checkout.py 的純函式,不經過 HTTP 或檔案。
"""

from datetime import date
from decimal import Decimal

from cart.domain.catalog import Category
from cart.domain.models import Cart, CartItem, CheckoutInput, Coupon, Promotion
from cart.services.checkout import (
    COUPON_STATUS_BELOW_THRESHOLD,
    COUPON_STATUS_EXPIRED,
    COUPON_STATUS_USABLE,
    build_checkout_result,
)

ELECTRONICS_PROMO = Promotion(
    date(2026, 11, 11), Decimal("0.7"), Category.ELECTRONICS, name="雙 11 電子品類 7 折"
)
COUPON = Coupon(date(2027, 3, 2), Decimal("1000"), Decimal("200"), id="C1", name="滿千折兩百")


def make_item(name: str, category: Category, price: str, quantity: int) -> CartItem:
    """以字串單價建立購物車項目,避免測試裡出現 float。"""
    return CartItem(name, category, Decimal(price), quantity)


def make_cart() -> Cart:
    """Case A 的購物車:電子兩項 + 酒類 + 食品。"""
    return Cart(
        items=[
            make_item("ipad", Category.ELECTRONICS, "2399.00", 1),
            make_item("顯示器", Category.ELECTRONICS, "1799.00", 1),
            make_item("啤酒", Category.ALCOHOL, "25.00", 12),
            make_item("麵包", Category.FOOD, "9.00", 5),
        ]
    )


def test_result_reports_original_and_promoted_subtotals():
    input_data = CheckoutInput(
        cart=make_cart(),
        promotions=[ELECTRONICS_PROMO],
        checkout_date=date(2026, 11, 11),
    )
    result = build_checkout_result(input_data)
    assert result.original_subtotal == Decimal("4543.00")
    assert result.promoted_subtotal == Decimal("3283.60")


def test_result_lists_applied_promotion_by_name():
    input_data = CheckoutInput(
        cart=make_cart(),
        promotions=[ELECTRONICS_PROMO],
        checkout_date=date(2026, 11, 11),
    )
    result = build_checkout_result(input_data)
    assert [promotion.name for promotion in result.applied_promotions] == ["雙 11 電子品類 7 折"]


def test_result_applies_coupon_after_promotion():
    input_data = CheckoutInput(
        cart=make_cart(),
        promotions=[ELECTRONICS_PROMO],
        checkout_date=date(2026, 11, 11),
        coupon=COUPON,
    )
    result = build_checkout_result(input_data)
    assert result.coupon_discount == Decimal("200")
    assert result.total == Decimal("3083.60")
    assert result.applied_coupon is COUPON


def test_result_marks_expired_coupon_and_forgets_discount():
    expired = Coupon(date(2025, 3, 2), Decimal("1000"), Decimal("200"), id="C1", name="滿千折兩百")
    input_data = CheckoutInput(
        cart=make_cart(),
        promotions=[],
        checkout_date=date(2026, 11, 11),
        coupon=expired,
    )
    result = build_checkout_result(input_data)
    assert result.coupon_status == COUPON_STATUS_EXPIRED
    assert result.coupon_discount == Decimal("0")
    assert result.applied_coupon is None


def test_result_marks_coupon_below_promoted_threshold():
    below_threshold = Coupon(date(2027, 3, 2), Decimal("9999"), Decimal("200"), id="C1", name="滿千折兩百")
    input_data = CheckoutInput(
        cart=Cart(items=[make_item("麵包", Category.FOOD, "9.00", 1)]),
        promotions=[],
        checkout_date=date(2026, 11, 11),
        coupon=below_threshold,
    )
    result = build_checkout_result(input_data)
    assert result.coupon_status == COUPON_STATUS_BELOW_THRESHOLD
    assert result.coupon_discount == Decimal("0")


def test_result_reports_usable_when_coupon_applies():
    input_data = CheckoutInput(
        cart=make_cart(),
        promotions=[],
        checkout_date=date(2026, 11, 11),
        coupon=COUPON,
    )
    result = build_checkout_result(input_data)
    assert result.coupon_status == COUPON_STATUS_USABLE


def test_result_reports_usable_when_no_coupon():
    input_data = CheckoutInput(
        cart=make_cart(),
        promotions=[],
        checkout_date=date(2026, 11, 11),
    )
    result = build_checkout_result(input_data)
    assert result.coupon_status == COUPON_STATUS_USABLE
    assert result.applied_coupon is None
