"""API 層的回傳資料結構(Pydantic schema)。"""

from pydantic import BaseModel


class ProductOut(BaseModel):
    """回傳給前端的單一商品,價格固定為字串以避免 float 誤差。"""

    name: str
    price: str


class CategoryGroupOut(BaseModel):
    """回傳給前端的單一品類分組。"""

    category: str
    products: list[ProductOut]
