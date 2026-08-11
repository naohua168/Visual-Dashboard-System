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

from ..core.config import load_config, get_output_path, BASE_DIR
from ..core.utils import log_step

# 4 大事业部
DEPARTMENTS = ["检测", "信息", "能源", "海外"]

# 比亚迪汽车工业有限公司 下属需按法人主体区分销售的子公司
# 规则：仅当某子公司同时存在 "广东汽车检测中心" 法人主体（→黄浩浩）与
#       非 "广东汽车检测中心" 法人主体（→周涵林）时，才做此区分；
#       单边存在时保持原拆分结果不动。
BYD_SUB_COMPANIES = [
    "汕尾比亚迪实业有限公司",
    "长沙市比亚迪汽车有限公司",
    "衡阳比亚迪实业有限公司",
    "韶关比亚迪实业有限公司",
    "西安比亚迪汽车零部件有限公司",
    "合肥比亚迪汽车有限公司",
    "深圳比亚迪汽车实业有限公司",
    "常州比亚迪汽车有限公司",
    "抚州比亚迪实业有限公司",
    "济南比亚迪汽车有限公司",
    "郑州比亚迪汽车有限公司",
]
BYD_GD_LEGAL = "广东汽车检测中心有限公司"   # 广东主体 → 黄浩浩
BYD_GD_SALES = "黄浩浩"
BYD_OTHER_SALES = "周涵林"                 # 非广东主体 → 周涵林


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

    cust_col = split_df["客户"].astype(str).str.strip()
    legal_col = split_df["法人主体"].astype(str).str.strip()

    affected = 0
    for cust in overlap:
        mask = cust_col == cust
        if not mask.any():
            continue
        is_gd = legal_col[mask] == BYD_GD_LEGAL
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
    """加载客户销售归属.json，扁平化为 {客户名: {父组名: {收入: {部门: {销售: 比例}}, 回款: ...}}}。

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
            key = sub_name.strip()
            flat.setdefault(key, {})[parent] = sub_data

    log_step("销售引擎", f"加载 {len(flat)} 条客户→销售映射")
    return flat


# 广东法人主体 → 归属"广东自有客户"父组（其余法人主体归其他父组）
GD_LEGAL_ENTITY = "广东汽车检测中心有限公司"
GD_PARENT_GROUP = "广东自有客户"


def _select_parent_group(cust_groups: dict[str, dict], legal_entity: str) -> dict:
    """同一客户出现在多个父组时，按法人主体选择父组配置。

    - 法人主体 == 广东汽车检测中心有限公司 → 取"广东自有客户"组
    - 其他 → 优先取"零部件客户"组；若无则取第一个组
    """
    if len(cust_groups) == 1:
        return next(iter(cust_groups.values()))

    if legal_entity == GD_LEGAL_ENTITY and GD_PARENT_GROUP in cust_groups:
        return cust_groups[GD_PARENT_GROUP]
    if "零部件客户" in cust_groups:
        return cust_groups["零部件客户"]
    return next(iter(cust_groups.values()))


def _load_byd_overlap() -> set[str]:
    """扫描原始 JSON，找出 BYD_SUB_COMPANIES 列表中隶属黄浩浩的子公司。
    只要黄浩浩负责，就触发法人区分：广东汽车检测中心→黄浩浩，其他→周涵林。"""
    path = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"
    if not path.exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sales_by_cust: dict[str, set[str]] = {}
    for parent, group in data.get("客户归属", {}).items():
        for sub_name, sub_data in group.get("子公司", {}).items():
            key = sub_name.strip()
            if key not in BYD_SUB_COMPANIES:
                continue
            all_s = sales_by_cust.setdefault(key, set())
            for metric in ("收入", "回款"):
                for dept, rats in sub_data.get(metric, {}).items():
                    all_s.update(rats.keys())

    overlap: set[str] = set()
    for cust, sales_set in sales_by_cust.items():
        if BYD_GD_SALES in sales_set:
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

    # 排除内部交易公司（客户=自身，与清洗层排除名单一致）
    excluded = _load_excluded_companies()
    if excluded and "客户" in df.columns:
        before = len(df)
        df = df[~df["客户"].astype(str).str.strip().isin(excluded)].copy()
        if before - len(df) > 0:
            log_step(f"销售{file_type}", f"排除内部交易客户: 丢弃{before - len(df)}行", "OK")

    if not attribution:
        log_step(f"销售{file_type}", "无归属映射，跳过拆分", "WARN")
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
        customer = str(row.get("客户", "")).strip()
        department = str(row.get("事业部", "")).strip()
        amount = float(row.get("金额", 0))

        # 查客户映射（可能多个父组）
        cust_groups = attribution.get(customer)
        if not cust_groups:
            # 未匹配 → 保留原始行，销售为空
            row_dict = row.to_dict()
            row_dict["销售"] = ""
            results.append(row_dict)
            unmatched += 1
            continue

        # 同一客户在多个父组（如 广东自有/零部件 重叠）时按法人主体选组
        legal_entity = str(row.get("法人主体", "")).strip()
        cust_data = _select_parent_group(cust_groups, legal_entity)

        # 取收入/回款的部门比例
        metric_ratios = cust_data.get(metric_key, {})
        dept_ratios = metric_ratios.get(department, {})

        if not dept_ratios:
            # 该部门无比例 → 保留原始行
            row_dict = row.to_dict()
            row_dict["销售"] = ""
            results.append(row_dict)
            unmatched += 1
            continue

        # 按比例拆分
        for sales_name, ratio in dept_ratios.items():
            allocated = amount * float(ratio)
            r = row.to_dict()
            r["销售"] = sales_name
            r["金额"] = allocated
            results.append(r)

        matched += 1

    split_df = pd.DataFrame(results)

    # 比亚迪子公司按法人主体区分销售（黄浩浩/周涵林，仅配置重名时处理）
    split_df = _apply_byd_sales_override(split_df)

    split_total = split_df["金额"].sum()

    # 统计
    unique_sales = split_df.loc[split_df["销售"] != "", "销售"].unique()
    log_step(f"销售{file_type}", f"拆分后: {len(split_df)}行 (匹配{matched}行, 未匹配{unmatched}行)")
    log_step(f"销售{file_type}", f"销售人数: {len(unique_sales)}人")
    log_step(f"销售{file_type}", f"金额合计: {split_total:,.2f}")

    # 总额校验
    diff = abs(total_amount - split_total)
    if diff < 1e-6:
        log_step(f"销售{file_type}", f"总额校验: {total_amount:,.2f} = {split_total:,.2f} 完全一致", "OK")
    else:
        log_step(f"销售{file_type}", f"总额校验: 差异 {diff:,.6f}", "WARN")

    # 写入
    output_key = f"销售{file_type}"
    output_path = get_output_path(config, output_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    split_df = split_df.fillna("")
    split_df.to_excel(output_path, index=False)
    log_step(f"销售{file_type}", f"写入: {output_path}", "OK")

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
    return results


if __name__ == "__main__":
    main()
