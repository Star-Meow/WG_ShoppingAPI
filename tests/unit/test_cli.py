"""命令列工具的測試。

以子程序實際執行 `python -m cart.cli`,驗證題目指定的 CLI 介面。
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def run_cli(*paths) -> subprocess.CompletedProcess:
    """以子程序執行 CLI,PYTHONPATH 指向 src,回傳完成的行程。"""
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    return subprocess.run(
        [sys.executable, "-m", "cart.cli", *[str(path) for path in paths]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_prints_case_a_amount():
    result = run_cli(FIXTURES_DIR / "case_a.txt")
    assert result.returncode == 0
    assert result.stdout.strip() == "3083.60"


def test_cli_prints_one_amount_per_file():
    result = run_cli(FIXTURES_DIR / "case_a.txt", FIXTURES_DIR / "case_b.txt")
    assert result.returncode == 0
    assert result.stdout.split() == ["3083.60", "43.54"]


def test_cli_without_args_prints_usage_and_fails():
    result = run_cli()
    assert result.returncode == 2
    assert "用法" in result.stderr


def test_cli_reports_missing_file():
    result = run_cli(FIXTURES_DIR / "no_such_case.txt")
    assert result.returncode == 1
    assert "無法讀取檔案" in result.stderr


def test_cli_reports_malformed_case(tmp_path):
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("這不是一份案例", encoding="utf-8")
    result = run_cli(bad_file)
    assert result.returncode == 1
    assert result.stdout == ""
