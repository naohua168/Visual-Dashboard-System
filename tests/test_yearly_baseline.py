# Author: naohua168 <bai_bai168@qq.com>
"""测试年基线清洗模块"""
from pathlib import Path
import pandas as pd
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
    for c in ["事业部","金额","客户","法人主体","日期"]:
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

def test_clean_single_filters_internal_trade_income(tmp_path):
    """收入文件: '是否属于内部交易'='是' 的行应被排除"""
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({
        "事业部": ["检测工程事业部", "检测工程事业部"],
        "客户名称": ["外部客户", "内部客户"],
        "金额": [100, 50],
        "是否属于内部交易": [None, "是"],
    }).to_excel(p, index=False)
    r = _clean_single("收入", p)
    assert len(r) == 1
    assert r["客户"].iloc[0] == "外部客户"
    assert r["金额"].sum() == 100

def test_clean_single_filters_internal_trade_payment(tmp_path):
    """回款文件: '是否属于内部款项'='是' 的行应被排除；无内部列时不过滤"""
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({
        "事业部": ["检测工程事业部", "检测工程事业部"],
        "客户名称": ["外部客户", "内部客户"],
        "金额": [200, 80],
        "是否属于内部款项": [None, "是"],
    }).to_excel(p, index=False)
    r = _clean_single("回款", p)
    assert len(r) == 1
    assert r["金额"].sum() == 200

def test_clean_single_no_internal_col(tmp_path):
    """无内部交易列时全部保留"""
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({
        "事业部": ["检测工程事业部", "检测工程事业部"],
        "客户名称": ["A", "B"],
        "金额": [100, 50],
    }).to_excel(p, index=False)
    r = _clean_single("收入", p)
    assert len(r) == 2
    assert r["金额"].sum() == 150


# ── 列映射配置化（2026-11-10：配置编辑器「字段映射」→ 数据源=年基线数据）──
def test_clean_single_uses_config_mapping(tmp_path):
    """源表列名与默认候选不同时，配置里的候选列名能命中"""
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({
        "事业部": ["检测工程事业部"],
        "客户": ["A"],
        "营业收入": [300],
    }).to_excel(p, index=False)
    spec = {"列映射": {"金额": ["营业收入"], "客户": ["客户"], "部门": ["事业部"]}}
    r = _clean_single("收入", p, None, spec)
    assert r["金额"].sum() == 300
    assert r["客户"].iloc[0] == "A"
    assert r["事业部"].iloc[0] == "检测"


def test_clean_single_mapping_missing_falls_back(tmp_path):
    """配置里没有 列映射（历史 JSON）→ 回退内置默认，行为不变"""
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({"事业部": ["检测工程事业部"], "客户名称": ["A"], "金额": [10]}).to_excel(p, index=False)
    r = _clean_single("收入", p, None, {"文件名": "t.xlsx"})
    assert r["金额"].sum() == 10


def test_clean_single_internal_marks_from_config(tmp_path):
    """内部交易剔除取值来自 `内部交易标记值`（默认「是」）"""
    from engine.yearly_baseline.cleaner import _clean_single
    p = tmp_path / "t.xlsx"
    pd.DataFrame({
        "事业部": ["检测工程事业部", "检测工程事业部"],
        "客户": ["A", "B"],
        "金额": [100, 50],
        "内部交易": ["Y", "N"],
    }).to_excel(p, index=False)
    spec = {
        "列映射": {"金额": ["金额"], "客户": ["客户"], "部门": ["事业部"], "内部交易": ["内部交易"]},
        "内部交易标记值": ["Y"],
    }
    r = _clean_single("收入", p, None, spec)
    assert len(r) == 1
    assert r["客户"].iloc[0] == "B"
