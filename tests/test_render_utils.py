# Author: naohua168 <bai_bai168@qq.com>
"""测试渲染辅助工具"""
from processors.utils import fmt_wan, fmt_pct, fmt_yoy, safe_float, wrap_name


class TestFmtWan:
    def test_normal(self):
        # 全局 .0f 取整显示（用户要求无小数点）
        assert fmt_wan(1234.56) == "1,235"

    def test_zero(self):
        assert fmt_wan(0) == "0"

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


class TestWrapName:
    """长名称折行 — 每行最多 25 字（2026-10-10 由 20 改：客户名尽量单行），优先自然断点"""

    def test_short_name_unchanged(self):
        assert wrap_name("深圳市科卫泰实业发展有限公司") == "深圳市科卫泰实业发展有限公司"

    def test_exact_width_unchanged(self):
        s = "一" * 25
        assert wrap_name(s) == s

    def test_25_chars_name_kept_in_one_line(self):
        """常见长客户名（20~25 字）必须保持单行 —— 客户列宽 28rem 正好放得下 25 个汉字"""
        for name in ("东风汽车有限公司东风日产乘用车公司",      # 17 字
                     "上汽通用五菱汽车股份有限公司",            # 14 字
                     "中汽院智能网联汽车检测中心（湖南）有限公司"):  # 22 字
            assert wrap_name(name) == name, f"{name} 不应折行"
            assert "<br>" not in wrap_name(name)

    def test_none_and_empty(self):
        assert wrap_name(None) == ""
        assert wrap_name("") == ""

    def test_every_line_within_width(self):
        s = "一" * 60
        lines = wrap_name(s).split("<br>")
        assert all(len(x) <= 25 for x in lines)
        assert "".join(lines) == s

    def test_split_at_natural_break(self):
        """超过 25 字才折行，且落在自然断点（不是硬切）"""
        s = "新丰县发展和改革局（新丰县粮食和物资储备局、新丰县国防动员办公室）"
        lines = wrap_name(s).split("<br>")
        assert all(len(x) <= 25 for x in lines)
        assert "".join(lines) == s
        assert lines[0][-1] in "、，,；;）)】」》 　·-—_/", f"首行不是自然断点: {lines[0]!r}"

    def test_custom_width(self):
        assert wrap_name("一" * 10, width=4) == "一一一一<br>一一一一<br>一一"

    def test_content_preserved_no_chars_lost(self):
        s = "中汽院智能网联汽车检测中心（湖南）有限公司"
        assert "".join(wrap_name(s).split("<br>")) == s
