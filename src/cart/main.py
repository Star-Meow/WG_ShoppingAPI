"""FastAPI 應用程式進入點。

API router 必須先註冊,靜態檔掛載放最後,否則 /api 會被靜態檔攔截。
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from cart.api import products
from cart.config import WEB_DIR


def create_app() -> FastAPI:
    """建立並設定 FastAPI 應用程式。"""
    app = FastAPI(title="購物車結算系統")
    app.include_router(products.router)
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
