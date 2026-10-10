# Author: naohua168 <bai_bai168@qq.com>
"""渲染确定性回归测试（2026-10-10 新增）

背景：看板产物曾出现"同一份数据、每次渲染客户/销售行序都不同"——根因是直接迭代 set
（顺序随进程哈希种子变化）写进了以名称为键的字典/列表。这里锁住三处确定性规则：
  1. 优先展示名单按**配置书写顺序**追加（不是 set 迭代序）
  2. 销售榜按「指标降序 + 姓名升序」排（同指标不再看 set 顺序）
  3. sales_owned_subs 的键按确定性顺序插入（按销售名排序）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from processors.config_loader import (
    CustomerFilter,
    expand_to_customer_names,
    expand_to_customer_names_ordered,
)

BASE_DIR = Path(__file__).resolve().parents[1]


class TestPriorityOrder:
    """优先展示名单：顺序来自配置，不来自 set"""

    def test_ordered_keeps_written_order(self):
        names = ["比亚迪电池", "广汽系"]
        ordered = expand_to_customer_names_ordered(BASE_DIR, names)
        assert ordered, "展开结果不应为空"
        # 与集合版本的成员完全一致（只是顺序不同）
        assert set(ordered) == expand_to_customer_names(BASE_DIR, names)

        first_group = expand_to_customer_names(BASE_DIR, [names[0]])
        idx = [i for i, n in enumerate(ordered) if n in first_group]
        assert idx == list(range(len(idx))), f"第一组应连续排在前段: {idx[:8]}"

    def test_ordered_is_stable_across_calls(self):
        names = ["比亚迪电池", "广汽系"]
        assert expand_to_customer_names_ordered(BASE_DIR, names) == \
            expand_to_customer_names_ordered(BASE_DIR, names)

    def test_filter_exposes_ordered_api(self):
        filt = CustomerFilter(priority=["广汽系"])
        ordered = filt.get_priority_names_ordered(BASE_DIR)
        assert isinstance(ordered, list) and ordered
        assert set(ordered) == filt.get_priority_names(BASE_DIR)


pytest.importorskip("pandas")


def _sales_data():
    """真实数据的销售页数据（与 test_page_renderers 同一口径）"""
    from processors.data_loader import load_all
    from processors.page_data import prepare_sales_data

    try:
        data = load_all(BASE_DIR)
    except Exception as exc:                        # pragma: no cover - 数据缺失时跳过
        pytest.skip(f"数据未就绪: {exc}")
    return prepare_sales_data(data, BASE_DIR)


_SEED_PROBE = """\
import json, sys
from pathlib import Path
sys.path.insert(0, r"{base}")
from processors.data_loader import load_all
from processors.page_data import prepare_sales_data
b = Path(r"{base}")
d = prepare_sales_data(load_all(b), b)
print(json.dumps({{"sales": list(d.sales_list),
                  "pay_sales": list(d.pay_sales_list),
                  "owned": list(d.sales_owned_subs)}}, ensure_ascii=False))
"""


def _dump_with_seed(seed: str) -> str:
    """换一个哈希种子重算销售页数据，返回关键顺序的 JSON"""
    env = dict(os.environ, PYTHONHASHSEED=seed)
    proc = subprocess.run(
        [sys.executable, "-c", _SEED_PROBE.format(base=BASE_DIR)],
        capture_output=True, text=True, env=env, cwd=BASE_DIR, timeout=300,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        pytest.skip(f"子进程计算失败（数据未就绪？）: {proc.stderr.strip()[:200]}")
    return proc.stdout.strip()


class TestSalesOrderDeterminism:
    def test_sales_list_sorted_by_target_then_name(self):
        """销售榜排序键 = (指标降序, 姓名升序) —— 同指标时顺序唯一确定"""
        d = _sales_data()
        keys = [(-d.sales_targets.get(s, 0), s) for s in d.sales_list]
        assert keys == sorted(keys), f"销售顺序不确定: {list(d.sales_list)[:8]}"

    def test_order_identical_across_hash_seeds(self):
        """换一个 PYTHONHASHSEED 重算，销售行序/归属键序必须完全相同

        这条才能真正抓住"直接迭代 set"的 bug：同进程内 set 顺序固定，只有换进程序列才暴露。
        """
        assert _dump_with_seed("1") == _dump_with_seed("2")

    def test_json_dump_stable(self):
        """同一进程内两次序列化必须完全一致（防止插入顺序被上游 set 影响）"""
        d1 = _sales_data()
        d2 = _sales_data()
        assert json.dumps(d1.sales_owned_subs, ensure_ascii=False, sort_keys=False) == \
            json.dumps(d2.sales_owned_subs, ensure_ascii=False, sort_keys=False)
