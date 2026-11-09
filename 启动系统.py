# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""Visual Dashboard System — 项目根目录启动程序

双击，或在任何目录下命令行运行：

    python 启动系统.py               环境自检 → 打开图形控制台（默认）
    python 启动系统.py --check       只体检（不起界面，适合交付验收/排障）
    python 启动系统.py --cli         命令行全流程
    python 启动系统.py --cli --step=render     参数原样透传给 bin/start.py
    python 启动系统.py report        按需产物（销售完成度表）
    python 启动系统.py --help        显示帮助
    pythonw 启动系统.py              无控制台窗口启动

它只做两件事，其余全部交给 bin/start.py：

  1. **挑一个能干活儿的 Python**：当前解释器满足「3.10+ 且装有 pandas / openpyxl / xlrd」
     就直接用；否则按 config/python_path.txt 的既定口径依次尝试
     `python_path.txt 指定目录 → runtime\\python（交付包内置）→ Conda 环境 → PATH`，
     找到合适的就带着原参数重启自己；
  2. **转交** bin/start.py（自检 → bin/app.py 图形控制台 / 命令行）。

流程编排仍在 bin/app.py / bin/runner.py，这里不重复实现任何业务逻辑。
"""
from __future__ import annotations

import ctypes
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # 项目根（本文件就在根目录）
MIN_PY = (3, 10)
REQUIRED_PKGS = ("pandas", "openpyxl", "xlrd")
PY_DIR_FILE = BASE_DIR / "config" / "python_path.txt"
CONDA_DIR = Path.home() / ".conda" / "envs" / "visual-dashboard-system"
REEXEC_FLAG = "VDS_LAUNCHER_REEXEC"                 # 防止换解释器后无限重启
CREATE_NO_WINDOW = 0x08000000                       # Windows: 子进程不弹控制台

# 候选解释器探测脚本：版本 + 三个必需依赖都满足才返回 0
_PROBE = (
    "import sys, importlib.util as u;"
    "pk = ('pandas', 'openpyxl', 'xlrd');"
    "sys.exit(0 if sys.version_info[:2] >= (3, 10) and all(u.find_spec(m) for m in pk) else 1)"
)

USAGE = """Visual Dashboard System — 项目根目录启动程序

用法:
  python 启动系统.py                    环境自检 + 打开图形控制台（默认）
  python 启动系统.py --check            只体检，不起界面
  python 启动系统.py --cli              命令行全流程
  python 启动系统.py --cli --step=render        单步运行（参数透传）
  python 启动系统.py --cli --from=split         从某步跑到最后
  python 启动系统.py report             按需生成销售完成度汇总表
  python 启动系统.py list               列出流水线步骤
  python 启动系统.py board              打开最新看板
  python 启动系统.py --help             显示本帮助

说明:
  · 本文件只负责「挑解释器 + 转交」，自检与流程编排在 bin/start.py → bin/app.py
  · 当前 Python 不满足要求时，会按 config/python_path.txt 的口径自动换一个再启动
  · 想不弹黑框：pythonw 启动系统.py；要桌面图标用 python bin/make_shortcut.py --desktop
"""

_WARNINGS: list[str] = []      # 解释器探测过程中的提示（失败时一起打印）


# ---------------------------------------------------------------- 解释器探测

def _exe_name() -> str:
    return "python.exe" if os.name == "nt" else "python"


def _same(a: str | Path, b: str | Path) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def _first_effective_line(path: Path) -> str | None:
    """取文件里第一行「有效内容」（跳过空行与 # 注释）"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s
    return None


def configured_python(path: Path | None = None) -> Path | None:
    """解析 config/python_path.txt 里手填的目录（填了可执行文件也认）

    无效路径不抛异常 —— 按该文件注释的约定「警告后继续探测下一步」。
    """
    src = PY_DIR_FILE if path is None else path
    raw = _first_effective_line(src)
    if raw is None:
        return None
    target = Path(os.path.expandvars(raw)).expanduser()
    if target.is_dir():
        exe = target / _exe_name()
        if exe.exists():
            return exe
        _WARNINGS.append(f"python_path.txt 指定的目录里没有 {_exe_name()}：{target}")
        return None
    if target.exists():
        return target
    _WARNINGS.append(f"python_path.txt 指定的路径不存在：{target}")
    return None


