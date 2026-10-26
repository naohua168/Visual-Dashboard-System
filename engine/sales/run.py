# Author: naohua168 <bai_bai168@qq.com>
"""
销售数据引擎 — 基于 客户销售归属.json 按收入/回款分别拆分

用法:
    python -m engine.sales.run              # 处理销售收入+销售回款
    python -m engine.sales.run --type=收入   # 只处理销售收入
    python -m engine.sales.run --type=回款   # 只处理销售回款
"""
import json
import sys

import pandas as pd

from ..core import business_rules as br
from ..core.config import load_config, get_output_path, BASE_DIR
from ..core.diagnostics import note_issue, output_dir, print_summary, write_reports
from ..core.io_utils import ExcelBusyError, save_excel
from ..core.name_key import (
    dup_name_groups,
    format_conflicts,
    key_set,
    match_key,
)
from ..core.business_rules import is_gd_legal
from ..core.utils import log_step, rel_path

# 4 大事业部（列顺序来自 业务规则.json → 部门.列表，2026-09-29）
DEPARTMENTS = br.departments()

# 比亚迪汽车工业有限公司 下属需按法人主体区分销售的子公司
# 规则：仅当某子公司同时存在 "广东汽车检测中心" 法人主体（→黄浩浩）与
#       非 "广东汽车检测中心" 法人主体（→周涵林）时，才做此区分；
#       单边存在时保持原拆分结果不动。
# 2026-09-29：清单 / 销售名 / 法人主体名外置到 `config/清洗配置/业务规则.json`
# （engine/core/business_rules.py 读取，缺项回落到此处等价的内置默认值）；
# 下面这些模块常量保留为别名，供其它模块与测试引用。
BYD_SUB_COMPANIES = br.byd_subs()
BYD_GD_LEGAL = br.legal_gd()                 # 广东主体 → 黄浩浩
BYD_GD_SALES = br.sales_byd_gd()
BYD_OTHER_SALES = br.sales_byd_other()       # 非广东主体 → 周涵林


def _apply_byd_sales_override(split_df: pd.DataFrame) -> pd.DataFrame:
    """比亚迪子公司：当原始配置中同一子公司在不同父级下同时归属于
    黄浩浩和周涵林（重名冲突）时，按法人主体重新分配——
    广东检测中心法人主体→黄浩浩，非广东→周涵林。
    """
    if "客户" not in split_df.columns or "法人主体" not in split_df.columns:
        return split_df

    overlap = _load_byd_overlap()
    if not overlap:
        return split_df

    # 客户名/法人主体都按匹配键比较（全角半角、空白差异不影响判定）
    cust_col = split_df["客户"].map(match_key)
    legal_col = split_df["法人主体"].map(match_key)

    affected = 0
    for cust in overlap:  # overlap 里存的是匹配键
        mask = cust_col == cust
        if not mask.any():
            continue
        is_gd = legal_col[mask].map(is_gd_legal)
        split_df.loc[mask & is_gd, "销售"] = BYD_GD_SALES
        split_df.loc[mask & ~is_gd, "销售"] = BYD_OTHER_SALES
        affected += int(mask.sum())

    if affected > 0:
        log_step("销售引擎", f"比亚迪子公司按法人主体区分销售: 调整{affected}行 "
                             f"（广东主体→{BYD_GD_SALES}, 非广东→{BYD_OTHER_SALES}）", "OK")
    return split_df


def _load_excluded_companies() -> list[str]:
    """加载内部交易排除名单（与清洗层一致）"""
    path = BASE_DIR / "data" / "mappings" / "部门事业部映射" / "部门事业部映射.json"
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            m = json.load(f)
        exc = m.get("excluded_internal_companies", {})
        if isinstance(exc, list):
            return exc
        return exc.get("companies", [])
    except Exception:
        return []


def _load_attribution() -> dict[str, dict[str, dict]]:
    """加载客户销售归属.json，扁平化为 {匹配键: {父组名: {收入: {部门: {销售: 比例}}, 回款: ...}}}。

    键 = `name_key.match_key(子公司名)`：全角半角括号、空白、大小写差异不再导致匹配不上
    （2026-09-29，如 `法雷奥汽车内部控制（深圳）有限公司` vs `... (深圳) ...`）。
    显示名不受影响；撞键时按配置里**先出现的写法**合并匹配，并在日志里提示去合并配置。

    保留父组名：同一客户可能同时出现在多个父组（如"广东自有客户"与"零部件客户"），
    拆分时需按法人主体判断取哪个父组的销售分配。
    """
    path = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
    if not path.exists():
        log_step("销售引擎", "客户销售归属.json 不存在", "WARN")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    flat: dict[str, dict[str, dict]] = {}
    for parent, group in data.get("客户归属", {}).items():
        for sub_name, sub_data in group.get("子公司", {}).items():
            key = match_key(sub_name)
            if not key:
                continue
            flat.setdefault(key, {})[parent] = sub_data

    # 同一家公司写成两遍（仅符号/空白差异）→ 提示人工合并；多组配置（不同父组）不算
    problems = dup_name_groups(data.get("客户归属", {}))
    if problems:
        log_step(
            "销售引擎",
            f"⚠ 归属表存在「同一家公司写成两遍」的条目 {len(problems)} 组"
            f"（匹配按先出现的写法合并，建议合并成一条）: {format_conflicts(problems)}",
            "WARN",
        )
    log_step("销售引擎", f"加载 {len(flat)} 条客户→销售映射")
    return flat


