from cart.api.products import build_category_groups


def test_build_returns_four_groups():
    groups = build_category_groups()
    assert len(groups) == 4


def test_build_returns_eighteen_products_in_total():
    groups = build_category_groups()
    total = 0
    for group in groups:
        total += len(group.products)
    assert total == 18


def test_build_returns_prices_as_strings():
    groups = build_category_groups()
    for group in groups:
        for product in group.products:
            assert isinstance(product.price, str)


def test_build_keeps_category_definition_order():
    groups = build_category_groups()
    categories = [group.category for group in groups]
    assert categories == ["電子", "食品", "日用品", "酒類"]
