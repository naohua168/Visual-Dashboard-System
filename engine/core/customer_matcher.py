"""
客户白名单匹配器 — 去空格模糊匹配
"""
import re
import pandas as pd


class CustomerMatcher:
    """客户白名单匹配器"""

    def __init__(self, valid_customers):
        """
        Args:
            valid_customers: 有效客户名列表 (list of str)
        """
        self.original = set(str(c).strip() for c in valid_customers if pd.notna(c))

        self.no_space_map = {}
        for name in self.original:
            no_space = re.sub(r"\s+", "", name)
            self.no_space_map[no_space] = name

        self.no_space_set = set(self.no_space_map.keys())

    def match(self, customer_name):
        """
        匹配客户名称（去空格模糊匹配）

        Returns:
            匹配成功: 白名单中的标准客户名 (str)
            匹配失败: None
        """
        if pd.isna(customer_name):
            return None
        no_space = re.sub(r"\s+", "", str(customer_name))
        return self.no_space_map.get(no_space)

    def filter_dataframe(self, df, customer_col="客户", keep_unmatched=False):
        """过滤 DataFrame，只保留白名单中的客户"""
        matched = df[customer_col].apply(self.match)

        if keep_unmatched:
            df = df.copy()
            df[customer_col] = matched
            return df
        else:
            mask = matched.notna()
            df = df[mask].copy()
            df[customer_col] = matched[mask]
            return df

    @property
    def count(self):
        """白名单客户数"""
        return len(self.original)
