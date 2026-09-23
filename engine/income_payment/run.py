"""
收入/回款清洗主入口 — 三路输出

数据来源说明：
  - 财务端（收入.xlsx/回款.xlsx/广东公司/湖南公司）：ERP系统导出，**当月数据**
  - 运营端（收入.xls/回款.xls）：运营系统导出，**当年1月至上月的累计数据**
    其中"1-4月"为1~4月合计，"5月"为5月单月

三路输出：
  1. 月收入/月回款          ← 仅财务端数据（当月）
  2. 季度累计收入/季度累计回款  ← 财务端 + 运营端中截止当季末的数据
  3. 当年累计收入/当年累计回款  ← 财务端 + 运营端全部数据（当年累计）

  同时保持兼容输出：收入/回款 = 当年累计

用法:
    python -m engine.income_payment.run              # 清洗收入+回款
    python -m engine.income_payment.run --type=收入   # 只清洗收入
    python -m engine.income_payment.run --type=回款   # 只清洗回款
"""
from __future__ import annotations

import re
import sys
from datetime import datetime

import pandas as pd

from ..core.config import (
    load_config,
    get_output_path,
    load_clean_params,
    get_quarterly_time_range,
)
from ..core.utils import log_step
from .financial import clean_financial
from .operations import clean_operations


def _parse_ops_date(s) -> str | None:
    """解析运营端日期原文，返回标准化的月份标签

    "1-4月" → "2026-04"（取末月，用于季度筛选）
    "5月" → "2026-05"
    具体日期 → 截取到月如 "2026-06"
    """
    if pd.isna(s):
        return None
    s = str(s).strip()
    m = re.match(r"(\d{1,2})-(\d{1,2})月?$", s)
    if m:
        e_year = datetime.now().year
        return f"{e_year}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{1,2})月?$", s)
    if m:
        e_year = datetime.now().year
        return f"{e_year}-{int(m.group(1)):02d}"
    try:
        return pd.Timestamp(s).strftime("%Y-%m")
    except (ValueError, TypeError):
        return None


