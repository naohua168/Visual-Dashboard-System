# Author: naohua168 <bai_bai168@qq.com>
"""交付物校验测试（2026-09-29 扩档）—— scripts/verify_dashboard.py

覆盖：数据总表/销售完成度表 缺失、必需 sheet 为空、齐全通过、--allow-missing-report。
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


def test_missing_both_artifacts(tmp_path):
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems)
    assert any("数据总表" in p for p in problems)
    assert any("销售完成度" in p for p in problems)


def test_allow_missing_report_downgrades(tmp_path):
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems, allow_missing_report=True)
    assert not any("销售完成度" in p for p in problems)
    assert any("数据总表" in p for p in problems)   # 总表仍然要报


def test_empty_required_sheet_reported(tmp_path):
    _make_total(tmp_path / "数据" / "data_20260929.xlsx",
                sheets=["当年累计收入", "销售收入"])       # 缺 8 个必需 sheet
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems)
    joined = " ".join(problems)
    assert "必需 sheet 缺失或为空" in joined
    assert "当年累计回款" in joined


def test_all_present_passes(tmp_path):
    _make_total(tmp_path / "数据" / "data_20260929.xlsx")
    _make_report(tmp_path / "销售完成度" / "销售完成度汇总_20260929.xlsx")
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems)
    assert problems == []


def test_newest_file_picked(tmp_path):
    old = tmp_path / "数据" / "data_20260101.xlsx"
    new = tmp_path / "数据" / "data_20260929.xlsx"
    _make_total(old, sheets=["当年累计收入"])                # 旧文件：sheet 不全
    _make_total(new)                                        # 新文件：齐全
    _make_report(tmp_path / "销售完成度" / "销售完成度汇总_20260929.xlsx")
    problems: list[str] = []
    vd.verify_artifacts(tmp_path, problems)
    assert problems == []                                   # 取最新那份（齐全）


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
