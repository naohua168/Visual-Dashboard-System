# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""构建内置 Python 运行时 `runtime/python`（替代原 `scripts/prepare_runtime.bat`）

把嵌入式 Python + 全部依赖装进项目，接收方「解压即用」，无需安装环境。

    python scripts/prepare_runtime.py                # 构建（已存在则跳过下载）
    python scripts/prepare_runtime.py --force        # 删掉 runtime/python 重建
    python scripts/prepare_runtime.py --version 3.12.10
    python scripts/prepare_runtime.py --deps "pandas==3.0.3 openpyxl==3.1.5 xlrd==2.0.2"
    python scripts/prepare_runtime.py --no-verify    # 跳过最后的 import 自检

与 .bat 的差异：
  · 下载走标准库 urllib、解压走 zipfile（不再依赖 PowerShell 的 Invoke-WebRequest/Expand-Archive）
  · 宿主机解释器直接用当前运行的 sys.executable（不再 where python 猜）
  · 失败信息给出可复制的修复命令，而不是只 echo 一句"下载失败"

注意：嵌入式 Python **不含 tkinter**，所以交付机上是 WPF 回退界面；
      若想让交付机也用 tkinter，请改用完整 Python 打包（不在本脚本范围）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # 项目根（本文件在 scripts/ 下）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DEFAULT_VERSION = "3.12.10"
CORE_DEPS = ("pandas", "openpyxl", "xlrd")     # 运行系统所需（pytest 只用于开发，不打进运行时）
EMBED_DIR = BASE_DIR / "runtime" / "python"


def embed_url(version: str) -> str:
    return f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"


def pth_name(version: str) -> str:
    """3.12.10 → python312._pth（嵌入式 Python 的 site 配置文件命名规则）"""
    major, minor, *_ = version.split(".")
    return f"python{major}{minor}._pth"


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "VisualDashboard/prepare_runtime"})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fp:  # noqa: S310
        total = int(resp.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fp.write(chunk)
            got += len(chunk)
            if total:
                print(f"\r    下载中 {got / 1048576:.1f}/{total / 1048576:.1f} MB", end="")
    print(f"\r    下载完成 {dest.stat().st_size / 1048576:.1f} MB" + " " * 12)


def write_pth(version: str) -> Path:
    """启用 site-packages + 项目根

    嵌入式 Python 默认不加载第三方包；且 `_pth` 存在时 `-m` 模式不会把当前目录
    加进 sys.path，必须显式写 `..\\..`（runtime/python → 项目根）。
    """
    pth = EMBED_DIR / pth_name(version)
    lines = [
        f"python{version.split('.')[0]}{version.split('.')[1]}.zip",
        ".",
        r"Lib\site-packages",
        r"..\..",
        "",
        "# Uncomment to run site.main() automatically",
        "import site",
    ]
    pth.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pth


def check_host_pip() -> None:
    try:
        out = subprocess.run([sys.executable, "-m", "pip", "--version"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit(f"❌ 无法调用 pip：{e}")
    if out.returncode != 0:
        raise SystemExit("❌ 当前解释器没有 pip，请改用带 pip 的 Python 运行本脚本：\n"
                         f"   {sys.executable} -m ensurepip --upgrade")


def install_deps(deps: list[str]) -> None:
    site_packages = EMBED_DIR / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "install", "--target", str(site_packages),
           "--no-compile", "--disable-pip-version-check", *deps]
    print(f"    {' '.join(cmd[3:])}")
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        raise SystemExit("❌ 依赖安装失败（检查网络 / pip 源）。可重试：\n"
                         f"   {sys.executable} -m pip install --target \"{site_packages}\" {' '.join(deps)}")


def verify() -> None:
    py = EMBED_DIR / "python.exe"
    code = ("import sys, pandas, openpyxl, xlrd;"
            "print('Python', sys.version.split()[0], '| pandas', pandas.__version__,"
            "'| openpyxl', openpyxl.__version__, '| xlrd', xlrd.__version__)")
    out = subprocess.run([str(py), "-c", code], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("❌ 运行时验证失败：\n" + (out.stderr or out.stdout))
    print("   " + out.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="构建内置 Python 运行时（runtime/python）")
    ap.add_argument("--version", default=DEFAULT_VERSION, help=f"嵌入式 Python 版本（默认 {DEFAULT_VERSION}）")
    ap.add_argument("--force", action="store_true", help="删除已有 runtime/python 后重建")
    ap.add_argument("--deps", default=None, help="覆盖依赖列表，如 \"pandas==3.0.3 openpyxl==3.1.5 xlrd==2.0.2\"")
    ap.add_argument("--no-verify", action="store_true", help="跳过最后的 import 自检")
    args = ap.parse_args(argv)

    if os.name != "nt":
        print("❌ 嵌入式 Python 是 Windows 专用构建产物，本脚本只能在 Windows 上运行。")
        return 2

    deps = args.deps.split() if args.deps else list(CORE_DEPS)
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   构建内置运行时（解压即用，免安装）                 ║")
    print("╚══════════════════════════════════════════════════════╝\n")
    print(f"宿主机解释器: {sys.executable}")
    check_host_pip()

    if EMBED_DIR.exists() and (EMBED_DIR / "python.exe").exists():
        if not args.force:
            print(f"[跳过] {EMBED_DIR.relative_to(BASE_DIR)} 已存在（重建请加 --force）")
            if not args.no_verify:
                print("\n─── 运行时验证 ───")
                verify()
            print("\n✅ 运行时已就绪，可直接打包：python bin/package.py")
            return 0
        print(f"[重建] 删除 {EMBED_DIR.relative_to(BASE_DIR)} …")
        shutil.rmtree(EMBED_DIR, ignore_errors=True)

    # 1) 下载 + 解压
    url = embed_url(args.version)
    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / f"python-{args.version}-embed-amd64.zip"
        print(f"[1/4] 下载嵌入式 Python {args.version}\n      {url}")
        try:
            download(url, zip_path)
        except Exception as e:
            raise SystemExit(f"❌ 下载失败（{type(e).__name__}: {e}）\n"
                             "   请检查网络/代理，或手动下载后用 --version 指定可用版本。")
        print(f"[2/4] 解压到 {EMBED_DIR.relative_to(BASE_DIR)}")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(EMBED_DIR)

    # 2) _pth
    pth = write_pth(args.version)
    print(f"[3/4] 写入 {pth.name}（启用 site-packages + 项目根）")

    # 3) 依赖
    print("[4/4] 安装依赖到内置运行时 …")
    install_deps(deps)

    # 4) 验证
    if not args.no_verify:
        print("\n─── 运行时验证 ───")
        verify()

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║  ✅ 内置运行时构建完成！                             ║")
    print("║  现在运行 python bin/package.py 打包，接收方解压即用。║")
    print("╚══════════════════════════════════════════════════════╝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
