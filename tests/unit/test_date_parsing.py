"""日期與金額解析的單元測試。"""

from datetime import date

import pytest

from cart.domain.errors import DateFormatError, InvalidPriceError
from cart.services.date_parsing import parse_date, parse_decimal


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2015-11-11", date(2015, 11, 11)),
        ("2015.11.11", date(2015, 11, 11)),
        ("2015/11/11", date(2015, 11, 11)),
        ("2016.3.2", date(2016, 3, 2)),
    ],
)
def test_parse_date_accepts_three_separators(text, expected):
    assert parse_date(text) == expected


def test_parse_date_accepts_zero_padded_and_single_digit():
    assert parse_date("2015-1-5") == date(2015, 1, 5)


@pytest.mark.parametrize(
    "text",
    [
        "2015年11月11日",
        "11/11/2015",
        "2015-11",
        "2015.11.11.11",
        "2015-13-01",
        "2015-02-30",
        "not-a-date",
    ],
)
def test_parse_date_rejects_unsupported_or_impossible_dates(text):
    with pytest.raises(DateFormatError):
        parse_date(text)


def test_parse_decimal_keeps_exact_value():
    assert str(parse_decimal("0.125", "單價")) == "0.125"


def test_parse_decimal_rejects_non_number():
    with pytest.raises(InvalidPriceError):
        parse_decimal("abc", "單價")
