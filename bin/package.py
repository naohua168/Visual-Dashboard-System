# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""打包交付（替代原 `bin/package.bat`）

    python bin/package.py                 打包 → Visual-Dashboard-System_vYYYYMMDD.zip
    python bin/package.py --dry-run       只打印将要复制的清单，不落盘
    python bin/package.py --no-runtime    不复制内置运行时（包更小，接收方需自备 Python）
    python bin/package.py --keep          保留解压用的临时目录（排障用）
    python bin/package.py --out-dir D:\\  指定 zip 输出目录（默认项目根）

与 .bat 的差异：
  · 不再依赖 PowerShell 取日期 / 压缩（改 datetime + zipfile，纯标准库）
  · 复制时忽略 __pycache__ / *.pyc / ~$ 锁文件 / .git，省一步清理
  · 新增 output/客户矩阵 骨架，并给出进度与体积统计
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent   # 项目根（本文件在 bin/ 下）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

COPY_DIRS = ("engine", "processors", "config", "bin", "scripts", "tests", "docs")
COPY_FILES = ("requirements.txt", "pytest.ini", "README.md")
DATA_COPY = ("data/raw", "data/mappings", "data/sheets/手动维护")
CLEAN_SUBDIRS = (
    "当年累计收入", "当年累计回款", "季度累计收入", "季度累计回款",
    "月收入", "月回款", "销售收入", "销售回款", "往年收入", "往年回款",
)
OUTPUT_SUBDIRS = ("看板", "数据", "销售完成度", "客户矩阵")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "~$*", ".git", ".pytest_cache")


