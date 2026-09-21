"""
Visual Dashboard System — 顶层调度器

用法:
    python main.py                          # 全流程：清洗 + 拆分
    python main.py --type=收入              # 只处理收入链路
    python main.py --step=clean             # 只执行清洗（Phase 1+2）
    python main.py --step=split             # 只执行销售拆分（Phase 3）
    python main.py --dry-run                # 预检模式（不写文件，仅检查依赖与配置）
    python main.py --list                   # 列出所有可用步骤
    python main.py --from=clean --to=split  # 区间执行

特性:
    - argparse 标准参数解析
    - subprocess 独立进程执行每一步（崩溃不影响其他步骤）
    - 退出码：0=成功，非 0=失败
    - 运行日志写入 logs/run_YYYYMMDD_HHMMSS.log
    - 失败时打印清晰错误信息与下一步建议
"""
from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
from pathlib import Path

# 项目根目录（main.py 所在目录）
BASE_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "logs"


# ──────────────────────────────────────────────────────────────
# 步骤定义
# ──────────────────────────────────────────────────────────────
# 每个步骤对应一个 subprocess 命令（python -m engine.xxx.run [--type=...] 或 python scripts/xxx.py）
CONFIG_EXCEL = "config/配置编辑器.xlsx"

STEPS = [
    {
        "key": "scan",
        "name": "配置预扫描: 广东自有客户自动归入",
        "script": "scripts/scan_gd_owned.py",
        "script_args": ["--write"],
        "optional": True,
        "description": "扫描 运营端/广东公司 中 法人=广东汽车检测中心 且无任何销售归属的客户 → 追加到 配置编辑器.xlsx"
                       "「销售归属」（广东自有客户 / 黎国键）。必须排在配置同步之前，才能被 Excel→JSON 带进去",
    },
    {
        "key": "config",
        "name": "配置同步: 配置编辑器.xlsx → JSON",
        "script": "scripts/config_excel_to_json.py",
        "requires_excel": True,
        "description": "把 config/配置编辑器.xlsx（时间配置/结算模式/展示规则/KPI/销售归属/字段映射）写回 JSON；"
                       "Excel 是唯一编辑入口、JSON 是生成物 —— 必须先同步，再清洗",
    },
    {
        "key": "yearly",
        "name": "Phase 0: 年基线清洗",
        "module": "engine.yearly_baseline.run",
        "optional": True,
        "description": "读取往年收入数据/往年回款数据，清洗为往年收入/往年回款标准表（失败仅影响年度同比）",
    },
    {
        "key": "clean",
        "name": "Phase 1+2: 收入/回款清洗",
        "module": "engine.income_payment.run",
        "description": "读取 7 个原始 Excel，清洗合并为收入/回款标准表（6 列）",
    },
    {
        "key": "split",
        "name": "Phase 3: 销售拆分",
        "module": "engine.sales.run",
        "description": "按 4 层规则拆分销售收入/销售回款（7 列，含销售列）",
    },
    {
        "key": "render",
        "name": "Phase 4: 渲染 HTML 看板",
        "module": "processors.run",
        "description": "加载已清洗数据，生成 6 页面 HTML 可视化看板到 output/",
    },
]

STEP_KEYS = [s["key"] for s in STEPS]
STEPS_BY_KEY = {s["key"]: s for s in STEPS}


# ──────────────────────────────────────────────────────────────
# 日志
# ──────────────────────────────────────────────────────────────
class Logger:
    """同时输出到 stdout 和日志文件"""

    def __init__(self, log_path: Path):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._fp = open(log_path, "a", encoding="utf-8")
        self.log_path = log_path

    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {msg}"
        print(line)
        self._fp.write(line + "\n")
        self._fp.flush()

    def close(self):
        self._fp.close()


