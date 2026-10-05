"""結算 API 的測試:優惠券清單、結算明細與錯誤對應 HTTP 狀態碼。

使用 TestClient 打真實的 HTTP 往返;結算金額由後端計算,前端不傳價。
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from cart.main import app
from cart.repository import json_store

CASE_A_ITEMS = [
    {"name": "ipad", "quantity": 1},
    {"name": "顯示器", "quantity": 1},
    {"name": "啤酒", "quantity": 12},
    {"name": "麵包", "quantity": 5},
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def system_date():
    """測試結束後清除後台日期覆寫,避免影響其他測試。"""
    yield
    json_store.save_current_date(None)


def test_list_coupons_returns_200(client: TestClient):
    response = client.get("/api/coupons")
    assert response.status_code == 200
    coupons = response.json()
    assert len(coupons) > 0
    for coupon in coupons:
        assert isinstance(coupon["id"], str)
        assert isinstance(coupon["name"], str)
        assert isinstance(coupon["threshold"], str)
        assert isinstance(coupon["discount"], str)


def test_checkout_without_coupon_returns_original_total(client: TestClient):
    response = client.post(
        "/api/checkout", json={"items": [{"name": "蔬菜", "quantity": 3}, {"name": "餐巾紙", "quantity": 8}]}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["original_subtotal"] == "43.54"
    assert result["promoted_subtotal"] == "43.54"
    assert result["coupon_discount"] == "0.00"
    assert result["total"] == "43.54"


def test_checkout_reports_promotion_discount_on_promo_date(client: TestClient, system_date):
    json_store.save_current_date(date(2026, 11, 11))
    response = client.post("/api/checkout", json={"items": CASE_A_ITEMS})
    assert response.status_code == 200
    result = response.json()
    assert result["original_subtotal"] == "4543.00"
    assert result["promoted_subtotal"] == "3283.60"
    assert result["total"] == "3283.60"
    assert "雙 11 電子品類 7 折" in result["applied_promotion_names"]


def test_checkout_applies_coupon_after_promotion(client: TestClient, system_date):
    json_store.save_current_date(date(2026, 11, 11))
    response = client.post(
        "/api/checkout",
        json={"items": CASE_A_ITEMS, "coupon_id": "COUPON-1000-100"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["promoted_subtotal"] == "3283.60"
    assert result["coupon_discount"] == "100.00"
    assert result["total"] == "3183.60"
    assert result["applied_coupon_name"] == "滿千折百"


def test_checkout_marks_expired_coupon_without_discount(client: TestClient):
    response = client.post(
        "/api/checkout",
        json={"items": [{"name": "ipad", "quantity": 1}], "coupon_id": "COUPON-EXPIRED-50"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["coupon_status"] == "expired"
    assert result["coupon_discount"] == "0.00"
    assert result["applied_coupon_name"] is None


def test_checkout_marks_coupon_below_threshold(client: TestClient):
    response = client.post(
        "/api/checkout",
        json={"items": [{"name": "麵包", "quantity": 1}], "coupon_id": "COUPON-1000-100"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["coupon_status"] == "below_threshold"
    assert result["coupon_discount"] == "0.00"


def test_checkout_rejects_unknown_product_with_400(client: TestClient):
    response = client.post("/api/checkout", json={"items": [{"name": "未知商品", "quantity": 1}]})
    assert response.status_code == 400
    assert "未知商品" in response.json()["detail"]


def test_checkout_rejects_unknown_coupon_with_400(client: TestClient):
    response = client.post(
        "/api/checkout",
        json={"items": [{"name": "ipad", "quantity": 1}], "coupon_id": "NO_SUCH_COUPON"},
    )
    assert response.status_code == 400
    assert "NO_SUCH_COUPON" in response.json()["detail"]
