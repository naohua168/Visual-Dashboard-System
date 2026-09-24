# Author: naohua168 <bai_bai168@qq.com>
"""排除标记行过滤 —— 收入端源表「初始化」= √ 为期初（历史单据迁移）行，
不计入当月收入（2026-09-24 用户口径）

当前配置：仅 `数据源.财务端.收入` 配该字段（候选 `初始化`，取值 `√`）；
          回款.xlsx 没有该字段 → 不配置，助手直接返回原表。
本文件同时验证助手对「多候选列取并集」「取值容错」「缺列/未配置」的通用行为。

覆盖：
  - 单列命中 / 多列并集命中
  - 未被标记的行保留
  - 源表无该列（未配置或列名不匹配）→ 原样返回，不报错
  - 未配置「排除标记」字段 → 原样返回
  - 值容错：√ / 是 / Y / 1，带空白
"""
import pandas as pd
import pytest

from engine.income_payment.financial import _exclude_marked_rows


def _cfg(candidates=("初始化", "是否初始化"), values=None):
    spec = {"列映射": {"客户": ["客户.名称"], "排除标记": list(candidates)}}
    if values is not None:
        spec["排除标记值"] = values
    return spec


def _df(**cols):
    return pd.DataFrame(cols)


def test_single_column_marked_rows_dropped():
    df = _df(**{
        "客户.名称": ["甲", "乙", "丙"],
        "初始化": ["√", None, "×"],
        "金额": [100.0, 200.0, 300.0],
    })
    out = _exclude_marked_rows(df, _cfg(), "测试")
    assert list(out["客户.名称"]) == ["乙", "丙"]
    assert float(out["金额"].sum()) == 500.0


@pytest.mark.parametrize("value", ["√", "是", "Y", "y", "1", "  √  "])
def test_value_tolerance(value):
    df = _df(**{"客户.名称": ["甲", "乙"], "初始化": [value, None]})
    out = _exclude_marked_rows(df, _cfg(), "测试")
    assert list(out["客户.名称"]) == ["乙"]


def test_two_marker_columns_union():
    """两列都是候选：任一列命中即剔除（取并集）"""
    df = _df(**{
        "客户.名称": ["甲", "乙", "丙"],
        "初始化": ["√", None, None],
        "是否初始化": [None, "√", None],
    })
    out = _exclude_marked_rows(df, _cfg(), "测试")
    assert list(out["客户.名称"]) == ["丙"]


def test_missing_column_returns_unchanged():
    """源表没有候选列（如回款表）→ 原样返回"""
    df = _df(**{"客户.名称": ["甲", "乙"]})
    out = _exclude_marked_rows(df, _cfg(), "测试")
    assert list(out["客户.名称"]) == ["甲", "乙"]


def test_field_not_configured_returns_unchanged():
    df = _df(**{"客户.名称": ["甲"], "初始化": ["√"]})
    out = _exclude_marked_rows(df, {"列映射": {"客户": ["客户.名称"]}}, "测试")
    assert list(out["客户.名称"]) == ["甲"]


def test_custom_values_config():
    df = _df(**{"客户.名称": ["甲", "乙"], "初始化": ["1", "0"]})
    out = _exclude_marked_rows(df, _cfg(values=["0"]), "测试")
    assert list(out["客户.名称"]) == ["甲"]


def test_empty_df_and_none_safe():
    assert _exclude_marked_rows(None, _cfg(), "测试") is None
    empty = pd.DataFrame(columns=["客户.名称", "初始化"])
    assert len(_exclude_marked_rows(empty, _cfg(), "测试")) == 0
