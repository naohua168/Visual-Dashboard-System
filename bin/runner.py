# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""Python 原生流程编排（GUI / CLI 共用）

与 `bin/main.py` 的 8 个步骤一一对应，但**在同一进程内直接调用各阶段的 Python 接口**
（不 subprocess、不经 .bat / PowerShell），因此图形入口可以实时拿到进度与日志。

    from bin.runner import STEPS, run_all
    rc = run_all(log=print)                         # 全流程
    rc = run_all(log=print, keys=["clean"])         # 只跑清洗

诊断语义与 main.py 一致：设置 `VD_RUN_ID` → 各步骤写中间件 → 收尾 finalize 合并成
`output/数据校验/` 里唯一一份报告。
"""
from __future__ import annotations

import datetime
import os
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # 项目根（本文件在 bin/ 下）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

RUN_ID_ENV = "VD_RUN_ID"


@dataclass(frozen=True)
class Step:
    key: str
    name: str
    desc: str
    optional: bool = False


STEPS: tuple[Step, ...] = (
    Step("scan", "配置预扫描", "广东自有客户自动归入", optional=True),
    Step("config", "配置同步", "配置编辑器.xlsx → JSON"),
    Step("yearly", "Phase 0 年基线", "往年收入/回款清洗", optional=True),
    Step("clean", "Phase 1+2 清洗", "收入/回款三路输出"),
    Step("split", "Phase 3 销售拆分", "按销售归属比例拆分"),
    Step("render", "Phase 4 渲染看板", "6 页 HTML + 数据总表"),
    Step("report", "Phase 5 完成度表", "销售完成度汇总"),
    Step("verify", "Phase 6 交付物校验", "看板 / 总表 / 完成度表"),
)
STEPS_BY_KEY = {s.key: s for s in STEPS}


@dataclass
class StepResult:
    key: str
    name: str
    ok: bool
    exit_code: int
    seconds: float


# ──────────────────────────────────────────────────────────────
# 各步骤实现（直接调用 Python 接口）
# ──────────────────────────────────────────────────────────────
def _step_scan(log) -> int:
    from scripts.scan_gd_owned import main as scan_main
    return int(scan_main(["--write"]) or 0)


def _step_config(log) -> int:
    """配置编辑器.xlsx → JSON（cli.main 读 sys.argv，这里临时置空）"""
    from scripts.editor import cli

    old = sys.argv[:]
    sys.argv = ["config_excel_to_json.py"]
    try:
        return int(cli.main() or 0)
    finally:
        sys.argv = old


def _step_yearly(log) -> int:
    from engine.yearly_baseline.run import main as yearly_main

    old = sys.argv[:]
    sys.argv = ["engine.yearly_baseline.run"]
    try:
        return int(yearly_main() or 0)
    finally:
        sys.argv = old


def _step_clean(log) -> int:
    from engine.core.config import load_config
    from engine.core.diagnostics import output_dir, write_reports
    from engine.income_payment.run import run_clean

    cfg = load_config()
    for ft in ("收入", "回款"):
        run_clean(ft, cfg)
    for p in write_reports(output_dir(cfg), step="清洗"):
        log(f"  📄 已写入: {p}")
    return 0


def _step_split(log) -> int:
    from engine.core.config import load_config
    from engine.core.diagnostics import output_dir, write_reports
    from engine.sales.run import run_split

    cfg = load_config()
    for ft in ("收入", "回款"):
        run_split(ft, cfg)
    for p in write_reports(output_dir(cfg), step="销售拆分"):
        log(f"  📄 已写入: {p}")
    return 0


def _step_render(log) -> int:
    from engine.core.config import load_config
    from engine.core.diagnostics import output_dir, write_reports
    from processors.run import run_render

    out = run_render()
    log(f"  ✅ 看板: {out}")
    cfg = load_config()
    for p in write_reports(output_dir(cfg), step="渲染"):
        log(f"  📄 已写入: {p}")
    return 0


def _step_report(log) -> int:
    from scripts.sales_summary_report import main as report_main
    return int(report_main([]) or 0)


def _step_verify(log) -> int:
    from scripts.verify_dashboard import main as verify_main
    return int(verify_main([]) or 0)


IMPLEMENTATIONS = {
    "scan": _step_scan,
    "config": _step_config,
    "yearly": _step_yearly,
    "clean": _step_clean,
    "split": _step_split,
    "render": _step_render,
    "report": _step_report,
    "verify": _step_verify,
}


# ──────────────────────────────────────────────────────────────
# 编排
# ──────────────────────────────────────────────────────────────
def run_all(log=print,
            keys: list[str] | None = None,
            on_step_start=None,
            on_step_done=None,
            stop_event=None) -> int:
    """按顺序执行步骤，返回整次运行的退出码（0=全部成功）

    Args:
        log: 日志回调（GUI 传队列写入器；CLI 传 print）
        keys: 只跑这些步骤（None=全部 8 步）
        on_step_start: (Step, index) → None
        on_step_done: (StepResult) → None
        stop_event: threading.Event；在步骤之间检查，置位则不再继续
    """
    from engine.core.config import load_config
    from engine.core.diagnostics import finalize, output_dir, reset, write_reports

    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.environ[RUN_ID_ENV] = run_id

    todo = [s for s in STEPS if (keys is None or s.key in keys)]
    results: list[StepResult] = []
    failed: StepResult | None = None

    log(f"\n▶ 开始运行（{run_id}）：{' → '.join(s.key for s in todo)}\n")

    for index, step in enumerate(todo):
        if stop_event is not None and stop_event.is_set():
            log("⏹ 已被用户停止")
            break

        if on_step_start is not None:
            on_step_start(step, index)
        log(f"\n═══ {step.name} · {step.desc} ═══")

        reset()          # 每步独立诊断（等价于 main.py 的独立子进程）
        t0 = time.time()
        rc = 0
        try:
            rc = int(IMPLEMENTATIONS[step.key](log) or 0)
        except SystemExit as e:                     # 引擎内部 sys.exit(...)
            rc = int(e.code or 0)
        except Exception as e:                      # 单步异常不炸掉整个界面
            rc = 1
            log(f"❌ {step.name} 异常: {e}")
            log(traceback.format_exc())

        # 落盘本步诊断（中间件；收尾统一合并）
        try:
            cfg = load_config()
            for p in write_reports(output_dir(cfg), step=step.name):
                log(f"  📄 诊断: {p}")
        except Exception as e:
            log(f"⚠️ 诊断落盘失败: {e}")

        res = StepResult(step.key, step.name, rc == 0, rc, time.time() - t0)
        results.append(res)
        if on_step_done is not None:
            on_step_done(res)

        if rc != 0:
            if step.optional:
                log(f"⚠️ {step.name} 失败（可选步骤，继续）：退出码 {rc}")
            else:
                log(f"❌ {step.name} 失败（退出码 {rc}），后续步骤已中止")
                failed = res
                break

    # ── 收尾：合并诊断 → 唯一报告 ──
    try:
        cfg = load_config()
        merged, report = finalize(output_dir(cfg), run_id)
        if report is not None:
            log(f"\n📋 数据校验报告: {report}")
        for line in merged.summary_lines():
            log("  " + line)
        has_error = merged.has_error()
    except Exception as e:
        log(f"⚠️ 数据质量汇总失败: {e}")
        has_error = False

    ok_n = sum(1 for r in results if r.ok)
    log(f"\n{'✅' if failed is None else '❌'} 运行结束：{ok_n}/{len(todo)} 步成功"
        f"，耗时 {sum(r.seconds for r in results):.1f}s")

    if failed is not None:
        return failed.exit_code or 1
    return 4 if has_error else 0
