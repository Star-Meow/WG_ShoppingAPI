from decimal import Decimal

from cart.domain.catalog import CATALOG, Category, products_by_category


def test_catalog_has_four_categories():
    grouped = products_by_category()
    assert len(grouped) == 4


def test_catalog_has_eighteen_products():
    assert len(CATALOG) == 18


def test_category_product_counts():
    grouped = products_by_category()
    assert len(grouped[Category.ELECTRONICS]) == 5
    assert len(grouped[Category.FOOD]) == 6
    assert len(grouped[Category.DAILY]) == 4
    assert len(grouped[Category.ALCOHOL]) == 3


def test_all_prices_are_decimal():
    for product in CATALOG:
        assert isinstance(product.price, Decimal)
