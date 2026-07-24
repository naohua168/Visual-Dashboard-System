"""
年基线清洗主入口

用法:
    python -m engine.yearly_baseline.run
    python -m engine.yearly_baseline.run --source=path/to/file.xlsx
"""
import sys
from pathlib import Path

import pandas as pd

from ..core.config import load_config
from ..core.mapping_loader import load_department_mapper
from .cleaner import run_clean, clean_yearly


def main():
    args = sys.argv[1:]
    source_path = None

    for arg in args:
        if arg.startswith("--source="):
            source_path = arg.split("=", 1)[1]

    print(f"\n{'#' * 60}")
    print("  年基线数据清洗引擎")
    print(f"  时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#' * 60}")

    config = load_config()
    mapper = load_department_mapper(config)

    if source_path:
        p = Path(source_path)
        if not p.exists():
            print("  ❌ 源文件不存在: %s" % p)
            return 1
        results = clean_yearly(source_path=p, mapper=mapper)
        if results is None:
            print("  ⚠️ 无法读取源文件，跳过")
            return 0
        for label, df in results.items():
            out_dir = p.parent / "年%s" % label
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "年%s.xlsx" % label
            df.to_excel(out_path, index=False)
            print("  ✅ %s: 写入 %s" % (label, out_path))
    else:
        results = run_clean(mapper)

    print(f"\n{'#' * 60}")
    print("  年基线清洗完成")
    if results:
        for label, df in results.items():
            print(f"  年{label}: {len(df)}行, 金额{df['金额'].sum():,.2f}")
    else:
        print("  无数据更新（使用已有缓存数据或源文件缺失）")
    print(f"{'#' * 60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
