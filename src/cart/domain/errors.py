"""結算領域的例外類型。

API 層捕捉這些例外後,可對應回適當的 HTTP 狀態碼;
CLI 層捕捉後印出錯誤訊息。兩者都不在領域層處理。
"""


class CheckoutError(Exception):
    """結算領域例外的共同類型,用於 API/CLI 統一捕捉。"""


class ParseError(CheckoutError):
    """測試案例文字不符合規定格式時拋出(欄位缺失、段落數量不對等)。"""


class UnknownProductError(CheckoutError):
    """購物車或目錄中出現未知商品時拋出。"""


class PriceMismatchError(CheckoutError):
    """案例文字所載單價與目錄不一致時拋出。

    結算金額以 CATALOG 為唯一價格來源(decisions.md D4),案例文字的單價
    只做一致性檢查,不吻合時代表輸入與系統目錄脫節,需人工確認。
    """


class CouponNotApplicableError(CheckoutError):
    """優惠券已過期或金額未達門檻時拋出。"""


class ProductNotInPromoCategoryError(CheckoutError):
    """商品不屬於任何促銷品類,但呼叫端要求套用促銷時拋出。"""


class UnknownCouponError(CheckoutError):
    """前端傳來的優惠券代號在系統中找不到時拋出。"""
