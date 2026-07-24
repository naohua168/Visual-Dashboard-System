"""测试年基线清洗模块"""
from pathlib import Path
import pandas as pd
import pytest
BASE_DIR = Path(__file__).parent.parent

def test_parse_yearly_date_single_month():
    from engine.yearly_baseline.cleaner import _parse_yearly_date
    assert _parse_yearly_date("3月") == "2024-03-01"

def test_parse_yearly_date_range():
    from engine.yearly_baseline.cleaner import _parse_yearly_date
    assert _parse_yearly_date("1-4月") == "2024-04-01"

def test_parse_yearly_date_none():
    from engine.yearly_baseline.cleaner import _parse_yearly_date
    assert _parse_yearly_date(None) is None

def test_parse_yearly_date_nan():
    from engine.yearly_baseline.cleaner import _parse_yearly_date
    import math
    assert _parse_yearly_date(math.nan) is None

def test_col_remap_renames():
    from engine.yearly_baseline.cleaner import _col_remap
    df = pd.DataFrame({"客户名称": ["A"], "金额": [100]})
    rm = {}
    _col_remap(df, "客户名称", "客户", rm)
    assert "客户" in df.columns

def test_clean_single_file_not_found(tmp_path):
    from engine.yearly_baseline.cleaner import _clean_single
    assert _clean_single("收入", tmp_path / "nonexist.xlsx") is None

def test_clean_single_output_columns(tmp_path):
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({"事业部": ["检测工程事业部"], "客户名称": ["T"], "金额": [100], "确认时间": ["5月"]}).to_excel(p, index=False)
    r = _clean_single("收入", p)
    for c in ["事业部","金额","客户","日期","是否为广东公司","是否为深圳公司"]:
        assert c in r.columns

def test_clean_single_dept_mapping(tmp_path):
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({"事业部": ["检测工程事业部"], "客户名称": ["T"], "金额": [200], "日期": ["6月"]}).to_excel(p, index=False)
    r = _clean_single("回款", p)
    assert r["事业部"].iloc[0] == "检测"

def test_clean_yearly_no_source(tmp_path):
    from engine.yearly_baseline.cleaner import clean_yearly
    assert clean_yearly(source_dir=tmp_path) is None
