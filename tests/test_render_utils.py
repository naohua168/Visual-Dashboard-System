"""测试渲染辅助工具"""
import math
import pytest

from processors.utils import fmt_wan, fmt_pct, fmt_yoy, safe_float


class TestFmtWan:
    def test_normal(self):
        assert fmt_wan(1234.56) == "1,234.56"

    def test_zero(self):
        assert fmt_wan(0) == "0.00"

    def test_none(self):
        assert fmt_wan(None) == "—"

    def test_nan(self):
        assert fmt_wan(float("nan")) == "—"

    def test_invalid_str(self):
        assert fmt_wan("abc") == "—"


class TestFmtPct:
    def test_normal(self):
        assert fmt_pct(50, 100) == "50.0%"

    def test_over_100(self):
        assert fmt_pct(150, 100) == "150.0%"

    def test_zero_denominator(self):
        assert fmt_pct(50, 0) == "—"

    def test_none_denominator(self):
        assert fmt_pct(50, None) == "—"

    def test_none_numerator(self):
        assert fmt_pct(None, 100) == "—"


class TestFmtYoy:
    def test_growth(self):
        assert fmt_yoy(120, 100) == "+20.0%"

    def test_decline(self):
        assert fmt_yoy(80, 100) == "-20.0%"

    def test_zero_previous(self):
        assert fmt_yoy(50, 0) == "—"

    def test_none(self):
        assert fmt_yoy(None, 100) == "—"


class TestSafeFloat:
    def test_int(self):
        assert safe_float(42) == 42.0

    def test_str(self):
        assert safe_float("3.14") == 3.14

    def test_none(self):
        assert safe_float(None) == 0.0

    def test_nan(self):
        assert safe_float(float("nan")) == 0.0

    def test_invalid(self):
        assert safe_float("abc") == 0.0
