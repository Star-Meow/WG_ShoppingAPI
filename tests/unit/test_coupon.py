"""折價券套用邏輯的單元測試。"""

from datetime import date
from decimal import Decimal

from cart.domain.models import Coupon
from cart.services.calculator import (
    REASON_BELOW_MIN_SPEND,
    REASON_EXPIRED,
    apply_coupon,
    apply_coupons,
    is_coupon_below_min_spend,
    is_coupon_expired,
    resolve_coupon_effect,
)

TRANSACTION_DATE = date(2015, 11, 11)


def make_coupon(
    expiry_date=None, min_spend=None, discount=None, effect=None
):
    return Coupon(
        expiry_date=expiry_date,
        min_spend=min_spend,
        discount=discount,
        effect=effect,
    )


def test_resolve_coupon_effect_negates_discount():
    coupon = make_coupon(discount=Decimal("200"))
    assert resolve_coupon_effect(coupon) == Decimal("-200")


def test_resolve_coupon_effect_prefers_effect_over_discount():
    coupon = make_coupon(discount=Decimal("200"), effect=Decimal("-50"))
    assert resolve_coupon_effect(coupon) == Decimal("-50")


def test_resolve_coupon_effect_allows_positive_service_fee():
    coupon = make_coupon(effect=Decimal("50"))
    assert resolve_coupon_effect(coupon) == Decimal("50")


def test_resolve_coupon_effect_is_zero_without_any_field():
    assert resolve_coupon_effect(make_coupon()) == Decimal("0")


def test_coupon_is_expired_after_expiry_date():
    coupon = make_coupon(expiry_date=date(2016, 3, 2))
    assert is_coupon_expired(coupon, date(2016, 3, 3))
    assert not is_coupon_expired(coupon, date(2016, 3, 2))


def test_coupon_without_expiry_date_never_expires():
    assert not is_coupon_expired(make_coupon(), date(2099, 1, 1))


def test_min_spend_includes_the_threshold():
    coupon = make_coupon(min_spend=Decimal("1000"))
    assert not is_coupon_below_min_spend(coupon, Decimal("1000"))
    assert is_coupon_below_min_spend(coupon, Decimal("999.99"))


def test_min_spend_judged_by_unrounded_subtotal():
    coupon = make_coupon(min_spend=Decimal("0.425"))
    assert not is_coupon_below_min_spend(coupon, Decimal("0.425"))


def test_apply_coupon_marks_expired_before_threshold():
    # 到期日早於交易日 → 過期,即使門檻也未達,過期原因優先回報
    coupon = make_coupon(
        expiry_date=date(2014, 3, 2), min_spend=Decimal("100000")
    )
    result = apply_coupon(coupon, 0, Decimal("500.00"), TRANSACTION_DATE)
    assert result.applied is False
    assert result.reason == REASON_EXPIRED


def test_apply_coupon_marks_below_min_spend():
    coupon = make_coupon(
        expiry_date=date(2016, 3, 2), min_spend=Decimal("1000")
    )
    result = apply_coupon(coupon, 0, Decimal("500.00"), TRANSACTION_DATE)
    assert result.applied is False
    assert result.reason == REASON_BELOW_MIN_SPEND


def test_apply_coupon_marks_usable_when_date_and_threshold_met():
    coupon = make_coupon(
        expiry_date=date(2016, 3, 2), min_spend=Decimal("1000")
    )
    result = apply_coupon(coupon, 0, Decimal("1500.00"), TRANSACTION_DATE)
    assert result.applied is True
    assert result.reason is None


def test_apply_coupons_applies_each_usable_coupon_in_order():
    coupons = [
        make_coupon(
            expiry_date=date(2016, 3, 2), min_spend=Decimal("1000"), discount=Decimal("500")
        ),
        make_coupon(
            expiry_date=date(2016, 3, 2), min_spend=Decimal("1000"), discount=Decimal("200")
        ),
    ]
    effect_sum, results = apply_coupons(coupons, Decimal("4899.30"), TRANSACTION_DATE)
    assert effect_sum == Decimal("-700")
    assert [r.applied for r in results] == [True, True]


def test_apply_coupons_reports_skipped_coupons_and_keeps_others():
    coupons = [
        make_coupon(
            expiry_date=date(2016, 3, 2), min_spend=Decimal("1000"), discount=Decimal("200")
        ),
        make_coupon(
            expiry_date=date(2014, 3, 2), min_spend=Decimal("1000"), discount=Decimal("100")
        ),
    ]
    effect_sum, results = apply_coupons(coupons, Decimal("1500.00"), TRANSACTION_DATE)
    assert effect_sum == Decimal("-200")
    assert results[0].applied is True
    assert results[1].applied is False
    assert results[1].reason == REASON_EXPIRED


def test_apply_coupons_empty_list_has_no_effect():
    effect_sum, results = apply_coupons([], Decimal("500.00"), TRANSACTION_DATE)
    assert effect_sum == Decimal("0")
    assert results == []
