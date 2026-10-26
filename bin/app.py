# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""Visual Dashboard System — Python 原生入口

    python bin/app.py                    图形控制台（tkinter，默认）
    python bin/app.py gui                同上（显式）
    python bin/app.py run                命令行全流程（同进程 Python 编排）
    python bin/app.py run --step=clean   只跑某一步（scan/config/yearly/clean/split/render/report/verify）
    python bin/app.py run --from=split   从某一步跑到最后
    python bin/app.py run --to=render    从第一步跑到某一步
    python bin/app.py list               列出 8 个步骤
    python bin/app.py board              打开最新看板 HTML
    python bin/app.py --help

与旧入口的区别：
  · 界面是 Python（tkinter）原生实现，不再启动 PowerShell / WPF
  · 流程在同一进程内直接调用各阶段 Python 接口（`bin/runner.py`），不转发 .bat
  · 仍保留 `bin/main.py`（子进程隔离的 CLI 调度器），供 run_all.bat / 排障使用
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

BASE_DIR = Path(__file__).resolve().parent.parent   # 项目根（本文件在 bin/ 下）
if str(BASE_DIR) not in sys.path:  # 允许从任意工作目录调用本文件
    sys.path.insert(0, str(BASE_DIR))

USAGE = """Visual Dashboard System — Python 入口

用法:
  python bin/app.py                      图形控制台（默认，tkinter）
  python bin/app.py gui                  同上（显式）
  python bin/app.py run                  命令行全流程（同进程 Python 编排）
  python bin/app.py run --step=clean     只跑某一步
  python bin/app.py run --from=split     从某一步跑到最后
  python bin/app.py run --to=render      从第一步跑到某一步
  python bin/app.py list                 列出 8 个步骤
  python bin/app.py board                打开最新看板 HTML
  python bin/app.py --help               显示本帮助

说明:
  · 图形入口需要系统带 Tk（标准库自带；内置 runtime 已包含）
  · 完整参数（--type / --dry-run / --no-config / --ignore-data-issues）请用：
        python bin/main.py --help
  · 双击入口「启动系统.bat」会调用本文件的图形界面
"""


def _rel(p: Path) -> str:
    try:
        return str(Path(p).relative_to(BASE_DIR))
    except (ValueError, TypeError):
        return str(p)


def _fallback_ps_gui() -> int:
    """tkinter 不可用时回退到传统 PowerShell 控制台

    嵌入式运行时（runtime/python，交付包自带）**不含 tkinter**，所以回退是必需的：
    本机 Conda / 完整 Python 用 tkinter 界面；交付包自动回到 WPF 控制台。
    """
    ps1 = BASE_DIR / "scripts" / "dashboard_launcher.ps1"
    if os.name != "nt" or not ps1.exists():
        return 2
    cmd = ["powershell.exe", "-NoProfile", "-STA",
           "-ExecutionPolicy", "RemoteSigned", "-File", str(ps1)]
    try:
        subprocess.Popen(cmd, cwd=str(BASE_DIR), creationflags=0x08000000)
    except OSError as e:
        print(f"回退传统控制台失败: {e}")
        return 3
    print("已回退到传统 PowerShell 控制台（当前 Python 无 tkinter）。")
    return 0


def cmd_gui() -> int:
    """启动 Python 图形控制台（tkinter）；不可用时自动回退传统控制台"""
    try:
        from bin.gui import main as gui_main
    except Exception as e:  # 无 tkinter（如嵌入式运行时）
        print(f"图形界面不可用（{e}），尝试回退传统控制台…")
        return _fallback_ps_gui()
    try:
        return gui_main()
    except Exception as e:  # 无显示环境 / 界面构建异常
        print(f"图形界面启动失败（{e}），尝试回退传统控制台…")
        return _fallback_ps_gui()


def _parse_keys(argv: list[str]) -> list[str] | None | Literal[False]:
    """解析 --step / --from / --to → 步骤 key 列表

    Returns:
        list[str] | None（全流程）| False（参数错误）
    """
    from bin.runner import STEPS

    order = [s.key for s in STEPS]
    keys: list[str] | None = None
    start = end = None

    for arg in argv:
        if arg.startswith("--step="):
            key = arg.split("=", 1)[1].strip()
            if key not in order:
                print(f"未知步骤: {key}；可选: {', '.join(order)}")
                return False
            keys = [key]
        elif arg.startswith("--from="):
            k = arg.split("=", 1)[1].strip()
            if k not in order:
                print(f"未知步骤: {k}；可选: {', '.join(order)}")
                return False
            start = order.index(k)
        elif arg.startswith("--to="):
            k = arg.split("=", 1)[1].strip()
            if k not in order:
                print(f"未知步骤: {k}；可选: {', '.join(order)}")
                return False
            end = order.index(k)
        else:
            print(f"未知参数: {arg}")
            print("完整参数请用: python bin/main.py --help")
            return False

    if start is not None or end is not None:
        if start is not None and end is not None and start > end:
            print("--from 不能排在 --to 之后")
            return False
        keys = order[(start or 0):(end + 1 if end is not None else len(order))]
    return keys


def cmd_run(argv: list[str]) -> int:
    """命令行全流程（同进程编排）"""
    from bin.runner import run_all

    keys = _parse_keys(argv)
    if keys is False:
        return 2
    return run_all(log=print, keys=keys)


def cmd_list() -> int:
    """列出 8 个步骤"""
    from bin.runner import STEPS

    print("\n" + "-" * 24 + "可用步骤" + "-" * 24)
    for i, s in enumerate(STEPS, 1):
        flag = "（可选）" if s.optional else ""
        print(f"  {i}. {s.key:<8} {s.name}{flag}")
        print(f"     {s.desc}")
    print(f"\n共 {len(STEPS)} 个步骤")
    return 0


def cmd_board() -> int:
    """用系统默认程序打开最新一份看板 HTML"""
    board_dir = BASE_DIR / "output" / "看板"
    files = sorted(
        (f for f in board_dir.glob("看板_*.html") if not f.name.startswith("~$")),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not files:
        print(f"未找到看板文件: {_rel(board_dir)}（先运行 python bin/app.py run）")
        return 2

    target = files[0]
    print(f"打开最新看板: {_rel(target)}")
    try:
        if os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError as e:
        print(f"打开失败: {e}")
        return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    """入口分发；返回进程退出码"""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return cmd_gui()

    cmd, rest = argv[0], argv[1:]
    if cmd in ("gui", "console", "界面"):
        return cmd_gui()
    if cmd in ("run", "all", "全流程"):
        return cmd_run(rest)
    if cmd in ("list", "steps", "步骤"):
        return cmd_list()
    if cmd in ("board", "看板"):
        return cmd_board()
    if cmd in ("-h", "--help", "help", "-?", "/?"):
        print(USAGE)
        return 0

    print(f"未知命令: {cmd}\n")
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
