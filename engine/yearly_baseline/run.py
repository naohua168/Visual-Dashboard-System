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
        if p.is_dir():
            # 目录模式：用通配符在子目录中查找
            print("  📂 目录模式: %s" % p)
            income_dir = p / "往年收入数据" if (p / "往年收入数据").exists() else p
            payment_dir = p / "往年回款数据" if (p / "往年回款数据").exists() else p
            inc_files = sorted(income_dir.glob("*.xlsx")) if income_dir.exists() else []
            pay_files = sorted(payment_dir.glob("*.xlsx")) if payment_dir.exists() else []
        elif p.is_file() and p.suffix == ".xlsx":
            # 单文件模式：根据文件名判断类型
            inc_files = [p] if "收入" in p.stem else []
            pay_files = [p] if "回款" in p.stem else []
            if not inc_files and not pay_files:
                inc_files = [p]  # 无法判断时按收入处理
        else:
            print("  ❌ 源路径不存在或不是 xlsx: %s" % p)
            return 1

        for label, files in [("收入", inc_files), ("回款", pay_files)]:
            if not files:
                continue
            fp = files[0]
            print("  📄 %s: %s" % (label, fp.name))
            results = clean_yearly(source_dir=str(fp), mapper=mapper)
            if results is None:
                print("  ⚠️ 无法读取源文件，跳过")
                continue
            _LABEL_MAP = {"收入": "往年收入", "回款": "往年回款"}
            for res_label, df in results.items():
                dir_name = _LABEL_MAP.get(res_label, res_label)
                out_dir = fp.parent / dir_name
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / "%s.xlsx" % dir_name
                df.to_excel(out_path, index=False)
                print("  ✅ %s: 写入 %s" % (res_label, out_path))
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
