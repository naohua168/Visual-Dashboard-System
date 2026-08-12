"""看板 HTML 全面验证：提取 <script> 用 node --check 校验语法，并核对 onclick 函数定义。

用法: python scripts/verify_dashboard.py [html_path]
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).parent.parent
html_path = sys.argv[1] if len(sys.argv) > 1 else None
if not html_path:
    htmls = sorted((BASE / "output" / "看板").glob("看板_*.html"))
    if not htmls:
        print("未找到看板 HTML")
        sys.exit(1)
    html_path = str(htmls[-1])
html = Path(html_path).read_text(encoding="utf-8")
print(f"验证文件: {html_path}")

# ── 1. 提取所有 <script> 内容 ──
scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
print(f"\n[{len(scripts)} 个 <script> 块]")

problems = []
for i, s in enumerate(scripts):
    if not s.strip():
        continue
    # 去除 HTML 注释
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(s)
        tmp = f.name
    r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
    if r.returncode != 0:
        problems.append(f"  script#{i}: 语法错误\n{r.stderr}")
    Path(tmp).unlink(missing_ok=True)

if problems:
    print("❌ JS 语法错误:")
    for p in problems:
        print(p)
else:
    print("✅ 所有 <script> 块语法正确")

# ── 2. 核对 onclick 引用的函数是否已定义 ──
print(f"\n[onclick 函数核对]")
all_js = "\n".join(scripts)
defined = set(re.findall(r"(?:function\s+|window\.)\s*([A-Za-z_$][\w$]*)\s*(?:\()?=", all_js))
defined |= set(re.findall(r"function\s+([A-Za-z_$][\w$]*)\s*\(", all_js))
defined |= set(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", all_js))

onclick_funcs = set(re.findall(r'onclick="([A-Za-z_$][\w$]*)\s*\(', html))
onclick_funcs |= set(re.findall(r'onclick=\'([A-Za-z_$][\w$]*)\s*\(', html))

_JS_KEYWORDS = {"if", "for", "while", "return", "var", "let", "const", "function", "else"}
missing = sorted(f for f in onclick_funcs if f not in defined and f not in _JS_KEYWORDS)
if missing:
    print(f"⚠️  引用但未定义的函数: {missing}")
else:
    print(f"✅ 所有 {len(onclick_funcs)} 个 onclick 函数均已定义")

# ── 3. 检查页面 template 结构 ──
tpls = re.findall(r'<template id="tpl-([^"]+)">', html)
print(f"\n[页面模板] {tpls}")
for t in tpls:
    m = re.search(rf'<div id="{t}" class="page"', html)
    if not m:
        print(f"⚠️  页面 {t} 缺少 <div id='{t}' class='page'> 包装")

# ── 4. 检查关键交互函数 ──
key_funcs = ["showPage", "openSalesModal", "closeSalesModal", "switchSc3Sales", "switchSc3Metric",
             "annual_inc_show", "annual_pay_show", "monthly_inc_show", "monthly_pay_show",
             "qtr_inc_show", "qtr_pay_show", "switchTab", "toggleFullscreen"]
print("\n[关键交互函数]")
for kf in key_funcs:
    print(f"  {'✅' if kf in defined else '❌ 缺失'} {kf}")

print("\n完成。")
