"""
销售数据直通 — 不拆分，只添加"销售"列用于前端展示

用法:
    python -m engine.sales.run              # 处理销售收入+销售回款
    python -m engine.sales.run --type=收入   # 只处理销售收入
    python -m engine.sales.run --type=回款   # 只处理销售回款
"""
import sys

import pandas as pd

from ..core.config import load_config, get_output_path, BASE_DIR
from ..core.utils import log_step


def run_split(file_type, config=None):
    """直通模式：不拆分，直接添加"销售"列为空"""
    if config is None:
        config = load_config()

    # 读取已清洗的收入/回款表（当年累计）
    source_key = f"当年累计{file_type}"
    if source_key not in config["输出"]:
        log_step(f"销售{file_type}", f"配置中缺少 '{source_key}'，回退到 '{file_type}'", "WARN")
        source_key = file_type
    source_folder = BASE_DIR / config["输出"][source_key]
    if source_folder.is_dir():
        xlsx_files = [f for f in source_folder.glob("*.xlsx") if not f.name.startswith("~$")]
        if xlsx_files:
            source_path = xlsx_files[0]
        else:
            source_path = source_folder / f"{source_key}.xlsx"
    else:
        source_path = source_folder
    log_step(f"销售{file_type}", f"读取已清洗数据: {source_path.name}")
    df = pd.read_excel(source_path)
    log_step(f"销售{file_type}", f"原始数据: {len(df)}行, 金额{df['金额'].sum():,.2f}")

    # 直通模式：添加"销售"列，不拆分
    print(f"\n{'='*50}")
    print(f"  Phase 3: 销售{file_type}（直通模式）")
    print(f"{'='*50}")

    df["销售"] = ""

    log_step(f"销售{file_type}", f"输出: {len(df)}行 (直通, 不拆分)")
    log_step(f"销售{file_type}", f"金额合计: {df['金额'].sum():,.2f}")

    # 写入
    output_key = f"销售{file_type}"
    output_path = get_output_path(config, output_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = df.fillna("")
    df.to_excel(output_path, index=False)
    log_step(f"销售{file_type}", f"写入: {output_path}", "OK")

    return df


def main():
    args = sys.argv[1:]
    file_types = []

    for arg in args:
        if arg.startswith("--type="):
            file_types = [arg.split("=")[1]]

    if not file_types:
        file_types = ["收入", "回款"]

    print(f"\n{'#'*60}")
    print(f"  销售数据直通模式")
    print(f"  处理对象: {', '.join(file_types)}")
    print(f"  时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    config = load_config()
    results = {}
    for ft in file_types:
        results[ft] = run_split(ft, config)

    print(f"\n{'#'*60}")
    print(f"  完成")
    for ft, df in results.items():
        print(f"  销售{ft}: {len(df)}行, 金额{df['金额'].sum():,.2f}")
    print(f"{'#'*60}")
    return results


if __name__ == "__main__":
    main()
