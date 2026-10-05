"""命令列文字解析:把測試案例的文字轉成結算領域物件。

本模組只做「字串 → 資料物件」,不計算金額。商品的品類與單價一律由
CATALOG 查得(decisions.md D4:結算金額以目錄為唯一價格來源),案例
文字所載的單價僅用於一致性檢查。

案例格式(段落以空行分隔):

    2015.11.11|0.7|電子            ← 促銷:日期|折扣|品類,可多行,可整段省略

    1*ipad:2399.00                 ← 購物車明細:數量*商品:單價,可多行
    12*啤酒:25.00

    2015.11.11                     ← 結算日
    2016.3.2 1000 200              ← 優惠券:日期 門檻 折額,可省略
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from cart.domain.catalog import Category, find_product_by_name
from cart.domain.errors import ParseError, PriceMismatchError, UnknownProductError
from cart.domain.models import Cart, CartItem, CheckoutInput, Coupon, Promotion


def split_sections(text: str) -> list[list[str]]:
    """以空行把案例文字切成段落;每個段落是一份非空行的清單。"""
    sections: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "":
            sections.append(current)
            current = []
            continue
        current.append(line)
    sections.append(current)
    return sections


def parse_date(text: str) -> date:
    """解析「YYYY.M.D」格式的日期,例如「2015.11.11」。"""
    parts = text.split(".")
    if len(parts) != 3:
        raise ParseError(f"日期格式應為 YYYY.M.D,實際為「{text}」")
    year = parse_int(parts[0], "日期的年")
    month = parse_int(parts[1], "日期的月")
    day = parse_int(parts[2], "日期的日")
    try:
        return date(year, month, day)
    except ValueError:
        raise ParseError(f"不是有效的日期:「{text}」") from None


def parse_int(text: str, field: str) -> int:
    """把文字解析為整數;不是整數時拋出 ParseError。"""
    try:
        return int(text)
    except ValueError:
        raise ParseError(f"{field}應為整數,實際為「{text}」") from None


def parse_decimal(text: str, field: str) -> Decimal:
    """把文字解析為 Decimal;不是數字時拋出 ParseError。"""
    try:
        return Decimal(text)
    except InvalidOperation:
        raise ParseError(f"{field}應為數字,實際為「{text}」") from None


def parse_category(text: str) -> Category:
    """把品類名稱轉為 Category 列舉;未知品類時拋出 ParseError。"""
    try:
        return Category(text)
    except ValueError:
        raise ParseError(f"未知品類:「{text}」") from None


def parse_promotion_line(text: str) -> Promotion:
    """解析促銷行「日期|折扣|品類」,例如「2015.11.11|0.7|電子」。"""
    parts = text.split("|")
    if len(parts) != 3:
        raise ParseError(f"促銷格式應為 日期|折扣|品類,實際為「{text}」")
    return Promotion(
        date=parse_date(parts[0]),
        discount=parse_decimal(parts[1], "促銷折扣"),
        category=parse_category(parts[2]),
    )


def parse_cart_line(text: str) -> CartItem:
    """解析購物車明細行「數量*商品:單價」,例如「1*ipad:2399.00」。

    品類與單價由 CATALOG 查得;案例文字的單價必須與目錄一致。
    """
    quantity_and_price = text.split(":")
    if len(quantity_and_price) != 2:
        raise ParseError(f"購物車明細格式應為 數量*商品:單價,實際為「{text}」")
    quantity_and_name = quantity_and_price[0].split("*")
    if len(quantity_and_name) != 2:
        raise ParseError(f"購物車明細格式應為 數量*商品:單價,實際為「{text}」")

    quantity = parse_int(quantity_and_name[0], "商品數量")
    if quantity <= 0:
        raise ParseError(f"商品數量應為正整數,實際為「{quantity}」")

    product = find_product_by_name(quantity_and_name[1])
    if product is None:
        raise UnknownProductError(f"購物車出現目錄以外的商品:「{quantity_and_name[1]}」")

    stated_price = parse_decimal(quantity_and_price[1], "商品單價")
    if stated_price != product.price:
        raise PriceMismatchError(
            f"「{product.name}」的單價應為 {product.price},案例文字為 {stated_price}"
        )
    return CartItem(
        name=product.name,
        category=product.category,
        unit_price=product.price,
        quantity=quantity,
    )


def parse_coupon_line(text: str) -> Coupon:
    """解析優惠券行「日期 門檻 折額」,例如「2016.3.2 1000 200」。"""
    parts = text.split()
    if len(parts) != 3:
        raise ParseError(f"優惠券格式應為 日期 門檻 折額,實際為「{text}」")
    return Coupon(
        expiry_date=parse_date(parts[0]),
        threshold=parse_decimal(parts[1], "優惠券門檻"),
        discount=parse_decimal(parts[2], "優惠券折額"),
    )


def parse_case_text(text: str) -> CheckoutInput:
    """把整份案例文字解析為一次結算所需的完整輸入。"""
    sections = split_sections(text)
    if len(sections) < 3:
        raise ParseError(
            "案例至少需 3 個段落(促銷 / 購物車 / 結算日與優惠券),"
            f"實際只有 {len(sections)} 段"
        )

    promotions = [parse_promotion_line(line) for line in sections[0]]
    items = [parse_cart_line(line) for line in sections[1]]
    if not items:
        raise ParseError("購物車明細不得為空")

    date_and_coupon: list[str] = []
    for section in sections[2:]:
        for line in section:
            date_and_coupon.append(line)
    if not date_and_coupon:
        raise ParseError("缺少結算日")

    checkout_date = parse_date(date_and_coupon[0])
    coupon_lines = date_and_coupon[1:]
    if len(coupon_lines) > 1:
        raise ParseError("每次結算只能使用一張優惠券")
    coupon = parse_coupon_line(coupon_lines[0]) if coupon_lines else None

    return CheckoutInput(
        cart=Cart(items=items),
        promotions=promotions,
        checkout_date=checkout_date,
        coupon=coupon,
    )
