"""FastAPI 應用程式進入點。

API router 必須先註冊,靜態檔掛載放最後,否則 /api 會被靜態檔攔截。
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from cart.api import checkout, products
from cart.config import WEB_DIR
from cart.domain.errors import CheckoutError, UnknownProductError


def create_app() -> FastAPI:
    """建立並設定 FastAPI 應用程式。"""
    app = FastAPI(title="購物車結算系統")

    @app.exception_handler(UnknownProductError)
    async def handle_unknown_product(_: Request, error: UnknownProductError):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    @app.exception_handler(CheckoutError)
    async def handle_checkout_error(_: Request, error: CheckoutError):
        return JSONResponse(status_code=400, content={"detail": str(error)})

    app.include_router(products.router)
    app.include_router(checkout.router)
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