def _size_mb(path: Path) -> float:
    total = path.stat().st_size if path.is_file() else sum(
        f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / 1024 / 1024


def build_manifest() -> list[tuple[Path, Path]]:
    """返回 [(源, 目标相对包根的路径)]，供复制与 dry-run 共用"""
    plan: list[tuple[Path, Path]] = []
    for name in COPY_DIRS:
        src = BASE_DIR / name
        if src.exists():
            plan.append((src, Path(name)))
    for name in COPY_FILES:
        src = BASE_DIR / name
        if src.exists():
            plan.append((src, Path(name)))
    for name in DATA_COPY:
        src = BASE_DIR / name
        if src.exists():
            plan.append((src, Path(name)))
    runtime = BASE_DIR / "runtime" / "python" / "python.exe"
    if runtime.exists():
        plan.append((BASE_DIR / "runtime", Path("runtime")))
    return plan


def copy_item(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=IGNORE)
    else:
        shutil.copy2(src, dst)


def make_skeletons(pkg: Path) -> None:
    """清洗产物 / 输出目录只建空骨架（运行时自动生成）"""
    for name in CLEAN_SUBDIRS:
        (pkg / "data" / "sheets" / "系统数据清理" / name).mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_SUBDIRS:
        (pkg / "output" / name).mkdir(parents=True, exist_ok=True)
    (pkg / "logs").mkdir(parents=True, exist_ok=True)
    (pkg / "output" / ".gitkeep").write_text("", encoding="utf-8")


def make_zip(pkg: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in sorted(pkg.rglob("*")):
            arc = (Path(pkg.name) / f.relative_to(pkg)).as_posix()
            if f.is_dir():
                # 空目录（output/、logs/、系统数据清理/…）必须显式写入目录条目，
                # 否则解压后骨架会丢（zipfile 默认只收文件）
                zf.write(f, arcname=arc + "/")
            else:
                zf.write(f, arcname=arc)


BANNER_TAIL = """╔══════════════════════════════════════════════════════╗
║  包含（完整环境，可解压即用）:                       ║
║  ▪ engine/      清洗引擎                             ║
║  ▪ processors/  渲染层                               ║
║  ▪ scripts/     工具脚本（配置同步 + 校验 + 导出）    ║
║  ▪ config/      配置（配置编辑器.xlsx + KPI 指标）    ║
║  ▪ bin/         入口（start.py 启动 / app.py 分发）  ║
║  ▪ docs/        部署指南 + 设计 + 字段映射 + 维护     ║
║  ▪ data/raw/    原始数据（财务端/运营端/往年/名单）   ║
║  ▪ data/mappings/ 映射（部门 + 客户名单）            ║
║  ▪ data/sheets/手动维护/  6 张指标表                 ║
║  ▪ runtime/     内置 Python 运行时（免安装）         ║
║  ▪ 产物无第三方 JS 依赖（离线可用）                  ║
╠══════════════════════════════════════════════════════╣
║  不包含（运行后自动生成）:                           ║
║  ▪ data/sheets/系统数据清理/  清洗中间产物            ║
║  ▪ output/看板/<年>/<月>/     6 页看板               ║
║  ▪ output/数据/<年>/<月>/     数据总表 (16 sheet)    ║
║  ▪ output/销售完成度/(按需)   销售完成度汇总表        ║
║  ▪ output/客户矩阵/(按需)     按客户清单导出的矩阵    ║
║  ▪ logs/          运行日志                           ║
╚══════════════════════════════════════════════════════╝"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="打包交付（Visual-Dashboard-System zip）")
    ap.add_argument("--dry-run", action="store_true", help="只打印清单，不复制/不压缩")
    ap.add_argument("--no-runtime", action="store_true", help="不复制内置 Python 运行时")
    ap.add_argument("--keep", action="store_true", help="保留临时目录（默认压缩后删除）")
    ap.add_argument("--out-dir", default=None, help="zip 输出目录（默认项目根）")
    args = ap.parse_args(argv)

    pkg_name = f"Visual-Dashboard-System_v{date.today():%Y%m%d}"
    pkg = BASE_DIR / pkg_name
    out_dir = Path(args.out_dir).resolve() if args.out_dir else BASE_DIR
    zip_path = out_dir / f"{pkg_name}.zip"

    plan = build_manifest()
    if args.no_runtime:
        plan = [(s, d) for s, d in plan if d.as_posix() != "runtime"]

    if args.dry_run:
        print(f"📦 将打包为 {pkg_name}.zip\n")
        for src, rel in plan:
            print(f"  + {rel.as_posix()}/" if src.is_dir() else f"  + {rel.as_posix()}")
        print(f"  + data/sheets/系统数据清理/（{len(CLEAN_SUBDIRS)} 个空目录）")
        print(f"  + output/（{'、'.join(OUTPUT_SUBDIRS)}，空目录）+ logs/")
        if not (BASE_DIR / "runtime" / "python" / "python.exe").exists():
            print("\n  ⚠️ 未找到 runtime/python/python.exe —— 打包后接收方需自备 Python 3.10+")
        print(f"\n📄 期望输出: {zip_path}")
        return 0

    if pkg.exists():
        shutil.rmtree(pkg, ignore_errors=True)
    zip_path.unlink(missing_ok=True)
    pkg.mkdir(parents=True, exist_ok=True)

    print(f"\n📦 打包 {pkg_name}\n")
    for i, (src, rel) in enumerate(plan, 1):
        mark = "目录" if src.is_dir() else "文件"
        print(f"[{i}/{len(plan)}] {mark} {rel.as_posix()}")
        copy_item(src, pkg / rel)
    if not (BASE_DIR / "runtime" / "python" / "python.exe").exists():
        print("\n⚠️ 未找到 runtime\\python\\python.exe —— 接收方需自备 Python 3.10+ 环境")

    make_skeletons(pkg)
    print("[骨架] data/sheets/系统数据清理/ · output/ · logs/")

    print("[压缩] 正在生成 zip（内置运行时时约 1–3 分钟）…")
    out_dir.mkdir(parents=True, exist_ok=True)
    make_zip(pkg, zip_path)

    mb = _size_mb(zip_path)
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  ✅ 打包完成: {zip_path.name}（{mb:.1f} MB）")
    print(BANNER_TAIL)

    if args.keep:
        print(f"\n临时目录已保留: {pkg}")
    else:
        shutil.rmtree(pkg, ignore_errors=True)
    print(f"\n产物: {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
