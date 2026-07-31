"""数据加载器 — 统一读取 data/sheets/ 下的所有数据表

所有渲染器都通过此模块获取数据，单一数据出口便于维护与测试。

加载时自动应用客户统称名单（子公司→母公司聚合），确保看板展示的
客户名以母公司维度呈现，使数据聚合更符合业务管理视角。
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


# ──────────────────────────────────────────────────────────────
# 客户统称映射器（子公司→母公司聚合）
# ──────────────────────────────────────────────────────────────

# 销售规则路径常量（渲染层独立使用，不再依赖 cleaning_config.json）
_SALES_RULES_DIR = "config/销售规则"


class CustomerUnifier:
    """客户统称映射器

    加载 客户统称名单.json，将子公司名归并到母公司名下，
    使看板的客户维度展示为母公司层级。
    """

    def __init__(self, base_dir: Path):
        path = base_dir / _SALES_RULES_DIR / "客户统称名单.json"
        self._subsidiary_to_parent: dict[str, str] = {}
        self._parents: set[str] = set()

        if path is None or not path.exists():
            self._count = 0
            self._parent_count = 0
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        company_mapping = data.get("company_mapping", {})
        for parent, subsidiaries in company_mapping.items():
            self._parents.add(parent)
            for sub in subsidiaries:
                # 若子公司名 == 母公司名（自引用），跳过
                if str(sub).strip() == str(parent).strip():
                    continue
                self._subsidiary_to_parent[str(sub).strip()] = parent

        self._count = len(self._subsidiary_to_parent)
        self._parent_count = len(self._parents)

    @property
    def count(self) -> int:
        """子公司数量（可被归并的客户数）"""
        return self._count

    @property
    def parent_count(self) -> int:
        """母公司数量"""
        return self._parent_count

    def unify(self, customer_name) -> str:
        """将客户名统一为母公司名

        规则：
          1. 名称为母公司名 → 保持不变
          2. 名称为子公司名 → 映射为母公司名
          3. 其他 → 保持不变
        """
        if customer_name is None or (isinstance(customer_name, float) and math.isnan(customer_name)):
            return customer_name
        name = str(customer_name).strip()
        if name in self._parents:
            return name
        return self._subsidiary_to_parent.get(name, name)

    def unify_df(self, df: pd.DataFrame, col: str = "客户") -> pd.DataFrame:
        """统一 DataFrame 中指定列的客户名"""
        if col not in df.columns:
            return df
        df = df.copy()
        df[col] = df[col].apply(self.unify)
        return df


@dataclass
class DashboardData:
    """看板所需的全量数据"""

    # 自动生成（4 张表，6/7 列）
    income: pd.DataFrame            # 收入（6列）
    payment: pd.DataFrame           # 回款（6列）
    sales_income: pd.DataFrame      # 销售收入（7列）
    sales_payment: pd.DataFrame     # 销售回款（7列）

    # 手工维护（6 张指标表）
    annual_income_targets: pd.DataFrame      # 年度收入总指标（客户+销售+4事业部）
    annual_payment_targets: pd.DataFrame     # 年度回款总指标
    quarterly_income_targets: pd.DataFrame   # 季度收入指标（客户+销售+4事业部）
    quarterly_payment_targets: pd.DataFrame  # 季度回款指标
    monthly_income_targets: pd.DataFrame     # 月度收入指标
    monthly_payment_targets: pd.DataFrame    # 月度回款指标

    # 年基线（2024，可能为空）
    yearly_income: pd.DataFrame | None = None
    yearly_payment: pd.DataFrame | None = None

    # 季度累计（自动生成）
    quarterly_income: pd.DataFrame | None = None   # 季度累计收入
    quarterly_payment: pd.DataFrame | None = None  # 季度累计回款

    # 月明细（更细粒度，与当年累计不同时间窗口）
    monthly_income_detail: pd.DataFrame | None = None  # 月收入明细
    monthly_payment_detail: pd.DataFrame | None = None  # 月回款明细

    # 销售个人目标（按 客户→销售 对应规则 × 部门目标 计算）
    sales_targets: dict[str, float] | None = None  # {销售名: 个人年度总目标}

    @property
    def has_yearly_baseline(self) -> bool:
        """年基线数据是否就绪（P5 同比页面是否可渲染）"""
        return (
            self.yearly_income is not None
            and len(self.yearly_income) > 0
            and self.yearly_payment is not None
            and len(self.yearly_payment) > 0
        )

    @property
    def has_quarterly_data(self) -> bool:
        """季度数据是否就绪"""
        return (
            self.quarterly_income is not None
            and len(self.quarterly_income) > 0
            and self.quarterly_payment is not None
            and len(self.quarterly_payment) > 0
        )


def _read_optional(path: Path) -> pd.DataFrame | None:
    """读取可选文件，不存在返回 None"""
    if not path.exists():
        return None
    try:
        return pd.read_excel(path)
    except Exception:
        return None


def _find_xlsx(folder: Path) -> Path:
    """从文件夹中查找唯一的 xlsx 文件（排除 ~$ 临时锁定文件）"""
    xlsx_files = [f for f in folder.glob("*.xlsx") if not f.name.startswith("~$")]
    if len(xlsx_files) == 1:
        return xlsx_files[0]
    if len(xlsx_files) > 1:
        return xlsx_files[0]
    # 文件夹不存在时返回默认路径（用于错误提示）
    return folder / f"{folder.name}.xlsx"


def _to_wan(df: pd.DataFrame, amount_col: str = "金额") -> pd.DataFrame:
    """将金额列统一转为万元（÷10000）

    根据设计：财务/运营端是元，广东/湖南是万元。
    由于已清洗表中混在一起且无来源标识，按"统一÷10000"处理。
    若原值是万元（如广东），会变成"万元÷10000=元"，与原始口径不一致。

    ⚠️ 折中方案：已清洗数据保留原始值（元/万元混合），渲染层不再÷10000，
       按原始数值展示并标注"（单位：元/万元混合，请参照数据源）"。
       实际看板展示建议由用户在数据源端统一单位。
    """
    return df  # 保留原始值，单位换算交给数据源端


def load_all(base_dir: Path) -> DashboardData:
    """加载 data/sheets/ 下全部数据表

    优先加载细分数据（月/当年累计/季度累计），兼容旧路径。
    """
    sheets = base_dir / "data" / "sheets"

    # 路径前缀
    SYS = "系统数据清理"
    MAN = "手动维护"

    # 优先加载当年累计（全量数据），从文件夹自动查找xlsx
    income = _read_optional(_find_xlsx(sheets / SYS / "当年累计收入"))
    if income is None:
        raise FileNotFoundError(f"缺少核心数据: {sheets / SYS / '当年累计收入'}")

    payment = _read_optional(_find_xlsx(sheets / SYS / "当年累计回款"))
    if payment is None:
        raise FileNotFoundError(f"缺少核心数据: {sheets / SYS / '当年累计回款'}")

    sales_income = pd.read_excel(_find_xlsx(sheets / SYS / "销售收入"))
    sales_payment = pd.read_excel(_find_xlsx(sheets / SYS / "销售回款"))

    annual_income_tgt = pd.read_excel(_find_xlsx(sheets / MAN / "年度收入总指标"))
    annual_payment_tgt = pd.read_excel(_find_xlsx(sheets / MAN / "年度回款总指标"))
    quarterly_income_tgt = pd.read_excel(_find_xlsx(sheets / MAN / "季度收入指标"))
    quarterly_payment_tgt = pd.read_excel(_find_xlsx(sheets / MAN / "季度回款指标"))
    monthly_income_tgt = pd.read_excel(_find_xlsx(sheets / MAN / "月度收入指标"))
    monthly_payment_tgt = pd.read_excel(_find_xlsx(sheets / MAN / "月度回款指标"))

    yearly_income = _read_optional(_find_xlsx(sheets / SYS / "往年收入"))
    yearly_payment = _read_optional(_find_xlsx(sheets / SYS / "往年回款"))

    # 季度累计数据
    quarterly_income = _read_optional(_find_xlsx(sheets / SYS / "季度累计收入"))
    quarterly_payment = _read_optional(_find_xlsx(sheets / SYS / "季度累计回款"))

    # 月明细数据
    monthly_income_detail = _read_optional(_find_xlsx(sheets / SYS / "月收入"))
    monthly_payment_detail = _read_optional(_find_xlsx(sheets / SYS / "月回款"))

    # ── 统一客户名（子公司→母公司聚合）──
    unifier = CustomerUnifier(base_dir)
    if unifier.count > 0:
        # 遍历所有含"客户"列的 DataFrame 进行归并
        all_dfs = [income, payment, sales_income, sales_payment,
                   annual_income_tgt, annual_payment_tgt,
                   quarterly_income_tgt, quarterly_payment_tgt,
                   monthly_income_tgt, monthly_payment_tgt]
        for _df in all_dfs:
            if "客户" in _df.columns:
                _df["客户"] = _df["客户"].apply(unifier.unify)

        for _df in [yearly_income, yearly_payment,
                    quarterly_income, quarterly_payment,
                    monthly_income_detail, monthly_payment_detail]:
            if _df is not None and "客户" in _df.columns:
                _df["客户"] = _df["客户"].apply(unifier.unify)

        print(f"  [数据加载] 客户统称映射已应用: {unifier.parent_count}个母公司, "
              f"{unifier.count}个子公司将被归并")

    return DashboardData(
        income=income,
        payment=payment,
        sales_income=sales_income,
        sales_payment=sales_payment,
        annual_income_targets=annual_income_tgt,
        annual_payment_targets=annual_payment_tgt,
        quarterly_income_targets=quarterly_income_tgt,
        quarterly_payment_targets=quarterly_payment_tgt,
        monthly_income_targets=monthly_income_tgt,
        monthly_payment_targets=monthly_payment_tgt,
        yearly_income=yearly_income,
        yearly_payment=yearly_payment,
        quarterly_income=quarterly_income,
        quarterly_payment=quarterly_payment,
        monthly_income_detail=monthly_income_detail,
        monthly_payment_detail=monthly_payment_detail,
        sales_targets=_compute_sales_targets(base_dir, annual_income_tgt),
    )


def _compute_sales_targets(base_dir: Path, annual_tgt: pd.DataFrame) -> dict[str, float] | None:
    """根据 客户销售对应规则 × 年度收入总指标 计算每个销售人员的年度总目标（4 事业部合计）

    公式：销售 S 的目标 = sum_over_(客户 C, 部门 D)( 目标(C, D) × 比例(S in C, D) )
    """
    rules_path = base_dir / _SALES_RULES_DIR / "客户销售对应规则.json"
    if rules_path is None or not rules_path.exists() or len(annual_tgt) == 0:
        return None
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)
    except Exception:
        return None

    # 4 大事业部
    DEPARTMENTS = ["检测", "信息", "能源", "海外"]

    # 总指标单位：万元（如 检测=5000 表示 5000 万年度目标）
    # 把总指标按 客户 汇总（同一客户可能有多行），目标是 4 列事业部
    tgt_by_cust: dict[str, dict[str, float]] = {}
    for _, row in annual_tgt.iterrows():
        cust = str(row.get("客户", "")).strip()
        if not cust:
            continue
        if cust not in tgt_by_cust:
            tgt_by_cust[cust] = {d: 0.0 for d in DEPARTMENTS}
        for d in DEPARTMENTS:
            tgt_by_cust[cust][d] += safe_float(row.get(d, 0))

    # 累加每个销售的目标
    sales_tgt: dict[str, float] = {}
    rule_keys = [k for k in rules if not k.startswith("_") and isinstance(rules[k], dict)]
    for section in rule_keys:
        section_data = rules[section]
        for cust, cfg in section_data.items():
            if not isinstance(cfg, dict):
                continue
            if "事业部" not in cfg:
                continue
            cust_tgt = tgt_by_cust.get(str(cust).strip(), {})
            dept_cfg = cfg.get("事业部", {})
            for dept, dcfg in dept_cfg.items():
                if not isinstance(dcfg, dict) or "比例" not in dcfg:
                    continue
                ratio_dict = dcfg["比例"]
                if not isinstance(ratio_dict, dict):
                    continue
                dept_target = cust_tgt.get(dept, 0)
                if not dept_target:
                    continue
                for sales, ratio in ratio_dict.items():
                    sales_tgt[sales] = sales_tgt.get(sales, 0) + dept_target * float(ratio)
    return sales_tgt if sales_tgt else None


def safe_float(v) -> float:
    """安全转 float，失败返回 0"""
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return 0.0
        return float(v)
    except (ValueError, TypeError):
        return 0.0
