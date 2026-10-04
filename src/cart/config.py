"""集中管理專案的路徑設定,路徑由檔案位置推算,不依賴執行時的工作目錄。"""

from pathlib import Path

# src/cart
PACKAGE_DIR = Path(__file__).resolve().parent
# 專案根目錄 shopping_cart/
PROJECT_ROOT = PACKAGE_DIR.parent.parent

# 前端靜態檔目錄 src/cart/web
WEB_DIR = PACKAGE_DIR / "web"
# 資料目錄 shopping_cart/data
DATA_DIR = PROJECT_ROOT / "data"
