# Author: naohua168 <bai_bai168@qq.com>
"""交付物全面验证 —— 看板 HTML + Excel 总表 + 销售完成度表（2026-09-29 扩档）

校验三件事：
  ① 看板 HTML：`<script>` 语法（node --check）、onclick 函数绑定、6 页 template、关键交互函数
  ② 数据总表 `<输出目录>/数据/data_YYYYMMDD.xlsx`：存在、非空、必需 sheet 齐全且有数据行
  ③ 销售完成度 `<输出目录>/销售完成度/销售完成度汇总_YYYYMMDD.xlsx`：存在、2 个 sheet 非空

用法:
    python scripts/verify_dashboard.py                 # 自动取最新的看板 HTML + 交付物
    python scripts/verify_dashboard.py <html_path>     # 指定 HTML
    python scripts/verify_dashboard.py --allow-missing-report   # 没跑销售完成度步骤时不报错
退出码: 0 = 全部通过；1 = 有 ❌ 问题（问题清单打印在最后）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from engine.core.utils import rel_path  # noqa: E402  （日志/提示路径统一相对项目根显示）

EXPECTED_PAGES = ["overview", "annual", "monthly", "sales", "yoy", "quarterly"]
KEY_FUNCS = ["showPage", "openSalesModal", "closeSalesModal", "switchSc3Sales", "switchSc3Metric",
             "annual_inc_show", "annual_pay_show", "monthly_inc_show", "monthly_pay_show",
             "qtr_inc_show", "qtr_pay_show", "switchTab", "toggleFullscreen"]
MIN_HTML_KB = 200.0            # 正常约 1.8MB；低于此值基本是渲染截断
# 数据总表必须有的 sheet（其余为可选：季度累计/往年/月，缺了只提示）
REQUIRED_SHEETS = ["当年累计收入", "当年累计回款", "销售收入", "销售回款",
                   "年度收入总指标", "年度回款总指标",
                   "季度收入指标", "季度回款指标", "月度收入指标", "月度回款指标"]
_JUNK_PREFIX = "~$"


def _newest(folder: Path, pattern: str) -> Path | None:
    files = sorted((f for f in folder.glob(pattern) if not f.name.startswith(_JUNK_PREFIX)),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def base_output_dir() -> Path:
    """输出根目录：取 前端渲染/看板展示配置.json → 文件输出.目录（渲染层同一事实源）"""
    try:
        cfg = json.loads((BASE / "config" / "前端渲染" / "看板展示配置.json").read_text(encoding="utf-8"))
        rel = cfg.get("文件输出", {}).get("目录", "output")
    except Exception:
        rel = "output"
    return BASE / rel


def _cfg_output(key: str, fallback: str) -> Path:
    """读 cleaning_config.json → 输出.<key>（缺省回落）"""
    try:
        cfg = json.loads((BASE / "config" / "清洗配置" / "cleaning_config.json").read_text(encoding="utf-8"))
        rel = cfg.get("输出", {}).get(key, fallback)
    except Exception:
        rel = fallback
    return BASE / str(rel)


# ══════════════════════════════════════════════════════════════
# ① 看板 HTML
# ══════════════════════════════════════════════════════════════
def _has_node() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=False)
        return True
    except (FileNotFoundError, OSError):
        return False


def verify_html(html_path: Path, problems: list[str]) -> None:
    html = html_path.read_text(encoding="utf-8")
    kb = html_path.stat().st_size / 1024
    print(f"验证文件: {rel_path(html_path)}")
    print(f"  大小: {kb:.1f} KB")
    if kb < MIN_HTML_KB:
        problems.append(f"看板 HTML 偏小（{kb:.1f} KB < {MIN_HTML_KB:.0f} KB），可能渲染不完整")

    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    print(f"\n[{len(scripts)} 个 <script> 块]")
    js_problems = []
    node_ok = _has_node()
    if not node_ok:
        # 没装 node 就跳过语法校验（只提示，不算交付问题；结构/绑定校验照旧）
        print("⚠️  未找到 node，跳过 JS 语法校验（只做结构/onclick 绑定校验）")
    for i, s in enumerate(scripts):
        if not node_ok or not s.strip():
            continue
        s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(s)
            tmp = f.name
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            js_problems.append(f"script#{i}: 语法错误\n{r.stderr}")
        Path(tmp).unlink(missing_ok=True)
    if js_problems:
        print("❌ JS 语法错误:")
        for p in js_problems:
            print(p)
        problems.extend(js_problems)
    elif node_ok:
        print("✅ 所有 <script> 块语法正确")

    print("\n[onclick 函数核对]")
    all_js = "\n".join(scripts)
    defined = set(re.findall(r"(?:function\s+|window\.)\s*([A-Za-z_$][\w$]*)\s*(?:\()?=", all_js))
    defined |= set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", all_js))
    defined |= set(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", all_js))
    onclick_funcs = set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\s*\(', html))
    onclick_funcs |= set(re.findall(r"onclick='([A-Za-z_$][\w$]*)\s*\(", html))
    keywords = {"if", "for", "while", "return", "var", "let", "const", "function", "else"}
    missing = sorted(f for f in onclick_funcs if f not in defined and f not in keywords)
    if missing:
        print(f"⚠️  引用但未定义的函数: {missing}")
        problems.append(f"onclick 引用了未定义函数: {missing}")
    else:
        print(f"✅ 所有 {len(onclick_funcs)} 个 onclick 函数均已定义")

    print("\n[页面模板]")
    tpls = re.findall(r'<template id="tpl-([^"]+)">', html)
    print(f"  实际: {tpls}")
    for page in EXPECTED_PAGES:
        if page not in tpls:
            problems.append(f"缺少页面模板: tpl-{page}")
        elif not re.search(rf'<div id="{page}" class="page"', html):
            problems.append(f"页面 {page} 缺少 <div id='{page}' class='page'> 包装")
    print(f"  {'✅ 6 页齐全' if all(p in tpls for p in EXPECTED_PAGES) else '❌ 页面缺失'}")

    print("\n[关键交互函数]")
    for kf in KEY_FUNCS:
        ok = kf in defined
        print(f"  {'✅' if ok else '❌ 缺失'} {kf}")
        if not ok:
            problems.append(f"缺少关键交互函数: {kf}")


# ══════════════════════════════════════════════════════════════
# ② 交付物：数据总表 + 销售完成度
# ══════════════════════════════════════════════════════════════
def _check_excel(path: Path, label: str, required_sheets: list[str], problems: list[str]) -> None:
    import pandas as pd

    if not path.exists():
        problems.append(f"缺少{label}: {rel_path(path)}")
        print(f"❌ 缺少{label}: {rel_path(path)}")
        return
    kb = path.stat().st_size / 1024
    try:
        book = pd.read_excel(path, sheet_name=None)
    except Exception as e:
        problems.append(f"{label} 无法读取: {e}")
        print(f"❌ {label} 无法读取: {e}")
        return
    empty_required = [s for s in required_sheets if s not in book or len(book[s]) == 0]
    empty_optional = [s for s, df in book.items() if len(df) == 0]
    print(f"  {label}: {path.name}（{kb:.1f} KB，{len(book)} 个 sheet，"
          f"必需 {len(required_sheets) - len(empty_required)}/{len(required_sheets)} 非空）")
    if empty_required:
        problems.append(f"{label} 必需 sheet 缺失或为空: {empty_required}")
        print(f"❌ 必需 sheet 缺失/为空: {empty_required}")
    if empty_optional:
        print(f"  ⚠️  空 sheet（可选，确认是否需要）: {empty_optional}")


def verify_artifacts(base_out: Path, problems: list[str], allow_missing_report: bool = False) -> None:
    print("\n[交付物]")
    data_dir = _cfg_output("数据", "output/数据/")
    if not data_dir.exists():
        data_dir = base_out / "数据"
    total = _newest(data_dir, "data_*.xlsx")
    if total is None:
        problems.append(f"缺少数据总表 Excel: {rel_path(data_dir / 'data_*.xlsx')}")
        print(f"❌ 缺少数据总表: {rel_path(data_dir / 'data_*.xlsx')}")
    else:
        _check_excel(total, "数据总表", REQUIRED_SHEETS, problems)

    rep_dir = _cfg_output("销售完成度", "output/销售完成度/")
    if not rep_dir.exists():
        rep_dir = base_out / "销售完成度"
    report = _newest(rep_dir, "销售完成度汇总_*.xlsx")
    if report is None:
        msg = f"缺少销售完成度表: {rel_path(rep_dir / '销售完成度汇总_*.xlsx')}"
        if allow_missing_report:
            print(f"  ⚠️  {msg}（已按 --allow-missing-report 忽略）")
        else:
            problems.append(msg)
            print(f"❌ {msg}")
    else:
        _check_excel(report, "销售完成度", ["销售收入", "销售回款"], problems)


# ══════════════════════════════════════════════════════════════
# main
# ══════════════════════════════════════════════════════════════
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="看板与交付物验证")
    ap.add_argument("html_path", nargs="?", default=None, help="看板 HTML 路径（默认取最新）")
    ap.add_argument("--allow-missing-report", action="store_true",
                    help="没跑「销售完成度」步骤时不判为问题")
    args = ap.parse_args(argv)

    base_out = base_output_dir()
    html_path = Path(args.html_path) if args.html_path else _newest(base_out / "看板", "看板_*.html")
    problems: list[str] = []

    if html_path is None or not Path(html_path).exists():
        print("❌ 未找到看板 HTML")
        return 1
    verify_html(Path(html_path), problems)
    verify_artifacts(base_out, problems, allow_missing_report=args.allow_missing_report)

    print("\n" + "═" * 56)
    if problems:
        print(f"❌ 交付物校验失败：{len(problems)} 个问题")
        for p in problems:
            print(f"   - {p}")
        print("═" * 56)
        return 1
    print("✅ 交付物校验通过：看板 HTML + 数据总表 + 销售完成度表 齐全且非空")
    print("═" * 56)
    return 0


if __name__ == "__main__":
    sys.exit(main())
