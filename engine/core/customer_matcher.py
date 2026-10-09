# Author: naohua168 <bai_bai168@qq.com>
"""
客户白名单匹配器 — 归一化匹配（全角半角、空白、大小写差异一律忽略）
"""
import pandas as pd

from .name_key import KeyIndex, match_key


class CustomerMatcher:
    """客户白名单匹配器

    匹配键来自 `engine.core.name_key.match_key`：先按「去空格」的历史能力继续满足，
    同时把全角/半角括号差异也归一（如 `法雷奥汽车内部控制（深圳）有限公司` vs `... (深圳) ...`）。
    命中后返回「客户名单里先出现的写法」作为标准名（显示名不受影响）。
    """

    def __init__(self, valid_customers):
        """
        Args:
            valid_customers: 有效客户名列表 (list of str)
        """
        idx = KeyIndex()
        self.original = set()
        self._key_map: dict[str, str] = {}
        for c in valid_customers:
            if pd.isna(c):
                continue
            name = str(c).strip()
            if not name:
                continue
            self.original.add(name)
            self._key_map.setdefault(idx.add(name), name)
        self._index = idx
        # 白名单里仅符号/空白差异的重复写法（供运行日志提示）
        self.conflicts = idx.conflicts

    def match(self, customer_name):
        """
        匹配客户名称（归一化匹配：全角半角 / 空格 / 大小写差异都忽略）

        Returns:
            匹配成功: 白名单中的标准客户名 (str)
            匹配失败: None
        """
        if pd.isna(customer_name):
            return None
        return self._key_map.get(match_key(customer_name))

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