# ──────────────────────────────────────────────────────────────
# 预检
# ──────────────────────────────────────────────────────────────
def preflight_check() -> list[str]:
    """检查运行依赖的文件是否存在，返回问题列表（空=全部通过）"""
    issues = []

    config_path = BASE_DIR / "config" / "清洗配置" / "cleaning_config.json"
    if not config_path.exists():
        issues.append(f"缺失配置文件: {config_path.relative_to(BASE_DIR)}")

    mappings_dir = BASE_DIR / "data" / "mappings"
    expected = ["部门事业部映射", "客户名单"]
    if not mappings_dir.exists():
        issues.append(f"缺失目录: data/mappings/")
    else:
        for sub in expected:
            if not (mappings_dir / sub).exists():
                issues.append(f"缺失映射目录: data/mappings/{sub}/")

    raw_dir = BASE_DIR / "data" / "raw"
    if not raw_dir.exists():
        issues.append(f"缺失目录: data/raw/（请放入原始 Excel）")
    else:
        fin = raw_dir / "财务端数据"
        ops = raw_dir / "运营端数据"
        if not fin.exists():
            issues.append(f"缺失目录: data/raw/财务端数据/")
        if not ops.exists():
            issues.append(f"缺失目录: data/raw/运营端数据/")

    return issues


# ──────────────────────────────────────────────────────────────
# 步骤执行
# ──────────────────────────────────────────────────────────────
def build_command(step: dict, file_type: str | None) -> list[str]:
    """构造步骤命令：script 型（如配置同步）直接跑脚本，module 型跑 python -m"""
    if step.get("script"):
        return [sys.executable, step["script"], *step.get("script_args", [])]
    cmd = [sys.executable, "-m", step["module"]]
    if file_type:
        cmd.append(f"--type={file_type}")
    return cmd


def step_available(step: dict) -> tuple[bool, str]:
    """检查步骤前置条件；返回 (是否可执行, 不可执行原因)"""
    if step.get("script"):
        if not (BASE_DIR / step["script"]).exists():
            return False, f"脚本不存在: {step['script']}"
        if step.get("requires_excel") and not (BASE_DIR / CONFIG_EXCEL).exists():
            return False, f"配置编辑器不存在: {CONFIG_EXCEL}（跳过配置同步）"
    return True, ""


def run_step(step: dict, file_type: str | None, logger: Logger, dry_run: bool) -> bool:
    """用 subprocess 执行单个步骤，返回是否成功（前置条件不满足 → 跳过并视为通过）"""
    ok, reason = step_available(step)
    if not ok:
        logger.log(f"  [跳过] {step['name']} —— {reason}", "WARN")
        return True

    cmd = build_command(step, file_type)

    # 阶段横幅 —— 图形控制台 dashboard_launcher.ps1 依赖此行推进阶段进度，勿改格式
    print(f"\n═══ {step['name']} ═══", flush=True)

    logger.log(f"启动: {step['name']}")
    logger.log(f"  命令: {' '.join(cmd)}")
    logger.log(f"  说明: {step['description']}")

    if dry_run:
        logger.log("  [DRY-RUN] 跳过实际执行", "WARN")
        return True

    try:
        result = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        logger.log(f"  Python 解释器未找到: {sys.executable}", "ERROR")
        return False

    if result.returncode == 0:
        logger.log(f"  ✅ 完成: {step['name']}", "OK")
        return True
    if step.get("optional"):
        logger.log(
            f"  ⚠️ 失败（可选步骤，继续后续）: {step['name']} (退出码 {result.returncode})",
            "WARN",
        )
        return True
    else:
        logger.log(
            f"  ❌ 失败: {step['name']} (退出码 {result.returncode})",
            "ERROR",
        )
        return False


