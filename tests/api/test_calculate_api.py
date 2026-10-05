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
        "total": "4199.30",
        "couponResults": [
            {"index": 0, "applied": True, "reason": None},
            {"index": 1, "applied": True, "reason": None},
        ],
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
