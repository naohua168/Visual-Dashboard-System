"""
财务端清洗 — 处理收入.xlsx、回款.xlsx、广东公司.xlsx、湖南公司.xlsx

全配置驱动，时间范围由 config.py 自动解析。
"""
import pandas as pd
from ..core.column_resolver import extract_columns, print_hit_columns
from ..core.utils import log_step, filter_by_date, standardize_output, read_excel_with_fallback
from ..core.config import get_data_path


def clean_financial_main(config, mapper, matcher, file_type, time_range):
    """清洗财务主表（收入.xlsx 或 回款.xlsx）"""
    src_config = config["数据源"]["财务端"][file_type]
    file_path = get_data_path(config, "财务端", file_type)

    log_step(f"财务端{file_type}", f"读取 {file_path.name}")
    df = read_excel_with_fallback(file_path, src_config["Sheet"], src_config["引擎"])
    total_in = len(df)
    log_step(f"财务端{file_type}", f"原始数据: {total_in}行 x {len(df.columns)}列")

    # 列名提取（冗余）
    df = extract_columns(df, src_config["列映射"])
    print_hit_columns(df, f"财务端{file_type}")

    # 客户区域筛选（仅保留三区）
    if "客户区域" in df.columns:
        before = len(df)
        df = df[df["客户区域"] == "三区"].copy()
        log_step(f"财务端{file_type}", f"三区筛选: 保留{len(df)}行, 排除{before - len(df)}行")

    # 日期筛选
    df = filter_by_date(df, "日期", time_range["start_date"], time_range["end_date"])
    log_step(f"财务端{file_type}", f"日期筛选后: {len(df)}行 (排除{total_in - len(df)}行)")
    if len(df) == 0:
        log_step(f"财务端{file_type}", "无数据（时间范围内无匹配记录），跳过", "WARN")
        return pd.DataFrame(columns=["事业部", "金额", "客户", "法人主体", "日期"])

    # 排除内部交易
    before = len(df)
    df = df[~df["客户"].apply(mapper.is_excluded)]
    log_step(f"财务端{file_type}", f"内部交易排除: 丢弃{before - len(df)}行")

    # 金额保留原始值
    df["金额"] = df["金额"].fillna(0)

    # 事业部分类（统一用回款版映射，含详细名+全名）
    df["事业部"] = df["部门"].apply(mapper.map_payment_dept)
    before = len(df)
    df = df.dropna(subset=["事业部"])
    log_step(f"财务端{file_type}", f"事业部映射: 成功{len(df)}行, 丢弃{before - len(df)}行")

    # 客户白名单匹配
    before = len(df)
    df = matcher.filter_dataframe(df, "客户", keep_unmatched=False)
    log_step(f"财务端{file_type}", f"白名单匹配: 成功{len(df)}行, 丢弃{before - len(df)}行")

    df = standardize_output(df)
    log_step(f"财务端{file_type}", f"最终: {len(df)}行", "OK")
    return df


def clean_guangdong(config, matcher, time_range, file_type):
    """清洗广东公司数据"""
    src_config = config["数据源"]["财务端"]["广东公司"]
    file_path = get_data_path(config, "财务端", "广东公司")
    sheet_name = src_config["Sheet"][file_type][0]

    log_step(f"广东{file_type}", f"读取 {file_path.name}[{sheet_name}]")
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine=src_config["引擎"])

    df = extract_columns(df, src_config["列映射"])
    df = filter_by_date(df, "日期", time_range["start_date"], time_range["end_date"])
    log_step(f"广东{file_type}", f"日期筛选后: {len(df)}行")

    # 广东公司原始数据是万元，乘以10000转为元，统一单位
    df["金额"] = pd.to_numeric(df["金额"], errors="coerce").fillna(0.0) * 10000.0
    df["事业部"] = src_config["事业部固定"]
    df["法人主体"] = "广东汽车检测中心有限公司"

    before = len(df)
    df = matcher.filter_dataframe(df, "客户", keep_unmatched=False)
    log_step(f"广东{file_type}", f"白名单匹配: 成功{len(df)}行, 丢弃{before - len(df)}行")

    df = standardize_output(df)
    log_step(f"广东{file_type}", f"最终: {len(df)}行, 金额合计: {df['金额'].sum():,.2f}（已转万元→元）", "OK")
    return df


def clean_hunan(config, matcher, time_range, file_type):
    """清洗湖南公司数据"""
    src_config = config["数据源"]["财务端"]["湖南公司"]
    file_path = get_data_path(config, "财务端", "湖南公司")
    sheet_name = src_config["Sheet"][file_type][0]

    log_step(f"湖南{file_type}", f"读取 {file_path.name}[{sheet_name}]")
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine=src_config["引擎"])

    df = extract_columns(df, src_config["列映射"])
    df = filter_by_date(df, "日期", time_range["start_date"], time_range["end_date"])
    log_step(f"湖南{file_type}", f"日期筛选后: {len(df)}行")

    # 湖南公司原始数据是万元，乘以10000转为元，统一单位
    df["金额"] = pd.to_numeric(df["金额"], errors="coerce").fillna(0.0) * 10000.0
    df["事业部"] = src_config["事业部固定"]
    df["法人主体"] = "中汽院智能网联汽车检测中心（湖南）有限公司"

    before = len(df)
    df = matcher.filter_dataframe(df, "客户", keep_unmatched=False)
    log_step(f"湖南{file_type}", f"白名单匹配: 成功{len(df)}行, 丢弃{before - len(df)}行")

    df = standardize_output(df)
    log_step(f"湖南{file_type}", f"最终: {len(df)}行, 金额合计: {df['金额'].sum():,.2f}（已转万元→元）", "OK")
    return df


def clean_financial(config, mapper, matcher, file_type, time_range):
    """财务端完整清洗：主表 + 广东 + 湖南 -> 合并"""
    print(f"\n{'='*50}")
    print(f"  Phase 1: 财务端{file_type}清洗")
    print(f"{'='*50}")

    df_main = clean_financial_main(config, mapper, matcher, file_type, time_range)
    df_gd = clean_guangdong(config, matcher, time_range, file_type)
    df_hn = clean_hunan(config, matcher, time_range, file_type)

    df_all = pd.concat([df_main, df_gd, df_hn], ignore_index=True)
    log_step(f"财务端{file_type}", f"合并: {len(df_main)} + {len(df_gd)} + {len(df_hn)} = {len(df_all)}行", "OK")
    return df_all
