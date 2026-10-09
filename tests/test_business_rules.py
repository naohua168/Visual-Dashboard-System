# Author: naohua168 <bai_bai168@qq.com>
"""业务规则参数测试（2026-09-29 新增）—— engine/core/business_rules.py

覆盖：默认值与现状一致、业务规则.json 覆盖生效、法人主体判定沿用全角半角容错、
以及"代码里的模块常量确实来自配置文件"（防止以后又写回硬编码）。
"""
import json

import pytest

from engine.core import business_rules as br


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    """每次测试重新读配置（缓存是进程级的）"""
    monkeypatch.setattr(br, "_RULES", None)


def test_defaults_match_current_business():
    assert br.sales_gd_self() == "黎国键"
    assert br.sales_byd_gd() == "黄浩浩"
    assert br.sales_byd_other() == "周涵林"
    assert br.parent_gd_self() == "广东自有客户"
    assert br.parent_other() == "零部件客户"
    assert br.parent_byd_industry() == "比亚迪汽车工业有限公司"
    assert br.parent_byd_battery() == "比亚迪电池"
    assert br.parent_sg() == "南方韶关"
    assert br.legal_gd() == "广东汽车检测中心有限公司"
    assert "韶关" in br.legal_sg()
    assert len(br.byd_subs()) == 11 and "合肥比亚迪汽车有限公司" in br.byd_subs()


def test_real_config_file_is_readable():
    """仓库里的 业务规则.json 必须能被解析（占位/示例值都不能影响默认口径）"""
    data = json.loads(br.RULES_PATH.read_text(encoding="utf-8"))
    assert "销售" in data and "父组" in data and "法人主体" in data and "比亚迪子公司" in data
    assert data["销售"]["广东自有"] == br.sales_gd_self()


def test_json_override(tmp_path, monkeypatch):
    cfg = {
        "销售": {"广东自有": "新销售甲", "比亚迪广东主体": "新销售乙"},
        "父组": {"南方韶关": "韶关新名"},
        "法人主体": {"广东汽车检测中心": "广东汽车检测中心(新)有限公司"},
    }
    p = tmp_path / "业务规则.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(br, "RULES_PATH", p)

    assert br.sales_gd_self() == "新销售甲"
    assert br.sales_byd_gd() == "新销售乙"
    assert br.sales_byd_other() == "周涵林"      # 未覆盖的项保持默认
    assert br.parent_sg() == "韶关新名"
    assert br.is_gd_legal("广东汽车检测中心（新)有限公司")   # 全角半角/空白仍容错
    assert not br.is_gd_legal("南方（韶关）智能网联新能源汽车试验检测中心有限公司")


def test_is_legal_helpers():
    assert br.is_gd_legal("广东汽车检测中心有限公司 ")
    assert not br.is_gd_legal("")
    assert br.is_sg_legal("南方(韶关)智能网联新能源汽车试验检测中心有限公司")
    assert not br.is_sg_legal(None)
    assert br.is_sz_legal("中认车联网技术服务（深圳）有限公司")


def test_broken_config_falls_back(tmp_path, monkeypatch, capsys):
    """配置写坏了 → 打警告 + 用默认值，不让流水线崩"""
    p = tmp_path / "业务规则.json"
    p.write_text("{ this is not json", encoding="utf-8")
    monkeypatch.setattr(br, "RULES_PATH", p)
    assert br.sales_gd_self() == "黎国键"
    assert br.byd_subs()


def test_modules_have_no_hardcoded_sales_names():
    """销售引擎里的常量来自业务规则（源码里不再写死销售名/父组名）"""
    import engine.sales.run as sales_run
    import processors.page_data_utils as pdu

    assert sales_run.BYD_GD_SALES == br.sales_byd_gd()
    assert sales_run.BYD_OTHER_SALES == br.sales_byd_other()
    assert sales_run.GD_PARENT_GROUP == br.parent_gd_self()
    assert sales_run.OTHER_PARENT_GROUP == br.parent_other()
    assert pdu.BYD_PARENT_BATTERY == br.parent_byd_battery()
    assert pdu.SG_LEGAL_ENTITY == br.legal_sg()

    # 源码里不应再出现"给这些常量赋值"的硬编码（注释/文档里提到不算）
    src = br._BASE_DIR / "engine" / "sales" / "run.py"
    text = src.read_text(encoding="utf-8")
    for literal in ('BYD_GD_SALES = "', 'BYD_OTHER_SALES = "', 'GD_PARENT_GROUP = "',
                    'OTHER_PARENT_GROUP = "', 'BYD_SUB_COMPANIES = ['):
        assert literal not in text, f"销售引擎仍有硬编码: {literal}"

    scan = (br._BASE_DIR / "scripts" / "scan_gd_owned.py").read_text(encoding="utf-8")
    for literal in ('GD_SALES = "', 'GD_PARENT = "', 'GD_LEGAL = "',
                    'STATE_PATH = BASE_DIR', 'BLACKLIST_NAMES = {', 'MIN_NAME_LEN = 5',
                    'LEGAL_COLS = [', 'CUST_COLS = [', 'INT_COLS = [', 'INTERNAL_VALUES = {'):
        assert literal not in scan, f"扫描脚本仍有硬编码: {literal}"

    cleaner = (br._BASE_DIR / "engine" / "yearly_baseline" / "cleaner.py").read_text(encoding="utf-8")
    assert '"检测工程事业部": "检测"' not in cleaner, "年基线事业部映射仍写死"
    assert '"广东公司": "广东汽车检测中心有限公司"' not in cleaner, "年基线法人简称映射仍写死"

    fin = (br._BASE_DIR / "engine" / "income_payment" / "financial.py").read_text(encoding="utf-8")
    assert '_DEFAULT_EXCLUDE_VALUES = ("√"' not in fin, "期初剔除标记值仍写死"


