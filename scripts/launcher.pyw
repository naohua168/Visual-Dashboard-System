# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""图形化控制台启动器（用 pythonw.exe 运行 → 无控制台窗口）

替代旧方案 `_launch_hidden.vbs`：
  · 旧方案用「VBS 隐藏窗口 + powershell -WindowStyle Hidden -ExecutionPolicy Bypass」，
    这一组合是恶意脚本的典型特征，极易被 360 / 火绒 / Defender 云查杀误判为木马；
  · 本启动器改用 subprocess + CREATE_NO_WINDOW 隐藏 PowerShell 窗口，界面仍是 WPF 控制台，
    命令行不含 Bypass / -WindowStyle Hidden 等高风险参数（执行策略用 RemoteSigned）。

用法：
    启动系统.bat → pythonw.exe scripts\\launcher.pyw
调试：
    python scripts/launcher.pyw --dry-run     # 只打印将要执行的命令，不启动界面
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PS1 = BASE_DIR / "scripts" / "dashboard_launcher.ps1"
CREATE_NO_WINDOW = 0x08000000  # Windows: 不创建控制台窗口


def build_command() -> list[str]:
    """构建 PowerShell 启动命令（RemoteSigned，避免 Bypass 触发杀软启发式）"""
    return [
        "powershell.exe",
        "-NoProfile",
        "-STA",
        "-ExecutionPolicy", "RemoteSigned",
        "-File", str(PS1),
    ]


def _alert(msg: str) -> None:
    """无控制台时用系统弹窗提示（pythonw 下 print 不可见）"""
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, "Visual Dashboard System", 0x10)
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = build_command()

    if "--dry-run" in argv:
        print("将执行:", " ".join(cmd))
        return 0

    if not PS1.exists():
        _alert(f"未找到图形控制台脚本：\n{PS1}\n\n可直接双击 run_all.bat 运行命令行全流程。")
        return 2

    flags = CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        subprocess.Popen(cmd, cwd=str(BASE_DIR), creationflags=flags, close_fds=True)
    except OSError as e:
        _alert(f"启动图形控制台失败：{e}\n\n可直接双击 run_all.bat 运行命令行全流程。")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
