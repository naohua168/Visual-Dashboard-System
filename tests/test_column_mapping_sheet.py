# -*- coding: utf-8 -*-
# Author: naohua168 <bai_bai168@qq.com>
"""字段映射 Excel 编辑层测试 — scripts/column_mapping_sheet.py

覆盖 2026-09-17 新增能力：让「配置编辑器.xlsx → 字段映射」sheet 控制清洗列名映射
"""
import json

import openpyxl
import pytest

from scripts.column_mapping_sheet import (
    MAP_HEADERS,
    build_mapping_rows,
    excel_to_column_mapping,
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
        assert rows[1][3:5] == ["创建时间", "创建日期"]

    def test_short_candidate_list_padded(self):
        rows = _rows()
        # 回款.日期 只有 1 个候选 → 其余候选列留空
        row = next(r for r in rows if r[:3] == ["财务端", "回款", "日期"])
        assert row[3] == "业务日期"
        assert row[4] == "" and row[CAND_PAD_END - 1] == ""

    def test_note_marks_single_candidate(self):
        rows = _rows()
        row = next(r for r in rows if r[:3] == ["财务端", "回款", "日期"])
        assert "唯一候选" in row[-1]


CAND_PAD_END = 3 + 5  # 数据源/来源/标准字段 + 候选1..5


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

    def test_extra_candidate_column_is_picked_up(self):
        cfg = {"数据源": {"财务端": {"收入": {"列映射": {"日期": ["创建时间"]}}}}}
        rows = [MAP_HEADERS + ["候选6"],
                ["财务端", "收入", "日期", "创建时间", "", "", "", "", "", "", "创建日期"]]
        mapping, _ = excel_to_column_mapping(_sheet(rows), cfg)
        assert mapping["财务端"]["收入"]["日期"] == ["创建时间", "创建日期"]

    def test_blank_rows_skipped(self):
        cfg = _cfg()
        rows = _rows(cfg) + [[None] * len(MAP_HEADERS)]
        mapping, _ = excel_to_column_mapping(_sheet(rows), cfg)
        assert mapping["财务端"]["收入"]["金额"] == ["不含税金额", "金额"]


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
        rows = self._mutate(cfg, ["财务端", "收入", "日期"], lambda r: r.__setitem__(4, "创建时间"))
        with pytest.raises(ValueError, match="候选重复"):
            excel_to_column_mapping(_sheet(rows), cfg)

    def test_all_candidates_empty(self):
        cfg = _cfg()
        rows = self._mutate(cfg, ["财务端", "回款", "日期"], lambda r: r.__setitem__(3, ""))
        with pytest.raises(ValueError, match="候选为空"):
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
