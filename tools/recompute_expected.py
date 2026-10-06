"""重算所有 fixture 的期望值,產生可直接貼回測試的 Python 字典。

用途:改完 tests/fixtures/case-N.json 的單價、數量或折扣後,執行本腳本即可取得
新的期望值。貼回 tests/api/test_calculate_api.py 的 CASE_EXPECTATIONS 後,
再用 pytest 驗證新數字是否符合預期。

注意:本腳本只是「把現況算出來」,不能取代人工確認。貼回之前請先判斷新數字
是否正確——測試的價值在於斷言「已知正確的答案」,而非「程式現在的輸出」。
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from cart.main import app

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def format_coupon_results(coupon_results):
    """把券結果格式化成測試檔使用的字串寫法。"""
    entries = []
    for result in coupon_results:
        reason = "None" if result["reason"] is None else f'"{result["reason"]}"'
        entries.append(
            f'{{"index": {result["index"]}, '
            f'"applied": {str(result["applied"])}, '
            f'"reason": {reason}}}'
        )
    return "[" + ", ".join(entries) + "]"


def main():
    client = TestClient(app)
    fixtures = sorted(FIXTURES_DIR.glob("case-*.json"))

    print("CASE_EXPECTATIONS = {")
    for fixture in fixtures:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        response = client.post("/api/calculate", json=payload)
        if response.status_code != 200:
            print(f'    # {fixture.name}: HTTP {response.status_code}, 跳過')
            continue
        result = response.json()
        print(f'    "{fixture.name}": {{')
        print(f'        "subtotal": "{result["subtotal"]}",')
        print(f'        "total": "{result["total"]}",')
        print(f'        "couponResults": {format_coupon_results(result["couponResults"])},')
        print("    },")
    print("}")


if __name__ == "__main__":
    main()
