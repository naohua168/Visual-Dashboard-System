# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""生成「启动控制台」快捷方式（.lnk）—— 让非技术同事双击即用

仓库已无任何 `.bat` 启动器，交付后只能命令行运行。这个脚本生成一个 Windows
快捷方式，双击直接打开图形控制台（用 pythonw，不弹黑框）。

    python bin/make_shortcut.py                 # 在项目根生成「启动控制台.lnk」
    python bin/make_shortcut.py --desktop       # 生成到桌面
    python bin/make_shortcut.py --name 看板系统  # 自定义名字
    python bin/make_shortcut.py --dry-run       # 只打印将要创建的快捷方式

说明：
  · 目标优先用 `runtime\\python\\pythonw.exe`（交付包自带），没有则回退当前解释器旁边的 pythonw.exe；
  · 快捷方式存的是**绝对路径**，所以文件夹整体搬家后需要重新生成一次；
  · .lnk 的创建依赖 Windows COM（WScript.Shell），这是标准库做不到的，
    因此这里只在这一步调用一次 PowerShell（不是启动路径，不影响"零外部依赖"）。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # 项目根（本文件在 bin/ 下）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DEFAULT_NAME = "启动控制台"
TARGET_SCRIPT = "bin\\app.py"


@dataclass
class ShortcutPlan:
    lnk: Path
    target: Path
    arguments: str
    workdir: Path
    description: str


def resolve_pythonw() -> Path | None:
    """优先内置运行时（交付机唯一的解释器），其次当前解释器同目录的 pythonw.exe"""
    candidates = [
        BASE_DIR / "runtime" / "python" / "pythonw.exe",
        Path(sys.executable).with_name("pythonw.exe"),
        Path(sys.executable).with_name("python.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def shortcut_plan(name: str = DEFAULT_NAME, dest_dir: Path | None = None) -> ShortcutPlan:
    target = resolve_pythonw()
    if target is None:
        raise FileNotFoundError("找不到 pythonw.exe / python.exe（runtime/ 与当前解释器目录都没有）")
    dest = Path(dest_dir) if dest_dir else BASE_DIR
    return ShortcutPlan(
        lnk=dest / f"{name}.lnk",
        target=target,
        arguments=TARGET_SCRIPT,
        workdir=BASE_DIR,
        description="Visual Dashboard System — 图形控制台",
    )


def desktop_dir() -> Path:
    return Path(os.path.expanduser("~")) / "Desktop"


def create_lnk(plan: ShortcutPlan) -> None:
    """用 WScript.Shell 创建快捷方式（.lnk 二进制格式，标准库无法直接生成）"""
    for p in (str(plan.lnk), str(plan.target), str(plan.workdir)):
        if '"' in p:
            raise ValueError(f"路径里含双引号，无法写入快捷方式: {p}")
    ps = (
        "$W = New-Object -ComObject WScript.Shell; "
        f'$S = $W.CreateShortcut("{plan.lnk}"); '
        f'$S.TargetPath = "{plan.target}"; '
        f'$S.Arguments = "{plan.arguments}"; '
        f'$S.WorkingDirectory = "{plan.workdir}"; '
        f'$S.Description = "{plan.description}"; '
        f'$S.IconLocation = "{plan.target},0"; '
        "$S.Save()"
    )
    plan.lnk.parent.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
                        capture_output=True, text=True).returncode
    if rc != 0 or not plan.lnk.exists():
        raise OSError("创建快捷方式失败（可能被安全软件拦截）")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成「启动控制台」快捷方式")
    ap.add_argument("--name", default=DEFAULT_NAME, help=f"快捷方式名字（默认 {DEFAULT_NAME}）")
    ap.add_argument("--desktop", action="store_true", help="生成到桌面（默认项目根）")
    ap.add_argument("--dest", default=None, help="指定输出目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不创建")
    args = ap.parse_args(argv)

    if os.name != "nt":
        print("❌ 快捷方式（.lnk）是 Windows 专有格式，本脚本只支持 Windows。")
        return 2

    dest = Path(args.dest) if args.dest else (desktop_dir() if args.desktop else BASE_DIR)
    try:
        plan = shortcut_plan(args.name, dest)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 2

    print(f"目标: {plan.target}")
    print(f"参数: {plan.arguments}")
    print(f"起始位置: {plan.workdir}")
    print(f"快捷方式: {plan.lnk}")
    if args.dry_run:
        print("\n（--dry-run：未实际创建）")
        return 0

    try:
        create_lnk(plan)
    except (OSError, ValueError) as e:
        print(f"❌ {e}")
        return 3
    print(f"\n✅ 已生成快捷方式：{plan.lnk}\n   双击即可打开图形控制台（不弹控制台窗口）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
