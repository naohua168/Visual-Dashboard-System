"""
列名解析器 — 冗余列名匹配，按顺序尝试备选列名
"""
import pandas as pd


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
        提取后的 DataFrame (列名为标准字段名)
    """
    result = pd.DataFrame()
    for std_name, candidates in column_mapping.items():
        if std_name.startswith("_"):
            continue
        actual_col = find_column(df, candidates)
        result[std_name] = df[actual_col]
        result.attrs.setdefault("_hit_columns", {})[std_name] = actual_col
    return result


def print_hit_columns(df, source_name):
    """打印实际命中的列名（调试用）"""
    hits = df.attrs.get("_hit_columns", {})
    if hits:
        print(f"  [{source_name}] 列名命中:")
        for std, actual in hits.items():
            print(f"    {std} <- {actual}")
