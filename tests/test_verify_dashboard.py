# Author: naohua168 <bai_bai168@qq.com>
"""交付物校验测试 —— scripts/verify_dashboard.py

覆盖：数据总表缺失、必需 sheet 为空、齐全通过、**按日期找产物**、
销售完成度表（按需产物）缺失不报错、旧文件不冒充当天产物。
（HTML 的 JS 语法校验需要 node，这里只测交付物部分与目录解析。）
"""
import pytest

from engine.core.io_utils import save_excel
from scripts import verify_dashboard as vd


@pytest.fixture(autouse=True)
def _point_outputs_at_tmp(tmp_path, monkeypatch):
    """把"配置里的输出目录"指向临时目录：_cfg_output(key) → tmp_path/<key>"""
    monkeypatch.setattr(vd, "_cfg_output", lambda key, fallback: tmp_path / key)
    return tmp_path


def _make_total(path, sheets=None, rows=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    names = sheets if sheets is not None else vd.REQUIRED_SHEETS
    save_excel({s: __import__("pandas").DataFrame({"客户": [f"c{i}" for i in range(rows)]})
                for s in names}, path)


def _make_report(path, rows=2):
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    save_excel({"销售收入": pd.DataFrame({"销售": ["甲"] * rows}),
                "销售回款": pd.DataFrame({"销售": ["乙"] * rows})}, path)


DAY = "20260929"


def test_missing_data_reported_report_not_required(tmp_path):
    """数据总表必须报；销售完成度是按需产物，缺了不算问题"""
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems, day=DAY)
    assert any("数据总表" in p for p in problems)
    assert not any("销售完成度" in p for p in problems)


def test_empty_required_sheet_reported(tmp_path):
    _make_total(tmp_path / "数据" / "data_20260929.xlsx",
                sheets=["当年累计收入", "销售收入"])       # 缺 8 个必需 sheet
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems, day=DAY)
    joined = " ".join(problems)
    assert "必需 sheet 缺失或为空" in joined
    assert "当年累计回款" in joined


def test_all_present_passes(tmp_path):
    _make_total(tmp_path / "数据" / "data_20260929.xlsx")
    _make_report(tmp_path / "销售完成度" / "销售完成度汇总_20260929.xlsx")
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems, day=DAY)
    assert problems == []


def test_report_present_is_checked(tmp_path):
    """生成过就照常校验内容（空 sheet 要报）"""
    import pandas as pd

    _make_total(tmp_path / "数据" / "data_20260929.xlsx")
    bad = tmp_path / "销售完成度" / "销售完成度汇总_20260929.xlsx"
    bad.parent.mkdir(parents=True, exist_ok=True)
    save_excel({"销售收入": pd.DataFrame(), "销售回款": pd.DataFrame()}, bad)
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems, day=DAY)
    assert any("销售完成度" in p for p in problems)


def test_old_file_does_not_count_as_today(tmp_path):
    """按日期找产物：昨天的文件不能冒充今天的（2026-11-06 修的漏洞）"""
    _make_total(tmp_path / "数据" / "data_20260101.xlsx")     # 只有旧文件
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems, day=DAY)
    assert any("数据总表" in p for p in problems)


def test_today_file_picked_among_old_ones(tmp_path):
    _make_total(tmp_path / "数据" / "data_20260101.xlsx", sheets=["当年累计收入"])  # 旧且不全
    _make_total(tmp_path / "数据" / "data_20260929.xlsx")                           # 当天且齐全
    _make_report(tmp_path / "销售完成度" / "销售完成度汇总_20260929.xlsx")
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems, day=DAY)
    assert problems == []


def test_verify_html_reports_missing_pages(tmp_path, monkeypatch):
    html = tmp_path / "看板_20260929.html"
    html.write_text("<html><body>" + "x" * 300_000 + "</body></html>", encoding="utf-8")
    monkeypatch.setattr(vd, "MIN_HTML_KB", 1.0)
    problems: list[str] = []
    vd.verify_html(html, problems)
    joined = " ".join(problems)
    assert "缺少页面模板" in joined
    assert "缺少关键交互函数" in joined


def test_base_output_dir_reads_frontend_config():
    assert vd.base_output_dir().name == "output"
