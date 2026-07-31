"""
映射加载器 — 加载部门映射、内部交易排除名单、客户名单
"""
import pandas as pd
from .config import load_mapping, BASE_DIR


class DepartmentMapper:
    """事业部映射器"""

    def __init__(self, mapping_data):
        # 收入版映射（4条，事业部全名->简称）
        self.income_map = {}
        for k, v in mapping_data.get("income_mapping", {}).items():
            if not k.startswith("_"):
                self.income_map[k] = v

        # 回款版映射（50+条，科室/中心名->简称）
        self.payment_map = {}
        for k, v in mapping_data.get("payment_mapping", {}).items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if not sub_k.startswith("_"):
                        self.payment_map[sub_k] = sub_v
            else:
                self.payment_map[k] = v

        # 事业部全名->简称（合并到回款版）
        full_name_map = mapping_data.get("payment_mapping", {}).get("_事业部全名映射", {})
        for k, v in full_name_map.items():
            if not k.startswith("_"):
                self.payment_map[k] = v

        # 内部交易排除名单（直接数组格式）
        excluded = mapping_data.get("excluded_internal_companies", [])
        self.excluded_companies = excluded if isinstance(excluded, list) else excluded.get("companies", [])

    def map_income_dept(self, dept_name):
        """收入版部门映射"""
        if pd.isna(dept_name):
            return None
        return self.income_map.get(str(dept_name).strip())

    def map_payment_dept(self, dept_name):
        """回款版部门映射（含详细名+全名）"""
        if pd.isna(dept_name):
            return None
        return self.payment_map.get(str(dept_name).strip())

    def is_excluded(self, customer_name):
        """是否在内部交易排除名单中"""
        if pd.isna(customer_name):
            return False
        return str(customer_name).strip() in self.excluded_companies


def load_department_mapper(config):
    """从配置加载部门映射器"""
    data = load_mapping("部门事业部映射", config)
    return DepartmentMapper(data)


def load_customer_list(config):
    """加载客户白名单"""
    import os

    try:
        data = load_mapping("客户名单", config)
        if isinstance(data, list):
            return [item.get("客户", item) if isinstance(item, dict) else str(item) for item in data]
        elif isinstance(data, dict):
            for k, v in data.items():
                if not k.startswith("_") and isinstance(v, list):
                    return v
    except (FileNotFoundError, KeyError):
        pass

    raw_path = BASE_DIR / "data" / "raw" / "客户名单" / "客户名单.xlsx"
    if os.path.exists(raw_path):
        df = pd.read_excel(raw_path)
        col = _find_first_column(df, ["客户", "客户名称", "客户名"])
        return df[col].dropna().astype(str).tolist()

    raise FileNotFoundError("客户名单文件未找到")


def _find_first_column(df, candidates):
    """查找第一个匹配的列名"""
    available = {str(c).strip(): c for c in df.columns}
    for name in candidates:
        if name.strip() in available:
            return available[name]
    raise KeyError(f"未找到列，尝试过: {candidates}, 可用: {list(df.columns)}")
