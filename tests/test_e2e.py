"""端到端测试 — 调用真实清洗引擎（需真实数据存在）

运行前提：data/raw/ 下放置了真实 Excel 文件
未放置数据时这些测试会被 skip。
"""
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).parent.parent
RAW_FIN = BASE_DIR / "data" / "raw" / "财务端数据"
RAW_OPS = BASE_DIR / "data" / "raw" / "运营端数据"
SHEETS = BASE_DIR / "data" / "sheets"


def has_raw_data():
    """检查是否存在原始数据"""
    if not RAW_FIN.exists() or not RAW_OPS.exists():
        return False
    fin_files = list(RAW_FIN.glob("*.xlsx"))
    ops_files = list(RAW_OPS.glob("*.xls"))
    return len(fin_files) >= 3 and len(ops_files) >= 2


pytestmark = pytest.mark.skipif(
    not has_raw_data(),
    reason="未检测到 data/raw/ 下的原始 Excel，跳过端到端测试",
)


def run_module(module, extra_args=None):
    cmd = [sys.executable, "-m", module]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(
        cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode, result.stdout + result.stderr


class TestEndToEndIncome:
    def test_clean_income(self):
        rc, out = run_module("engine.income_payment.run", ["--type=收入"])
        assert rc == 0, f"清洗收入失败:\n{out}"
        # 三路输出文件应存在
        assert (SHEETS / "月收入" / "月收入.xlsx").exists()
        assert (SHEETS / "当年累计收入" / "当年累计收入.xlsx").exists()
        assert (SHEETS / "季度累计收入" / "季度累计收入.xlsx").exists()

    def test_clean_payment(self):
        rc, out = run_module("engine.income_payment.run", ["--type=回款"])
        assert rc == 0, f"清洗回款失败:\n{out}"
        assert (SHEETS / "月回款" / "月回款.xlsx").exists()
        assert (SHEETS / "当年累计回款" / "当年累计回款.xlsx").exists()
        assert (SHEETS / "季度累计回款" / "季度累计回款.xlsx").exists()


class TestEndToEndSales:
    def test_split_income(self):
        rc, out = run_module("engine.sales.run", ["--type=收入"])
        assert rc == 0, f"拆分销售收入失败:\n{out}"
        assert (SHEETS / "销售收入" / "销售收入.xlsx").exists()

    def test_split_payment(self):
        rc, out = run_module("engine.sales.run", ["--type=回款"])
        assert rc == 0, f"拆分销售回款失败:\n{out}"
        assert (SHEETS / "销售回款" / "销售回款.xlsx").exists()


class TestEndToEndPipeline:
    def test_main_full_pipeline(self):
        """python main.py 一键全流程"""
        rc, out = subprocess.run(
            [sys.executable, "main.py"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).returncode, None
        assert rc == 0
