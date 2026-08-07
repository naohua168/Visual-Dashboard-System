"""数据加载器 — 统一读取 data/sheets/ 下的所有数据表

所有渲染器都通过此模块获取数据，单一数据出口便于维护与测试。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


# ──────────────────────────────────────────────────────────────
# 客户统称映射器已移除 — 不再使用客户统称名单.json
# ──────────────────────────────────────────────────────────────


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
        """年基线数据是否可用于同比（有数据即认为就绪，汇总模式不再要求月份粒度）"""
        if self.yearly_income is None or len(self.yearly_income) == 0:
            return False
        if self.yearly_payment is None or len(self.yearly_payment) == 0:
            return False
        return True

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
        sales_targets=None,  # 销售规则已移除，目标由手工指标表直接读取
    )


def safe_float(v) -> float:
    """安全转 float，失败返回 0"""
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return 0.0
        return float(v)
    except (ValueError, TypeError):
        return 0.0
