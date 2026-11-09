# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""Visual Dashboard System — 启动引导（替代原 `启动系统.bat`）

它是 .bat 的纯 Python 等价物：**先自检环境，再交给 bin/app.py**。
原来的 .bat 干三件事（找解释器 / 查依赖 / 预检后启界面），
「找解释器」这一件在 Python 里不需要（已经在跑了），剩下两件收在这里。

    python bin/start.py              自检 → 启图形控制台（默认）
    python bin/start.py --check      只自检，不起界面（适合排障/交付验收）
    python bin/start.py --cli        自检 → 命令行全流程
    python bin/start.py --cli --step=render   参数原样透传给 bin/app.py run
    python bin/start.py report       其余子命令也支持（report / list / board / gui）
    python bin/start.py --quiet ...  不打印自检表，仅静默通过

自检项：Python 版本 / 依赖包 / tkinter / 配置文件 / 原始数据与映射 / 输出目录可写。
硬性失败（❌）退出码 2；⚠️ 只提示，不拦。
"""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # 项目根（本文件在 bin/ 下）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

MIN_PY = (3, 10)
REQUIRED_PKGS = ("pandas", "openpyxl", "xlrd")

USAGE = """Visual Dashboard System — 启动引导

用法:
  python bin/start.py                 自检 + 启动图形控制台（默认）
  python bin/start.py --check         只自检（不起界面）
  python bin/start.py --cli           自检 + 命令行全流程
  python bin/start.py --cli --step=render    透传给 bin/app.py run
  python bin/start.py report          按需生成销售完成度表（等价 bin/app.py report）
  python bin/start.py list            列出 7 个步骤
  python bin/start.py board           打开最新看板
  python bin/start.py --help          显示本帮助

说明:
  · 本文件只做「环境自检 + 转交」，流程编排仍在 bin/app.py / bin/runner.py
  · 想不弹黑框：pythonw bin/start.py
  · 交付包里的内置 runtime 不含 tkinter，会自动回退传统控制台（bin/app.py 负责）
"""

OK, WARN, FAIL = "ok", "warn", "fail"
ICON = {OK: "✅", WARN: "⚠️ ", FAIL: "❌"}


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    hint: str = ""


def check_python(minimum: tuple[int, int] = MIN_PY) -> Check:
    cur = sys.version_info
    text = f"{cur.major}.{cur.minor}.{cur.micro}"
    if (cur.major, cur.minor) >= minimum:
        return Check("Python 版本", OK, text)
    return Check("Python 版本", FAIL, text,
                 f"需要 {minimum[0]}.{minimum[1]}+；请换用更高版本或交付包内置 runtime")


def check_packages() -> Check:
    missing = [p for p in REQUIRED_PKGS if importlib.util.find_spec(p) is None]
    if not missing:
        return Check("依赖包", OK, " / ".join(REQUIRED_PKGS))
    return Check("依赖包", FAIL, f"缺少 {', '.join(missing)}",
                 f"安装：{Path(sys.executable).name} -m pip install -r requirements.txt")


def check_tkinter() -> Check:
    try:
        import tkinter  # noqa: F401
    except Exception as e:  # 嵌入式运行时没有 tkinter
        return Check("图形界面 (tkinter)", WARN, f"不可用（{type(e).__name__}）",
                     "将回退传统 WPF 控制台（scripts/dashboard_launcher.ps1），功能不受影响")
    return Check("图形界面 (tkinter)", OK, "可用")


def check_project_files() -> list[Check]:
    """复用 bin/main.py 的预检规则（数据源 / 配置 / 映射 / 指标表），避免两套口径"""
    try:
        from bin.main import preflight_check

        issues = preflight_check()
    except Exception as e:  # 预检本身异常不该阻断启动
        return [Check("项目文件", WARN, f"预检失败（{type(e).__name__}: {e}）")]
    if not issues:
        return [Check("项目文件", OK, "配置 / 原始数据 / 映射 / 指标表齐全")]
    checks = [Check("项目文件", FAIL, issues[0])]
    checks += [Check("", FAIL, msg) for msg in issues[1:]]
    checks[-1].hint = "缺什么补什么；纯看已有产物可先不管，跑流程时必须补齐"
    return checks


def check_output_writable() -> Check:
    out = BASE_DIR / "output"
    probe = out / ".write_test"
    try:
        out.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as e:
        return Check("输出目录", FAIL, f"{out} 不可写（{e}）",
                     "检查目录是否只读 / 被占满 / 被安全软件锁定")
    return Check("输出目录", OK, str(out.relative_to(BASE_DIR)))


def collect_checks() -> list[Check]:
    return [
        check_python(),
        check_packages(),
        check_tkinter(),
        *check_project_files(),
        check_output_writable(),
    ]


def format_checks(checks: list[Check]) -> str:
    """渲染成对齐的状态表（中文按 2 列宽处理）"""
    def width(text: str) -> int:
        return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)

    name_w = max((width(c.name) for c in checks), default=0)
    lines = ["", "环境自检"]
    for c in checks:
        pad = " " * (name_w - width(c.name))
        head = f"  {ICON[c.status]} {c.name}{pad}"
        line = f"{head}  {c.detail}" if c.detail else head
        lines.append(line)
        if c.hint and c.status != OK:
            lines.append(f"     ↳ {c.hint}")
    return "\n".join(lines)


def has_blocking(checks: list[Check]) -> bool:
    return any(c.status == FAIL for c in checks)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help", "help", "-?", "/?"):
        print(USAGE)
        return 0

    quiet = "--quiet" in argv
    argv = [a for a in argv if a != "--quiet"]
    check_only = "--check" in argv
    argv = [a for a in argv if a != "--check"]

    checks = collect_checks()
    if not quiet:
        print(format_checks(checks))
    if has_blocking(checks):
        print("\n❌ 自检未通过，已停止启动。修好标 ❌ 的项后重试（或按提示安装依赖）。")
        return 2
    if check_only:
        print("\n✅ 自检通过。")
        return 0

    from bin.app import main as app_main

    if "--cli" in argv:
        argv = [a for a in argv if a != "--cli"]
        print("\n启动命令行全流程…\n")
        return app_main(["run", *argv])

    if not argv:
        print("\n启动图形控制台…\n")
        return app_main([])
    return app_main(argv)


if __name__ == "__main__":
    sys.exit(main())
