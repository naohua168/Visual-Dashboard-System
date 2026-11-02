# Author: naohua168 <bai_bai168@qq.com>
"""扫描「广东自有客户」应自动归入的公司，并写回配置编辑器（Excel）

口径（2026-09-21 用户确认；2026-11-02 按 `业务规则.json → 广东自有归入._说明` 补齐来源）：
  · **候选来源 = 运营端 收入/回款（.xls）+ 财务端「广东公司.xlsx」（收入/回款两个 Sheet）**
    —— 2026-11-02 之前只扫运营端，与业务规则的说明不一致，现按说明统一
  · 法人主体 = 广东汽车检测中心有限公司（运营端看 法人主体/核算单位/所属单位 列；
    财务端「广东公司.xlsx」整表视为该法人，取值来自 `数据源.财务端.广东公司.法人主体`，
    若配置成别的法人则整表跳过）
  · **不属于任何销售**：客户名在 `客户销售归属.json` 的所有父组里都没出现过（公司级判定）
  · **公司级**排除内部交易（2026-09-22 用户口径）：只要该公司在运营端有**任意一行**内部交易标记
    （`是否属于内部单位/内部款项` == 是），或出现在内部交易排除名单
    （`部门事业部映射.json → excluded_internal_companies`）→ **整家公司不进入候选**
    （广东公司表若有同类列，按同一口径处理）
  → 追加到 `config/配置编辑器.xlsx` 的「销售归属」sheet：
     母公司=广东自有客户 / 指标=收入/回款 / 部门=检测,信息,能源,海外 / 销售=黎国键 / 比例=1

为什么需要状态文件：
  人工若把某行从 Excel 里删掉（不想让它归入），下一轮扫描不应该又加回来
  → `data/mappings/广东自有/已自动归入.json` 记录"曾经自动归入过"的客户，永不再自动追加；
    如需重新归入，请手工在 Excel 里加回来（Excel 始终是唯一编辑入口）。

用法:
    python scripts/scan_gd_owned.py            # 只扫描并打印清单（不改文件）
    python scripts/scan_gd_owned.py --write    # 扫描后写回 Excel + 状态文件（流水线用）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from engine.core import business_rules as br  # noqa: E402
from engine.core.business_rules import is_gd_legal  # noqa: E402
from engine.core.config import get_data_path, load_config  # noqa: E402
from engine.core.name_key import key_set, match_key  # noqa: E402

# 2026-09-29 起：法人主体 / 父组 / 销售 / 部门 / 黑名单 / 列名候选 / 内部交易标记值
# 全部配置驱动（config/清洗配置/业务规则.json → 广东自有归入），人员或口径调整不必改代码。
GD_LEGAL = br.legal_gd()
GD_PARENT = br.parent_gd_self()
GD_SALES = br.sales_gd_self()
DEPTS = br.departments()
EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
ATTR_PATH = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
STATE_PATH = br.gd_state_path()          # 「已自动归入」状态文件（企业已单独删掉的不会再加回）

LEGAL_COLS = br.gd_legal_cols()
CUST_COLS = br.gd_customer_cols()
INT_COLS = br.gd_internal_cols()
INTERNAL_VALUES = br.gd_internal_values()

# 明显不是"客户"的名字（源表占位行 / 汇总行 / 自身法人名）→ 不写入销售归属
BLACKLIST_NAMES = br.gd_blacklist()
MIN_NAME_LEN = br.gd_min_name_len()


# ──────────────────────────────────────────────────────────────
# 配置读取
# ──────────────────────────────────────────────────────────────
def load_config_subs() -> set[str]:
    """客户销售归属.json 里所有父组下的子公司名（= 已属于某销售的客户）"""
    data = json.loads(ATTR_PATH.read_text(encoding="utf-8"))
    subs: set[str] = set()
    for group in data.get("客户归属", {}).values():
        for sub in group.get("子公司", {}):
            subs.add(str(sub).strip())
    return subs


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _pick_col(cols, candidates):
    return next((c for c in candidates if c in cols), None)


def _load_excluded_keys() -> set[str]:
    """内部交易公司排除名单（与清洗层 mapper / 销售引擎同源，按匹配键）"""
    try:
        p = BASE_DIR / "data" / "mappings" / "部门事业部映射" / "部门事业部映射.json"
        raw = json.loads(p.read_text(encoding="utf-8")).get("excluded_internal_companies", {})
        items = raw if isinstance(raw, list) else raw.get("companies", [])
        return key_set(items)
    except Exception:
        return set()


def _amount_multiplier_of(src_config, file_type: str) -> float:
    """读配置 `金额乘数`（数值 / 按 Sheet 的字典）；未配置按 1（仅用于日志概览，不参与判定）"""
    raw = src_config.get("金额乘数")
    if isinstance(raw, dict):
        raw = raw.get(file_type)
    try:
        return float(raw) if raw is not None else 1.0
    except (TypeError, ValueError):
        return 1.0


# ──────────────────────────────────────────────────────────────
# 候选收集
# ──────────────────────────────────────────────────────────────
def collect_from_operations(cfg) -> dict[str, dict]:
    """运营端 收入.xls / 回款.xls：法人（或核算单位）=广东 的公司

    ⚠️ 2026-09-22 用户口径 —— **公司级**排除内部交易：
       只要该公司在运营端有**任意一行**内部交易标记（`是否属于内部单位/内部款项` 等 == 是），
       或该公司名出现在内部交易排除名单里
       （`data/mappings/部门事业部映射/部门事业部映射.json → excluded_internal_companies`，
         与清洗层 `mapper.is_excluded` / 销售引擎 `_load_excluded_companies` 同一份）
       → **整家公司不进入候选**（而不是只丢掉内部交易那几行）。
    """
    # 内部交易公司排除名单（与 engine/sales/run.py::_load_excluded_companies 同源）
    excluded: set[str] = _load_excluded_keys()

    found: dict[str, dict] = {}
    internal_companies: set[str] = set()

    for ft in ["收入", "回款"]:
        conf = cfg["数据源"]["运营端"][ft]
        for sh in conf["Sheet"]:
            try:
                df = pd.read_excel(get_data_path(cfg, "运营端", ft), sheet_name=sh, engine=conf["引擎"])
            except Exception:
                continue
            legal = _pick_col(df.columns, LEGAL_COLS)
            cust = _pick_col(df.columns, CUST_COLS)
            if not legal or not cust:
                continue
            # 法人主体按匹配键判定（全角半角/空白差异不影响，2026-09-29）
            sub = df[df[legal].map(is_gd_legal)].copy()
            if sub.empty:
                continue
            int_col = _pick_col(df.columns, INT_COLS)
            if int_col is not None:
                flag = sub[int_col].astype(str).str.strip().isin(INTERNAL_VALUES)
                # ① 公司级：只要出现过内部交易标记 → 整家公司排除（按匹配键记录）
                internal_companies |= key_set(sub.loc[flag, cust].astype(str).str.strip())
                # ② 行级：内部交易行本身也不计入行数/金额
                sub = sub[~flag]
            if sub.empty:
                continue
            amt = pd.to_numeric(sub.get("金额"), errors="coerce").fillna(0) if "金额" in sub.columns else 0
            sub = sub.assign(_amt=amt)
            for name, g in sub.groupby(sub[cust].astype(str).str.strip()):
                if not name:
                    continue
                rec = found.setdefault(name, {"来源": [], "行数": 0, "金额": 0.0})
                rec["来源"].append(f"运营端-{ft}")
                rec["行数"] += len(g)
                rec["金额"] += float(g["_amt"].sum())

    # 排除判定按匹配键（全角半角/空白差异不影响），展示/返回仍是原客户名
    drop_keys = (internal_companies | excluded) & key_set(found)
    drop = [name for name in sorted(found) if match_key(name) in drop_keys]
    for name in drop:
        print("  ⏭️  公司级排除（内部交易/排除名单）: %s" % name)
        found.pop(name, None)
    return found


def collect_from_financial_gd(cfg) -> dict[str, dict]:
    """财务端「广东公司.xlsx」：整表法人 = 广东汽车检测中心（配置 `法人主体`）

    2026-11-02 起与运营端一并作为候选来源（按 `业务规则.json → 广东自有归入._说明`）：
      · 独立格式来源：金额单位万元（`金额乘数`）、事业部固定、不过客户白名单
        —— 只贡献"客户名"，金额仅用于日志概览
      · 客户列按 `数据源.财务端.广东公司.列映射.客户` 的候选取
      · 法人按配置整表判定：配置的 `法人主体` 不是广东汽车检测中心 → 整表跳过
      · 内部交易列若存在 → 公司级排除（与运营端同口径）
      · **不按日期筛**：与运营端一致，只看"表里出现过这家客户"
    """
    src_config = ((cfg.get("数据源") or {}).get("财务端") or {}).get("广东公司") or {}
    if not src_config:
        return {}
    if not is_gd_legal(src_config.get("法人主体", GD_LEGAL)):
        print("  ⏭️  广东公司：配置的法人主体不是广东汽车检测中心，跳过该来源")
        return {}

    try:
        file_path = get_data_path(cfg, "财务端", "广东公司")
    except Exception as e:
        print(f"  ⚠️ 广东公司路径不可用，跳过该来源: {e}")
        return {}
    if not file_path.exists():
        print(f"  ⚠️ 广东公司文件不存在，跳过该来源: {file_path.name}")
        return {}

    col_map = src_config.get("列映射") or {}
    cust_cols = col_map.get("客户") or CUST_COLS
    amt_cols = col_map.get("金额") or ["金额"]
    excluded = _load_excluded_keys()

    found: dict[str, dict] = {}
    internal_companies: set[str] = set()

    for ft in ["收入", "回款"]:
        sheets = (src_config.get("Sheet") or {}).get(ft) or []
        sheet = sheets[0] if sheets else ft
        try:
            df = pd.read_excel(file_path, sheet_name=sheet,
                               engine=src_config.get("引擎", "openpyxl"))
        except Exception as e:
            print(f"  ⚠️ 广东公司[{sheet}] 读取失败，跳过: {e}")
            continue

        cust = _pick_col(df.columns, cust_cols)
        if not cust:
            continue
        sub = df
        int_col = _pick_col(df.columns, INT_COLS)
        if int_col is not None:
            flag = sub[int_col].astype(str).str.strip().isin(INTERNAL_VALUES)
            # ① 公司级：只要出现过内部交易标记 → 整家公司排除
            internal_companies |= key_set(sub.loc[flag, cust].astype(str).str.strip())
            sub = sub[~flag]
        if sub.empty:
            continue

        amt_col = _pick_col(sub.columns, amt_cols)
        mult = _amount_multiplier_of(src_config, ft)
        amt = (pd.to_numeric(sub[amt_col], errors="coerce").fillna(0) * mult) if amt_col else 0
        sub = sub.assign(_amt=amt)
        for name, g in sub.groupby(sub[cust].astype(str).str.strip()):
            if not name:
                continue
            rec = found.setdefault(name, {"来源": [], "行数": 0, "金额": 0.0})
            rec["来源"].append(f"广东公司-{ft}")
            rec["行数"] += len(g)
            rec["金额"] += float(g["_amt"].sum())

    # 排除判定按匹配键（全角半角/空白差异不影响），展示/返回仍是原客户名
    drop_keys = (internal_companies | excluded) & key_set(found)
    for name in [n for n in sorted(found) if match_key(n) in drop_keys]:
        print("  ⏭️  公司级排除（内部交易/排除名单）: %s" % name)
        found.pop(name, None)
    return found


def collect_candidates(cfg) -> dict[str, dict]:
    """候选来源 = 运营端（收入/回款 .xls）+ 财务端「广东公司.xlsx」

    2026-11-02：原先只扫运营端，与 `业务规则.json → 广东自有归入._说明`
    （"运营端/广东公司 中 法人=广东汽车检测中心 且无任何销售归属的客户"）不一致，
    按该说明补齐广东公司来源。两个来源里的同一客户合并统计（来源/行数/金额累加）。
    """
    found = collect_from_operations(cfg)
    for name, rec in collect_from_financial_gd(cfg).items():
        cur = found.setdefault(name, {"来源": [], "行数": 0, "金额": 0.0})
        for src in rec["来源"]:
            if src not in cur["来源"]:
                cur["来源"].append(src)
        cur["行数"] += rec["行数"]
        cur["金额"] += rec["金额"]
    return found


def plan_additions(cands: dict[str, dict], configured: set[str], state: dict) -> tuple[list[tuple[str, dict]], list[str]]:
    """返回 (需要新增的 [(客户名, 概览)], 被跳过的原因列表)"""
    todo, skipped = [], []
    # 已配置 / 曾经归入 / 黑名单 一律按匹配键判定（全角半角、空白差异不影响，2026-09-29）
    configured_keys = {match_key(x) for x in configured}
    state_keys = {match_key(x) for x in state}
    blacklist_keys = {match_key(x) for x in BLACKLIST_NAMES}
    for name, rec in sorted(cands.items(), key=lambda kv: -kv[1]["金额"]):
        key = match_key(name)
        if key in configured_keys or key in state_keys:
            continue
        if key in blacklist_keys:
            skipped.append(f"{name}（自身法人/占位行，已排除）")
            continue
        if len(name) < MIN_NAME_LEN:
            skipped.append(f"{name}（名字过短，疑似占位行，已排除）")
            continue
        todo.append((name, rec))
    return todo, skipped


# ──────────────────────────────────────────────────────────────
# 写回 Excel
# ──────────────────────────────────────────────────────────────
def append_to_excel(names: list[str], note: str) -> int:
    import openpyxl
    from copy import copy
    from openpyxl.styles import Alignment

    from scripts.sheet_style import save_workbook   # 确定性保存（固定属性 + 规范化 zip）

    wb = openpyxl.load_workbook(EXCEL_PATH)
    if "销售归属" not in wb.sheetnames:
        raise RuntimeError("配置编辑器缺少「销售归属」sheet")
    ws = wb["销售归属"]
    # 已存在判定按匹配键（同一家公司写成全角/半角括号时不再重复追加，2026-09-29）
    existing_keys = {match_key(r[1]) for r in ws.iter_rows(min_row=2, values_only=True) if r[1]}

    rows = []
    for name in names:
        if match_key(name) in existing_keys:
            continue
        for dept in DEPTS:
            rows.append([GD_PARENT, name, "收入/回款", dept, GD_SALES, 1.0, note])
    if not rows:
        return 0

    last = ws.max_row
    for i, row in enumerate(rows, start=1):
        ws.append(row)
        for c in range(1, 8):
            try:
                ws.cell(row=last + i, column=c)._style = copy(ws.cell(row=last, column=c)._style)
            except Exception:
                pass
            ws.cell(row=last + i, column=c).alignment = Alignment(horizontal="left", vertical="center")
    save_workbook(wb, EXCEL_PATH)
    return len(rows)


# ──────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="扫描并自动归入「广东自有客户」（法人=广东汽车检测中心 且无销售归属）")
    ap.add_argument("--write", action="store_true", help="写回配置编辑器 Excel + 状态文件（默认只扫描）")
    args = ap.parse_args(argv)

    cfg = load_config()
    cands = collect_candidates(cfg)
    configured = load_config_subs()
    state = load_state()

    todo, skipped = plan_additions(cands, configured, state)
    print("=" * 66)
    print("广东自有客户 · 自动归入扫描（法人=%s，公司级判定，已排除内部交易）" % GD_LEGAL)
    print("  候选客户 %d 家 | 已在配置 %d 家 | 曾自动归入 %d 家 | 本次需新增 %d 家"
          % (len(cands), len([c for c in cands if c in configured]), len(state), len(todo)))
    for s in skipped:
        print("  跳过: %s" % s)
    if not todo:
        print("  ✅ 无新增（无需改动配置）")
        return 0

    print("  本次新增清单：")
    for name, rec in todo:
        print("    - %-42s %s  行数%2d  金额 %8.2f 万" % (
            name, "/".join(sorted(set(rec["来源"]))), rec["行数"], rec["金额"] / 10000))

    if not args.write:
        print("\n（未写回。加 --write 即写入「配置编辑器.xlsx → 销售归属」并记录状态）")
        return 0

    note = "%s 自动归入（运营端/广东公司 法人=广东汽车检测中心 且无销售归属）" % datetime.now().strftime("%Y-%m-%d")
    n_rows = append_to_excel([n for n, _ in todo], note)
    today = datetime.now().strftime("%Y-%m-%d")
    for name, _ in todo:
        state[name] = today
    save_state(state)
    print("\n  ✅ 已写入 Excel「销售归属」+%d 行（%d 家 × 4 部门），状态文件已更新"
          % (n_rows, len(todo)))
    print("     下一步：运行配置同步（Excel → JSON）后即生效（流水线会自动做）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
