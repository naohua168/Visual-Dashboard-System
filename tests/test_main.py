"""测试顶层调度器 main.py — 参数解析与预检"""
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).parent.parent
MAIN_PY = BASE_DIR / "main.py"


def run_main(args=None):
    """以 subprocess 执行 main.py，返回 (returncode, stdout)"""
    cmd = [sys.executable, str(MAIN_PY)]
    if args:
        cmd.extend(args)
    result = subprocess.run(
        cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode, result.stdout + result.stderr


class TestArgumentParsing:
    def test_no_args_runs_full_pipeline(self):
        # 不带参数应执行全部步骤（依赖真实数据，可能成功或失败）
        # 这里只验证程序能启动并打印 banner
        rc, out = run_main(["--list"])
        assert rc == 0
        assert "可用步骤" in out
        assert "clean" in out
        assert "split" in out

    def test_help(self):
        rc, out = run_main(["--help"])
        assert rc == 0
        assert "Visual Dashboard System" in out
        assert "--type" in out
        assert "--step" in out
        assert "--dry-run" in out


class TestDryRun:
    def test_dry_run_passes_preflight(self):
        """预检应通过（依赖配置与 mappings 已就位）"""
        rc, out = run_main(["--dry-run"])
        # rc=0 表示预检通过
        assert rc == 0, f"预检失败:\n{out}"
        assert "预检通过" in out
        assert "engine.income_payment.run" in out
        assert "engine.sales.run" in out
        assert "processors.run" in out  # 渲染步骤

    def test_dry_run_with_type(self):
        rc, out = run_main(["--dry-run", "--type=收入"])
        assert rc == 0
        assert "--type=收入" in out


class TestInvalidArgs:
    def test_invalid_type(self):
        rc, out = run_main(["--type=不存在的"])
        assert rc != 0  # argparse 拒绝

    def test_invalid_step(self):
        rc, out = run_main(["--step=不存在的"])
        assert rc != 0

    def test_invalid_range_order(self):
        # --from 在 --to 之后（无步骤可执行）
        rc, out = run_main(["--from=split", "--to=clean"])
        assert rc == 1
        assert "无步骤" in out
