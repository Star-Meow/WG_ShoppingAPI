"""題目驗收案例:讀取 fixture 檔,從文字一路解析、計算到結算金額。

這兩個案例是題目的硬性驗收條件:
  case_a.txt 電子 0.7 折促銷 + 門檻 1000 折 200 的優惠券 → 3083.60
  case_b.txt 無促銷、無優惠券 → 43.54
"""

from decimal import Decimal
from pathlib import Path

import pytest

from cart.cli.parser import parse_case_text
from cart.services.checkout import calculate_checkout

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

EXPECTED_AMOUNTS = {
    "case_a.txt": Decimal("3083.60"),
    "case_b.txt": Decimal("43.54"),
}


@pytest.mark.parametrize("filename,expected", sorted(EXPECTED_AMOUNTS.items()))
def test_acceptance_case_amount(filename: str, expected: Decimal):
    text = (FIXTURES_DIR / filename).read_text(encoding="utf-8")
    checkout_input = parse_case_text(text)
    amount = calculate_checkout(checkout_input)
    assert amount == expected
