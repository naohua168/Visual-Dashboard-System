# -*- coding: utf-8 -*-
# Author: naohua168 <bai_bai168@qq.com>
"""运营端日期解析测试 — 月份标签 / 真实日期 / 年份归属"""
import pandas as pd

from engine.income_payment.operations import OPS_YEAR, _parse_ops_date


class TestOpsDateLabel:
    """月份标签写法（运营端特有）"""

    def test_range_label_takes_last_month(self):
        # "1-4月" 取末月，保证季度筛选正确分账
        assert _parse_ops_date("1-4月") == pd.Timestamp(year=OPS_YEAR, month=4, day=1)
        assert _parse_ops_date("1-4月", 2027) == pd.Timestamp(year=2027, month=4, day=1)

    def test_single_month_label(self):
        assert _parse_ops_date("5月", 2026) == pd.Timestamp(year=2026, month=5, day=1)
        assert _parse_ops_date("12月", 2026) == pd.Timestamp(year=2026, month=12, day=1)

    def test_year_comes_from_argument_not_today(self):
        """年份归属必须由调用方（年度配置）决定，而非跑批当天年份"""
        assert _parse_ops_date("5月", 2027).year == 2027

    def test_year_defaults_to_ops_year(self):
        assert _parse_ops_date("5月").year == OPS_YEAR


class TestOpsDateReal:
    """真实日期写法（与标签混用）"""

    def test_datetime_string_with_time(self):
        assert _parse_ops_date("2026-06-30 00:00:00") == pd.Timestamp("2026-06-30")

    def test_datetime_string_date_only(self):
        assert _parse_ops_date("2026-02-11") == pd.Timestamp("2026-02-11")

    def test_timestamp_object(self):
        assert _parse_ops_date(pd.Timestamp("2026-06-26")) == pd.Timestamp("2026-06-26")

    def test_normalize_strips_time_component(self):
        assert _parse_ops_date(pd.Timestamp("2026-06-26 13:45:59")) == pd.Timestamp("2026-06-26")


class TestOpsDateInvalid:
    def test_none_and_nat(self):
        assert _parse_ops_date(None) is None
        assert _parse_ops_date(pd.NaT) is None
        assert _parse_ops_date(float("nan")) is None

    def test_empty_string(self):
        assert _parse_ops_date("") is None

    def test_garbage_returns_none(self):
        assert _parse_ops_date("本年累计") is None
        assert _parse_ops_date("abc") is None
