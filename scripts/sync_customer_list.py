# Author: naohua168 <bai_bai168@qq.com>
"""「销售归属」→「客户名单」自动同步（只加不删）

为什么需要（2026-11-02 用户提出）：
    财务端 收入.xlsx / 回款.xlsx 清洗时按「客户名单」白名单过滤
    （`engine/income_payment/financial.py::_filter_by_whitelist`，名单外**整行丢弃**）。
    于是「配置编辑器 → 销售归属」里新加了一个客户、客户名单里却没有 →
    这家公司的钱进不了看板，表现为"看板上没数据"，很难排查。
    本模块在「配置同步」（Excel → JSON）之后运行，把归属表里的客户补进名单。

口径（2026-11-02 用户确认）：
    · 全量同步：归属表**所有父组**下的子公司名都进名单
    · **只加不删**：名单里有、归属表里没有 → 保留；不做反向提示
    · **直接写 + 备份**：没有新增就完全不碰文件；有新增先备份到
      `logs/名单同步/客户名单.bak_*.xlsx`（默认保留最近 5 份）
    · 过滤 `business_rules.gd_blacklist()`（合计/小计/无/内部… + 三个法人自身名）
    · 去重按 `name_key.match_key`（全角半角括号、空白、大小写都算同一家）
    · 名单文件被 Excel 占用 → 打警告后跳过，异常不外抛（流水线不中断）

用法：
    python scripts/sync_customer_list.py              # 同步（读 客户销售归属.json）
    python scripts/sync_customer_list.py --dry-run    # 只看会新增多少，不写文件
    python scripts/sync_customer_list.py --excel      # 从配置编辑器.xlsx 读（最新编辑）
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from copy import copy
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from openpyxl import load_workbook  # noqa: E402

from engine.core import business_rules as br  # noqa: E402
from engine.core.name_key import match_key  # noqa: E402
from engine.core.utils import rel_path  # noqa: E402

try:  # 直接以脚本方式运行时
    from sheet_style import save_workbook
except ImportError:  # 以包形式导入时（如单元测试）
    from scripts.sheet_style import save_workbook  # type: ignore[no-redef]

CUST_XLSX = BASE_DIR / "data" / "raw" / "客户名单" / "客户名单.xlsx"
ATTR_JSON = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
BACKUP_DIR = BASE_DIR / "logs" / "名单同步"
DEFAULT_KEEP = 5
PREVIEW_N = 5          # 日志里最多列出几个新增客户名


# ──────────────────────────────────────────────────────────────
# 归属表读取
# ──────────────────────────────────────────────────────────────
def load_attribution(from_excel: bool = False) -> dict:
    """读销售归属：默认读 JSON（系统事实源），`from_excel=True` 时读配置编辑器 Excel"""
    if from_excel:
        import openpyxl

        from scripts.editor.attribution import excel_to_attribution

        wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
        if "销售归属" not in wb.sheetnames:
            raise RuntimeError(f"配置编辑器缺少「销售归属」sheet: {rel_path(EXCEL_PATH)}")
        return excel_to_attribution(wb["销售归属"])

    if not ATTR_JSON.exists():
        raise FileNotFoundError(f"客户销售归属.json 不存在: {rel_path(ATTR_JSON)}")
    return json.loads(ATTR_JSON.read_text(encoding="utf-8")).get("客户归属", {}) or {}


def _as_names(value) -> list[str]:
    """配置值 → 名字列表（支持 JSON 数组，也兼容 `"a/b/c"`、`"a,b"` 这类手写字符串）"""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(x).strip() for x in value if str(x).strip()]
    return [p.strip() for p in str(value).replace("，", ",").replace("、", ",").replace("/", ",").split(",")
            if p.strip()]


def collect_customers(attribution: dict, skip_parents=(), skip_customers=()) -> list[tuple[str, str]]:
    """归属 dict → [(客户名, 首个所属父组)]，按出现顺序、按匹配键去重

    `skip_parents` / `skip_customers` 里的名字按 `match_key` 比较（全角半角/空白/大小写归一）。
    """
    skip_p = {match_key(x) for x in skip_parents}
    skip_c = {match_key(x) for x in skip_customers}
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for parent, group in (attribution or {}).items():
        if match_key(parent) in skip_p:
            continue
        for sub in ((group or {}).get("子公司", {}) or {}):
            name = str(sub).strip()
            key = match_key(name)
            if not key or key in skip_c or key in seen:
                continue
            seen.add(key)
            out.append((name, str(parent).strip()))
    return out


# ──────────────────────────────────────────────────────────────
# 名单读写
# ──────────────────────────────────────────────────────────────
def read_customer_names(path: Path) -> list[str]:
    """读名单 Excel 第 1 列（第 1 行是表头「客户」）"""
    wb = load_workbook(path)
    ws = wb[wb.sheetnames[0]]
    names = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        v = row[0] if row else None
        if v is None:
            continue
        s = str(v).strip()
        if s:
            names.append(s)
    return names


def _backup(path: Path, backup_dir: Path, keep: int) -> Path:
    """写前备份 + 只保留最近 keep 份"""
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"{path.stem}.bak_{ts}{path.suffix}"
    n = 1
    while dst.exists():
        dst = backup_dir / f"{path.stem}.bak_{ts}_{n}{path.suffix}"
        n += 1
    shutil.copy2(path, dst)
    olds = sorted(backup_dir.glob(f"{path.stem}.bak_*{path.suffix}"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    for p in olds[max(int(keep), 1):]:
        try:
            p.unlink()
        except OSError:
            pass
    return dst


def _append_rows(ws, names: list[str]) -> int:
    """把客户名追加到第 1 列末尾（样式沿用末行），返回写入行数"""
    last = ws.max_row
    style_src = max(last, 1)
    for i, name in enumerate(names, start=1):
        cell = ws.cell(row=last + i, column=1, value=name)
        try:
            cell._style = copy(ws.cell(row=style_src, column=1)._style)
        except Exception:
            pass
    return len(names)


# ──────────────────────────────────────────────────────────────
# 同步主流程
# ──────────────────────────────────────────────────────────────
def sync_customer_list(attribution: dict | None = None,
                       dry_run: bool = False,
                       log=print,
                       path=None,
                       backup_dir=None,
                       keep: int | None = None) -> dict:
    """把归属表里的客户补进客户名单（只加不删）

    Args:
        attribution: 归属 dict（{母公司: {"子公司": {...}}}）；None = 读 客户销售归属.json
        dry_run: 只算差异，不写文件、不备份
        path: 名单 xlsx（默认 data/raw/客户名单/客户名单.xlsx）
        backup_dir / keep: 备份目录与保留份数（默认 logs/名单同步/，5 份）

    Returns:
        {"status": "unchanged"|"updated"|"would_update"|"locked"|"missing",
         "added": [客户名...], "total": 名单最终家数, "backup": 备份路径或 None}
    """
    target = Path(path) if path else CUST_XLSX
    rules = br.customer_list_sync_rules()
    skip_parents = _as_names(rules.get("排除父组"))
    skip_customers = set(_as_names(rules.get("排除客户"))) | br.gd_blacklist()
    keep_n = int(keep if keep is not None else (rules.get("备份保留份数") or DEFAULT_KEEP))

    if attribution is None:
        attribution = load_attribution()

    wanted = collect_customers(attribution, skip_parents, skip_customers)

    if not target.exists():
        log(f"  ⚠️ 客户名单不存在，跳过自动同步: {rel_path(target)}")
        return {"status": "missing", "added": [], "total": 0, "backup": None}

    existing = {match_key(n) for n in read_customer_names(target)}
    added = [(n, p) for n, p in wanted if match_key(n) not in existing]
    total_before = len(existing)

    if not added:
        log(f"  客户名单已是最新（{total_before} 家，无需新增）")
        return {"status": "unchanged", "added": [], "total": total_before, "backup": None}

    dist = Counter(p for _, p in added)
    dist_txt = "、".join(f"{p} {n}" for p, n in dist.most_common())
    preview = "、".join(n for n, _ in added[:PREVIEW_N])
    more = f"…（共 {len(added)} 家）" if len(added) > PREVIEW_N else ""

    if dry_run:
        log(f"  【DRY-RUN】客户名单将新增 {len(added)} 家（{dist_txt}），"
            f"{total_before} → {total_before + len(added)} 家")
        log(f"    新增: {preview}{more}")
        return {"status": "would_update", "added": [n for n, _ in added],
                "total": total_before + len(added), "backup": None}

    backup = _backup(target, Path(backup_dir) if backup_dir else BACKUP_DIR, keep_n)
    wb = load_workbook(target)
    ws = wb[wb.sheetnames[0]]
    _append_rows(ws, [n for n, _ in added])
    try:
        save_workbook(wb, target)
    except PermissionError:
        log(f"  ⚠️ 客户名单正被 Excel 占用，本次未写入（关闭后重跑即可）: {rel_path(target)}")
        return {"status": "locked", "added": [n for n, _ in added],
                "total": total_before, "backup": None}

    total_after = total_before + len(added)
    log(f"  ✅ 客户名单自动同步：新增 {len(added)} 家（{dist_txt}），当前共 {total_after} 家")
    log(f"    新增: {preview}{more}")
    log(f"    原文件已备份: {rel_path(backup)}")
    return {"status": "updated", "added": [n for n, _ in added],
            "total": total_after, "backup": backup}


# ──────────────────────────────────────────────────────────────
# 命令行
# ──────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="销售归属 → 客户名单 自动同步（只加不删；无新增不碰文件）")
    ap.add_argument("--dry-run", action="store_true", help="只看会新增多少，不写文件")
    ap.add_argument("--excel", action="store_true",
                    help="从「配置编辑器.xlsx → 销售归属」读（默认读 客户销售归属.json）")
    args = ap.parse_args(argv)

    print("=" * 66)
    print("客户名单自动同步（销售归属 → 客户名单，只加不删）")
    try:
        att = load_attribution(from_excel=args.excel)
    except Exception as e:
        print(f"  ⚠️ 读取销售归属失败，跳过: {e}")
        return 2
    res = sync_customer_list(att, dry_run=args.dry_run)
    print(f"  来源: {'配置编辑器.xlsx' if args.excel else rel_path(ATTR_JSON)}"
          f" | 名单: {rel_path(CUST_XLSX)}")
    if args.dry_run:
        print("\n（DRY-RUN 未写文件。去掉 --dry-run 即真正写入）")
    return 0 if res["status"] in ("updated", "unchanged", "would_update") else 2


if __name__ == "__main__":
    sys.exit(main())
