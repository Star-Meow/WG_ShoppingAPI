"""命令列工具:讀取測試案例檔,解析後計算結算金額並印出。

用法:

    python -m cart.cli <案例檔> [<案例檔> ...]

每個案例印出一行金額(四捨五入到小數 2 位);解析或結算錯誤印到 stderr,
並以非零狀態碼結束。本模組是外層介面,只負責「讀檔 → 解析 → 結算 → 印出」。
"""

import sys
from pathlib import Path

from cart.cli.parser import parse_case_text
from cart.domain.errors import CheckoutError
from cart.services.checkout import calculate_checkout

USAGE = "用法: python -m cart.cli <案例檔> [<案例檔> ...]"


def run_case(path: Path) -> str:
    """讀取單一案例檔,回傳結算金額的字串。"""
    text = path.read_text(encoding="utf-8")
    checkout_input = parse_case_text(text)
    amount = calculate_checkout(checkout_input)
    return str(amount)


def main(argv: list[str]) -> int:
    """依序處理每個案例檔;全部成功回 0,任一失敗回 1,無參數回 2。"""
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2

    exit_code = 0
    for argument in argv:
        try:
            amount = run_case(Path(argument))
        except CheckoutError as error:
            print(f"{argument}: {error}", file=sys.stderr)
            exit_code = 1
            continue
        except OSError as error:
            print(f"{argument}: 無法讀取檔案({error.strerror})", file=sys.stderr)
            exit_code = 1
            continue
        print(amount)
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
