"""計算引擎的單元測試:促銷、小計與最終金額。"""

from datetime import date
from decimal import Decimal

from cart.domain.models import CaseInput, LineItem, Promotion
from cart.services.calculator import (
    calculate,
    calculate_line_total,
    calculate_subtotal,
    round_to_two_places,
)

TRANSACTION_DATE = date(2015, 11, 11)


def make_item(name, category, qty, unit_price):
    return LineItem(
        name=name, category=category, quantity=qty, unit_price=Decimal(unit_price)
    )


def make_promotion(category=None, rate=None, effect=None, date_=None):
    return Promotion(
        date=date_,
        category=category,
        rate=Decimal(rate) if rate is not None else None,
        effect=Decimal(effect) if effect is not None else None,
    )


def test_line_total_without_promotion_is_quantity_times_price():
    item = make_item("啤酒", "酒類", 12, "25.00")
    assert calculate_line_total(item, [], TRANSACTION_DATE) == Decimal("300.00")


def test_line_total_applies_matching_category_rate():
    item = make_item("ipad", "電子", 1, "2399.00")
    promotion = make_promotion(category="電子", rate="0.7", date_=TRANSACTION_DATE)
    assert calculate_line_total(item, [promotion], TRANSACTION_DATE) == Decimal(
        "1679.300"
    )


def test_line_total_ignores_promotion_for_other_category():
    item = make_item("鍵盤", "電子", 2, "349.00")
    promotion = make_promotion(category="日用品", rate="0.7", date_=TRANSACTION_DATE)
    assert calculate_line_total(item, [promotion], TRANSACTION_DATE) == Decimal(
        "698.00"
    )


def test_line_total_ignores_promotion_on_other_date():
    item = make_item("鍵盤", "電子", 2, "349.00")
    promotion = make_promotion(
        category="電子", rate="0.7", date_=date(2015, 12, 25)
    )
    assert calculate_line_total(item, [promotion], TRANSACTION_DATE) == Decimal(
        "698.00"
    )


def test_line_total_multiplies_multiple_matching_rates():
    item = make_item("ipad", "電子", 1, "1000.00")
    promotions = [
        make_promotion(category="電子", rate="0.7", date_=TRANSACTION_DATE),
        make_promotion(rate="0.8"),
    ]
    assert calculate_line_total(item, promotions, TRANSACTION_DATE) == Decimal("560.000")


def test_line_total_adds_effects_and_rates():
    item = make_item("咖啡杯", "日用品", 2, "25.00")
    promotions = [
        make_promotion(category="日用品", rate="0.9"),
        make_promotion(effect="50"),
    ]
    assert calculate_line_total(item, promotions, TRANSACTION_DATE) == Decimal("95.000")


def test_line_total_applies_promotion_without_date_on_any_day():
    item = make_item("咖啡杯", "日用品", 2, "25.00")
    promotion = make_promotion(effect="50")
    assert calculate_line_total(item, [promotion], date(2099, 1, 1)) == Decimal(
        "100.00"
    )


def test_subtotal_sums_line_totals_without_rounding():
    items = [
        make_item("ipad", "電子", 1, "2399.00"),
        make_item("顯示器", "電子", 1, "1799.00"),
        make_item("啤酒", "酒類", 12, "25.00"),
        make_item("麵包", "食品", 5, "9.00"),
    ]
    promotions = [
        make_promotion(category="電子", rate="0.7", date_=TRANSACTION_DATE)
    ]
    assert calculate_subtotal(items, promotions, TRANSACTION_DATE) == Decimal(
        "3283.600"
    )


def test_calculate_case_a_end_to_end():
    from cart.domain.models import Coupon

    items = [
        make_item("ipad", "電子", 1, "2399.00"),
        make_item("顯示器", "電子", 1, "1799.00"),
        make_item("啤酒", "酒類", 12, "25.00"),
        make_item("麵包", "食品", 5, "9.00"),
    ]
    input_data = CaseInput(
        date=TRANSACTION_DATE,
        items=items,
        promotions=[
            make_promotion(category="電子", rate="0.7", date_=TRANSACTION_DATE)
        ],
        coupons=[
            Coupon(
                expiry_date=date(2016, 3, 2),
                min_spend=Decimal("1000"),
                discount=Decimal("200"),
                effect=None,
            )
        ],
    )
    result = calculate(input_data)
    assert result.subtotal == Decimal("3283.600")
    assert result.total == Decimal("3083.60")


def test_round_to_two_places_uses_half_up():
    assert round_to_two_places(Decimal("0.325")) == Decimal("0.33")
    assert round_to_two_places(Decimal("0.324")) == Decimal("0.32")
    assert round_to_two_places(Decimal("0.326")) == Decimal("0.33")


def test_calculator_precision_avoids_float_error():
    items = [
        make_item("餅乾", "食品", 3, "0.10"),
        make_item("蛋糕", "食品", 1, "0.125"),
    ]
    result = calculate(
        CaseInput(date=TRANSACTION_DATE, items=items, promotions=[], coupons=[])
    )
    assert result.subtotal == Decimal("0.425")
    assert result.total == Decimal("0.43")
