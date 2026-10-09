# Author: naohua168 <bai_bai168@qq.com>
"""公司名匹配键测试 — engine/core/name_key.py（2026-09-29）

背景：源表与配置里同一家公司可能写成 `法雷奥汽车内部控制（深圳）有限公司`
（全角括号）与 `... (深圳) ...`（半角括号），原先各处「strip 后精确查表」会匹配不上
→ 销售拆分落到"待确认"、客户白名单直接丢行、法人主体判定错配。

覆盖：
  - match_key：全角/半角括号、全角字母数字、空格/全角空格/零宽字符、大小写
  - 不该被合并的：内容层差异（（深圳） vs （上海）、有限公司 增删）必须保持不同
  - same_name / is_gd_legal / is_sg_legal / is_sz_legal
  - KeyIndex：撞键保留先出现的写法 + conflicts 记录
  - KeyedLookup：查表容错、遍历仍是原写法、dict 语义的后写覆盖
  - key_set / pair_key / format_conflicts
"""
import pytest

from engine.core.name_key import (
    LEGAL_GD,
    LEGAL_SG,
    KeyIndex,
    KeyedLookup,
    dup_name_groups,
    format_conflicts,
    is_gd_legal,
    is_sg_legal,
    is_sz_legal,
    key_set,
    match_key,
    pair_key,
    same_name,
)

FALIAO_FULL = "法雷奥汽车内部控制（深圳）有限公司"   # 全角括号
FALIAO_HALF = "法雷奥汽车内部控制(深圳)有限公司"     # 半角括号
GD_FULL = "广东汽车检测中心有限公司"


# ══════════════════════════════════════════════════════════════
# match_key：只做「符号层」归一
# ══════════════════════════════════════════════════════════════
class TestMatchKey:
    def test_fullwidth_and_halfwidth_brackets_equal(self):
        assert match_key(FALIAO_FULL) == match_key(FALIAO_HALF)

    def test_space_variants(self):
        assert match_key("延锋（广州）座椅系统有限公司") == match_key("延锋 (广州) 座椅系统有限公司")
        assert match_key("SAMSUNG SDI CO.,LTD.") == match_key("SAMSUNGSDICO.,LTD.")

    def test_fullwidth_space_and_invisible_chars(self):
        assert match_key("某公司\u3000甲") == match_key("某公司甲")
        assert match_key("某公司\u200b甲") == match_key("某公司甲")

    def test_fullwidth_alnum_and_case(self):
        assert match_key("ＡＢＣ柴油机有限公司") == match_key("abc柴油机有限公司")

    def test_none_and_nan(self):
        assert match_key(None) == ""
        assert match_key(float("nan")) == ""
        assert match_key("") == ""

    @pytest.mark.parametrize("a, b", [
        ("某公司（深圳）有限公司", "某公司（上海）有限公司"),   # 括号内容不同 → 不能合并
        ("某公司有限公司", "某公司"),                        # 删后缀 → 不能合并
        ("甲检测中心", "乙检测中心"),
    ])
    def test_content_level_diff_not_merged(self, a, b):
        """内容层差异（括号里的地名、后缀增删）必须保持不同，避免误合并不同法人"""
        assert match_key(a) != match_key(b)


def test_same_name():
    assert same_name(FALIAO_FULL, FALIAO_HALF)
    assert not same_name(FALIAO_FULL, "法雷奥汽车内部控制（上海）有限公司")
    assert not same_name("", "")


# ══════════════════════════════════════════════════════════════
# 法人主体判定
# ══════════════════════════════════════════════════════════════
class TestLegalHelpers:
    def test_gd_legal_with_any_bracket_style(self):
        assert is_gd_legal(LEGAL_GD)
        assert is_gd_legal("广东汽车检测中心有限公司 ")
        assert not is_gd_legal("南方（韶关）智能网联新能源汽车试验检测中心有限公司")
        assert not is_gd_legal(float("nan"))

    def test_sg_legal_fullwidth_and_halfwidth(self):
        assert is_sg_legal(LEGAL_SG)
        assert is_sg_legal("南方(韶关)智能网联新能源汽车试验检测中心有限公司")
        assert not is_sg_legal(GD_FULL)

    def test_sz_legal(self):
        assert is_sz_legal("中认车联网技术服务（深圳）有限公司")
        assert is_sz_legal("深圳市某某公司")
        assert not is_sz_legal(GD_FULL)


