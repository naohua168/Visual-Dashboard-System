"""测试渲染引擎 — 端到端生成 HTML"""
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).parent.parent
OUTPUT = BASE_DIR / "output"


def has_sheets():
    sheets = BASE_DIR / "data" / "sheets"
    required = ["当年累计收入/当年累计收入.xlsx", "当年累计回款/当年累计回款.xlsx",
                "销售收入/销售收入.xlsx", "销售回款/销售回款.xlsx"]
    man = sheets / "手动维护"
    required_man = ["年度收入总指标", "月度收入指标", "月度回款指标"]
    return (all((sheets / r).exists() for r in required)
            and all(list((man / d).glob("*.xlsx")) for d in required_man))


pytestmark = pytest.mark.skipif(not has_sheets(), reason="data/sheets/ 不完整")


def test_render_generates_html():
    """渲染器应生成有效的 HTML 文件"""
    output_file = OUTPUT / "test_看板.html"
    if output_file.exists():
        output_file.unlink()

    cmd = [sys.executable, "-m", "processors.run", f"--output={output_file}"]
    result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8")

    assert result.returncode == 0, f"渲染失败:\n{result.stderr}"
    assert output_file.exists(), "输出文件未创建"

    html = output_file.read_text(encoding="utf-8")
    # 验证 HTML 结构
    assert html.startswith("<!DOCTYPE html>")
    assert "<html lang=\"zh-CN\">" in html
    # 6 个页面
    for page_id in ["overview", "annual", "monthly", "sales", "yoy", "quarterly"]:
        assert f'id="{page_id}"' in html, f"缺少页面 {page_id}"
    # 6 个导航项（<a data-target="...">）
    nav_count = html.count('<a data-target="')
    assert nav_count == 6, f"应有 6 个导航项，实际 {nav_count}"
    # Chart.js 引用
    assert "chart.js" in html
    # P4 年基线检查
    assert "同比" in html

    output_file.unlink()  # 清理测试文件


def test_render_with_main_pipeline():
    """main.py render 步骤应成功"""
    cmd = [sys.executable, "main.py", "--step=render"]
    result = subprocess.run(
        cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding="utf-8"
    )
    assert result.returncode == 0, f"main.py render 失败:\n{result.stderr}"
