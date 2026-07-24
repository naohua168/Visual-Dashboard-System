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
from pathlib import Path

import pandas as pd

from ..core.config import load_config, load_mapping, get_output_path, get_time_range, load_clean_params
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


def _filter_ops_by_quarter(df: pd.DataFrame) -> pd.DataFrame:
    """从运营端数据中筛选出当前季度累计部分

    运营端数据为当年1月至上月的累计数据（如"1-4月"合计+"5月"单月）。
    季度累计 = 截止当季末的数据。

    实现方式：
      1. 从系统日期推断当前数据月份（dynamic模式=上月）
      2. 确定当前季度范围（Q1/Q2/Q3/Q4）
      3. 逐行取日期列的月份，保留月份在当季范围内的行
    """
    if len(df) == 0:
        return df.copy()

    # dynamic 模式取上月作为财务端数据月份
    cur_data_month = datetime.now().month - 1
    if cur_data_month <= 0:
        cur_data_month = 12

    # 当前季度范围（Q1:1-3, Q2:4-6, Q3:7-9, Q4:10-12）
    q_start = ((cur_data_month - 1) // 3) * 3 + 1
    q_end = q_start + 2

    if "日期" not in df.columns:
        return df.copy()

    # 日期列内容为 Timestamp（operations._parse_ops_date 已返回 END month）
    months = pd.to_datetime(df["日期"], errors="coerce").dt.month
    mask = months.notna() & (months >= q_start) & (months <= q_end)
    filtered = df[mask].copy()
    return filtered


def _write_output(df: pd.DataFrame, output_key: str, config: dict, label: str):
    """写入输出文件"""
    path = get_output_path(config, output_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    df = df.fillna("")
    df.to_excel(path, index=False)
    log_step(label, f"写入: {path} ({len(df)}行, 金额{df['金额'].sum():,.2f})", "OK")


def run_clean(file_type, config=None):
    """清洗单个表（收入或回款），三路输出"""
    if config is None:
        config = load_config()

    # 使用统一的参数加载入口
    params = load_clean_params(config)
    mapper = params["mapper"]
    matcher = params["matcher"]
    fin_range = params["fin_range"]
    ops_fixed_date = params["ops_fixed_date"]

    log_step("系统", f"客户白名单: {matcher.count}个客户")
    log_step("系统", f"财务端时间范围: {fin_range}")
    log_step("系统", f"运营端固定日期: {ops_fixed_date}")

    # ── Phase 1: 财务端（当月数据） ──
    df_financial = clean_financial(config, mapper, matcher, file_type, fin_range)
    log_step(f"财务端{file_type}", f"财务端数据 = {len(df_financial)}行, 金额{df_financial['金额'].sum():,.2f}（当月）")

    # ── Phase 2: 运营端（当年累计，含1-4月合计+5月） ──
    df_operations = clean_operations(config, mapper, matcher, file_type, ops_fixed_date)
    log_step(f"运营端{file_type}", f"运营端数据 = {len(df_operations)}行, 金额{df_operations['金额'].sum():,.2f}（1-5月累计）")

    # ── Phase 3: 三路合并输出 ──
    print(f"\n{'='*50}")
    print(f"  三路合并输出: {file_type}")
    print(f"{'='*50}")

    # ---- 3a. 月数据：仅财务端 ----
    df_monthly = df_financial.copy()
    log_step(file_type, f"月{file_type}: {len(df_monthly)}行（仅财务端）")
    _write_output(df_monthly, f"月{file_type}", config, f"月{file_type}")

    # ---- 3b. 当年累计：财务端 + 运营端全部 ----
    df_yearly_cumulative = pd.concat([df_financial, df_operations], ignore_index=True)
    log_step(file_type, f"当年累计{file_type}: 财务{len(df_financial)} + 运营{len(df_operations)} = {len(df_yearly_cumulative)}行")
    _write_output(df_yearly_cumulative, f"当年累计{file_type}", config, f"当年累计{file_type}")

    # ---- 3c. 季度累计：财务端 + 运营端截止当季末 ----
    df_ops_quarter = _filter_ops_by_quarter(df_operations)
    df_quarterly = pd.concat([df_financial, df_ops_quarter], ignore_index=True)
    log_step(file_type, f"季度累计{file_type}: {len(df_quarterly)}行")
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
    results = {}
    for ft in file_types:
        results[ft] = run_clean(ft, config)

    print(f"\n{'#'*60}")
    print(f"  清洗完成 — 三路输出汇总")
    print(f"{'#'*60}")
    for ft, df in results.items():
        print(f"  {ft}: {len(df)}行, 金额{df['金额'].sum():,.2f}")
        print(f"    ├─ 月{ft}: 仅财务端当月")
        print(f"    ├─ 季度累计{ft}: 财务端+运营端")
        print(f"    └─ 当年累计{ft}: 财务端+运营端")
    print(f"{'#'*60}")
    return results


if __name__ == "__main__":
    main()
