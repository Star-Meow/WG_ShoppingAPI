"""日期與金額解析:把 JSON 字串轉成領域物件可用的 date 與 Decimal。

支援三種日期格式:YYYY-MM-DD、YYYY.MM.DD、YYYY/MM/DD。
金額一律走 Decimal,絕不經過 float。
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from cart.domain.errors import DateFormatError, InvalidPriceError

SUPPORTED_DATE_SEPARATORS = ("-", ".", "/")


def parse_date(text: str) -> date:
    """解析三種分隔格式的日期;不支援的格式或不可能的日期拋 DateFormatError。"""
    parts = None
    for separator in SUPPORTED_DATE_SEPARATORS:
        if separator in text:
            parts = text.split(separator)
            break

    if parts is None or len(parts) != 3:
        raise DateFormatError(f"日期格式應為 YYYY-MM-DD、YYYY.MM.DD 或 YYYY/MM/DD,實際為「{text}」")

    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
    except ValueError:
        raise DateFormatError(f"日期欄位不是整數:「{text}」") from None

    try:
        return date(year, month, day)
    except ValueError:
        raise DateFormatError(f"不是有效的日期:「{text}」") from None


def parse_decimal(text: str, field: str) -> Decimal:
    """把金額欄位解析為 Decimal;不是合法數值時拋 InvalidPriceError。"""
    try:
        return Decimal(text)
    except InvalidOperation:
        raise InvalidPriceError(f"{field}應為數值,實際為「{text}」") from None
