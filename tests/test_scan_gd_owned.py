# Author: naohua168 <bai_bai168@qq.com>
"""「广东自有客户」自动归入扫描 —— 候选判定逻辑测试（2026-09-21 用户口径）

规则：法人=广东汽车检测中心 且 **不属于任何销售**（公司级）→ 自动归入 广东自有客户/黎国键；
      · 已在配置里 → 跳过
      · 曾自动归入过（状态文件有记录，例如人工从 Excel 删除）→ **永不再自动加回**
      · 自身法人名 / 占位行（"广东公司"、"合计"…）/ 过短名字 → 排除
"""
import importlib.util
from pathlib import Path

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


# ══════════════════════════════════════════════════════════════
# 候选来源：运营端 + 财务端「广东公司.xlsx」（2026-11-02 按业务规则口径统一）
# ══════════════════════════════════════════════════════════════
def _gd_cfg(legal="广东汽车检测中心有限公司", mult=10000):
    return {
        "数据源": {
            "财务端": {
                "文件夹": "财务端数据",
                "广东公司": {
                    "文件名": "广东公司.xlsx",
                    "Sheet": {"收入": ["收入"], "回款": ["回款"]},
                    "引擎": "openpyxl",
                    "列映射": {"日期": ["日期"], "客户": ["客户", "客户名称"],
                               "金额": ["金额", "金额(万元)"]},
                    "过客户白名单": False,
                    "事业部固定": "检测",
                    "法人主体": legal,
                    "金额乘数": mult,
                },
            }
        }
    }


def _make_gd_file(path, inc_rows, pay_rows):
    """造一份广东公司.xlsx（收入/回款两个 Sheet，金额单位万元）"""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "收入"
    ws.append(["客户", "日期", "金额"])
    for r in inc_rows:
        ws.append(list(r))
    ws2 = wb.create_sheet("回款")
    ws2.append(["客户", "日期", "金额"])
    for r in pay_rows:
        ws2.append(list(r))
    wb.save(path)
    return path


class TestCollectFinancialGd:
    def test_reads_both_sheets_and_converts_to_yuan(self, tmp_path, monkeypatch):
        p = _make_gd_file(tmp_path / "广东公司.xlsx",
                          [("甲科技有限公司", "2026-05-01", 1.5)],
                          [("甲科技有限公司", "2026-06-01", 2.0),
                           ("乙科技有限公司", "2026-06-02", 0.5)])
        monkeypatch.setattr(mod, "get_data_path", lambda cfg, src, key: p)
        monkeypatch.setattr(mod, "_load_excluded_keys", lambda: set())

        found = mod.collect_from_financial_gd(_gd_cfg())
        assert set(found) == {"甲科技有限公司", "乙科技有限公司"}
        # 万元 × 10000 → 元
        assert found["甲科技有限公司"]["金额"] == 15000.0 + 20000.0
        assert found["甲科技有限公司"]["行数"] == 2
        assert sorted(found["甲科技有限公司"]["来源"]) == ["广东公司-回款", "广东公司-收入"]

    def test_skips_when_legal_is_not_gd(self, tmp_path, monkeypatch):
        p = _make_gd_file(tmp_path / "广东公司.xlsx", [("甲科技有限公司", "2026-05-01", 1)], [])
        monkeypatch.setattr(mod, "get_data_path", lambda cfg, src, key: p)
        assert mod.collect_from_financial_gd(_gd_cfg(legal="别的法人主体有限公司")) == {}

    def test_missing_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "get_data_path",
                            lambda cfg, src, key: tmp_path / "不存在.xlsx")
        assert mod.collect_from_financial_gd(_gd_cfg()) == {}

    def test_merges_with_operations_source(self, monkeypatch):
        """collect_candidates = 运营端 + 广东公司；同一客户行数/金额累加、来源合并"""
        monkeypatch.setattr(mod, "collect_from_operations",
                            lambda cfg: {"甲科技有限公司": {"来源": ["运营端-收入"],
                                                        "行数": 2, "金额": 100.0}})
        monkeypatch.setattr(mod, "collect_from_financial_gd",
                            lambda cfg: {"甲科技有限公司": {"来源": ["广东公司-收入"],
                                                        "行数": 1, "金额": 500.0},
                                         "乙科技有限公司": {"来源": ["广东公司-回款"],
                                                        "行数": 1, "金额": 300.0}})
        merged = mod.collect_candidates({})
        assert merged["甲科技有限公司"]["行数"] == 3
        assert merged["甲科技有限公司"]["金额"] == 600.0
        assert sorted(merged["甲科技有限公司"]["来源"]) == ["广东公司-收入", "运营端-收入"]
        assert merged["乙科技有限公司"]["行数"] == 1
