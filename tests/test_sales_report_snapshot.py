# Author: naohua168 <bai_bai168@qq.com>
"""销售完成度表 · 指定数据版本（快照）—— scripts/sales_summary_report.py

覆盖：从 data_YYYYMMDD.xlsx 取数、缺 sheet 报错、
     产物落到**那一期**的年月目录、文件名用那一期的日期。
"""
import datetime
from pathlib import Path

import pandas as pd
import pytest

from engine.core.io_utils import save_excel
from scripts import sales_summary_report as sr

DEPTS = sr.DEPTS


def _make_book(path: Path) -> Path:
    """造一个最小可用的数据总表（4 张必需 sheet）"""
    dept = DEPTS[0]
    sales = pd.DataFrame({"销售": ["甲", "乙"], "事业部": [dept, dept], "金额": [1000.0, 500.0]})
    tgt = pd.DataFrame({"销售": ["甲", "乙"], dept: [0.5, 0.25]})   # 万元
    save_excel({
        "销售收入": sales,
        "销售回款": sales.copy(),
        "年度收入总指标": tgt,
        "年度回款总指标": tgt.copy(),
    }, path)
    return path


class TestGenerateFromSnapshot:
    def test_uses_snapshot_sheets(self, tmp_path):
        snap = _make_book(tmp_path / "data_20261030.xlsx")
        out = tmp_path / "o.xlsx"
        p = sr.generate(out, snapshot=snap)

        df = pd.read_excel(p, sheet_name="销售收入").set_index("销售")
        assert df.loc["甲", "实际合计"] == 1000.0
        assert df.loc["甲", "指标合计"] == 5000.0      # 0.5 万 × 10000
        assert df.loc["乙", "实际合计"] == 500.0

    def test_output_lands_in_snapshot_month(self, tmp_path, monkeypatch):
        """不指定 output 时：按快照日期落盘（不是今天）"""
        monkeypatch.setattr(sr, "BASE_DIR", tmp_path)
        monkeypatch.setattr(sr, "_load_cfg", lambda: {})
        snap = _make_book(tmp_path / "data_20261030.xlsx")

        p = sr.generate(None, snapshot=snap)
        assert p.name == "销售完成度汇总_20261030.xlsx"
        assert p.parent.parts[-3:] == ("销售完成度", "2026", "10")
        assert p.exists()

    def test_missing_sheet_raises(self, tmp_path):
        bad = tmp_path / "data_20261030.xlsx"
        save_excel({"销售收入": pd.DataFrame({"销售": ["甲"], "事业部": [DEPTS[0]], "金额": [1.0]})}, bad)
        with pytest.raises(ValueError) as e:
            sr.generate(tmp_path / "o.xlsx", snapshot=bad)
        assert "缺少必需 sheet" in str(e.value)


class TestOutputDir:
    def test_month_dir_follows_when(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sr, "BASE_DIR", tmp_path)
        monkeypatch.setattr(sr, "_load_cfg", lambda: {})
        d = sr.output_dir(datetime.date(2026, 10, 30))
        assert d.parts[-3:] == ("销售完成度", "2026", "10")

    def test_default_is_this_month(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sr, "BASE_DIR", tmp_path)
        monkeypatch.setattr(sr, "_load_cfg", lambda: {})
        today = datetime.date.today()
        assert sr.output_dir().parts[-2:] == (f"{today:%Y}", f"{today:%m}")
