"""結算規則的單元測試:促銷折扣、優惠券判定與金額進位。

直接測 services/checkout.py 的純函式,不經過 HTTP 或檔案。
"""

from datetime import date
from decimal import Decimal

from cart.domain.catalog import Category
from cart.domain.models import Cart, CartItem, CheckoutInput, Coupon, Promotion
from cart.services.checkout import (
    calculate_checkout,
    calculate_coupon_discount,
    calculate_promoted_item_subtotal,
    calculate_promoted_subtotal,
    find_active_promotion,
    is_coupon_applicable,
    is_coupon_expired,
    is_coupon_threshold_met,
    is_promotion_active,
    round_to_two_places,
)

ELECTRONICS_PROMO = Promotion(date(2015, 11, 11), Decimal("0.7"), Category.ELECTRONICS)
COUPON = Coupon(date(2016, 3, 2), Decimal("1000"), Decimal("200"))


def make_item(name: str, category: Category, price: str, quantity: int) -> CartItem:
    """以字串單價建立購物車項目,避免測試裡出現 float。"""
    return CartItem(name, category, Decimal(price), quantity)


def test_round_to_two_places_rounds_half_up():
    assert round_to_two_places(Decimal("100.005")) == Decimal("100.01")
    assert round_to_two_places(Decimal("100.004")) == Decimal("100.00")
    assert round_to_two_places(Decimal("3083.6")) == Decimal("3083.60")


def test_cart_subtotal_sums_items_without_discount():
    cart = Cart(
        items=[
            make_item("ipad", Category.ELECTRONICS, "2399.00", 1),
            make_item("麵包", Category.FOOD, "9.00", 5),
        ]
    )
    assert cart.subtotal() == Decimal("2444.00")


def test_promotion_is_active_only_on_its_date():
    assert is_promotion_active(ELECTRONICS_PROMO, date(2015, 11, 11)) is True
    assert is_promotion_active(ELECTRONICS_PROMO, date(2015, 11, 10)) is False
    assert is_promotion_active(ELECTRONICS_PROMO, date(2015, 11, 12)) is False


def test_find_active_promotion_matches_category_and_date():
    found = find_active_promotion(
        [ELECTRONICS_PROMO], Category.ELECTRONICS, date(2015, 11, 11)
    )
    assert found is ELECTRONICS_PROMO


def test_find_active_promotion_ignores_other_category():
    found = find_active_promotion([ELECTRONICS_PROMO], Category.FOOD, date(2015, 11, 11))
    assert found is None


def test_find_active_promotion_ignores_other_date():
    found = find_active_promotion(
        [ELECTRONICS_PROMO], Category.ELECTRONICS, date(2015, 11, 12)
    )
    assert found is None


def test_find_active_promotion_returns_none_when_no_promotions():
    found = find_active_promotion([], Category.ELECTRONICS, date(2015, 11, 11))
    assert found is None


def test_promoted_item_subtotal_applies_matching_promotion():
    item = make_item("ipad", Category.ELECTRONICS, "2399.00", 1)
    subtotal = calculate_promoted_item_subtotal(item, [ELECTRONICS_PROMO], date(2015, 11, 11))
    assert subtotal == Decimal("1679.30")


def test_promoted_item_subtotal_keeps_price_without_matching_promotion():
    item = make_item("ipad", Category.ELECTRONICS, "2399.00", 1)
    subtotal = calculate_promoted_item_subtotal(item, [ELECTRONICS_PROMO], date(2015, 11, 12))
    assert subtotal == Decimal("2399.00")


def test_promoted_subtotal_discounts_matching_category_only():
    cart = Cart(
        items=[
            make_item("ipad", Category.ELECTRONICS, "2399.00", 1),
            make_item("顯示器", Category.ELECTRONICS, "1799.00", 1),
            make_item("啤酒", Category.ALCOHOL, "25.00", 12),
            make_item("麵包", Category.FOOD, "9.00", 5),
        ]
    )
    promoted = calculate_promoted_subtotal(cart, [ELECTRONICS_PROMO], date(2015, 11, 11))
    assert promoted == Decimal("3283.60")


