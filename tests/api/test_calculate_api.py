"""/api/calculate 的 API 測試:逐一讀取案例檔打 API 並比對預期結果。"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cart.main import app

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


CASE_EXPECTATIONS = {
    "case-1.json": {
        "subtotal": "3283.600",
        "total": "3083.60",
        "couponResults": [{"index": 0, "applied": True, "reason": None}],
    },
    "case-2.json": {
        "subtotal": "43.54",
        "total": "43.54",
        "couponResults": [{"index": 0, "applied": False, "reason": "below_min_spend"}],
    },
    "case-3.json": {
        "subtotal": "5999.00",
        "total": "5999.00",
        "couponResults": [{"index": 0, "applied": False, "reason": "expired"}],
    },
    "case-4.json": {
        "subtotal": "698.00",
        "total": "698.00",
        "couponResults": [],
    },
    "case-5.json": {
        "subtotal": "698.00",
        "total": "698.00",
        "couponResults": [],
    },
    "case-6.json": {
        "subtotal": "4899.300",
        "total": "4399.30",
        "couponResults": [{"index": 0, "applied": True, "reason": None}],
    },
    "case-7.json": {
        "subtotal": "100.00",
        "total": "100.00",
        "couponResults": [],
    },
    "case-8.json": {
        "subtotal": "0.425",
        "total": "0.33",
        "couponResults": [{"index": 0, "applied": True, "reason": None}],
    },
    "case-10.json": {
        "subtotal": "7199.2800",
        "total": "6699.28",
        "couponResults": [{"index": 0, "applied": True, "reason": None}],
    },
    "case-11.json": {
        "subtotal": "0.99",
        "total": "0.69",
        "couponResults": [{"index": 0, "applied": True, "reason": None}],
    },
    "case-12.json": {
        "subtotal": "80.3500",
        "total": "60.35",
        "couponResults": [{"index": 0, "applied": True, "reason": None}],
    },
}


@pytest.mark.parametrize("filename", sorted(CASE_EXPECTATIONS))
def test_case_files_match_expected_results(client, filename):
    payload = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    assert response.json() == CASE_EXPECTATIONS[filename]


def test_calculate_accepts_all_three_date_formats(client):
    for transaction_date in ("2015-11-11", "2015.11.11", "2015/11/11"):
        response = client.post(
            "/api/calculate",
            json={
                "date": transaction_date,
                "items": [
                    {"name": "鍵盤", "category": "電子", "qty": 1, "unitPrice": "100.00"}
                ],
                "promotions": [],
                "coupons": [],
            },
        )
        assert response.status_code == 200
        assert response.json()["total"] == "100.00"


def test_calculate_rejects_bad_date_format_with_400(client):
    response = client.post(
        "/api/calculate",
        json={
            "date": "2015年11月11日",
            "items": [
                {"name": "鍵盤", "category": "電子", "qty": 1, "unitPrice": "100.00"}
            ],
        },
    )
    assert response.status_code == 400
    assert "日期格式" in response.json()["detail"]


def test_calculate_rejects_non_positive_quantity_with_422(client):
    response = client.post(
        "/api/calculate",
        json={
            "date": "2015-11-11",
            "items": [
                {"name": "鍵盤", "category": "電子", "qty": 0, "unitPrice": "100.00"}
            ],
        },
    )
    assert response.status_code == 422


def test_calculate_rejects_empty_cart_with_422(client):
    response = client.post(
        "/api/calculate",
        json={"date": "2015-11-11", "items": []},
    )
    assert response.status_code == 422


def test_calculate_rejects_non_decimal_price_with_400(client):
    response = client.post(
        "/api/calculate",
        json={
            "date": "2015-11-11",
            "items": [
                {"name": "鍵盤", "category": "電子", "qty": 1, "unitPrice": "免費"}
            ],
        },
    )
    assert response.status_code == 400


def test_calculate_defaults_promotions_and_coupons_to_empty(client):
    response = client.post(
        "/api/calculate",
        json={
            "date": "2015-11-11",
            "items": [
                {"name": "鍵盤", "category": "電子", "qty": 2, "unitPrice": "349.00"}
            ],
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "subtotal": "698.00",
        "total": "698.00",
        "couponResults": [],
    }


def test_calculate_prefers_coupon_effect_over_discount(client):
    """規則 6:折價券同時帶 effect 與 discount 時,以 effect 為準( API 層以真實 JSON 驗證)。"""
    response = client.post(
        "/api/calculate",
        json={
            "date": "2015-11-11",
            "items": [
                {"name": "巧克力", "category": "食品", "qty": 1, "unitPrice": "0.99"}
            ],
            "promotions": [],
            "coupons": [
                {
                    "expiryDate": "2015-11-11",
                    "minSpend": "0.99",
                    "discount": "0.50",
                    "effect": "-0.30",
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == "0.69"


def test_calculate_runs_same_case_with_all_three_date_formats(client):
    """同一組促銷與折價券,把交易日改成三種分隔格式,結果必須完全相同。"""
    base_payload = {
        "items": [
            {"name": "牛奶", "category": "生活用品類", "qty": 2, "unitPrice": "45.50"},
            {"name": "雞蛋", "category": "食品", "qty": 1, "unitPrice": "8.00"},
        ],
        "promotions": [
            {
                "date": "2015-11-11",
                "category": "生活用品類",
                "rate": "0.85",
                "effect": "-10",
            },
            {"category": "食品", "effect": "5"},
        ],
        "coupons": [{"expiryDate": "2016-03-02", "minSpend": "50", "discount": "20"}],
    }

    results = []
    for transaction_date in ("2015-11-11", "2015.11.11", "2015/11/11"):
        response = client.post(
            "/api/calculate",
            json={"date": transaction_date, **base_payload},
        )
        assert response.status_code == 200
        results.append(response.json())

    assert results[0] == results[1] == results[2]
    assert results[0]["total"] == "60.35"


def test_calculate_applies_promotion_effect_before_coupon_threshold(client):
    """促銷 effect 先納入小計,再以未四捨五入的小計判斷券門檻。"""
    response = client.post(
        "/api/calculate",
        json={
            "date": "2015-11-11",
            "items": [
                {"name": "餅乾", "category": "食品", "qty": 3, "unitPrice": "0.10"}
            ],
            "promotions": [{"effect": "0.10"}],
            "coupons": [
                {"expiryDate": "2016-03-02", "minSpend": "0.40", "discount": "0.10"}
            ],
        },
    )
    assert response.status_code == 200
    # 0.30 + 0.10 = 0.40 恰到門檻(含等號),券生效
    assert response.json() == {
        "subtotal": "0.40",
        "total": "0.30",
        "couponResults": [{"index": 0, "applied": True, "reason": None}],
    }
