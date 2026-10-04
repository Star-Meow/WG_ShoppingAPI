from fastapi.testclient import TestClient

from cart.main import app


def test_get_products_returns_200_with_four_groups():
    client = TestClient(app)
    response = client.get("/api/products")
    assert response.status_code == 200
    groups = response.json()
    assert len(groups) == 4


def test_get_products_returns_eighteen_items_in_total():
    client = TestClient(app)
    response = client.get("/api/products")
    groups = response.json()
    total = 0
    for group in groups:
        total += len(group["products"])
    assert total == 18


def test_get_products_returns_prices_as_strings():
    client = TestClient(app)
    response = client.get("/api/products")
    groups = response.json()
    for group in groups:
        for product in group["products"]:
            assert isinstance(product["price"], str)


def test_index_returns_html():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
