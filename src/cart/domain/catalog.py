"""商品目錄的領域資料:品類列舉、商品資料物件與預設目錄。

單價為 MVP 預設值,之後可調整。
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Category(str, Enum):
    """商品品類,值即為前端顯示的中文名稱。"""

    ELECTRONICS = "電子"
    FOOD = "食品"
    DAILY = "日用品"
    ALCOHOL = "酒類"


@dataclass(frozen=True)
class Product:
    """商品資料物件,只負責存放資料。"""

    name: str
    category: Category
    price: Decimal


# MVP 預設目錄,共 4 類 18 項;單價之後可調整
CATALOG: tuple[Product, ...] = (
    # 電子(5)
    Product(name="ipad", category=Category.ELECTRONICS, price=Decimal("2399.00")),
    Product(name="iphone", category=Category.ELECTRONICS, price=Decimal("5999.00")),
    Product(name="顯示器", category=Category.ELECTRONICS, price=Decimal("1799.00")),
    Product(name="筆記型電腦", category=Category.ELECTRONICS, price=Decimal("6999.00")),
    Product(name="鍵盤", category=Category.ELECTRONICS, price=Decimal("349.00")),
    # 食品(6)
    Product(name="麵包", category=Category.FOOD, price=Decimal("9.00")),
    Product(name="餅乾", category=Category.FOOD, price=Decimal("12.00")),
    Product(name="蛋糕", category=Category.FOOD, price=Decimal("45.00")),
    Product(name="牛肉", category=Category.FOOD, price=Decimal("88.00")),
    Product(name="魚", category=Category.FOOD, price=Decimal("36.00")),
    Product(name="蔬菜", category=Category.FOOD, price=Decimal("5.98")),
    # 日用品(4)
    Product(name="餐巾紙", category=Category.DAILY, price=Decimal("3.20")),
    Product(name="收納箱", category=Category.DAILY, price=Decimal("59.00")),
    Product(name="咖啡杯", category=Category.DAILY, price=Decimal("25.00")),
    Product(name="雨傘", category=Category.DAILY, price=Decimal("39.00")),
    # 酒類(3)
    Product(name="啤酒", category=Category.ALCOHOL, price=Decimal("25.00")),
    Product(name="白酒", category=Category.ALCOHOL, price=Decimal("128.00")),
    Product(name="伏特加", category=Category.ALCOHOL, price=Decimal("168.00")),
)


def products_by_category() -> dict[Category, list[Product]]:
    """依品類分組目錄中的商品,分組順序依照 Category 的定義順序。"""
    grouped: dict[Category, list[Product]] = {}
    for product in CATALOG:
        category = product.category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(product)
    return grouped
