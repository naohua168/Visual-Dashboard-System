# -*- coding: utf-8 -*-
# Author: naohua168 <bai_bai168@qq.com>
"""配置编辑器「整本工作簿」测试 — 表格设计 + 横幅兼容解析（2026-09-28）

覆盖：
  - 统一样式：每张表第 1 行横幅、第 2 行表头、数据自第 3 行起、标签页颜色、冻结/筛选
  - 解析兼容：带横幅（表头在第 2 行）与历史文件（表头在第 1 行）都能解析
  - `--init` 模板：6 张 sheet 齐全、说明页在最后、解析回 JSON 一致
"""
import json
from pathlib import Path

import openpyxl
import pytest

import scripts.config_excel_to_json as cej
from scripts.sheet_style import TAB_COLORS, banner, header_row, locate_header_row

BASE_DIR = Path(__file__).parent.parent
EXCEL = BASE_DIR / "config" / "配置编辑器.xlsx"
SHEETS = ["时间配置", "展示规则", "销售归属", "KPI指标", "字段映射", "说明"]


def _sheet(rows, banner_text: str | None = None, headers: list[str] | None = None):
    """构造 sheet：headers 必填；banner_text 非空 → 横幅在第 1 行、表头第 2 行，
    否则按历史布局把表头写在第 1 行"""
    wb = openpyxl.Workbook()
    ws = wb.active
    if headers:
        if banner_text is not None:
            banner(ws, banner_text, len(headers))
            header_row(ws, headers, row=2)
        else:
            header_row(ws, headers, row=1)
    for r in rows:
        ws.append(r)
    return ws


def _public(node) -> dict:
    """去掉 _ 前缀说明字段，便于比较配置值（与 test_display_rules_sheet 同口径）"""
    out = {}
    for k, v in (node or {}).items():
        if isinstance(k, str) and k.startswith("_"):
            continue
        out[k] = _public(v) if isinstance(v, dict) else v
    return out


# ══════════════════════════════════════════════════════════════
# 表头行定位
# ══════════════════════════════════════════════════════════════
class TestLocateHeaderRow:
    def test_first_row(self):
        rows = [("页面", "指标", "值(万元)"), ("年度达成", "收入", 1)]
        assert locate_header_row(rows, ("页面", "指标")) == 0

    def test_after_banner(self):
        rows = [("说明横幅", None), ("页面", "指标", "值(万元)")]
        assert locate_header_row(rows, ("页面", "指标"), max_scan=4) == 1

    def test_not_found(self):
        assert locate_header_row([("甲", "乙")], ("页面", "指标")) == -1


# ══════════════════════════════════════════════════════════════
# 解析兼容：带横幅 / 无横幅
# ══════════════════════════════════════════════════════════════
class TestBannerTolerantParsing:
    TIME_HEADERS = ["配置名", "模式", "动态策略", "开始日期", "结束日期", "年份", "月份范围", "说明"]
    TIME_ROWS = [
        ["年度累计", "static", "", "2026-01-01", "2026-09-30", "", "", "数据总览/年度达成"],
        ["月度数据", "static", "", "2026-09-01", "2026-09-30", "", "", "月度达成页"],
        ["季度累计筛选", "static", "", "2026-07-01", "2026-09-30", "", "", "季度达成页"],
        ["年基线数据", "static", "", "", "", 2025, "1-9", "Phase 0"],
        ["结算模式", "常规", "", "", "", "", "", "月底结算/常规"],
    ]

    def test_time_banner_and_legacy(self):
        with_banner = _sheet(self.TIME_ROWS, "横幅", self.TIME_HEADERS)
        legacy = _sheet(self.TIME_ROWS, None, self.TIME_HEADERS)
        a = cej.excel_to_time_config(with_banner)
        b = cej.excel_to_time_config(legacy)
        assert a == b
        assert a["年度累计"]["end_date"] == "2026-09-30"
        assert a["结算模式"]["值"] == "常规"

    def test_time_column_order_independent(self):
        """列顺序调整（按表头名定位）也能解析"""
        heads = ["模式", "配置名", "开始日期", "结束日期", "动态策略", "年份", "月份范围", "说明"]
        rows = [[r[1], r[0], r[3], r[4], r[2], r[5], r[6], r[7]] for r in self.TIME_ROWS]
        ws = _sheet(rows, "横幅", heads)
        cfg = cej.excel_to_time_config(ws)
        assert cfg["月度数据"]["start_date"] == "2026-09-01"

    def test_kpi_banner(self):
        heads = ["页面", "指标", "值(万元)", "说明"]
        rows = [["年度达成", "收入", 50000, "覆盖"], ["年度达成", "回款", "", ""],
                ["月度达成", "收入", "", ""], ["月度达成", "回款", "", ""],
                ["季度达成", "收入", "", ""], ["季度达成", "回款", "", ""]]
        kpi = cej.excel_to_kpi(_sheet(rows, "横幅", heads))
        assert kpi["年度达成"]["收入"] == 50000.0
        assert kpi["月度达成"]["回款"] is None

    def test_attribution_banner(self):
        heads = ["母公司", "子公司", "指标", "部门", "销售", "比例", "说明"]
        rows = [["甲公司", "甲公司", "收入,回款", "检测", "张三", "1", ""],
                ["甲公司", "乙公司", "收入", "信息", "李四", "0.5", ""]]
        att = cej.excel_to_attribution(_sheet(rows, "横幅", heads))
        assert att["甲公司"]["子公司"]["乙公司"]["收入"]["信息"] == {"李四": 0.5}
        assert att["甲公司"]["子公司"]["甲公司"]["回款"]["检测"] == {"张三": 1.0}

    def test_time_missing_header_raises(self):
        ws = _sheet([["甲", "乙"]], "横幅", ["甲", "乙"])
        with pytest.raises(ValueError, match="找不到表头行"):
            cej.excel_to_time_config(ws)