# 广东法人主体 → 归属"广东自有客户"父组（其余法人主体归其他父组）
# 2026-09-29：法人主体名 / 父组名外置到 业务规则.json（这里保留别名，比较走 is_gd_legal）
GD_LEGAL_ENTITY = br.legal_gd()
GD_PARENT_GROUP = br.parent_gd_self()
OTHER_PARENT_GROUP = br.parent_other()


def _find_group(cust_groups: dict[str, dict], name: str) -> str | None:
    """在父组 dict 里按匹配键找组名（忽略全角半角/空白差异）"""
    target = match_key(name)
    for key in cust_groups:
        if match_key(key) == target:
            return key
    return None


def _select_parent_group(cust_groups: dict[str, dict], legal_entity: str) -> tuple[str, dict]:
    """同一客户出现在多个父组时，按法人主体选择父组配置。

    返回 (父组名, 配置)。父组名会写入拆分结果的"母公司"列，供前端按此分组。

    - 法人主体（归一化后）== 广东汽车检测中心有限公司 → 取"广东自有客户"组
    - 其他 → 优先取"零部件客户"组；若无则取第一个组
    """
    if len(cust_groups) == 1:
        only = next(iter(cust_groups.items()))
        return only[0], only[1]

    if is_gd_legal(legal_entity):
        gd = _find_group(cust_groups, GD_PARENT_GROUP)
        if gd:
            return gd, cust_groups[gd]
    other = _find_group(cust_groups, OTHER_PARENT_GROUP)
    if other:
        return other, cust_groups[other]
    first = next(iter(cust_groups.items()))
    return first[0], first[1]


def _load_byd_overlap() -> set[str]:
    """扫描原始 JSON，找出 BYD_SUB_COMPANIES 列表中**同时配置黄浩浩与周涵林**
    （即销售在配置层重合）的子公司。

    仅当这两家公司在 JSON 中都出现（即同一客户在配置里就同时归属黄浩浩和
    周涵林）时，才触发法人区分：广东汽车检测中心→黄浩浩，非广东→周涵林。
    单边配置（仅黄浩浩或仅周涵林）的公司保持原拆分结果不动。
    """
    path = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    byd_keys = key_set(BYD_SUB_COMPANIES)  # 名单与配置都用匹配键比较
    sales_by_cust: dict[str, set[str]] = {}
    for parent, group in data.get("客户归属", {}).items():
        for sub_name, sub_data in group.get("子公司", {}).items():
            key = match_key(sub_name)
            if key not in byd_keys:
                continue
            all_s = sales_by_cust.setdefault(key, set())
            for metric in ("收入", "回款"):
                for dept, rats in sub_data.get(metric, {}).items():
                    all_s.update(rats.keys())

    overlap: set[str] = set()
    for cust, sales_set in sales_by_cust.items():
        # 必须同时配置黄浩浩 + 周涵林才算"销售重合"，才触发法人区分
        if BYD_GD_SALES in sales_set and BYD_OTHER_SALES in sales_set:
            overlap.add(cust)
    return overlap


