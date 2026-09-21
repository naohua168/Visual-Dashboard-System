"""「广东自有客户」自动归入扫描 —— 候选判定逻辑测试（2026-09-21 用户口径）

规则：法人=广东汽车检测中心 且 **不属于任何销售**（公司级）→ 自动归入 广东自有客户/黎国键；
      · 已在配置里 → 跳过
      · 曾自动归入过（状态文件有记录，例如人工从 Excel 删除）→ **永不再自动加回**
      · 自身法人名 / 占位行（"广东公司"、"合计"…）/ 过短名字 → 排除
"""
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "scan_gd_owned", Path(__file__).parent.parent / "scripts" / "scan_gd_owned.py"
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)

plan_additions = mod.plan_additions
BLACKLIST_NAMES = mod.BLACKLIST_NAMES
MIN_NAME_LEN = mod.MIN_NAME_LEN


def _cands(**kwargs) -> dict:
    """kwargs: 客户名=金额(元)"""
    return {n: {"来源": ["运营端-收入"], "行数": 1, "金额": amt} for n, amt in kwargs.items()}


class TestPlanAdditions:
    def test_new_customer_is_added(self):
        todo, skipped = plan_additions(_cands(**{"上海北汇信息科技有限公司": 51100}), set(), {})
        assert [t[0] for t in todo] == ["上海北汇信息科技有限公司"]
        assert skipped == []

    def test_already_configured_is_skipped(self):
        todo, _ = plan_additions(_cands(**{"上海北汇信息科技有限公司": 1}), {"上海北汇信息科技有限公司"}, {})
        assert todo == []

    def test_state_record_prevents_readding(self):
        """人工从 Excel 删掉后（状态文件仍有记录）→ 不再自动加回"""
        todo, _ = plan_additions(
            _cands(**{"上海北汇信息科技有限公司": 1}), set(), {"上海北汇信息科技有限公司": "2026-09-21"}
        )
        assert todo == []

    def test_blacklist_and_short_names_are_skipped(self):
        cands = _cands(**{"广东公司": 1, "广东汽车检测中心有限公司": 1, "合计": 1, "内部交易": 1})
        todo, skipped = plan_additions(cands, set(), {})
        assert todo == []
        assert len(skipped) == 4

    def test_sorted_by_amount_desc(self):
        cands = _cands(**{"甲公司某某某": 100, "乙公司某某某": 999})
        todo, _ = plan_additions(cands, set(), {})
        assert [t[0] for t in todo] == ["乙公司某某某", "甲公司某某某"]

    def test_blacklist_contains_legal_entity_names(self):
        assert "广东汽车检测中心有限公司" in BLACKLIST_NAMES
        assert "广东公司" in BLACKLIST_NAMES
        assert MIN_NAME_LEN >= 5