# ══════════════════════════════════════════════════════════════
# 真实工作簿：统一设计
# ══════════════════════════════════════════════════════════════
@pytest.mark.skipif(not EXCEL.exists(), reason="配置编辑器.xlsx 不存在")
class TestRealWorkbookDesign:
    def _wb(self):
        return openpyxl.load_workbook(EXCEL)

    def test_sheet_set_and_order(self):
        assert self._wb().sheetnames == SHEETS

    def test_every_sheet_has_banner(self):
        """每张表第 1 行是横幅（说明页是标题行），表头在第 2 行"""
        wb = self._wb()
        for name in SHEETS:
            ws = wb[name]
            first = ws.cell(row=1, column=1).value
            assert first, f"{name} 缺少第 1 行横幅/标题"

    def test_tab_colors_and_freeze(self):
        wb = self._wb()
        for name in SHEETS:
            ws = wb[name]
            tab = ws.sheet_properties.tabColor
            assert tab is not None, f"{name} 缺少标签页颜色"
            assert str(tab.rgb).endswith(TAB_COLORS[name])
        for name in ("时间配置", "展示规则", "销售归属", "KPI指标", "字段映射"):
            assert wb[name].freeze_panes, f"{name} 未冻结窗格"

    def test_editable_columns_highlighted(self):
        """可编辑列（时间配置的模式/日期、销售归属的销售/比例、展示规则的值）为浅黄底"""
        wb = self._wb()
        assert wb["时间配置"].cell(row=3, column=2).fill.fgColor.rgb.endswith("FFF9E6")
        assert wb["销售归属"].cell(row=3, column=5).fill.fgColor.rgb.endswith("FFF9E6")
        ws = wb["展示规则"]
        data_row = next(r for r in range(3, ws.max_row + 1)
                        if ws.cell(row=r, column=4).value == "销售TopN")
        assert ws.cell(row=data_row, column=5).fill.fgColor.rgb.endswith("FFF9E6"), "值列未高亮"

    def test_sales_sheet_banded_by_parent(self):
        """销售归属：按母公司分块斑马纹（相邻母公司底色不同）"""
        ws = self._wb()["销售归属"]
        parents, fills = [], []
        for r in range(3, ws.max_row + 1):
            p = ws.cell(row=r, column=1).value
            if p and (not parents or parents[-1] != p):
                parents.append(p)
                fills.append(ws.cell(row=r, column=1).fill.fgColor.rgb)
        assert len(parents) > 5, "母公司数异常"
        assert len(set(fills)) >= 2, "未按母公司分块着色"

    def test_autofilter_on_data_sheets(self):
        wb = self._wb()
        for name, ref in (("时间配置", "A2:H2"), ("销售归属", "A2:G2"), ("字段映射", "A2:J2")):
            assert wb[name].auto_filter.ref == ref, f"{name} 自动筛选范围异常"

    def test_kpi_and_rules_keep_dropdowns(self):
        wb = self._wb()
        assert len(wb["KPI指标"].data_validations.dataValidation) == 2   # 页面 / 指标
        assert len(wb["时间配置"].data_validations.dataValidation) == 2  # 模式 / 动态策略
        assert len(wb["销售归属"].data_validations.dataValidation) == 2  # 指标 / 部门
        assert len(wb["展示规则"].data_validations.dataValidation) == 3  # 排序 / 整数 / 客户名提示

    def test_note_sheet_section_titles_styled(self):
        ws = self._wb()["说明"]
        texts = {r: ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)}
        sections = [r for r, v in texts.items()
                    if isinstance(v, str) and v[:2] in ("1.", "2.", "3.")]
        assert sections, "说明页缺少分节标题"
        for r in sections:
            assert ws.cell(row=r, column=1).font.bold, f"说明页第 {r} 行分节标题未加粗"


# ══════════════════════════════════════════════════════════════
# --init 模板（写到临时路径）
# ══════════════════════════════════════════════════════════════
def test_init_template_design(tmp_path, monkeypatch):
    out = tmp_path / "editor_test.xlsx"
    monkeypatch.setattr(cej, "EXCEL_PATH", out)
    cej.init_excel_template()

    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == SHEETS, f"sheet 顺序/集合异常: {wb.sheetnames}"
    for name in SHEETS:
        assert wb[name].cell(row=1, column=1).value, f"{name} 缺少横幅"
    assert wb["展示规则"].cell(row=2, column=4).value == "配置项"
    assert wb["时间配置"].cell(row=2, column=1).value == "配置名"

    # 解析回 JSON：与事实源一致
    rules = json.loads((BASE_DIR / "config" / "前端渲染" / "展示规则.json").read_text(encoding="utf-8"))
    from scripts.display_rules_sheet import excel_to_display_rules

    parsed = excel_to_display_rules(wb["展示规则"])
    for page in rules:
        if page.startswith("_"):
            continue
        assert _public(parsed[page]) == _public(rules[page]), f"{page} 模板往返不一致"

    # 时间配置 / KPI / 销售归属 也能从带横幅的模板解析
    cfg = json.loads((BASE_DIR / "config" / "清洗配置" / "cleaning_config.json").read_text(encoding="utf-8"))
    assert cej.excel_to_time_config(wb["时间配置"])["年度累计"]["end_date"] == cfg["时间范围"]["年度累计"]["end_date"]
    assert cej.excel_to_kpi(wb["KPI指标"])["年度达成"]["收入"] is None
    att = cej.excel_to_attribution(wb["销售归属"])
    assert len(att) == 118 and sum(len(g["子公司"]) for g in att.values()) == 583
