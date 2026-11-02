# -*- coding: utf-8 -*-
# Author: naohua168 <bai_bai168@qq.com>
"""字段映射 Excel 编辑层测试 — scripts/column_mapping_sheet.py

覆盖 2026-09-17 新增能力：让「配置编辑器.xlsx → 字段映射」sheet 控制清洗列名映射
"""
import json
from pathlib import Path

import openpyxl
import pytest

from scripts.column_mapping_sheet import (
    CAND_MAX,
    MAP_HEADERS,
    VALUE_COL,
    _iter_sources,
    build_mapping_rows,
    excel_to_column_mapping,
    excel_to_kept_values,
    read_latest_hits,
    update_column_mapping,
)

MIN_CFG = {
    "数据源": {
        "_说明": "两套独立数据",
        "财务端": {
            "文件夹": "data/raw/财务端数据",
            "收入": {
                "文件名": "收入.xlsx",
                "列映射": {"日期": ["创建时间", "创建日期"], "金额": ["不含税金额", "金额"]},
                "金额除数": 1,
                "过客户白名单": True,
            },
            "回款": {
                "文件名": "回款.xlsx",
                "列映射": {"日期": ["业务日期"], "金额": ["应收金额"]},
                "过客户白名单": True,
            },
        },
        "运营端": {
            "收入": {
                "文件名": "收入.xls",
                "列映射": {"日期": ["确认时间", "到款时间"], "客户": ["客户"]},
            }
        },
    }
}


def _cfg() -> dict:
    return json.loads(json.dumps(MIN_CFG))


