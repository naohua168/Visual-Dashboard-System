"""
列名解析器 — 冗余列名匹配，按顺序尝试备选列名
"""
import pandas as pd

from .hit_log import append_hit_block


def find_column(df, candidates):
    """
    冗余列名查找：按顺序尝试备选列名，返回第一个匹配的

    Args:
        df: DataFrame
        candidates: 备选列名列表，如 ["创建时间", "创建日期", "审核日期"]

    Returns:
        匹配成功的列名 (str)

    Raises:
        KeyError: 全部备选都未匹配
    """
    available = {str(c).strip(): c for c in df.columns}

    for name in candidates:
        stripped = name.strip()
        if stripped in available:
            return available[stripped]

    raise KeyError(
        f"未找到匹配列，尝试过: {candidates}\n"
        f"可用列名: {list(df.columns)}"
    )


def extract_columns(df, column_mapping):
    """
    按列映射配置提取列，支持冗余

    Args:
        df: 原始 DataFrame
        column_mapping: 列映射配置，如 {"日期": ["创建时间", "创建日期"], "客户": ["客户.名称"]}

    Returns:
        提取后的 DataFrame (列名为标准字段名)，并在 attrs 中附带命中信息：
          _hit_columns:    {标准字段: 实际命中的源列名}
          _hit_candidates: {标准字段: [候选列名...]}（用于判断是主候选还是降级命中）
    """
    result = pd.DataFrame()
    hits: dict[str, str] = {}
    hit_candidates: dict[str, list[str]] = {}
    for std_name, candidates in column_mapping.items():
        if std_name.startswith("_"):
            continue
        actual_col = find_column(df, candidates)
        result[std_name] = df[actual_col]
        hits[std_name] = str(actual_col)
        hit_candidates[std_name] = [str(c) for c in candidates]
    # 一次性写 attrs（避免逐列 setdefault 依赖 pandas 的 attrs 传播行为）
    result.attrs["_hit_columns"] = hits
    result.attrs["_hit_candidates"] = hit_candidates
    return result


def print_hit_columns(df, source_name, write_log: bool = True):
    """打印实际命中的列名，并追加落盘到 logs/column_hits_YYYYMMDD.txt

    - 命中次序 > 1 的会在日志里标为「⚠️ 降级命中」（第一候选在源文件中不存在，
      靠后备候选兜住），便于识别脆弱点
    - 落盘失败（如无写权限）不影响清洗主流程
    """
    hits = df.attrs.get("_hit_columns", {})
    if not hits:
        return
    candidates = df.attrs.get("_hit_candidates", {})
    print(f"  [{source_name}] 列名命中:")
    for std, actual in hits.items():
        print(f"    {std} <- {actual}")
    if write_log:
        try:
            append_hit_block(source_name, hits, candidates)
        except OSError as e:
            print(f"  ⚠️ 命中日志写入失败: {e}")
