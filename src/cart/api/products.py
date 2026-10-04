"""商品瀏覽 API:將領域目錄轉成回傳格式並透過 HTTP 提供。"""

from decimal import Decimal

from fastapi import APIRouter

from cart.api.schemas import CategoryGroupOut, ProductOut
from cart.domain.catalog import Category, Product, products_by_category

router = APIRouter(prefix="/api", tags=["products"])


def format_price(price: Decimal) -> str:
    """將金額格式化為固定兩位小數的字串。"""
    return str(price.quantize(Decimal("0.01")))


def to_product_out(product: Product) -> ProductOut:
    """將領域商品轉成 API 回傳格式。"""
    return ProductOut(name=product.name, price=format_price(product.price))


def build_category_groups() -> list[CategoryGroupOut]:
    """將目錄轉成按品類分組的回傳格式,順序依照 Category 的定義順序。

    這是純函式,不經過 HTTP 也能直接呼叫測試。
    """
    grouped = products_by_category()
    groups: list[CategoryGroupOut] = []
    for category in Category:
        products = grouped.get(category, [])
        product_outs = [to_product_out(product) for product in products]
        groups.append(CategoryGroupOut(category=category.value, products=product_outs))
    return groups


@router.get("/products")
def list_products() -> list[CategoryGroupOut]:
    """回傳全部商品,依品類分組。"""
    return build_category_groups()
