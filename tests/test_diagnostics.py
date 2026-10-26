# Author: naohua168 <bai_bai168@qq.com>
"""数据质量诊断测试（2026-09-29 新增）

覆盖：问题记录/级别统计、白名单丢弃行落盘、摘要文案、步骤间 JSON 合并、目录解析。
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from engine.core import diagnostics as dg


def test_note_and_counts():
    d = dg.Diagnostics()
    d.note("WARN", "广东收入", "空表")
    d.note("ERROR", "南方韶关收入", "读取失败: xx")
    d.note("ERROR", "南方韶关回款", "读取失败: xx")
    assert d.counts()["WARN"] == 1 and d.counts()["ERROR"] == 2
    assert d.has_error() is True


def test_reject_summary_and_totals():
    d = dg.Diagnostics()
    d.note_rejects("财务端收入", [
        {"客户名": "甲客户", "金额": 100.0, "日期": "2026-08-01"},
        {"客户名": "乙客户", "金额": 50.5, "日期": ""},
    ])
    d.note_rejects("财务端回款", [{"客户名": "丙客户", "金额": 1.0}])
    n, amt = d.reject_totals()
    assert (n, round(amt, 2)) == (3, 151.5)
    summary = {r["来源"]: r["行数"] for r in d.reject_summary()}
    assert summary == {"财务端收入": 2, "财务端回款": 1}


def test_summary_lines_flags_errors_and_rejects():
    d = dg.Diagnostics()
    d.note("ERROR", "财务端收入", "读取失败")
    d.note_rejects("财务端收入", [{"客户名": "甲", "金额": 10000.0}])
    lines = "\n".join(d.summary_lines())
    assert "白名单未匹配丢弃: 1 行 / 1.0 万元" in lines
    assert "❌ ERROR 1 条" in lines
    assert "E1 / W0" in lines


def test_summary_lines_clean_run():
    assert "✅ 未发现数据质量问题" in "\n".join(dg.Diagnostics().summary_lines())


def test_single_step_run_writes_exactly_one_file(tmp_path, monkeypatch):
    """单独跑某一步（无运行号）：诊断目录只出现 1 个文件，4 个 sheet 齐全"""
    monkeypatch.delenv(dg.RUN_ID_ENV, raising=False)
    d = dg.Diagnostics()
    d.note("WARN", "广东收入", "空表")
    d.note_rejects("财务端收入", [{"客户名": "未匹配客户", "金额": 12345.0, "日期": "2026-08-02"}])
    written = d.write_reports(tmp_path, step="清洗", stamp="20260929_120000")

    assert [p.name for p in written] == ["数据质量摘要_20260929_120000.xlsx"]
    assert [p.name for p in tmp_path.iterdir()] == ["数据质量摘要_20260929_120000.xlsx"], "目录里只能有一个文件"

    xls = written[0]
    sheets = pd.read_excel(xls, sheet_name=None)
    assert list(sheets) == ["概览", "问题清单", "丢弃汇总", "未匹配明细"]
    assert sheets["未匹配明细"]["客户名"].iloc[0] == "未匹配客户"
    assert float(sheets["未匹配明细"]["金额"].iloc[0]) == 12345.0
    assert sheets["问题清单"]["说明"].iloc[0] == "空表"
    assert sheets["丢弃汇总"]["行数"].iloc[0] == 1
    assert sheets["概览"]["步骤"].tolist() == ["清洗", "合计"]
    assert sheets["概览"]["WARN"].iloc[0] == 1


def test_batch_run_defers_then_finalize_writes_one_file(tmp_path, monkeypatch):
    """批处理（bin/main.py 设 VD_RUN_ID）：各步骤只写中间件 → 收尾合并成唯一报告并删中间件"""
    rid = datetime.now().strftime("%Y%m%d_%H%M%S")   # 用当天时间：否则会被 prune_old_reports 当过期清理
    monkeypatch.setenv(dg.RUN_ID_ENV, rid)

    a = dg.Diagnostics()
    a.note("WARN", "广东收入", "空表")
    a.note_rejects("财务端收入", [{"客户名": "甲", "金额": 100.0}])
    assert [p.name for p in a.write_reports(tmp_path, step="清洗")] == [f"数据质量摘要_清洗_{rid}.json"]

    b = dg.Diagnostics()
    b.note("ERROR", "南方韶关回款", "读取失败")
    b.write_reports(tmp_path, step="销售拆分")
    assert len(list(tmp_path.glob("*.json"))) == 2 and not list(tmp_path.glob("*.xlsx"))

    merged, report = dg.finalize(tmp_path)
    assert report is not None and report.name == f"数据质量摘要_{rid}.xlsx"
    assert merged.counts()["WARN"] == 1 and merged.counts()["ERROR"] == 1
    assert merged.reject_totals()[0] == 1
    assert [p.name for p in tmp_path.iterdir()] == [report.name], "收尾后目录里只剩那一个报告"
    assert pd.read_excel(report, sheet_name="概览")["步骤"].tolist() == ["清洗", "销售拆分", "合计"]


def test_finalize_without_pending_reports_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv(dg.RUN_ID_ENV, raising=False)
    merged, report = dg.finalize(tmp_path, rid="20260929_000000")
    assert report is None and list(tmp_path.iterdir()) == []
    assert merged.counts()["ERROR"] == 0


def test_merge_and_collect_step_reports(tmp_path, monkeypatch):
    """只读合并（collect_step_reports）：按日期前缀取中间件，不写文件、不删除"""
    rid = datetime.now().strftime("%Y%m%d_%H%M%S")
    monkeypatch.setenv(dg.RUN_ID_ENV, rid)   # 批处理 → 只留中间件
    a, b = dg.Diagnostics(), dg.Diagnostics()
    a.note("WARN", "A", "空表")
    b.note("ERROR", "B", "读取失败")
    b.note_rejects("B", [{"客户名": "x", "金额": 1.0}])
    a.write_reports(tmp_path, step="清洗")
    b.write_reports(tmp_path, step="销售拆分")

    today = rid.split("_")[0]
    merged = dg.collect_step_reports(tmp_path, date_prefix=today)
    assert merged.counts()["WARN"] == 1 and merged.counts()["ERROR"] == 1
    assert merged.reject_totals()[0] == 1
    # 换一天 → 不应合并到旧文件
    other = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    assert dg.collect_step_reports(tmp_path, date_prefix=other).counts()["ERROR"] == 0
    # 只读：中间件仍在
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_output_dir_reads_config_with_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv(dg.DIAG_DIR_ENV, raising=False)
    assert dg.output_dir({"输出": {"数据校验": "output/校验/"}}, tmp_path) == tmp_path / "output" / "校验"
    assert dg.output_dir({}, tmp_path) == tmp_path / "output" / "数据校验"


def test_output_dir_env_redirect_wins(tmp_path, monkeypatch):
    """VD_DIAG_DIR 优先于配置（测试/临时重定向）；相对路径按项目根解析

    用途：测试跑真实流水线时把报告写到临时目录，正式 output/数据校验/ 保持干净。
    """
    monkeypatch.setenv(dg.DIAG_DIR_ENV, str(tmp_path / "diag"))
    assert dg.output_dir({"输出": {"数据校验": "output/数据校验"}}, tmp_path) == tmp_path / "diag"

    monkeypatch.setenv(dg.DIAG_DIR_ENV, "logs/tmp_diag")
    assert dg.output_dir({}, tmp_path) == tmp_path / "logs" / "tmp_diag"


def test_conftest_redirects_diagnostics_out_of_repo():
    """pytest 会话已把诊断目录重定向到临时目录（防测试污染正式目录）"""
    assert dg.current_run_id() or True  # 运行号可选；关键是下面这条
    repo_root = Path(__file__).resolve().parent.parent   # 仓库根（tests/ 的上一级）
    redirected = dg.output_dir({}, repo_root.parent)     # 故意传「仓库外」的基准目录
    assert "vd_diag_pytest" in str(redirected), f"测试未重定向诊断目录: {redirected}"


def test_module_level_helpers_share_singleton(tmp_path):
    dg.reset()
    dg.note_issue("WARN", "X", "空表")
    dg.note_rejects("X", [{"客户名": "甲", "金额": 2.0}])
    files = dg.write_reports(tmp_path, step="清洗", stamp="T")
    assert all(p.exists() for p in files)
    assert "1 行" in "\n".join(dg.summary_lines())
    dg.reset()  # 不污染其它测试
    assert dg.DIAG.counts()["WARN"] == 0


def test_report_paths_are_under_output_dir():
    """默认落盘目录 = output/数据校验（用户要求）"""
    assert dg.DEFAULT_OUT_REL == "output/数据校验"
    assert Path(dg.DEFAULT_OUT_REL).parts[0] == "output"


def test_old_reports_are_pruned(tmp_path):
    """超期诊断文件自动清理；人工放的文件不动（文件名无时间戳）"""
    old = tmp_path / "白名单未匹配行_20200101_000000.xlsx"
    recent = tmp_path / "白名单未匹配行_20990101_000000.xlsx"
    manual = tmp_path / "我手动放的说明.txt"
    for p in (old, recent, manual):
        p.write_text("x", encoding="utf-8")

    dg.Diagnostics().write_reports(tmp_path, step="清洗", stamp="20260929_235959")

    assert not old.exists()
    assert recent.exists() and manual.exists()