# ══════════════════════════════════════════════════════════════
# 新增分节：部门 / 简称映射 / 广东自有归入 / 期初剔除 / 归入规则
# ══════════════════════════════════════════════════════════════
def test_departments_single_source():
    """部门列表 = 业务规则.json；引擎/渲染层/扫描脚本/汇总表/DEPT 下拉都取它"""
    import engine.sales.run as sales_run
    import processors.page_data_utils as pdu
    from scripts import config_excel_to_json as cej

    deps = br.departments()
    assert deps == ["检测", "信息", "能源", "海外"]
    assert sales_run.DEPARTMENTS == deps
    assert pdu.DEPARTMENTS == deps
    assert cej.DEPT_VALUES == deps


def test_departments_tolerates_written_string(tmp_path, monkeypatch):
    """手写成「检测/信息/能源/海外」也能解析（跟指标列一个脾气）"""
    p = tmp_path / "业务规则.json"
    p.write_text(json.dumps({"部门": {"列表": "检测/信息/能源,海外"}}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(br, "RULES_PATH", p)
    assert br.departments() == ["检测", "信息", "能源", "海外"]


def test_alias_and_full_maps():
    assert br.dept_full_map()["检测工程事业部"] == "检测"
    assert br.entity_alias()["广东公司"] == br.legal_gd()
    assert br.legal_full("广东公司") == br.legal_gd()
    assert br.legal_full("广东公司 ") == br.legal_gd()          # 空白容错
    assert br.legal_full("不认识的法人") == "不认识的法人"        # 原样返回
    assert br.legal_hunan() == "中汽院智能网联汽车检测中心（湖南）有限公司"


def test_sz_marker_configurable(tmp_path, monkeypatch):
    p = tmp_path / "业务规则.json"
    p.write_text(json.dumps({"法人主体": {"深圳标记": "深圳市"}}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(br, "RULES_PATH", p)
    assert br.sz_marker() == "深圳市"
    assert br.is_sz_legal("中认车联网技术服务（深圳市）有限公司")
    assert not br.is_sz_legal("中认车联网技术服务（深圳）有限公司")


def test_gd_self_scan_rules():
    """广东自有归入：状态文件 / 最短名长 / 黑名单 / 列名候选 / 内部交易标记值"""
    assert br.gd_state_path().name == "已自动归入.json"
    assert br.gd_state_path().is_absolute()
    assert br.gd_min_name_len() >= 5
    blk = br.gd_blacklist()
    assert "广东公司" in blk and "合计" in blk
    assert br.legal_gd() in blk and br.legal_sg() in blk      # 自身法人名自动进黑名单
    assert br.gd_customer_cols() == ["客户", "客户名称"]
    assert "核算单位" in br.gd_legal_cols()
    assert "√" in br.gd_internal_values()
    assert len(br.gd_internal_cols()) >= 4


def test_gd_self_scan_rules_override(tmp_path, monkeypatch):
    p = tmp_path / "业务规则.json"
    p.write_text(json.dumps({"广东自有归入": {
        "状态文件": "data/mappings/自定义/状态.json",
        "最短客户名长度": 3,
        "黑名单": "占位/合计",
        "内部交易标记值": ["是", "Y"],
    }}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(br, "RULES_PATH", p)
    assert br.gd_state_path() == br._BASE_DIR / "data" / "mappings" / "自定义" / "状态.json"
    assert br.gd_min_name_len() == 3
    assert {"占位", "合计"} <= br.gd_blacklist()
    assert br.gd_internal_values() == {"是", "Y"}


def test_exclude_marker_defaults():
    vals = br.exclude_marker_defaults()
    assert "√" in vals and "是" in vals and len(vals) >= 5


def test_entry_rules_documented():
    """特殊归入规则写进配置（文档性）：韶关/广东自有/零部件/比亚迪/科技公司/白名单"""
    docs = br.entry_rules()
    for key in ("南方韶关", "广东自有", "零部件", "比亚迪", "科技公司", "白名单"):
        assert key in docs and docs[key], f"归入规则缺少 {key}"

    data = json.loads(br.RULES_PATH.read_text(encoding="utf-8"))
    assert "归入规则" in data
    assert "内部交易排除" in data and "名单字段" in data["内部交易排除"]
