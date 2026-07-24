"""测试客户白名单去空格模糊匹配"""
import pandas as pd
import pytest

from engine.core.customer_matcher import CustomerMatcher


@pytest.fixture
def matcher():
    return CustomerMatcher(["比亚迪汽车工业有限公司", "中国一汽", "上海汽车集团股份有限公司"])


class TestCustomerMatcher:
    def test_exact_match(self, matcher):
        assert matcher.match("比亚迪汽车工业有限公司") == "比亚迪汽车工业有限公司"

    def test_strip_spaces(self, matcher):
        # 客户名带空格也能匹配
        assert matcher.match("比 亚 迪 汽 车 工 业 有 限 公 司") == "比亚迪汽车工业有限公司"

    def test_no_match_returns_none(self, matcher):
        assert matcher.match("不存在的客户") is None

    def test_na_returns_none(self, matcher):
        assert matcher.match(None) is None
        assert matcher.match(float("nan")) is None

    def test_count(self, matcher):
        assert matcher.count == 3

    def test_filter_keep_only_matched(self, matcher):
        df = pd.DataFrame({"客户": ["比亚迪汽车工业有限公司", "未知客户", "中国一汽"]})
        result = matcher.filter_dataframe(df, "客户", keep_unmatched=False)
        assert len(result) == 2
        assert "未知客户" not in result["客户"].values

    def test_filter_keep_unmatched(self, matcher):
        df = pd.DataFrame({"客户": ["比亚迪汽车工业有限公司", "未知客户"]})
        result = matcher.filter_dataframe(df, "客户", keep_unmatched=True)
        assert len(result) == 2  # 不丢行
        # 未匹配的应为 None
        assert result["客户"].isna().sum() == 1
