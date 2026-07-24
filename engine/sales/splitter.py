"""
销售拆分核心 — 4层匹配 + 金额不四舍五入 + 总额校验

4层匹配：广东公司规则 -> 深圳公司规则 -> 其他规则 -> 默认规则 -> 待确认兜底
"""
import pandas as pd
from ..core.utils import log_step


class SalesSplitter:
    """销售拆分器（含母公司规则继承）"""

    def __init__(self, rules_data, subsidiary_to_parent=None):
        self.gd_rules = rules_data.get("广东公司规则", {})
        self.sz_rules = rules_data.get("深圳公司规则", {})
        self.other_rules = rules_data.get("其他规则", {})
        self.default_rules = rules_data.get("默认规则", {})
        # 子公司→母公司映射（统称名单），用于规则继承
        self._subsidiary_to_parent = subsidiary_to_parent or {}

    def _try_parent_inheritance(self, customer, department, is_guangdong, is_shenzhen):
        """当客户无直接规则时，尝试继承母公司的销售规则"""
        parent = self._subsidiary_to_parent.get(str(customer).strip())
        if not parent:
            return [], {}, ""

        log_step("继承", "客户'%s'尝试继承母公司'%s'的规则" % (customer, parent))
        # 用母公司名重新走4层匹配
        sales, ratios, layer = self.match(parent, department, is_guangdong, is_shenzhen, parent_attempt=True)
        if sales and layer != "待确认":
            return sales, ratios, "继承:%s(%s)" % (parent, layer)
        return [], {}, ""

    def _query_rule(self, rules_dict, customer, department):
        """在规则字典中查找客户+事业部的销售配置"""
        if customer not in rules_dict:
            return [], {}

        rule = rules_dict[customer]
        if not isinstance(rule, dict):
            return [], {}

        # 跳过自动添加的"待确认"兜底规则（让母公司继承逻辑有机会执行）
        if rule.get("_来源") == "无匹配 -> 待确认":
            return [], {}

        dept_config = rule.get("事业部", None)
        if dept_config is None:
            # 无事业部配置，适用于所有事业部
            sales_list = rule.get("销售", [])
            ratios = rule.get("比例", None)
            if not sales_list:
                return [], {}
            if ratios is None:
                ratios = self._auto_ratio(sales_list)
            return sales_list, ratios

        if not isinstance(dept_config, dict):
            return [], {}

        if department not in dept_config:
            return [], {}

        dept_rule = dept_config[department]
        if not isinstance(dept_rule, dict):
            return [], {}

        sales_list = dept_rule.get("销售", [])
        ratios = dept_rule.get("比例", None)
        if not sales_list:
            return [], {}
        if ratios is None:
            ratios = self._auto_ratio(sales_list)
        return sales_list, ratios

    @staticmethod
    def _auto_ratio(sales_list):
        """无比例时自动均分"""
        n = len(sales_list)
        if n == 1:
            return {sales_list[0]: 1.0}
        ratio = 1.0 / n
        return {s: ratio for s in sales_list}

    def match(self, customer, department, is_guangdong, is_shenzhen, parent_attempt=False):
        """4层匹配：广东->深圳->其他->默认->母公司继承->待确认"""
        # 广东公司规则
        if is_guangdong == "是":
            sales, ratios = self._query_rule(self.gd_rules, customer, department)
            if sales:
                return sales, ratios, "广东公司规则"

        # 深圳公司规则
        if is_shenzhen == "是":
            sales, ratios = self._query_rule(self.sz_rules, customer, department)
            if sales:
                return sales, ratios, "深圳公司规则"

        # 其他规则
        sales, ratios = self._query_rule(self.other_rules, customer, department)
        if sales:
            return sales, ratios, "其他规则"

        # 默认规则
        sales, ratios = self._query_rule(self.default_rules, customer, department)
        if sales:
            return sales, ratios, "默认规则"

        # 母公司规则继承（仅对原始客户执行，避免无限递归）
        if not parent_attempt:
            sales, ratios, layer = self._try_parent_inheritance(
                customer, department, is_guangdong, is_shenzhen)
            if sales:
                return sales, ratios, layer

        # 最终兜底
        return ["待确认"], {"待确认": 1.0}, "待确认"
        # 广东公司规则
        if is_guangdong == "是":
            sales, ratios = self._query_rule(self.gd_rules, customer, department)
            if sales:
                return sales, ratios, "广东公司规则"

        # 深圳公司规则
        if is_shenzhen == "是":
            sales, ratios = self._query_rule(self.sz_rules, customer, department)
            if sales:
                return sales, ratios, "深圳公司规则"

        # 其他规则
        sales, ratios = self._query_rule(self.other_rules, customer, department)
        if sales:
            return sales, ratios, "其他规则"

        # 默认规则
        sales, ratios = self._query_rule(self.default_rules, customer, department)
        if sales:
            return sales, ratios, "默认规则"

        # 最终兜底
        return ["待确认"], {"待确认": 1.0}, "待确认"

    def split(self, df):
        """拆分整个DataFrame"""
        results = []
        stats = {
            "广东公司规则": 0, "深圳公司规则": 0,
            "其他规则": 0, "默认规则": 0, "待确认": 0,
            "继承": 0,
        }
        # 继承层会动态添加键（如 "继承:广汽系(其他规则)"），用此汇总

        for _, row in df.iterrows():
            customer = row["客户"]
            department = row["事业部"]
            amount = row["金额"]
            date = row["日期"]
            is_gd = row.get("是否为广东公司", "")
            is_sz = row.get("是否为深圳公司", "")

            sales_list, ratios, layer = self.match(customer, department, is_gd, is_sz)
            if layer not in stats:
                stats[layer] = 0
            stats[layer] += 1

            # 拆分（不四舍五入，保留完整精度）
            for sales_name in sales_list:
                allocated = amount * ratios.get(sales_name, 0)
                results.append({
                    "事业部": department,
                    "金额": allocated,
                    "客户": customer,
                    "销售": sales_name,
                    "日期": date,
                    "是否为广东公司": is_gd,
                    "是否为深圳公司": is_sz,
                })

        return pd.DataFrame(results), stats

    def validate(self, original_df, split_df, table_name):
        """总额守恒校验"""
        original_total = original_df["金额"].sum()
        split_total = split_df["金额"].sum()
        diff = abs(original_total - split_total)

        if diff < 1e-6:
            log_step(table_name, f"总额校验: {original_total:,.2f} = {split_total:,.2f} 完全一致", "OK")
            return True
        else:
            log_step(table_name, f"总额校验: 差异 {diff:,.6f}", "WARN")
            return False
