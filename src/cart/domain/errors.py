"""領域錯誤:計算過程的例外階層。

所有錯誤都是「輸入不符合規格」,統一由 API 層轉成 HTTP 400。
"""


class CalculationError(Exception):
    """計算錯誤的基底類別,供 API 層統一捕捉。"""


class DateFormatError(CalculationError):
    """日期格式不屬於支援的三種格式之一。"""


class InvalidQuantityError(CalculationError):
    """商品數量不為正整數。"""


class InvalidPriceError(CalculationError):
    """商品單價或促銷/折價券的金額欄位不是合法數值。"""


class EmptyCartError(CalculationError):
    """購物車明細為空,無法計算。"""