def candidate_interpreters() -> list[Path]:
    """按约定顺序给出候选解释器（只保留真实存在的，已去重）"""
    raw: list[Path] = []
    cfg = configured_python()
    if cfg:
        raw.append(cfg)
    raw.append(BASE_DIR / "runtime" / "python" / _exe_name())   # 交付包内置运行时
    raw.append(CONDA_DIR / _exe_name())                         # 本机 Conda 环境
    for name in ("python", "python3", "py"):
        found = shutil.which(name)
        if found:
            raw.append(Path(found))
    raw.append(Path(sys.executable))                            # 兜底：当前解释器

    out: list[Path] = []
    seen: set[str] = set()
    for c in raw:
        key = os.path.normcase(str(c))
        if key in seen or not c.exists():
            continue
        seen.add(key)
        out.append(c)
    return out


def interpreter_ok() -> bool:
    """当前进程是否满足最低要求（版本 + 依赖），同进程判断，零额外开销"""
    if sys.version_info[:2] < MIN_PY:
        return False
    return all(importlib.util.find_spec(p) is not None for p in REQUIRED_PKGS)


def probe(exe: Path, timeout: float = 60.0) -> bool:
    """用子进程验证候选解释器（别的解释器只能这样验）"""
    flags = CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        done = subprocess.run([str(exe), "-c", _PROBE], capture_output=True,
                              timeout=timeout, creationflags=flags)
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


# ---------------------------------------------------------------- 输出与转交

def _has_console() -> bool:
    """pythonw 下 stdout/stderr 为 None，print 不可见"""
    return sys.stdout is not None and sys.stderr is not None


def _alert(msg: str) -> None:
    """有控制台就打印；无控制台（双击 pythonw）用系统弹窗，避免「闪一下没反应」"""
    if _has_console():
        print(msg, file=sys.stderr)
        return
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, "Visual Dashboard System", 0x10)
    except Exception:
        pass


def delegate(argv: list[str]) -> int:
    """转交 bin/start.py：自检 → bin/app.py"""
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from bin.start import main as start_main

    return start_main(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help", "-?", "/?"):
        print(USAGE)
        return 0

    if interpreter_ok():
        return delegate(argv)

    cur = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    missing = [p for p in REQUIRED_PKGS if importlib.util.find_spec(p) is None]
    reasons: list[str] = []
    if sys.version_info[:2] < MIN_PY:
        reasons.append(f"版本低于 {MIN_PY[0]}.{MIN_PY[1]}")
    if missing:
        reasons.append(f"缺少 {', '.join(missing)}")
    reason = "、".join(reasons) or "环境不满足要求"

    if os.environ.get(REEXEC_FLAG):
        # 已经换过一次解释器仍不合格：不再来回重启，交给 bin/start.py 报缺依赖
        print(f"⚠️  已切换到 {sys.executable}（{cur}），但仍然{reason}。")
        print("   继续转交 bin/start.py 体检，按提示补齐依赖后重试。")
        return delegate(argv)

    for exe in candidate_interpreters():
        if _same(exe, sys.executable):
            continue
        if probe(exe):
            print(f"当前 Python（{cur}，{reason}）不可用，改用：{exe}")
            env = dict(os.environ)
            env[REEXEC_FLAG] = "1"
            try:
                done = subprocess.run([str(exe), str(Path(__file__).resolve()), *argv], env=env)
            except OSError as e:
                _WARNINGS.append(f"用 {exe} 重启失败：{e}")
                continue
            return done.returncode

    lines = [
        "❌ 没有找到可用的 Python（要求 3.10+ 且装有 pandas / openpyxl / xlrd）。",
        f"   当前解释器：{sys.executable}（{cur}，{reason}）",
        *[f"   · {w}" for w in _WARNINGS],
        f"   建议：在 {PY_DIR_FILE} 里写一行 Python 所在目录，",
        "         或使用交付包内置 runtime\\python，然后重试。",
        "   体检命令：python bin/start.py --check",
    ]
    _alert("\n".join(lines))
    return 2


if __name__ == "__main__":
    sys.exit(main())
