# Author: naohua168 <bai_bai168@qq.com>
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
from ..core.diagnostics import note_issue
from ..core.io_utils import ExcelBusyError, save_excel
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

    results: dict[str, "pd.DataFrame"] = {}
    _LABEL_MAP = {"收入": "往年收入", "回款": "往年回款"}

    if source_path:
        p = Path(source_path)
        if p.is_dir():
            # 目录模式：往年收入数据/往年回款数据 子目录（没有就用目录本身）
            print("  📂 目录模式: %s" % p)
            income_dir = p / "往年收入数据" if (p / "往年收入数据").exists() else p
            payment_dir = p / "往年回款数据" if (p / "往年回款数据").exists() else p
            inc_files = sorted(f for f in income_dir.glob("*.xlsx") if not f.name.startswith("~$")) \
                if income_dir.exists() else []
            pay_files = sorted(f for f in payment_dir.glob("*.xlsx") if not f.name.startswith("~$")) \
                if payment_dir.exists() else []
        elif p.is_file() and p.suffix == ".xlsx":
            # 单文件模式：根据文件名判断类型
            inc_files = [p] if "收入" in p.stem else []
            pay_files = [p] if "回款" in p.stem else []
            if not inc_files and not pay_files:
                inc_files = [p]  # 无法判断时按收入处理
        else:
            print("  ❌ 源路径不存在或不是 xlsx: %s" % p)
            return 1

        if not inc_files and not pay_files:
            # 2026-09-29 修复：原先两个 glob 都为空会让 results 未绑定 → UnboundLocalError
            print("  ❌ 目录下没有可用的 xlsx（往年收入数据/往年回款数据 或目录本身）: %s" % p)
            return 1

        for label, files in [("收入", inc_files), ("回款", pay_files)]:
            if not files:
                print("  ⚠️ %s: 无源文件，跳过" % label)
                continue
            # 2026-09-29 修复：同一类型下**所有**文件都处理（原先只取第一个），按类型合并后写一份
            frames: dict[str, list] = {}
            for fp in files:
                print("  📄 %s: %s" % (label, fp.name))
                res = clean_yearly(source_dir=str(fp), mapper=mapper)
                if res is None:
                    print("  ⚠️ 无法读取，跳过: %s" % fp.name)
                    note_issue("WARN", "年基线%s" % label, "无法读取源文件: %s" % fp.name)
                    continue
                for res_label, df in res.items():
                    frames.setdefault(res_label, []).append(df)
            for res_label, dfs in frames.items():
                merged = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
                dir_name = _LABEL_MAP.get(res_label, res_label)
                out_path = files[0].parent / dir_name / ("%s.xlsx" % dir_name)
                try:
                    save_excel(merged, out_path)
                except ExcelBusyError as e:
                    print("  ❌ 写入失败：%s" % e)
                    return 3
                results[res_label] = merged
                print("  ✅ %s: 写入 %s（%d 个源文件合并 → %d 行）"
                      % (res_label, out_path, len(dfs), len(merged)))
    else:
        results = run_clean(mapper) or {}

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
