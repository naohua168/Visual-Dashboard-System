# Author: naohua168 <bai_bai168@qq.com>
"""「父组名自带销售」的分隔符容错 — 科技公司·王海龙 / 科技公司·李巍（2026-09-29）

背景：2026-09-29 起归属表把按销售拆行的母公司直接写成 `母公司·销售`（科技公司·王海龙 /
科技公司·李巍），老的分隔符容错（`_销售拆分.客户矩阵` 驱动）就管不到它们了。
现在指标表里无论写成 `科技公司-王海龙` / `科技公司 王海龙` / `科技公司王海龙`，
都归一到归属表里的规范写法，避免同一个销售被拆成两行。

覆盖：
  - dotted_parent_patterns / normalize_known_parent（注入式单测）
  - 真实配置集成：两张父组名、归一化、is_sales_key（截断保护）
  - _consolidate_customers 把指标表手填写法归一
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import engine.core.name_key as nkey
import processors.page_data_utils as u
from processors.config_loader import CustomerFilter, expand_to_customer_names

BASE_DIR = Path(__file__).parent.parent
ATTR = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
DOTTED = ["科技公司·王海龙", "科技公司·李巍"]


# ══════════════════════════════════════════════════════════════
# 单元：任意分隔符（含漏打分隔符）
# ══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("name", [
    "科技公司·王海龙", "科技公司-王海龙", "科技公司 王海龙", "科技公司王海龙",
    "科技公司／王海龙", "科技公司、王海龙", "科技公司  王海龙", "科技公司:王海龙",
])
def test_dotted_parent_any_separator(name):
    pats = u.dotted_parent_patterns(DOTTED)
    assert u.normalize_known_parent(name, pats) == "科技公司·王海龙"


def test_dotted_parent_second_sales():
    pats = u.dotted_parent_patterns(DOTTED)
    assert u.normalize_known_parent("科技公司 李巍", pats) == "科技公司·李巍"


@pytest.mark.parametrize("name", [
    "科技公司",             # 裸母公司：不是销售行
    "科技公司·别人",        # 销售名对不上
    "科技公司",
    "",
    "南方韶关",
])
def test_dotted_parent_no_false_positive(name):
    pats = u.dotted_parent_patterns(DOTTED)
    assert u.normalize_known_parent(name, pats) is None


def test_dotted_parent_sales_of():
    """sales_of_dotted_parent：规范名最后一段 = 销售名"""
    pats = u.dotted_parent_patterns(DOTTED)
    assert u.normalize_known_parent("科技公司-李巍", pats).split("·")[-1] == "李巍"


def test_dotted_patterns_read_config_once(monkeypatch):
    """性能回归：连续调用不得反复读 客户销售归属.json

    （曾因为每次调用都 json.loads 一遍 500KB 配置，导致逐行归一慢到像卡死）
    """
    calls = {"n": 0}
    real_read = Path.read_text

    def counting_read(self, *a, **k):
        calls["n"] += 1
        return real_read(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", counting_read)
    monkeypatch.setattr(u, "_DOTTED_NAMES", None)
    monkeypatch.setattr(nkey, "_DOTTED_RE_CACHE", {})
    u.dotted_parent_patterns()
    after_first = calls["n"]
    for _ in range(50):
        u.dotted_parent_patterns()
        u.normalize_known_parent("科技公司-王海龙")
    assert calls["n"] == after_first, "重复调用不应再读配置文件"


# ══════════════════════════════════════════════════════════════
# 集成：真实配置
# ══════════════════════════════════════════════════════════════
@pytest.mark.skipif(not ATTR.exists(), reason="客户销售归属.json 不存在")
class TestRealConfig:
    @pytest.fixture(autouse=True)
    def _fresh_caches(self, monkeypatch):
        """避免全局缓存串味（_SUB_TO_PARENT 首次调用后永久缓存）"""
        monkeypatch.setattr(u, "_SUB_TO_PARENT", None)
        monkeypatch.setattr(nkey, "_DOTTED_RE_CACHE", {})

    def test_two_dotted_parents_in_config(self):
        groups = json.loads(ATTR.read_text(encoding="utf-8"))["客户归属"]
        dotted = {p for p in groups if "·" in p}
        assert dotted == set(DOTTED), f"归属表里的「父组名自带销售」与预期不一致: {dotted}"

    @pytest.mark.parametrize("written", ["科技公司·王海龙", "科技公司-王海龙", "科技公司 王海龙"])
    def test_normalize_split_cust(self, written):
        assert u.normalize_split_cust(written) == "科技公司·王海龙"

    def test_is_sales_key(self):
        assert u.is_sales_key("科技公司·王海龙") is True
        assert u.is_sales_key("科技公司-李巍") is True   # 手填写法也算
        assert u.is_sales_key("南方韶关") is False
        assert u.is_sales_key("不存在的客户") is False

    def test_consolidate_customers_normalizes_written_forms(self):
        df = pd.DataFrame({"客户": ["科技公司-王海龙", "科技公司 李巍", "不存在的客户"]})
        out = u._consolidate_customers(df)["客户"].tolist()
        assert out == ["科技公司·王海龙", "科技公司·李巍", "不存在的客户"]

    def test_consolidate_target_merges_written_forms(self):
        """指标表把两位销售写成不同分隔符 → 各自归一到规范行，不会拆成四行"""
        tgt = pd.DataFrame([
            {"客户": "科技公司-王海龙", "销售": "王海龙", "检测": 100, "信息": 0, "能源": 0, "海外": 0},
            {"客户": "科技公司 王海龙", "销售": "王海龙", "检测": 20, "信息": 0, "能源": 0, "海外": 0},
            {"客户": "科技公司·李巍", "销售": "李巍", "检测": 5, "信息": 7, "能源": 0, "海外": 0},
        ])
        out = u._consolidate_target(tgt)
        got = {r["客户"]: (r["检测"], r["信息"]) for _, r in out.iterrows()}
        assert got == {"科技公司·王海龙": (120, 0), "科技公司·李巍": (5, 7)}

    # ── 展示规则（优先展示 / 客户筛选）同样容错 ──
    @pytest.mark.parametrize("written", ["科技公司-王海龙", "科技公司 王海龙"])
    def test_expand_written_form_normalized(self, written):
        """写成别的分隔符 → 归一到规范名（这一行本身）"""
        assert expand_to_customer_names(BASE_DIR, [written]) == {"科技公司·王海龙"}

    def test_expand_dotted_parent_keeps_itself(self):
        """写规范名（它同时是父组）：既要展开其子公司，也要保留这一行本身"""
        got = expand_to_customer_names(BASE_DIR, ["科技公司·王海龙"])
        assert "科技公司·王海龙" in got
        assert len(got) > 1

    def test_expand_group_still_works(self):
        """普通组名展开不受影响（广汽系 → 其子公司名，不含组名本身）"""
        got = expand_to_customer_names(BASE_DIR, ["广汽系"])
        assert got and "广汽系" not in got

    def test_priority_filter_matches_written_form(self):
        filt = CustomerFilter(priority=["科技公司-王海龙"])
        assert filt.get_priority_names(BASE_DIR) == {"科技公司·王海龙"}

    def test_include_filter_keeps_dotted_parent_row(self):
        """客户筛选写 科技公司·王海龙 → 该行保留、其他行过滤掉"""
        filt = CustomerFilter(include=["科技公司·王海龙"])
        got = filt.apply(["科技公司·王海龙", "科技公司·李巍", "别的公司"], base_dir=BASE_DIR)
        assert got == ["科技公司·王海龙"]

    def test_include_filter_matches_written_form(self):
        """客户筛选里写 科技公司-李巍 → 仍只保留矩阵里的 科技公司·李巍 行"""
        filt = CustomerFilter(include=["科技公司-李巍"])
        got = filt.apply(["科技公司·李巍", "科技公司·王海龙", "别的公司"], base_dir=BASE_DIR)
        assert got == ["科技公司·李巍"]
