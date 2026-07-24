"""测试列名冗余匹配"""
import pandas as pd
import pytest

from engine.core.column_resolver import find_column, extract_columns


class TestFindColumn:
    def test_exact_match(self):
        df = pd.DataFrame({"客户": [1, 2], "金额": [3, 4]})
        assert find_column(df, ["客户"]) == "客户"

    def test_first_candidate_wins(self):
        df = pd.DataFrame({"客户名称": [1], "客户": [2]})
        # 第一个候选命中即返回
        assert find_column(df, ["客户名称", "客户"]) == "客户名称"

    def test_strip_whitespace(self):
        df = pd.DataFrame({"  客户  ": [1]})
        assert find_column(df, ["客户"]) == "  客户  "

    def test_no_match_raises(self):
        df = pd.DataFrame({"foo": [1]})
        with pytest.raises(KeyError):
            find_column(df, ["客户"])

    def test_fallback_candidates(self):
        df = pd.DataFrame({"创建日期": [1]})
        # 第一个不存在，命中第二个
        assert find_column(df, ["创建时间", "创建日期"]) == "创建日期"


class TestExtractColumns:
    def test_basic_extraction(self):
        df = pd.DataFrame({"创建日期": ["2026-01-01"], "客户名称": ["A"], "含税金额": [100]})
        mapping = {"日期": ["创建时间", "创建日期"], "客户": ["客户.名称", "客户名称"], "金额": ["含税金额"]}
        result = extract_columns(df, mapping)
        assert list(result.columns) == ["日期", "客户", "金额"]
        assert result["客户"].iloc[0] == "A"

    def test_skip_underscore_keys(self):
        df = pd.DataFrame({"客户": ["A"]})
        mapping = {"_说明": ["备注"], "客户": ["客户"]}
        result = extract_columns(df, mapping)
        assert list(result.columns) == ["客户"]

    def test_records_hit_columns(self):
        df = pd.DataFrame({"客户名称": ["A"]})
        mapping = {"客户": ["客户.名称", "客户名称"]}
        result = extract_columns(df, mapping)
        assert result.attrs["_hit_columns"]["客户"] == "客户名称"