def test_promoted_subtotal_equals_subtotal_without_active_promotion():
    cart = Cart(items=[make_item("ipad", Category.ELECTRONICS, "2399.00", 1)])
    promoted = calculate_promoted_subtotal(cart, [ELECTRONICS_PROMO], date(2015, 11, 12))
    assert promoted == Decimal("2399.00")


def test_coupon_is_valid_on_and_before_expiry_date():
    assert is_coupon_expired(COUPON, date(2016, 3, 1)) is False
    assert is_coupon_expired(COUPON, date(2016, 3, 2)) is False


def test_coupon_is_expired_after_expiry_date():
    assert is_coupon_expired(COUPON, date(2016, 3, 3)) is True


def test_coupon_threshold_includes_the_threshold_amount():
    assert is_coupon_threshold_met(COUPON, Decimal("999.99")) is False
    assert is_coupon_threshold_met(COUPON, Decimal("1000")) is True
    assert is_coupon_threshold_met(COUPON, Decimal("1000.01")) is True


def test_coupon_applicable_requires_valid_date_and_threshold():
    assert is_coupon_applicable(COUPON, Decimal("2000"), date(2016, 3, 2)) is True
    assert is_coupon_applicable(COUPON, Decimal("2000"), date(2016, 3, 3)) is False
    assert is_coupon_applicable(COUPON, Decimal("999"), date(2016, 3, 2)) is False


def test_coupon_discount_is_zero_without_coupon():
    assert calculate_coupon_discount(None, Decimal("9999"), date(2016, 3, 2)) == Decimal("0")


def test_coupon_discount_is_zero_when_not_applicable():
    assert calculate_coupon_discount(COUPON, Decimal("999"), date(2016, 3, 2)) == Decimal("0")
    assert calculate_coupon_discount(COUPON, Decimal("9999"), date(2016, 3, 3)) == Decimal("0")


def test_coupon_discount_amount_when_applicable():
    discount = calculate_coupon_discount(COUPON, Decimal("3283.60"), date(2015, 11, 11))
    assert discount == Decimal("200")


def test_checkout_applies_promotion_then_coupon():
    checkout_input = CheckoutInput(
        cart=Cart(
            items=[
                make_item("ipad", Category.ELECTRONICS, "2399.00", 1),
                make_item("顯示器", Category.ELECTRONICS, "1799.00", 1),
                make_item("啤酒", Category.ALCOHOL, "25.00", 12),
                make_item("麵包", Category.FOOD, "9.00", 5),
            ]
        ),
        promotions=[ELECTRONICS_PROMO],
        checkout_date=date(2015, 11, 11),
        coupon=COUPON,
    )
    assert calculate_checkout(checkout_input) == Decimal("3083.60")


def test_checkout_without_promotion_and_coupon():
    checkout_input = CheckoutInput(
        cart=Cart(
            items=[
                make_item("蔬菜", Category.FOOD, "5.98", 3),
                make_item("餐巾紙", Category.DAILY, "3.20", 8),
            ]
        ),
        promotions=[],
        checkout_date=date(2015, 1, 1),
        coupon=None,
    )
    assert calculate_checkout(checkout_input) == Decimal("43.54")


def test_coupon_threshold_is_judged_after_promotion_discount():
    """原價過門檻但促銷後未過門檻時,優惠券不得折抵。"""
    promotion = Promotion(date(2015, 6, 1), Decimal("0.4"), Category.ELECTRONICS)
    checkout_input = CheckoutInput(
        cart=Cart(items=[make_item("ipad", Category.ELECTRONICS, "2399.00", 1)]),
        promotions=[promotion],
        checkout_date=date(2015, 6, 1),
        coupon=COUPON,
    )
    assert calculate_checkout(checkout_input) == Decimal("959.60")


def test_checkout_rounds_half_up_to_two_places():
    checkout_input = CheckoutInput(
        cart=Cart(items=[make_item("蛋糕", Category.FOOD, "9.995", 3)]),
        promotions=[],
        checkout_date=date(2015, 1, 1),
        coupon=None,
    )
    assert calculate_checkout(checkout_input) == Decimal("29.99")
