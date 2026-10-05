"""FastAPI 應用程式進入點。

只註冊計算 API;領域錯誤統一轉成 HTTP 400。
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cart.api import calculate
from cart.domain.errors import CalculationError


def create_app() -> FastAPI:
    """建立並設定 FastAPI 應用程式。"""
    app = FastAPI(title="購物車結算計算 API")

    @app.exception_handler(CalculationError)
    async def handle_calculation_error(_: Request, error: CalculationError):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    app.include_router(calculate.router)
    return app


app = create_app()