# ══════════════════════════════════════════════════════════════
# KeyIndex：撞键记录
# ══════════════════════════════════════════════════════════════
class TestKeyIndex:
    def test_lookup_hits_both_spellings(self):
        idx = KeyIndex()
        idx.add(FALIAO_HALF)
        assert idx.key(FALIAO_FULL) in idx
        assert idx.get(FALIAO_FULL) == FALIAO_HALF   # 先出现的写法

    def test_conflicts_recorded(self):
        idx = KeyIndex()
        idx.add(FALIAO_HALF)
        idx.add(FALIAO_FULL)
        idx.add("唯一公司有限公司")
        assert idx.size == 2
        assert idx.conflicts == {match_key(FALIAO_HALF): [FALIAO_HALF, FALIAO_FULL]}

    def test_no_conflict_when_identical(self):
        idx = KeyIndex()
        idx.add(FALIAO_HALF)
        idx.add(FALIAO_HALF)
        assert idx.conflicts == {}


def test_key_set_and_format_conflicts():
    keys = key_set([FALIAO_FULL, FALIAO_HALF, "", None])
    assert len(keys) == 1 and "" not in keys
    assert format_conflicts({}) == ""
    assert "法雷奥" in format_conflicts({match_key(FALIAO_FULL): [FALIAO_FULL, FALIAO_HALF]})


def test_format_conflicts_limits():
    conflicts = {f"k{i}": [f"a{i}", f"b{i}"] for i in range(10)}
    assert "另 2 组" in format_conflicts(conflicts, limit=8)


# ══════════════════════════════════════════════════════════════
# KeyedLookup：查表容错、遍历原样
# ══════════════════════════════════════════════════════════════
class TestKeyedLookup:
    def test_get_by_other_spelling(self):
        d = KeyedLookup()
        d.add(FALIAO_HALF, "王海龙")
        assert d.get(FALIAO_FULL) == "王海龙"
        assert d.get("不存在的公司") is None
        assert d.get("不存在的公司", "默认") == "默认"

    def test_iteration_keeps_original_names(self):
        d = KeyedLookup()
        d.add(FALIAO_HALF, 1)
        d.add("另一家公司", 2)
        assert list(d) == [FALIAO_HALF, "另一家公司"]
        assert d.items() == [(FALIAO_HALF, 1), ("另一家公司", 2)]
        assert len(d) == 2

    def test_contains_and_getitem(self):
        d = KeyedLookup()
        d.add(FALIAO_HALF, 1)
        assert FALIAO_FULL in d
        assert d[FALIAO_FULL] == 1

    def test_setitem_overwrites_like_dict(self):
        """`映射[名] = 值` 与 dict 同语义：后写覆盖"""
        d = KeyedLookup()
        d[FALIAO_HALF] = "A"
        d[FALIAO_FULL] = "B"
        assert d.get(FALIAO_FULL) == "B"
        assert list(d) == [FALIAO_HALF]

    def test_add_keeps_first(self):
        """add() 保留先出现的值（归属表口径）"""
        d = KeyedLookup()
        d.add(FALIAO_HALF, "A")
        d.add(FALIAO_FULL, "B")
        assert d.get(FALIAO_FULL) == "A"

    def test_pair_key_lookup(self):
        d = KeyedLookup(pair_key)
        d.add((FALIAO_HALF, "王海龙"), "广东自有客户")
        assert d.get((FALIAO_FULL, "王海龙")) == "广东自有客户"
        assert d.get((FALIAO_HALF, "别人")) is None


# ══════════════════════════════════════════════════════════════
# dup_name_groups：找出归属表里"同一家公司写成两遍"的条目
# ══════════════════════════════════════════════════════════════
class TestDupNameGroups:
    def test_same_parent_two_spellings(self):
        """同一父组下两种写法 → 报"""
        problems = dup_name_groups({
            "零部件客户": {"子公司": {
                "延锋(广州)座椅系统有限公司": {},
                "延锋（广州）座椅系统有限公司": {},
            }},
        })
        assert len(problems) == 1
        assert sorted(next(iter(problems.values()))) == [
            "延锋(广州)座椅系统有限公司", "延锋（广州）座椅系统有限公司"]

    def test_self_group_and_sub_elsewhere(self):
        """自引用父组 + 另挂父组 → 报（两条路都能命中）"""
        problems = dup_name_groups({
            "莱茵技术监护(深圳)有限公司": {"子公司": {"莱茵技术监护(深圳)有限公司": {}}},
            "科技公司": {"子公司": {"莱茵技术监护（深圳）有限公司": {}}},
        })
        assert len(problems) == 1

    def test_multi_group_is_not_duplicate(self):
        """多组配置（不同父组各一份）→ 不报"""
        assert dup_name_groups({
            "广东自有客户": {"子公司": {"佛吉亚汽车部件（佛山）有限公司": {}}},
            "零部件客户": {"子公司": {"佛吉亚汽车部件(佛山)有限公司": {}}},
        }) == {}

    def test_distinct_names_no_report(self):
        assert dup_name_groups({
            "科技公司": {"子公司": {"甲有限公司": {}, "乙有限公司": {}}},
        }) == {}
        assert dup_name_groups({}) == {}
