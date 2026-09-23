"""扫描「广东自有客户」应自动归入的公司，并写回配置编辑器（Excel）

口径（2026-09-21 用户确认）：
  · 法人主体 = 广东汽车检测中心有限公司（运营端看的 法人主体/核算单位/所属单位 列；
    财务端「广东公司.xlsx」整表视为该法人）
  · **不属于任何销售**：客户名在 `客户销售归属.json` 的所有父组里都没出现过（公司级判定）
  · **公司级**排除内部交易（2026-09-22 用户口径）：只要该公司在运营端有**任意一行**内部交易标记
    （`是否属于内部单位/内部款项` == 是），或出现在内部交易排除名单
    （`部门事业部映射.json → excluded_internal_companies`）→ **整家公司不进入候选**
  → 追加到 `config/配置编辑器.xlsx` 的「销售归属」sheet：
     母公司=广东自有客户 / 指标=收入,回款 / 部门=检测,信息,能源,海外 / 销售=黎国键 / 比例=1

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

from engine.core.config import get_data_path, load_config  # noqa: E402

GD_LEGAL = "广东汽车检测中心有限公司"
GD_PARENT = "广东自有客户"
GD_SALES = "黎国键"
DEPTS = ["检测", "信息", "能源", "海外"]
EXCEL_PATH = BASE_DIR / "config" / "配置编辑器.xlsx"
ATTR_PATH = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
STATE_PATH = BASE_DIR / "data" / "mappings" / "广东自有" / "已自动归入.json"

LEGAL_COLS = ["法人主体", "核算单位", "所属单位"]
CUST_COLS = ["客户", "客户名称"]
INT_COLS = [
    "是否属于内部交易", "是否属于内部单位", "是否内部交易", "内部交易",
    "是否属于内部款项", "是否内部款项",
]
INTERNAL_VALUES = {"是", "内部", "Y", "y", "√"}

# 明显不是"客户"的名字（自身法人名 / 源表占位行 / 汇总行）→ 不写入销售归属
BLACKLIST_NAMES = {
    "广东公司",
    "广东汽车检测中心有限公司",
    "南方（韶关）智能网联新能源汽车试验检测中心有限公司",
    "南方(韶关)智能网联新能源汽车试验检测中心有限公司",
    "合计", "小计", "总计", "其他", "无", "内部", "内部交易",
}
MIN_NAME_LEN = 5


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
    excluded: set[str] = set()
    try:
        p = BASE_DIR / "data" / "mappings" / "部门事业部映射" / "部门事业部映射.json"
        raw = json.loads(p.read_text(encoding="utf-8")).get("excluded_internal_companies", {})
        items = raw if isinstance(raw, list) else raw.get("companies", [])
        excluded = {str(x).strip() for x in items}
    except Exception:
        excluded = set()

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
            sub = df[df[legal].astype(str).str.strip() == GD_LEGAL].copy()
            if sub.empty:
                continue
            int_col = _pick_col(df.columns, INT_COLS)
            if int_col is not None:
                flag = sub[int_col].astype(str).str.strip().isin(INTERNAL_VALUES)
                # ① 公司级：只要出现过内部交易标记 → 整家公司排除
                internal_companies |= set(sub.loc[flag, cust].astype(str).str.strip())
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

    drop = (internal_companies | excluded) & set(found)
    for name in sorted(drop):
        print("  ⏭️  公司级排除（内部交易/排除名单）: %s" % name)
    for name in drop:
        found.pop(name, None)
    return found


def collect_from_guangdong(cfg) -> dict[str, dict]:
    """财务端 广东公司.xlsx：整表视为广东法人（该文件无 法人主体 列）"""
    found: dict[str, dict] = {}
    conf = cfg["数据源"]["财务端"]["广东公司"]
    try:
        path = get_data_path(cfg, "财务端", "广东公司")
    except Exception:
        return found
    for ft in ["收入", "回款"]:
        sh = (conf["Sheet"].get(ft) or [None])[0]
        if not sh:
            continue
        try:
            df = pd.read_excel(path, sheet_name=sh, engine=conf.get("引擎", "openpyxl"))
        except Exception:
            continue
        cust = _pick_col(df.columns, CUST_COLS)
        if not cust:
            continue
        amt = pd.to_numeric(df.get("金额"), errors="coerce").fillna(0) * 10000 if "金额" in df.columns else 0
        df = df.assign(_amt=amt)
        for name, g in df.groupby(df[cust].astype(str).str.strip()):
            if not name:
                continue
            rec = found.setdefault(name, {"来源": [], "行数": 0, "金额": 0.0})
            rec["来源"].append(f"广东公司-{ft}")
            rec["行数"] += len(g)
            rec["金额"] += float(g["_amt"].sum())
    return found


def collect_candidates(cfg) -> dict[str, dict]:
    """候选来源 = **只扫运营端**（用户口径 2026-09-21：“运营端收入回款表里出现的”）

    ⚠️ 财务端「广东公司.xlsx」**不参与**判定：
        它是独立格式来源、口径与运营端不同，纳入会把"当期窗口外 / 其它法人"的客户
        也带进来（实测：上海北汇信息科技有限公司 因此被误加，并牵连出韶关归属问题）。
        如需把该来源的客户也归入，请手工在「配置编辑器.xlsx → 销售归属」里添加。
    """
    return collect_from_operations(cfg)


def plan_additions(cands: dict[str, dict], configured: set[str], state: dict) -> tuple[list[tuple[str, dict]], list[str]]:
    """返回 (需要新增的 [(客户名, 概览)], 被跳过的原因列表)"""
    todo, skipped = [], []
    for name, rec in sorted(cands.items(), key=lambda kv: -kv[1]["金额"]):
        if name in configured or name in state:
            continue
        if name in BLACKLIST_NAMES:
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

    wb = openpyxl.load_workbook(EXCEL_PATH)
    if "销售归属" not in wb.sheetnames:
        raise RuntimeError("配置编辑器缺少「销售归属」sheet")
    ws = wb["销售归属"]
    existing = {str(r[1]).strip() for r in ws.iter_rows(min_row=2, values_only=True) if r[1]}

    rows = []
    for name in names:
        if name in existing:
            continue
        for dept in DEPTS:
            rows.append([GD_PARENT, name, "收入,回款", dept, GD_SALES, 1.0, note])
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
    wb.save(EXCEL_PATH)
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
