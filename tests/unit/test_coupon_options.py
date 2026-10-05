"""優惠券可選清單的單元測試:collect_coupon_options。

直接測 services/checkout.py 的純函式,不經過 HTTP 或檔案。
券狀態必須由後端統一判斷,前端不能自行解讀門檻或到期日。
"""

from datetime import date
from decimal import Decimal

from cart.domain.catalog import Category
from cart.domain.models import Cart, CartItem, Coupon
from cart.services.checkout import (
    COUPON_STATUS_BELOW_THRESHOLD,
    COUPON_STATUS_EXPIRED,
    COUPON_STATUS_USABLE,
    collect_coupon_options,
)


def make_cart(total: str) -> Cart:
    """用單一品項湊出指定原價的購物車,讓門檻判斷可預期。"""
    return Cart(items=[CartItem("麵包", Category.FOOD, Decimal(total), 1)])


def statuses_of(options) -> dict:
    """把可選清單轉成 {券 id: 狀態},方便逐券斷言。"""
    return {option.coupon.id: option.status for option in options}


def test_options_mark_usable_coupon_when_threshold_met():
    coupons = [Coupon(date(2027, 3, 2), Decimal("100"), Decimal("10"), id="C1", name="滿百折十")]
    options = collect_coupon_options(coupons, Decimal("100.00"), date(2026, 11, 11))
    assert statuses_of(options) == {"C1": COUPON_STATUS_USABLE}


def test_options_mark_below_threshold_when_promoted_amount_too_small():
    coupons = [Coupon(date(2027, 3, 2), Decimal("1000"), Decimal("100"), id="C1", name="滿千折百")]
    options = collect_coupon_options(coupons, Decimal("99.00"), date(2026, 11, 11))
    assert statuses_of(options) == {"C1": COUPON_STATUS_BELOW_THRESHOLD}


def test_options_mark_expired_coupon_even_if_threshold_met():
    coupons = [Coupon(date(2025, 6, 30), Decimal("100"), Decimal("10"), id="C1", name="滿百折十")]
    options = collect_coupon_options(coupons, Decimal("9999.00"), date(2026, 11, 11))
    assert statuses_of(options) == {"C1": COUPON_STATUS_EXPIRED}


def test_options_judge_threshold_by_promoted_amount_not_original():
    """門檻以促銷後金額判斷(規則 3):原價過門檻但促銷後未過,仍為未達門檻。"""
    coupons = [Coupon(date(2027, 3, 2), Decimal("3000"), Decimal("500"), id="C1", name="滿三千折五百")]
    options = collect_coupon_options(coupons, Decimal("2938.60"), date(2026, 11, 11))
    assert statuses_of(options) == {"C1": COUPON_STATUS_BELOW_THRESHOLD}


def test_options_report_mixed_statuses_across_coupons():
    """多張券同時出現時,每張各自依自己的門檻與到期日判斷。"""
    coupons = [
        Coupon(date(2027, 6, 30), Decimal("100"), Decimal("10"), id="USABLE", name="滿百折十"),
        Coupon(date(2026, 12, 31), Decimal("3000"), Decimal("500"), id="BELOW", name="滿三千折五百"),
        Coupon(date(2026, 6, 30), Decimal("100"), Decimal("50"), id="EXPIRED", name="過期券"),
    ]
    options = collect_coupon_options(coupons, Decimal("150.00"), date(2026, 11, 11))
    assert statuses_of(options) == {
        "USABLE": COUPON_STATUS_USABLE,
        "BELOW": COUPON_STATUS_BELOW_THRESHOLD,
        "EXPIRED": COUPON_STATUS_EXPIRED,
    }


def test_options_keep_coupon_reference_for_display():
    """清單需保留券本身,讓 API 層能取出 id、名稱與門檻等顯示資訊。"""
    coupon = Coupon(date(2027, 3, 2), Decimal("100"), Decimal("10"), id="C1", name="滿百折十")
    options = collect_coupon_options([coupon], Decimal("100.00"), date(2026, 11, 11))
    assert options[0].coupon is coupon


def test_options_is_empty_when_no_coupons():
    options = collect_coupon_options([], Decimal("100.00"), date(2026, 11, 11))
    assert options == []