def run_split(file_type, config=None):
    """按客户销售归属拆分单个表（收入或回款）"""
    if config is None:
        config = load_config()

    # 加载客户→销售映射
    attribution = _load_attribution()

    # 读取已清洗的当年累计数据
    source_key = f"当年累计{file_type}"
    source_folder = BASE_DIR / config["输出"][source_key]
    if source_folder.is_dir():
        xlsx_files = [f for f in source_folder.glob("*.xlsx") if not f.name.startswith("~$")]
        source_path = xlsx_files[0] if xlsx_files else source_folder / f"{source_key}.xlsx"
    else:
        source_path = source_folder

    log_step(f"销售{file_type}", f"读取: {source_path.name}")
    df = pd.read_excel(source_path)
    total_in = len(df)
    total_amount = df["金额"].sum()
    log_step(f"销售{file_type}", f"原始: {total_in}行, 金额{total_amount:,.2f}")

    # 排除内部交易公司（客户=自身，与清洗层排除名单一致；名单/客户名都按匹配键比较）
    excluded = key_set(_load_excluded_companies())
    if excluded and "客户" in df.columns:
        before = len(df)
        df = df[~df["客户"].map(match_key).isin(excluded)].copy()
        if before - len(df) > 0:
            log_step(f"销售{file_type}", f"排除内部交易客户: 丢弃{before - len(df)}行", "OK")

    if not attribution:
        log_step(f"销售{file_type}", "无归属映射，跳过拆分（输出文件不会更新）", "WARN")
        note_issue("WARN", f"销售{file_type}", "无归属映射 → 跳过拆分（销售收入/回款沿用上一期）")
        df["销售"] = ""
        return df

    # 确定查收入的还是回款的
    metric_key = "收入" if file_type == "收入" else "回款"

    print(f"\n{'='*50}")
    print(f"  Phase 3: 销售{file_type}拆分")
    print(f"{'='*50}")

    results = []
    matched = 0
    unmatched = 0

    for _, row in df.iterrows():
        # 客户名经归一化匹配键查表：全角半角括号/空白/大小写差异不再导致漏匹配
        customer = match_key(row.get("客户", ""))
        department = str(row.get("事业部", "")).strip()
        amount = float(row.get("金额", 0))

        # 查客户映射（可能多个父组）
        cust_groups = attribution.get(customer)
        if not cust_groups:
            # 未匹配 → 标记为"待确认"（销售达成页可查看待确认客户明细）
            row_dict = row.to_dict()
            row_dict["销售"] = "待确认"
            row_dict["母公司"] = ""
            results.append(row_dict)
            unmatched += 1
            continue

        # 同一客户在多个父组（如 广东自有/零部件 重叠）时按法人主体选组
        legal_entity = str(row.get("法人主体", "")).strip()
        parent_name, cust_data = _select_parent_group(cust_groups, legal_entity)

        # 「广东自有客户」门控（2026-09-21 用户口径）：
        #   该组只收 法人主体 = 广东汽车检测中心有限公司 的行。
        #   同一客户在其它法人（如 南方韶关）下的行不归销售 → 保持"待确认"，
        #   否则会出现"韶关的行业绩算给了广东自有销售"的口径错配。
        if match_key(parent_name) == match_key(GD_PARENT_GROUP) and not is_gd_legal(legal_entity):
            row_dict = row.to_dict()
            row_dict["销售"] = "待确认"
            row_dict["母公司"] = parent_name
            results.append(row_dict)
            unmatched += 1
            continue

        # 取收入/回款的部门比例
        metric_ratios = cust_data.get(metric_key, {})
        dept_ratios = metric_ratios.get(department, {})

        if not dept_ratios:
            # 该部门无比例 → 标记为"待确认"
            row_dict = row.to_dict()
            row_dict["销售"] = "待确认"
            row_dict["母公司"] = parent_name
            results.append(row_dict)
            unmatched += 1
            continue

        # 按比例拆分
        for sales_name, ratio in dept_ratios.items():
            allocated = amount * float(ratio)
            r = row.to_dict()
            r["销售"] = sales_name
            r["母公司"] = parent_name
            r["金额"] = allocated
            results.append(r)

        matched += 1

    split_df = pd.DataFrame(results)

    # 比亚迪子公司按法人主体区分销售（黄浩浩/周涵林，仅配置重名时处理）
    split_df = _apply_byd_sales_override(split_df)

    split_total = split_df["金额"].sum()

    # 统计（排除待确认）
    unique_sales = split_df.loc[~split_df["销售"].isin(["", "待确认"]), "销售"].unique()
    log_step(f"销售{file_type}", f"拆分后: {len(split_df)}行 (匹配{matched}行, 未匹配{unmatched}行)")
    log_step(f"销售{file_type}", f"销售人数: {len(unique_sales)}人")
    log_step(f"销售{file_type}", f"金额合计: {split_total:,.2f}")

    # 总额校验
    diff = abs(total_amount - split_total)
    if diff < 1e-6:
        log_step(f"销售{file_type}", f"总额校验: {total_amount:,.2f} = {split_total:,.2f} 完全一致", "OK")
    else:
        log_step(f"销售{file_type}", f"总额校验: 差异 {diff:,.6f}", "WARN")

    # 写入（被 Excel 占用 → 友好提示 + 退出码 3）
    output_key = f"销售{file_type}"
    output_path = get_output_path(config, output_key)
    try:
        save_excel(split_df.fillna(""), output_path)
    except ExcelBusyError as e:
        log_step(f"销售{file_type}", f"❌ 写入失败：{e}", "ERROR")
        raise SystemExit(3) from e
    log_step(f"销售{file_type}", f"写入: {rel_path(output_path)}", "OK")

    return split_df


def main():
    args = sys.argv[1:]
    file_types = []

    for arg in args:
        if arg.startswith("--type="):
            file_types = [arg.split("=")[1]]

    if not file_types:
        file_types = ["收入", "回款"]

    print(f"\n{'#'*60}")
    print(f"  销售拆分引擎 — 基于 客户销售归属.json")
    print(f"  处理对象: {', '.join(file_types)}")
    print(f"  时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    config = load_config()
    results = {}
    for ft in file_types:
        results[ft] = run_split(ft, config)

    print(f"\n{'#'*60}")
    print(f"  拆分完成")
    for ft, df in results.items():
        print(f"  销售{ft}: {len(df)}行, 金额{df['金额'].sum():,.2f}")
    print(f"{'#'*60}")

    # 收尾：本步骤的数据质量摘要（写盘 + 打印；最终退出码由 bin/main.py 统一决定）
    for p in write_reports(output_dir(config), step="销售拆分"):
        print(f"  📄 已写入: {p}")
    print_summary("销售拆分 · 数据质量汇总")
    return results


if __name__ == "__main__":
    main()