def _filter_by_date_range(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """按日期范围筛选数据"""
    if len(df) == 0 or "日期" not in df.columns:
        return df.copy()
    dates = pd.to_datetime(df["日期"], errors="coerce")
    mask = dates.notna() & (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
    return df[mask].copy()


def _write_output(df: pd.DataFrame, output_key: str, config: dict, label: str):
    """写入输出文件

    ⚠️ 输出 Excel 若正被 Excel/WPS 打开 → PermissionError（WinError 13）。
    这里给出明确提示并以退出码 3 终止，避免抛裸异常让人难定位。
    """
    path = get_output_path(config, output_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df.fillna("")
    try:
        df.to_excel(path, index=False)
    except PermissionError as e:
        log_step(
            label,
            f"❌ 写入失败：{path} 正被 Excel/WPS 等程序占用 → 请关闭该文件后重跑",
            "ERROR",
        )
        raise SystemExit(3) from e
    log_step(label, f"写入: {path} ({len(df)}行, 金额{df['金额'].sum():,.2f})", "OK")


def _get_settle_mode(config: dict) -> str:
    """读取结算模式：'月底结算' / '常规'（默认常规）"""
    try:
        tr = config.get("时间范围", {})
        mode = (tr.get("结算模式", {}) or {}).get("值", "常规")
        return mode if mode in ("月底结算", "常规") else "常规"
    except Exception:
        return "常规"


def run_clean(file_type, config=None):
    """清洗单个表（收入或回款），三路输出

    结算模式影响：
      - 常规:      当年累计/季度累计 = 财务端(当月) + 运营端(当年累计)
      - 月底结算:  运营端已是完整年度累计(含当月) → 当年累计/季度累计 = 仅运营端,
                   不再叠加财务端(避免当月重复)；财务端仍用于月数据(月度达成页)。
    """
    if config is None:
        config = load_config()

    settle_mode = _get_settle_mode(config)
    is_month_end = settle_mode == "月底结算"

    # 使用统一的参数加载入口
    params = load_clean_params(config)
    mapper = params["mapper"]
    matcher = params["matcher"]
    fin_range = params["fin_range"]
    annual_range = params["annual_range"]

    log_step("系统", f"客户白名单: {matcher.count}个客户")
    log_step("系统", f"财务端时间范围: {fin_range} (mode={fin_range.get('_mode', 'static')})")
    log_step("系统", f"年度累计上限: {annual_range['end_date']}")
    log_step("系统", f"结算模式: {settle_mode}" + (" → 当年累计/季度累计=仅运营端" if is_month_end else " → 当年累计/季度累计=财务端+运营端"))

    # ── Phase 1: 财务端（当月数据） ──
    df_financial = clean_financial(config, mapper, matcher, file_type, fin_range)
    log_step(f"财务端{file_type}", f"财务端数据 = {len(df_financial)}行, 金额{df_financial['金额'].sum():,.2f}（当月）")

    # ── Phase 2: 运营端（当年累计，含1-4月合计+5月…） ──
    df_operations = clean_operations(config, mapper, matcher, file_type)
    log_step(f"运营端{file_type}", f"运营端数据 = {len(df_operations)}行, 金额{df_operations['金额'].sum():,.2f}（当年累计）")

    # ── Phase 3: 三路合并输出 ──
    print(f"\n{'='*50}")
    print(f"  三路合并输出: {file_type}")
    print(f"{'='*50}")

    # ---- 3a. 月数据：仅财务端 ----
    df_monthly = df_financial.copy()
    log_step(file_type, f"月{file_type}: {len(df_monthly)}行（仅财务端）")
    _write_output(df_monthly, f"月{file_type}", config, f"月{file_type}")

    # ---- 3b. 当年累计（按年度累计 end_date 上限裁剪）----
    df_ops_annual = _filter_by_date_range(df_operations, annual_range["start_date"], annual_range["end_date"])
    if is_month_end:
        # 月底结算：运营端=完整年度累计(含当月)，直接用，不叠加财务端(否则当月重复)
        df_yearly_cumulative = df_ops_annual.copy()
        log_step(file_type,
                 f"当年累计{file_type}[月底结算]: 仅运营端 {len(df_ops_annual)}行(/{len(df_operations)}全量) "
                 f"，财务端{len(df_financial)}行仅用于月数据", "OK")
    else:
        df_yearly_cumulative = pd.concat([df_financial, df_ops_annual], ignore_index=True)
        log_step(file_type,
                 f"当年累计{file_type}[常规]: 财务{len(df_financial)} + 运营{len(df_ops_annual)}(/ {len(df_operations)}全量) = {len(df_yearly_cumulative)}行")
    _write_output(df_yearly_cumulative, f"当年累计{file_type}", config, f"当年累计{file_type}")

    # ---- 3c. 季度累计：按配置时间范围筛选 ----
    q_range = get_quarterly_time_range(config)
    df_ops_quarter = _filter_by_date_range(df_operations, q_range["start_date"], q_range["end_date"])
    if is_month_end:
        df_quarterly = df_ops_quarter.copy()
        log_step(file_type,
                 f"季度累计范围[月底结算]: {q_range['start_date']} ~ {q_range['end_date']}, 仅运营端 {len(df_quarterly)}行", "OK")
    else:
        df_quarterly = pd.concat([df_financial, df_ops_quarter], ignore_index=True)
        q_mode = q_range.get("_mode", "static")
        log_step(file_type, f"季度累计范围[{q_mode}]: {q_range['start_date']} ~ {q_range['end_date']}, {len(df_quarterly)}行")
    _write_output(df_quarterly, f"季度累计{file_type}", config, f"季度累计{file_type}")

    # 汇总
    log_step(file_type, f"事业部分布: {df_yearly_cumulative['事业部'].value_counts().to_dict()}")
    log_step(file_type, f"金额合计: {df_yearly_cumulative['金额'].sum():,.2f}")

    return df_yearly_cumulative


def main():
    args = sys.argv[1:]
    file_types = []

    for arg in args:
        if arg.startswith("--type="):
            file_types = [arg.split("=")[1]]

    if not file_types:
        file_types = ["收入", "回款"]

    print(f"\n{'#'*60}")
    print(f"  数据清洗引擎 -- 三路输出模式")
    print(f"  清洗对象: {', '.join(file_types)}")
    print(f"  时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    config = load_config()
    settle_mode = _get_settle_mode(config)
    yearly_desc = "仅运营端" if settle_mode == "月底结算" else "财务端+运营端"
    results = {}
    for ft in file_types:
        results[ft] = run_clean(ft, config)

    print(f"\n{'#'*60}")
    print(f"  清洗完成 — 三路输出汇总（结算模式: {settle_mode}）")
    print(f"{'#'*60}")
    for ft, df in results.items():
        print(f"  {ft}: {len(df)}行, 金额{df['金额'].sum():,.2f}")
        print(f"    ├─ 月{ft}: 仅财务端当月")
        print(f"    ├─ 季度累计{ft}: {yearly_desc}")
        print(f"    └─ 当年累计{ft}: {yearly_desc}")
    print(f"{'#'*60}")
    return results


if __name__ == "__main__":
    main()
