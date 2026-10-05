"""案例文字解析的單元測試。

解析器只做「字串 → 資料物件」,這裡固定使用內嵌文字,不讀寫檔案。
"""

from datetime import date
from decimal import Decimal

import pytest

from cart.cli.parser import (
    parse_cart_line,
    parse_case_text,
    parse_coupon_line,
    parse_date,
    parse_promotion_line,
)
from cart.domain.catalog import Category
from cart.domain.errors import ParseError, PriceMismatchError, UnknownProductError

CASE_A_TEXT = """2015.11.11|0.7|電子

1*ipad:2399.00
1*顯示器:1799.00
12*啤酒:25.00
5*麵包:9.00

2015.11.11
2016.3.2 1000 200
"""

CASE_B_TEXT = """
3*蔬菜:5.98
8*餐巾紙:3.20

2015.01.01
"""


def test_parse_date_parses_year_month_day():
    assert parse_date("2015.11.11") == date(2015, 11, 11)
    assert parse_date("2016.3.2") == date(2016, 3, 2)


def test_parse_date_rejects_wrong_format():
    with pytest.raises(ParseError):
        parse_date("2015-11-11")


def test_parse_date_rejects_impossible_date():
    with pytest.raises(ParseError):
        parse_date("2015.11.31")


def test_parse_promotion_line_parses_all_three_fields():
    promotion = parse_promotion_line("2015.11.11|0.7|電子")
    assert promotion.date == date(2015, 11, 11)
    assert promotion.discount == Decimal("0.7")
    assert promotion.category == Category.ELECTRONICS


def test_parse_promotion_line_rejects_wrong_format():
    with pytest.raises(ParseError):
        parse_promotion_line("2015.11.11|0.7")


def test_parse_promotion_line_rejects_unknown_category():
    with pytest.raises(ParseError):
        parse_promotion_line("2015.11.11|0.7|家電")


def test_parse_cart_line_takes_category_and_price_from_catalog():
    item = parse_cart_line("12*啤酒:25.00")
    assert item.name == "啤酒"
    assert item.category == Category.ALCOHOL
    assert item.unit_price == Decimal("25.00")
    assert item.quantity == 12


def test_parse_cart_line_rejects_unknown_product():
    with pytest.raises(UnknownProductError):
        parse_cart_line("1*滑鼠:99.00")


def test_parse_cart_line_rejects_price_inconsistent_with_catalog():
    with pytest.raises(PriceMismatchError):
        parse_cart_line("1*啤酒:1.00")


def test_parse_cart_line_rejects_non_positive_quantity():
    with pytest.raises(ParseError):
        parse_cart_line("0*啤酒:25.00")


def test_parse_coupon_line_parses_all_three_fields():
    coupon = parse_coupon_line("2016.3.2 1000 200")
    assert coupon.expiry_date == date(2016, 3, 2)
    assert coupon.threshold == Decimal("1000")
    assert coupon.discount == Decimal("200")


def test_parse_coupon_line_rejects_wrong_format():
    with pytest.raises(ParseError):
        parse_coupon_line("2016.3.2 1000")


def test_parse_case_text_parses_case_a_fully():
    checkout_input = parse_case_text(CASE_A_TEXT)

    assert len(checkout_input.promotions) == 1
    assert checkout_input.promotions[0].category == Category.ELECTRONICS
    assert [item.name for item in checkout_input.cart.items] == [
        "ipad",
        "顯示器",
        "啤酒",
        "麵包",
    ]
    assert checkout_input.checkout_date == date(2015, 11, 11)
    assert checkout_input.coupon is not None
    assert checkout_input.coupon.threshold == Decimal("1000")


def test_parse_case_text_parses_case_b_without_promotion_and_coupon():
    checkout_input = parse_case_text(CASE_B_TEXT)

    assert checkout_input.promotions == []
    assert [item.name for item in checkout_input.cart.items] == ["蔬菜", "餐巾紙"]
    assert checkout_input.checkout_date == date(2015, 1, 1)
    assert checkout_input.coupon is None


def test_parse_case_text_parses_multiple_promotion_lines():
    text = """2015.11.11|0.7|電子
2015.11.11|0.8|食品

1*ipad:2399.00

2015.11.11"""
    checkout_input = parse_case_text(text)
    assert len(checkout_input.promotions) == 2


def test_parse_case_text_rejects_missing_checkout_date():
    with pytest.raises(ParseError):
        parse_case_text("1*ipad:2399.00\n")


def test_parse_case_text_rejects_empty_cart():
    with pytest.raises(ParseError):
        parse_case_text("2015.11.11|0.7|電子\n\n\n2015.11.11")


def test_parse_case_text_rejects_multiple_coupons():
    with pytest.raises(ParseError):
        parse_case_text(
            "1*ipad:2399.00\n\n2015.11.11\n2016.3.2 1000 200\n2016.4.1 500 50"
        )
