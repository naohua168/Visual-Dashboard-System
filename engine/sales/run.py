"""
销售拆分主入口

用法:
    python -m engine.sales.run              # 拆分销售收入+销售回款
    python -m engine.sales.run --type=收入   # 只拆分销售收入
    python -m engine.sales.run --type=回款   # 只拆分销售回款
"""
import json
import sys

import pandas as pd

from ..core.config import load_config, load_mapping, get_output_path, BASE_DIR
from ..core.utils import log_step
from .splitter import SalesSplitter


def run_split(file_type, config=None):
    """拆分单个表（销售收入或销售回款）"""
    if config is None:
        config = load_config()

    # 读取已清洗的收入/回款表（当年累计），从文件夹自动查找xlsx
    source_key = f"当年累计{file_type}"
    if source_key not in config["输出"]:
        log_step(f"销售{file_type}", f"配置中缺少 '{source_key}'，回退到 '{file_type}'", "WARN")
        source_key = file_type
    source_folder = BASE_DIR / config["输出"][source_key]
    # 如果是文件夹，自动查找唯一的xlsx文件
    if source_folder.is_dir():
        xlsx_files = list(source_folder.glob("*.xlsx"))
        if xlsx_files:
            source_path = xlsx_files[0]
        else:
            source_path = source_folder / f"{source_key}.xlsx"
    else:
        source_path = source_folder
    log_step(f"销售{file_type}", f"读取已清洗数据: {source_path.name}")
    df = pd.read_excel(source_path)
    log_step(f"销售{file_type}", f"原始数据: {len(df)}行, 金额{df['金额'].sum():,.2f}")

    # 加载销售规则
    rules_data = load_mapping("客户销售对应规则", config)
    # 加载统称名单，构建子公司→母公司映射（用于规则继承）
    unify_path = BASE_DIR / config["映射文件"]["客户统称名单"]
    subsidiary_to_parent = {}
    if unify_path.exists():
        unify_data = json.loads(unify_path.read_text(encoding="utf-8"))
        company_mapping = unify_data.get("company_mapping", {})
        for parent, subs in company_mapping.items():
            for sub in subs:
                sub_name = str(sub).strip()
                if sub_name != str(parent).strip():
                    subsidiary_to_parent[sub_name] = parent
        log_step(f"销售{file_type}", f"统称名单加载: {len(subsidiary_to_parent)}个子公司可继承母公司规则")
    splitter = SalesSplitter(rules_data, subsidiary_to_parent)
    log_step(f"销售{file_type}",
             f"规则: 广东{len(splitter.gd_rules)} + 深圳{len(splitter.sz_rules)} + "
             f"其他{len(splitter.other_rules)} + 默认{len(splitter.default_rules)}条")

    # 拆分
    print(f"\n{'='*50}")
    print(f"  Phase 3: 销售{file_type}拆分")
    print(f"{'='*50}")

    split_df, stats = splitter.split(df)

    # 统计
    log_step(f"销售{file_type}", f"拆分后: {len(split_df)}行 (拆分率: {len(split_df)/len(df):.2f})")
    inherit_total = 0
    for layer, count in sorted(stats.items()):
        if count == 0:
            continue
        if layer.startswith("继承"):
            inherit_total += count
        log_step(f"销售{file_type}", f"  {layer}: {count}行")
    if inherit_total > 0:
        log_step(f"销售{file_type}", f"  继承合计: {inherit_total}行 (母公司规则继承)")
    log_step(f"销售{file_type}",
             f"待确认比例: {stats['待确认']}/{len(df)} = {stats['待确认']/len(df)*100:.1f}%")
    log_step(f"销售{file_type}", f"销售人数: {split_df['销售'].nunique()}人")

    # 总额校验
    splitter.validate(df, split_df, f"销售{file_type}")

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
    print(f"  销售拆分引擎 -- 销售收入/销售回款")
    print(f"  拆分对象: {', '.join(file_types)}")
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
