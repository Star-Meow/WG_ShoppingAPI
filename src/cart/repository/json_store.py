"""JSON 檔案存取:全專案唯一讀寫檔案的地方。

- `data/seed.json`:商品目錄以外的種子資料,目前為促銷與優惠券。
- `data/runtime.json`:執行時期產生的狀態(如後台覆寫的當前日期)。

domain 與 services 層不會直接讀寫檔案,一律透過本模組;
本模組只負責「JSON ↔ 領域物件」的轉換,不放業務規則。
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from cart.config import DATA_DIR
from cart.domain.catalog import Category
from cart.domain.models import Coupon, Promotion

SEED_PATH = DATA_DIR / "seed.json"
RUNTIME_PATH = DATA_DIR / "runtime.json"


def _read_json(path: Path) -> dict:
    """讀取 JSON 檔;檔案不存在或內容為空時回傳空 dict。"""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if text == "":
        return {}
    return json.loads(text)


def _parse_date(text: str) -> date:
    """把 'YYYY-MM-DD' 解析為 date。"""
    return date.fromisoformat(text)


def load_promotions(path: Path = SEED_PATH) -> list[Promotion]:
    """從 seed 讀取促銷清單;無資料時回傳空清單。"""
    data = _read_json(path)
    raw_promotions = data.get("promotions", [])
    promotions = []
    for raw in raw_promotions:
        promotions.append(
            Promotion(
                date=_parse_date(raw["date"]),
                discount=Decimal(str(raw["discount"])),
                category=Category(raw["category"]),
                name=raw.get("name", ""),
            )
        )
    return promotions


def load_coupons(path: Path = SEED_PATH) -> list[Coupon]:
    """從 seed 讀取優惠券清單;無資料時回傳空清單。"""
    data = _read_json(path)
    raw_coupons = data.get("coupons", [])
    coupons = []
    for raw in raw_coupons:
        coupons.append(
            Coupon(
                expiry_date=_parse_date(raw["expiry_date"]),
                threshold=Decimal(str(raw["threshold"])),
                discount=Decimal(str(raw["discount"])),
                id=raw["id"],
                name=raw.get("name", raw["id"]),
            )
        )
    return coupons


def find_coupon_by_id(coupon_id: str, path: Path = SEED_PATH) -> Coupon | None:
    """依 id 查找優惠券;查無時回傳 None。"""
    for coupon in load_coupons(path):
        if coupon.id == coupon_id:
            return coupon
    return None


def load_current_date(path: Path = RUNTIME_PATH) -> date | None:
    """讀取後台覆寫的當前日期;未覆寫時回傳 None(代表用系統真實日期)。"""
    data = _read_json(path)
    raw = data.get("current_date")
    if raw is None:
        return None
    return _parse_date(raw)


def save_current_date(value: date | None, path: Path = RUNTIME_PATH) -> None:
    """寫入或清除後台覆寫的當前日期;傳 None 代表切回系統真實日期。"""
    if value is None:
        data = _read_json(path)
        data.pop("current_date", None)
    else:
        data = {"current_date": value.isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
