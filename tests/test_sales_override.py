# Author: naohua168 <bai_bai168@qq.com>
"""测试比亚迪子公司按法人主体区分销售的 override 逻辑
仅当配置中同时配置黄浩浩 + 周涵林（销售重合）的公司才触发法人区分；
单边配置的公司保持原拆分结果不动。
"""
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent


def test_load_byd_overlap_only_dual_config():
    """当前配置下，overlap 应仅包含同时配置黄浩浩+周涵林的比亚迪子公司"""
    from engine.sales.run import _load_byd_overlap, BYD_SUB_COMPANIES
    overlap = _load_byd_overlap()
    # BYD_SUB_COMPANIES 共 11 家；当前仅"合肥比亚迪汽车有限公司"同时挂在
    # "比亚迪汽车工业有限公司"(黄浩浩)与"比亚迪电池"(周涵林)两个父组
    assert "合肥比亚迪汽车有限公司" in overlap
    # 单边配置的公司不应进入 overlap（不论数据里有哪种法人主体，都不触发 override）
    single = [c for c in BYD_SUB_COMPANIES if c != "合肥比亚迪汽车有限公司"]
    for c in single:
        assert c not in overlap, f"{c} 不应进入 overlap（未与周涵林同时配置）"


def test_apply_override_skips_non_overlap():
    """非 overlap 公司的拆分结果不应被 override 修改"""
    from engine.sales.run import _apply_byd_sales_override
    # 单边配置公司：原本配置为黄浩浩，混入非广东法人行也应保持黄浩浩
    df = pd.DataFrame([
        {"客户": "汕尾比亚迪实业有限公司", "法人主体": "广东汽车检测中心有限公司", "销售": "黄浩浩"},
        {"客户": "汕尾比亚迪实业有限公司", "法人主体": "中国汽车工程研究院股份有限公司", "销售": "黄浩浩"},
        {"客户": "长沙比亚迪汽车有限公司", "法人主体": "中国汽车工程研究院股份有限公司", "销售": "黄浩浩"},
    ])
    out = _apply_byd_sales_override(df.copy())
    # 所有行应保持黄浩浩（汕尾/长沙配置层只挂黄浩浩，未与周涵林重合）
    assert (out["销售"] == "黄浩浩").all()


def test_apply_override_dual_config_triggers():
    """overlap 中的公司按法人区分：广东→黄浩浩，非广东→周涵林"""
    from engine.sales.run import _apply_byd_sales_override
    df = pd.DataFrame([
        {"客户": "合肥比亚迪汽车有限公司", "法人主体": "广东汽车检测中心有限公司", "销售": "黄浩浩"},
        {"客户": "合肥比亚迪汽车有限公司", "法人主体": "中国汽车工程研究院股份有限公司", "销售": "黄浩浩"},
        {"客户": "合肥比亚迪汽车有限公司", "法人主体": "中认车联网技术服务（深圳）有限公司", "销售": "黄浩浩"},
    ])
    out = _apply_byd_sales_override(df.copy())
    s = out.set_index("法人主体")["销售"]
    assert s["广东汽车检测中心有限公司"] == "黄浩浩"
    assert s["中国汽车工程研究院股份有限公司"] == "周涵林"
    assert s["中认车联网技术服务（深圳）有限公司"] == "周涵林"