def _sheet(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    return ws


def _rows(cfg=None):
    return build_mapping_rows(cfg or _cfg())


class TestBuildRows:
    def test_header_and_row_count(self):
        cfg = _cfg()
        rows = _rows(cfg)
        assert rows[0] == MAP_HEADERS
        # 财务端 收入2字段 + 回款2字段 + 运营端 收入2字段 = 6 行
        assert len(rows) == 1 + 6
        assert rows[1][:3] == ["财务端", "收入", "日期"]
        # 候选合并为一个单元格，用「/」分隔（2026-10-29 口径）
        assert rows[1][3] == "创建时间 / 创建日期"

    def test_single_candidate_cell(self):
        rows = _rows()
        row = next(r for r in rows if r[:3] == ["财务端", "回款", "日期"])
        assert row[3] == "业务日期"

    def test_note_marks_single_candidate(self):
        rows = _rows()
        row = next(r for r in rows if r[:3] == ["财务端", "回款", "日期"])
        assert "唯一候选" in row[-1]

    def test_candidates_capped_at_three(self):
        """2026-10-29 口径：候选最多 3 个，超出截断并在说明列标注"""
        cfg = {"数据源": {"财务端": {"收入": {"列映射": {"金额": ["a", "b", "c", "d"]}}}}}
        rows = build_mapping_rows(cfg)
        row = rows[1]
        assert row[3] == "a / b / c"
        assert row[4] == ""  # 「必填取值」列（未配置 → 空）
        assert "截断" in row[-1]

    def test_slash_in_column_name_is_escaped(self):
        """列名本身含「/」时转义为 \\/，避免被当成分隔符"""
        cfg = {"数据源": {"财务端": {"收入": {"列映射": {"金额": ["产品名称/物料名称"]}}}}}
        rows = build_mapping_rows(cfg)
        assert rows[1][3] == "产品名称\\/物料名称"

    def test_kept_values_rendered_in_value_column(self):
        """保留取值（如 已审核 / 外部结算）要体现在「必填取值」列"""
        cfg = {"数据源": {"财务端": {"收入": {
            "列映射": {"单据状态": ["单据状态"], "委托类型": ["委托类型"]},
            "保留取值": {"单据状态": ["已审核"], "委托类型": ["外部结算"]},
        }}}}
        rows = build_mapping_rows(cfg)
        i = MAP_HEADERS.index(VALUE_COL)
        got = {r[2]: r[i] for r in rows[1:]}
        assert got == {"单据状态": "已审核", "委托类型": "外部结算"}


CAND_COL_IDX = MAP_HEADERS.index("候选列名")  # 候选/取值的列位置（表结构变更时自动跟随）


class TestParse:
    def test_roundtrip_equals_source_config(self):
        cfg = _cfg()
        mapping, warns = excel_to_column_mapping(_sheet(_rows(cfg)), cfg)
        assert warns == []
        for src, name, spec in [
            ("财务端", "收入", cfg["数据源"]["财务端"]["收入"]),
            ("财务端", "回款", cfg["数据源"]["财务端"]["回款"]),
            ("运营端", "收入", cfg["数据源"]["运营端"]["收入"]),
        ]:
            assert mapping[src][name] == spec["列映射"]

    def test_hit_and_note_columns_ignored(self):
        cfg = _cfg()
        rows = _rows(cfg)
        i_hit = MAP_HEADERS.index("当前命中(只读)")
        for r in rows[1:]:
            r[i_hit] = "不存在的列名"
        mapping, _ = excel_to_column_mapping(_sheet(rows), cfg)
        assert "不存在的列名" not in mapping["财务端"]["收入"]["日期"]

    def test_legacy_multi_column_layout_still_parsed(self):
        """旧版「候选1..候选5」多列布局仍可解析（解析时按上限截断）"""
        cfg = {"数据源": {"财务端": {"收入": {"列映射": {"日期": ["创建时间"]}}}}}
        headers = ["数据源", "来源", "标准字段", "候选1", "候选2", "候选3", "候选4",
                   "当前命中(只读)", "说明"]
        rows = [headers,
                ["财务端", "收入", "日期", "创建时间", "创建日期", "审核日期", "第四候选", "", ""]]
        mapping, warns = excel_to_column_mapping(_sheet(rows), cfg)
        assert mapping["财务端"]["收入"]["日期"] == ["创建时间", "创建日期", "审核日期"]
        assert any("截断" in w for w in warns)

    def test_single_cell_split_and_escape(self):
        """单元内用「/」分隔；`\\/` 还原为字面量斜杠"""
        cfg = {"数据源": {"财务端": {"收入": {"列映射": {"金额": ["a"]}}}}}
        rows = _rows(cfg)
        rows[1][CAND_COL_IDX] = "不含税金额/金额\\/总计"
        mapping, _ = excel_to_column_mapping(_sheet(rows), cfg)
        assert mapping["财务端"]["收入"]["金额"] == ["不含税金额", "金额/总计"]

    def test_blank_rows_skipped(self):
        cfg = _cfg()
        rows = _rows(cfg) + [[None] * len(MAP_HEADERS)]
        mapping, _ = excel_to_column_mapping(_sheet(rows), cfg)
        assert mapping["财务端"]["收入"]["金额"] == ["不含税金额", "金额"]


class TestKeptValues:
    """「必填取值」列 ↔ 保留取值"""

    def test_roundtrip(self):
        cfg = _cfg()
        inc = cfg["数据源"]["财务端"]["收入"]
        inc["列映射"].update({"单据状态": ["单据状态"], "委托类型": ["委托类型"]})
        inc["保留取值"] = {"单据状态": ["已审核"], "委托类型": ["外部结算"]}
        kept, warns = excel_to_kept_values(_sheet(_rows(cfg)), cfg)
        assert warns == []
        inc = kept["财务端"]["收入"]
        assert inc["单据状态"] == ["已审核"]
        assert inc["委托类型"] == ["外部结算"]
        assert inc["日期"] == [] and inc["金额"] == []  # 空单元格 → 显式空列表（不限制）

    def test_multiple_values_split(self):
        cfg = _cfg()
        rows = _rows(cfg)
        rows[1][MAP_HEADERS.index(VALUE_COL)] = "已审核, 外部结算；已收款"
        kept, _ = excel_to_kept_values(_sheet(rows), cfg)
        assert kept["财务端"]["收入"]["日期"] == ["已审核", "外部结算", "已收款"]

    def test_missing_column_is_backward_compatible(self):
        """历史工作簿没有「必填取值」列 → 返回空，调用方不改动保留取值"""
        cfg = _cfg()
        rows = _rows(cfg)
        i = MAP_HEADERS.index(VALUE_COL)
        headers = [h for h in MAP_HEADERS if h != VALUE_COL]
        trimmed = [headers] + [[v for j, v in enumerate(r) if j != i] for r in rows[1:]]
        kept, warns = excel_to_kept_values(_sheet(trimmed), cfg)
        assert (kept, warns) == (None, [])  # None = 不改动任何取值配置

    def test_duplicate_value_rejected(self):
        cfg = _cfg()
        rows = _rows(cfg)
        rows[1][MAP_HEADERS.index(VALUE_COL)] = "已审核、已审核"
        with pytest.raises(ValueError, match="必填取值重复"):
            excel_to_kept_values(_sheet(rows), cfg)

    def test_value_on_unknown_field_rejected(self):
        cfg = _cfg()
        rows = _rows(cfg)
        rows[1][2] = "乱七八糟字段"
        rows[1][MAP_HEADERS.index(VALUE_COL)] = "已审核"
        with pytest.raises(ValueError, match="未知标准字段"):
            excel_to_kept_values(_sheet(rows), cfg)

    def test_excluded_marker_value_rendered(self):
        """排除标记值（√，命中即剔除）也要体现在「必填取值」列"""
        cfg = {"数据源": {"财务端": {"收入": {
            "列映射": {"排除标记": ["初始化"]},
            "排除标记值": ["√"],
        }}}}
        rows = build_mapping_rows(cfg)
        i = MAP_HEADERS.index(VALUE_COL)
        assert rows[1][i] == "√"
        assert "剔除" in rows[1][-1]

    def test_excluded_marker_parsed(self):
        cfg = {"数据源": {"财务端": {"收入": {
            "列映射": {"排除标记": ["初始化"]},
            "排除标记值": ["√"],
        }}}}
        kept, _ = excel_to_kept_values(_sheet(build_mapping_rows(cfg)), cfg)
        assert kept["财务端"]["收入"]["排除标记"] == ["√"]

    def test_department_and_internal_trade_values_parsed(self):
        """部门 / 内部交易 的取值可编辑并解析（默认值分别为映射表 4 个全称 / 是）"""
        cfg = {"数据源": {"运营端": {"收入": {
            "列映射": {"部门": ["事业部"], "内部交易": ["是否属于内部单位"], "金额": ["收入"]},
            "事业部取值": ["检测", "信息"],
        }}}}
        rows = build_mapping_rows(cfg)
        i = MAP_HEADERS.index(VALUE_COL)
        dept = next(r for r in rows if r[2] == "部门")
        internal = next(r for r in rows if r[2] == "内部交易")
        assert dept[i] == "检测 / 信息"   # 配置值原样展示
        assert internal[i] == "是"        # 未配置 → 默认值
        dept[i] = "检测/零部件事业部"
        kept, _ = excel_to_kept_values(_sheet(rows), cfg)
        assert kept["运营端"]["收入"]["部门"] == ["检测", "零部件事业部"]
        assert kept["运营端"]["收入"]["内部交易"] == ["是"]


class TestValidation:
    def _mutate(self, cfg, target, fn):
        rows = _rows(cfg)
        for r in rows[1:]:
            if r[:3] == target:
                fn(r)
        return rows

    def test_unknown_source(self):
        cfg = _cfg()
        rows = _rows(cfg)
        rows[1][0] = "财务端X"
        with pytest.raises(ValueError, match="未知来源"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_unknown_field(self):
        cfg = _cfg()
        rows = _rows(cfg)
        rows[1][2] = "乱七八糟字段"
        with pytest.raises(ValueError, match="未知标准字段"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_missing_existing_field(self):
        cfg = _cfg()
        rows = [r for r in _rows(cfg) if r[:3] != ["财务端", "收入", "金额"]]
        with pytest.raises(ValueError, match="缺少原有标准字段"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_duplicate_candidate(self):
        cfg = _cfg()
        rows = self._mutate(cfg, ["财务端", "收入", "日期"],
                            lambda r: r.__setitem__(CAND_COL_IDX, "创建时间/创建时间"))
        with pytest.raises(ValueError, match="候选重复"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_all_candidates_empty(self):
        cfg = _cfg()
        rows = self._mutate(cfg, ["财务端", "回款", "日期"],
                            lambda r: r.__setitem__(CAND_COL_IDX, ""))
        with pytest.raises(ValueError, match="候选为空"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_more_than_three_candidates_rejected(self):
        """单列布局超过 3 个候选 → 明确报错，不静默丢弃"""
        cfg = _cfg()
        rows = self._mutate(cfg, ["财务端", "收入", "日期"],
                            lambda r: r.__setitem__(CAND_COL_IDX, "a/b/c/d"))
        with pytest.raises(ValueError, match="超过上限"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_duplicate_row(self):
        cfg = _cfg()
        rows = _rows(cfg)
        rows.append(list(rows[1]))
        with pytest.raises(ValueError, match="重复行"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_missing_required_column(self):
        cfg = _cfg()
        rows = [["数据源", "来源", "候选1"], ["财务端", "收入", "创建时间"]]
        with pytest.raises(ValueError, match="表头缺少必需列"):
            excel_to_column_mapping(_sheet(rows), cfg)


class TestUpdateConfig:
    def _write_cfg(self, tmp_path, cfg=None):
        p = tmp_path / "cleaning_config.json"
        p.write_text(json.dumps(cfg or _cfg(), ensure_ascii=False, indent=2), encoding="utf-8")
        return p

    def test_only_mapping_replaced_others_kept(self, tmp_path):
        cfg = _cfg()
        p = self._write_cfg(tmp_path)
        mapping = {"财务端": {"收入": {"日期": ["创建时间", "新列名"], "金额": ["不含税金额", "金额"]}}}
        new_cfg, changed = update_column_mapping(mapping, cfg_path=p, backup_dir=tmp_path / "logs")
        assert changed == ["财务端.收入"]
        saved = json.loads(p.read_text(encoding="utf-8"))
        assert saved["数据源"]["财务端"]["收入"]["列映射"]["日期"] == ["创建时间", "新列名"]
        # 其余键原样保留
        assert saved["数据源"]["财务端"]["收入"]["金额除数"] == 1
        assert saved["数据源"]["财务端"]["收入"]["过客户白名单"] is True
        assert saved["数据源"]["财务端"]["收入"]["文件名"] == "收入.xlsx"
        assert saved["数据源"]["财务端"]["回款"]["列映射"] == cfg["数据源"]["财务端"]["回款"]["列映射"]
        assert saved["数据源"]["_说明"] == "两套独立数据"
        # 备份已生成
        assert len(list((tmp_path / "logs").glob("cleaning_config.bak_*.json"))) == 1

    def test_no_change_detected(self, tmp_path):
        cfg = _cfg()
        p = self._write_cfg(tmp_path)
        mapping = {"财务端": {"收入": cfg["数据源"]["财务端"]["收入"]["列映射"]}}
        _, changed = update_column_mapping(mapping, cfg_path=p, backup_dir=tmp_path / "logs")
        assert changed == []

    def test_dry_run_does_not_write(self, tmp_path):
        p = self._write_cfg(tmp_path)
        before = p.read_text(encoding="utf-8")
        mapping = {"财务端": {"回款": {"日期": ["新日期列"], "金额": ["应收金额"]}}}
        _, changed = update_column_mapping(mapping, dry_run=True,
                                           cfg_path=p, backup_dir=tmp_path / "logs")
        assert changed == ["财务端.回款"]
        assert p.read_text(encoding="utf-8") == before
        assert not (tmp_path / "logs").exists()

    def test_output_is_valid_json(self, tmp_path):
        p = self._write_cfg(tmp_path)
        update_column_mapping({"财务端": {"收入": {"日期": ["a"]}}},
                             cfg_path=p, backup_dir=tmp_path / "logs")
        json.loads(p.read_text(encoding="utf-8"))  # 不抛异常即有效

    def test_kept_values_written_and_cleared(self, tmp_path):
        """必填取值：填了 → 写入保留取值；清空 → 删除该键"""
        cfg = _cfg()
        cfg["数据源"]["财务端"]["收入"]["保留取值"] = {"金额": ["旧值"]}
        cfg["数据源"]["财务端"]["回款"]["保留取值"] = {"金额": ["旧值"]}
        p = self._write_cfg(tmp_path, cfg)
        mapping = {
            "财务端": {
                "收入": cfg["数据源"]["财务端"]["收入"]["列映射"],
                "回款": cfg["数据源"]["财务端"]["回款"]["列映射"],
            }
        }
        kept = {"财务端": {"收入": {"金额": ["已审核", "外部结算"]}}}  # 回款清空
        _, changed = update_column_mapping(
            mapping, kept_values=kept, cfg_path=p, backup_dir=tmp_path / "logs"
        )
        saved = json.loads(p.read_text(encoding="utf-8"))
        assert saved["数据源"]["财务端"]["收入"]["保留取值"] == {"金额": ["已审核", "外部结算"]}
        assert "保留取值" not in saved["数据源"]["财务端"]["回款"]
        assert "财务端.收入.保留取值" in changed and "财务端.回款.保留取值" in changed

    def test_kept_values_none_keeps_untouched(self, tmp_path):
        """kept_values=None（历史工作簿）→ 保留取值 原样不动"""
        cfg = _cfg()
        cfg["数据源"]["财务端"]["收入"]["保留取值"] = {"金额": ["已审核"]}
        p = self._write_cfg(tmp_path, cfg)
        update_column_mapping(
            {"财务端": {"收入": cfg["数据源"]["财务端"]["收入"]["列映射"]}},
            cfg_path=p, backup_dir=tmp_path / "logs",
        )
        saved = json.loads(p.read_text(encoding="utf-8"))
        assert saved["数据源"]["财务端"]["收入"]["保留取值"] == {"金额": ["已审核"]}

    def test_excluded_marker_written_to_flat_key(self, tmp_path):
        """排除标记的取值写回同级的 排除标记值（平铺列表，命中即剔除）"""
        cfg = _cfg()
        inc = cfg["数据源"]["财务端"]["收入"]
        inc["列映射"]["排除标记"] = ["初始化"]
        inc["排除标记值"] = ["√"]
        p = self._write_cfg(tmp_path, cfg)
        mapping = {"财务端": {"收入": inc["列映射"]}}
        kept = {"财务端": {"收入": {"排除标记": ["√", "是"]}}}
        _, changed = update_column_mapping(
            mapping, kept_values=kept, cfg_path=p, backup_dir=tmp_path / "logs"
        )
        saved = json.loads(p.read_text(encoding="utf-8"))
        assert saved["数据源"]["财务端"]["收入"]["排除标记值"] == ["√", "是"]
        assert "保留取值" not in saved["数据源"]["财务端"]["收入"]
        assert any("排除标记值" in c for c in changed)

    def test_excluded_marker_cleared_removes_key(self, tmp_path):
        """清空「必填取值」→ 删除 排除标记值 键"""
        cfg = _cfg()
        inc = cfg["数据源"]["财务端"]["收入"]
        inc["列映射"]["排除标记"] = ["初始化"]
        inc["排除标记值"] = ["√"]
        p = self._write_cfg(tmp_path, cfg)
        mapping = {"财务端": {"收入": inc["列映射"]}}
        _, changed = update_column_mapping(
            mapping, kept_values={"财务端": {"收入": {}}},
            cfg_path=p, backup_dir=tmp_path / "logs",
        )
        saved = json.loads(p.read_text(encoding="utf-8"))
        assert "排除标记值" not in saved["数据源"]["财务端"]["收入"]
        assert any("排除标记值" in c for c in changed)

    def test_dept_values_written_to_flat_key(self, tmp_path):
        """事业部取值 写回平铺列表（可写简称/全称，原样保留）"""
        cfg = _cfg()
        inc = cfg["数据源"]["财务端"]["收入"]
        inc["列映射"]["部门"] = ["成本中心"]
        p = self._write_cfg(tmp_path, cfg)
        mapping = {"财务端": {"收入": inc["列映射"]}}
        kept = {"财务端": {"收入": {"部门": ["检测", "能源动力事业部"]}}}
        _, changed = update_column_mapping(
            mapping, kept_values=kept, cfg_path=p, backup_dir=tmp_path / "logs"
        )
        saved = json.loads(p.read_text(encoding="utf-8"))
        assert saved["数据源"]["财务端"]["收入"]["事业部取值"] == ["检测", "能源动力事业部"]
        assert "保留取值" not in saved["数据源"]["财务端"]["收入"]
        assert any("事业部取值" in c for c in changed)

    def test_dept_values_cleared_written_as_empty_list(self, tmp_path):
        """部门取值清空 → 显式写空列表（= 不限制），不是删键"""
        cfg = _cfg()
        inc = cfg["数据源"]["财务端"]["收入"]
        inc["列映射"]["部门"] = ["成本中心"]
        inc["事业部取值"] = ["检测", "信息"]
        p = self._write_cfg(tmp_path, cfg)
        mapping = {"财务端": {"收入": inc["列映射"]}}
        _, _ = update_column_mapping(
            mapping, kept_values={"财务端": {"收入": {"部门": []}}},
            cfg_path=p, backup_dir=tmp_path / "logs",
        )
        saved = json.loads(p.read_text(encoding="utf-8"))
        assert saved["数据源"]["财务端"]["收入"]["事业部取值"] == []


class TestHitLogParsing:
    LOG = """────────────────────────────────────────────────────────────────
2026-09-17 10:00:00  [财务端收入] 列名命中
────────────────────────────────────────────────────────────────
  日期   <- 创建时间  （第 1/3 候选）
  部门   <- 成本中心  ⚠️ 降级命中（第 2/2 候选）
  ⚠️ 降级命中 1 处: 部门←成本中心

────────────────────────────────────────────────────────────────
2026-09-17 11:00:00  [财务端收入] 列名命中
────────────────────────────────────────────────────────────────
  日期   <- 创建日期  （第 1/2 候选）

────────────────────────────────────────────────────────────────
2026-09-17 11:00:00  [广东收入] 列名命中
────────────────────────────────────────────────────────────────
  日期 <- 日期  （第 1/2 候选）
"""

    def test_latest_block_wins_and_summary_skipped(self, tmp_path):
        (tmp_path / "column_hits_20260917.txt").write_text(self.LOG, encoding="utf-8")
        hits = read_latest_hits(tmp_path)
        assert hits["财务端收入"]["日期"] == "创建日期"  # 同一来源取最后一次
        assert hits["广东收入"]["日期"] == "日期"
        assert "⚠️" not in hits["财务端收入"]  # 汇总行不被解析为字段

    def test_missing_dir_returns_empty(self, tmp_path):
        assert read_latest_hits(tmp_path / "nope") == {}

    def test_hit_backfilled_into_rows(self, tmp_path):
        (tmp_path / "column_hits_20260917.txt").write_text(self.LOG, encoding="utf-8")
        rows = build_mapping_rows(_cfg(), read_latest_hits(tmp_path))
        row = next(r for r in rows if r[:3] == ["财务端", "收入", "日期"])
        assert row[MAP_HEADERS.index("当前命中(只读)")] == "创建日期"


# ──────────────────────────────────────────────────────────────
# 真实配置文件一致性：配置编辑器.xlsx ↔ cleaning_config.json
# ──────────────────────────────────────────────────────────────
REAL_ROOT = Path(__file__).parent.parent
REAL_EDITOR = REAL_ROOT / "config" / "配置编辑器.xlsx"
REAL_CFG = REAL_ROOT / "config" / "清洗配置" / "cleaning_config.json"


@pytest.mark.skipif(not REAL_EDITOR.exists(), reason="配置编辑器.xlsx 不存在")
class TestRealConfigConsistency:
    """两个维护入口（Excel 编辑层 / JSON 事实源）不允许漂移

    失败时运行 `python scripts/config_excel_to_json.py` 同步即可（Excel → JSON）。
    """

    def test_mapping_sheet_matches_json(self):
        cfg = json.loads(REAL_CFG.read_text(encoding="utf-8"))
        mapping, _ = excel_to_column_mapping(
            openpyxl.load_workbook(REAL_EDITOR)["字段映射"], cfg
        )
        for src, name, spec in _iter_sources(cfg):
            expect = {f: v for f, v in spec["列映射"].items() if not f.startswith("_")}
            assert mapping[src][name] == expect, (
                f"{src}/{name} 列映射与 JSON 不一致，请同步: python scripts/config_excel_to_json.py"
            )

    def test_department_and_internal_trade_show_values(self):
        """部门（事业部全称）/ 内部交易（是）的取值要体现在表里（只读展示）"""
        cfg = json.loads(REAL_CFG.read_text(encoding="utf-8"))
        rows = build_mapping_rows(cfg)
        i = MAP_HEADERS.index(VALUE_COL)
        dept_rows = [r for r in rows[1:] if r[2] == "部门"]
        assert dept_rows and all(r[i] for r in dept_rows), "部门 应显示事业部全称"
        internal_rows = [r for r in rows[1:] if r[2] == "内部交易"]
        assert internal_rows and all(r[i] == "是" for r in internal_rows)

    def test_shaoguan_amount_is_yuan(self):
        """2026-09-28 起 南方韶关 整文件（收入+回款）单位为「元」→ 金额乘数 1"""
        cfg = json.loads(REAL_CFG.read_text(encoding="utf-8"))
        assert cfg["数据源"]["财务端"]["南方韶关"]["金额乘数"] == 1

        ws = openpyxl.load_workbook(REAL_EDITOR)["字段映射"]
        row = next(
            r for r in ws.iter_rows(min_row=2, values_only=True)
            if tuple(str(v).strip() if v else "" for v in r[:3]) == ("财务端", "南方韶关", "金额")
        )
        cands = [c.strip() for c in str(row[3]).split("/") if c.strip()]
        assert "金额(元)" in cands, f"韶关金额候选应含「金额(元)」: {cands}"

    def test_note_sheet_documents_units(self):
        """「说明」sheet 第 9 节说明各来源金额单位（编辑器是维护入口）"""
        wb = openpyxl.load_workbook(REAL_EDITOR)
        text = "\n".join(str(r[0]) for r in wb["说明"].iter_rows(values_only=True) if r[0])
        assert "9. 金额单位" in text
        assert "南方韶关 = 元" in text