# ──────────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Visual Dashboard System 顶层调度器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
        "  python main.py                    # 全流程\n"
        "  python main.py --type=收入         # 只处理收入链路\n"
        "  python main.py --step=clean       # 只清洗\n"
        "  python main.py --from=clean --to=split\n"
        "  python main.py --dry-run          # 预检\n"
        "  python main.py --list             # 列出步骤",
    )
    p.add_argument("--type", choices=["收入", "回款"], help="只处理某一表类型")
    p.add_argument("--step", choices=STEP_KEYS, help="只执行单个步骤")
    p.add_argument("--from", dest="from_step", choices=STEP_KEYS, help="起始步骤（区间执行）")
    p.add_argument("--to", dest="to_step", choices=STEP_KEYS, help="结束步骤（区间执行）")
    p.add_argument("--dry-run", action="store_true", help="预检模式，不执行实际命令")
    p.add_argument("--no-config", dest="no_config", action="store_true",
                   help="跳过配置同步（Excel → JSON），用于直接改 JSON 的场景")
    p.add_argument("--list", dest="list_steps", action="store_true", help="列出所有可用步骤")
    return p


def resolve_steps(args) -> list[dict]:
    """根据参数解析要执行的步骤列表"""
    if args.list_steps:
        return []
    if args.step:
        return [STEPS_BY_KEY[args.step]]
    if args.from_step or args.to_step:
        start_idx = STEP_KEYS.index(args.from_step) if args.from_step else 0
        end_idx = STEP_KEYS.index(args.to_step) if args.to_step else len(STEP_KEYS) - 1
        if start_idx > end_idx:
            return []
        return STEPS[start_idx : end_idx + 1]
    return STEPS  # 默认全部


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --list
    if args.list_steps:
        print(f"\n{'可用步骤':-^50}")
        for i, s in enumerate(STEPS, 1):
            print(f"  {i}. {s['key']:<10} {s['name']}")
            print(f"     {s['description']}")
        print(f"\n共 {len(STEPS)} 个步骤")
        return 0

    steps_to_run = resolve_steps(args)
    if args.no_config:
        steps_to_run = [s for s in steps_to_run if s["key"] != "config"]
    if not steps_to_run:
        print("无步骤可执行（检查 --from/--to 顺序）")
        return 1

    # 预检
    issues = preflight_check()
    if issues:
        print("\n❌ 预检失败：")
        for i in issues:
            print(f"  - {i}")
        print("\n请先解决以上问题再运行。")
        return 2
    if args.dry_run:
        print("\n✅ 预检通过（dry-run 模式，不执行实际命令）")
        print("\n将执行以下步骤：")
        for s in steps_to_run:
            print(f"  - {' '.join(build_command(s, args.type))}")
        return 0

    # 启动日志
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"run_{ts}.log"
    logger = Logger(log_path)

    logger.log("#" * 60)
    logger.log("Visual Dashboard System — 启动")
    logger.log(f"  时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.log(f"  工作目录: {BASE_DIR}")
    logger.log(f"  日志文件: {log_path.relative_to(BASE_DIR)}")
    logger.log(f"  执行步骤: {[s['key'] for s in steps_to_run]}")
    if any(s["key"] == "config" for s in steps_to_run):
        logger.log("  提示: 配置请改 config/配置编辑器.xlsx（本流程第 1 步自动同步为 JSON）")
    if args.type:
        logger.log(f"  表类型: {args.type}")
    logger.log("#" * 60)

    # 依次执行
    success_count = 0
    failed_step = None
    for step in steps_to_run:
        ok = run_step(step, args.type, logger, args.dry_run)
        if ok:
            success_count += 1
        else:
            failed_step = step
            break  # 任一步骤失败则终止后续

    # 总结
    logger.log("#" * 60)
    if failed_step:
        logger.log(
            f"❌ 流程中断：{failed_step['key']} 失败，已执行 {success_count}/{len(steps_to_run)} 步",
            "ERROR",
        )
        logger.log(f"   查看日志: {log_path}")
        logger.log(f"   修复后可用 --from={failed_step['key']} 重试")
        logger.log("#" * 60)
        logger.close()
        return 3
    else:
        logger.log(
            f"✅ 全部完成：{success_count}/{len(steps_to_run)} 步成功",
            "OK",
        )
        logger.log("#" * 60)
        logger.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
