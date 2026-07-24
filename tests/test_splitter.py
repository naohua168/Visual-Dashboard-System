"""测试销售拆分逻辑 + 总额校验"""
import pandas as pd
import pytest

from engine.sales.splitter import SalesSplitter


@pytest.fixture
def rules_data():
    """合成测试规则数据"""
    return {
        "广东公司规则": {
            "广州汽车集团股份有限公司": {
                "事业部": {
                    "检测": {"销售": ["张三", "李四"], "比例": {"张三": 0.6, "李四": 0.4}}
                }
            }
        },
        "深圳公司规则": {
            "深圳某公司": {
                "事业部": {
                    "信息": {"销售": ["王五"]}
                }
            }
        },
        "其他规则": {
            "比亚迪汽车工业有限公司": {
                "销售": ["赵六", "孙七"], "比例": {"赵六": 0.5, "孙七": 0.5}
            }
        },
        "默认规则": {
            "中国一汽": {"销售": ["周八"]}
        },
    }


@pytest.fixture
def splitter(rules_data):
    return SalesSplitter(rules_data)


class TestMatch:
    def test_guangdong_rule_first(self, splitter):
        # 广东公司优先匹配广东规则
        sales, ratios, layer = splitter.match("广州汽车集团股份有限公司", "检测", "是", "")
        assert layer == "广东公司规则"
        assert sales == ["张三", "李四"]
        assert ratios["张三"] == 0.6

    def test_shenzhen_rule(self, splitter):
        sales, ratios, layer = splitter.match("深圳某公司", "信息", "", "是")
        assert layer == "深圳公司规则"
        assert sales == ["王五"]
        assert ratios["王五"] == 1.0

    def test_other_rule(self, splitter):
        sales, ratios, layer = splitter.match("比亚迪汽车工业有限公司", "检测", "", "")
        assert layer == "其他规则"
        assert sales == ["赵六", "孙七"]
        assert ratios["赵六"] == 0.5

    def test_default_rule(self, splitter):
        sales, ratios, layer = splitter.match("中国一汽", "检测", "", "")
        assert layer == "默认规则"
        assert sales == ["周八"]

    def test_fallback_pending(self, splitter):
        sales, ratios, layer = splitter.match("完全不存在的客户", "检测", "", "")
        assert layer == "待确认"
        assert sales == ["待确认"]
        assert ratios["待确认"] == 1.0

    def test_auto_ratio_when_missing(self, splitter):
        # 无比例配置时自动均分
        rules = {"其他规则": {"X公司": {"销售": ["A", "B", "C"]}}}
        s = SalesSplitter(rules)
        sales, ratios, layer = s.match("X公司", "检测", "", "")
        assert ratios["A"] == pytest.approx(1 / 3)
        assert ratios["B"] == pytest.approx(1 / 3)
        assert ratios["C"] == pytest.approx(1 / 3)


class TestSplit:
    def test_basic_split(self, splitter):
        df = pd.DataFrame([
            {"事业部": "检测", "金额": 1000.0, "客户": "广州汽车集团股份有限公司",
             "日期": "2026-06-01", "是否为广东公司": "是", "是否为深圳公司": ""},
        ])
        result, stats = splitter.split(df)
        assert len(result) == 2  # 拆成 2 行
        assert "销售" in result.columns
        assert result["金额"].sum() == pytest.approx(1000.0)  # 总额守恒
        assert stats["广东公司规则"] == 1

    def test_total_conservation(self, splitter):
        """总额校验：拆分前后金额完全一致"""
        df = pd.DataFrame([
            {"事业部": "检测", "金额": 1000.0, "客户": "广州汽车集团股份有限公司",
             "日期": "2026-06-01", "是否为广东公司": "是", "是否为深圳公司": ""},
            {"事业部": "信息", "金额": 500.0, "客户": "深圳某公司",
             "日期": "2026-06-01", "是否为广东公司": "", "是否为深圳公司": "是"},
            {"事业部": "检测", "金额": 800.0, "客户": "比亚迪汽车工业有限公司",
             "日期": "2026-06-01", "是否为广东公司": "", "是否为深圳公司": ""},
            {"事业部": "检测", "金额": 200.0, "客户": "不存在客户",
             "日期": "2026-06-01", "是否为广东公司": "", "是否为深圳公司": ""},
        ])
        result, stats = splitter.split(df)
        original_total = df["金额"].sum()
        split_total = result["金额"].sum()
        # 总额守恒（不四舍五入，所以理论上完全相等）
        assert abs(original_total - split_total) < 1e-9

    def test_validate_pass(self, splitter):
        df = pd.DataFrame([{"事业部": "检测", "金额": 1000.0, "客户": "X",
                            "日期": "2026-06-01", "是否为广东公司": "", "是否为深圳公司": ""}])
        result, _ = splitter.split(df)
        assert splitter.validate(df, result, "test") is True

    def test_stats_keys(self, splitter):
        df = pd.DataFrame([
            {"事业部": "检测", "金额": 100.0, "客户": "X",
             "日期": "2026-06-01", "是否为广东公司": "", "是否为深圳公司": ""}
        ])
        _, stats = splitter.split(df)
        for key in ["广东公司规则", "深圳公司规则", "其他规则", "默认规则", "待确认"]:
            assert key in stats
