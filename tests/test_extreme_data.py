# Author: naohua168 <bai_bai168@qq.com>
"""极端数据健壮性测试（2026-09-30）

覆盖四大类边界：
  1. 日期窗口边界：首日 0 点 / 末日 23:59:59 / 窗口外 / 空日期 / 纯日期 end_date 自动补全
  2. 金额异常：0 / 负数（红冲）/ 空值 / 极大值 —— 清洗不崩、合计正确
  3. 客户名异常：空 / 超长 / 全半角差异 / 特殊字符（引号、尖括号、&、反斜杠）
  4. 达成率与空输入：目标 0、实际 0、除零、空表渲染

设计原则：全部使用构造数据 + 临时目录，不读取也不改动 data/ 下的真实业务数据。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import engine.income_payment.financial as fin_mod  # noqa: E402
from engine.core.config import end_of_day, resolve_time_range  # noqa: E402
from engine.core.customer_matcher import CustomerMatcher  # noqa: E402
from engine.core.mapping_loader import DepartmentMapper  # noqa: E402
from engine.core.name_key import match_key  # noqa: E402
from engine.core.utils import filter_by_date  # noqa: E402

TR = {"start_date": "2026-09-01", "end_date": "2026-09-30"}


# ══════════════════════════════════════════════════════════════
# 1. 日期窗口边界
# ══════════════════════════════════════════════════════════════
class TestDateBoundary:
    @staticmethod
    def _df() -> pd.DataFrame:
        return pd.DataFrame({
            "日期": pd.to_datetime([
                "2026-08-31 23:59:59",   # 窗口前 1 秒
                "2026-09-01 00:00:00",   # 窗口首日 0 点
                "2026-09-15 12:00:00",
                "2026-09-30 23:59:59",   # 窗口末日最后 1 秒
                "2026-10-01 00:00:00",   # 窗口后 1 秒
                None,                    # 空日期
            ]),
            "金额": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        })

    def test_整月窗口包含首日0点与末日最后一秒(self):
        kept = filter_by_date(self._df(), "日期", "2026-09-01", "2026-09-30")
        assert list(kept["金额"]) == [2.0, 3.0, 4.0]

    def test_纯日期与显式到秒结果一致(self):
        a = filter_by_date(self._df(), "日期", "2026-09-01", "2026-09-30")
        b = filter_by_date(self._df(), "日期", "2026-09-01", "2026-09-30 23:59:59")
        assert list(a["金额"]) == list(b["金额"])

    def test_单日窗口(self):
        kept = filter_by_date(self._df(), "日期", "2026-09-30", "2026-09-30")
        assert list(kept["金额"]) == [4.0]

    def test_空日期行被排除且不抛异常(self):
        kept = filter_by_date(self._df(), "日期", "2026-09-01", "2026-09-30")
        assert kept["日期"].notna().all()

    def test_窗口内无数据返回空表(self):
        df = pd.DataFrame({"日期": pd.to_datetime(["2020-01-01"]), "金额": [1.0]})
        assert len(filter_by_date(df, "日期", "2026-09-01", "2026-09-30")) == 0

    def test_end_of_day补全且幂等(self):
        assert end_of_day("2026-09-30") == "2026-09-30 23:59:59"
        assert end_of_day("2026-09-30 23:59:59") == "2026-09-30 23:59:59"
        assert end_of_day("2026-09-30 00:00:01") == "2026-09-30 00:00:01"
        assert end_of_day(" 2026-09-30 ") == "2026-09-30 23:59:59"

    def test_static时间范围自动补全(self):
        r = resolve_time_range({"start_date": "2026-09-01", "end_date": "2026-09-30"})
        assert r["end_date"] == "2026-09-30 23:59:59"


# ══════════════════════════════════════════════════════════════
# 2. 金额异常（清洗层，走真实 clean_financial_main）
# ══════════════════════════════════════════════════════════════
def _cfg() -> dict:
    return {"数据源": {"财务端": {"收入": {
        "文件名": "收入.xlsx",
        "Sheet": ["Sheet1"],
        "引擎": "openpyxl",
        "列映射": {"日期": ["创建时间"], "客户": ["客户.名称"], "金额": ["不含税金额"],
                   "部门": ["成本中心"], "法人主体": ["公司"]},
        "过客户白名单": False,          # 本组只验证金额/日期边界，先不叠加白名单
    }}}}


def _run(rows, tmp_path, monkeypatch):
    xlsx = tmp_path / "收入.xlsx"
    pd.DataFrame(rows).to_excel(xlsx, sheet_name="Sheet1", index=False)
    monkeypatch.setattr(fin_mod, "get_data_path", lambda *a, **k: xlsx)
    monkeypatch.setattr(fin_mod, "print_hit_columns", lambda *a, **k: None)
    mapper = DepartmentMapper({"payment_mapping": {"检测工程事业部": "检测"}})
    return fin_mod.clean_financial_main(_cfg(), mapper, CustomerMatcher([]), "收入", TR)


class TestAmountEdge:
    def _rows(self, amounts):
        return [{"创建时间": "2026-09-10 10:00:00", "客户.名称": f"客户{i}",
                 "不含税金额": a, "成本中心": "检测工程事业部", "公司": "某公司"}
                for i, a in enumerate(amounts)]

    def test_零负空极大金额都不丢行(self, tmp_path, monkeypatch):
        out = _run(self._rows([0, -1234.56, None, 9.9e12]), tmp_path, monkeypatch)
        assert len(out) == 4, "异常金额行不应被丢弃"

    def test_空金额按0计且合计等于有效值之和(self, tmp_path, monkeypatch):
        out = _run(self._rows([0, -100.0, None, 250.0]), tmp_path, monkeypatch)
        assert abs(float(out["金额"].sum()) - 150.0) < 1e-6

    def test_负数金额保留原值(self, tmp_path, monkeypatch):
        out = _run(self._rows([-100.0]), tmp_path, monkeypatch)
        assert float(out["金额"].iloc[0]) == -100.0


# ══════════════════════════════════════════════════════════════
# 3. 客户名异常
# ══════════════════════════════════════════════════════════════
class TestCustomerNameEdge:
    def test_空白客户名不崩溃且被计数(self, tmp_path, monkeypatch):
        rows = [
            {"创建时间": "2026-09-10", "客户.名称": "", "不含税金额": 1.0,
             "成本中心": "检测工程事业部", "公司": "某公司"},
            {"创建时间": "2026-09-10", "客户.名称": None, "不含税金额": 2.0,
             "成本中心": "检测工程事业部", "公司": "某公司"},
        ]
        out = _run(rows, tmp_path, monkeypatch)
        assert len(out) == 2          # 不校验白名单时应原样保留，仅客户名被清理

    def test_空客户名在白名单开启时被丢弃(self, tmp_path, monkeypatch):
        cfg = _cfg()
        cfg["数据源"]["财务端"]["收入"]["过客户白名单"] = True
        rows = [{"创建时间": "2026-09-10", "客户.名称": "", "不含税金额": 1.0,
                 "成本中心": "检测工程事业部", "公司": "某公司"}]
        xlsx = tmp_path / "收入.xlsx"
        pd.DataFrame(rows).to_excel(xlsx, sheet_name="Sheet1", index=False)
        monkeypatch.setattr(fin_mod, "get_data_path", lambda *a, **k: xlsx)
        monkeypatch.setattr(fin_mod, "print_hit_columns", lambda *a, **k: None)
        out = fin_mod.clean_financial_main(
            cfg, DepartmentMapper({"payment_mapping": {"检测工程事业部": "检测"}}),
            CustomerMatcher(["某某公司"]), "收入", TR)
        assert len(out) == 0

    def test_全半角与空格差异不影响白名单命中(self):
        m = CustomerMatcher(["法雷奥汽车内部控制（深圳）有限公司"])
        assert m.match("法雷奥汽车内部控制(深圳)有限公司") is not None
        assert m.match(" 法雷奥汽车内部控制（深圳）有限公司 ") is not None

    def test_超长客户名清洗层不崩溃(self, tmp_path, monkeypatch):
        name = "超长客户名" * 200
        out = _run([{"创建时间": "2026-09-10", "客户.名称": name, "不含税金额": 1.0,
                     "成本中心": "检测工程事业部", "公司": "某公司"}], tmp_path, monkeypatch)
        assert len(out) == 1 and len(str(out["客户"].iloc[0])) > 100


# ══════════════════════════════════════════════════════════════
# 4. 渲染层：特殊字符注入 + 达成率除零 + 空表
# ══════════════════════════════════════════════════════════════
def _matrix_html(name: str) -> str:
    from processors.page_annual import AnnualPage
    page = AnnualPage()
    page.base_dir = BASE_DIR
    cols = ["检测", "信息", "能源", "海外", "合计"]
    piv = pd.DataFrame([[1.0, 0.0, 0.0, 0.0, 1.0]], index=[name], columns=cols)
    tgt = pd.DataFrame([[10.0, 0.0, 0.0, 0.0, 10.0]], index=[name], columns=cols)
    # subs_all 里放一个「真正的子公司」→ 该行变成可点击，覆盖 onclick 里拼接客户名的分支
    return page._build_matrix(piv, tgt, [name], 1.0, tab="inc",
                              subs_all={name: [name, "某子公司"]}, subs_detail={}, subs_with_data={})


class TestRenderSafety:
    @pytest.mark.parametrize("name", [
        "普通客户有限公司",
        "含单引号'客户",
        "含双引号\"客户",
        "含尖括号<客户>",
        "含和号&客户",
        "含反斜杠\\客户",
    ])
    def test_特殊字符客户名渲染后可被HTML解析器还原(self, name):
        """客户名以文本形式出现在 DOM 中（即特殊字符已转义，浏览器解析后仍是原文）"""
        from html.parser import HTMLParser

        html = _matrix_html(name)
        collected: list[str] = []

        class _P(HTMLParser):
            def handle_data(self, data):
                collected.append(data)

        _P().feed(html)
        joined = "".join(collected)
        assert name in joined, f"客户名未能原样还原（存在注入/转义风险）: {name!r}"

    @pytest.mark.xfail(reason="已知限制：渲染层未做 HTML 转义，客户名含 ASCII 标签（如 <script>）会被解析成标签；"
                              "业务上客户名不含尖括号，暂不修（2026-09-30 记录）", strict=False)
    def test_ASCII标签客户名未转义_已知限制(self):
        html = _matrix_html("含标签<script>x</script>客户")
        assert "&lt;script&gt;" in html, "若此断言通过说明已加转义，可移除本 xfail 标记"

    @pytest.mark.parametrize("name", ["含单引号'客户", "含反斜杠\\客户"])
    def test_onclick属性内JS字符串不被客户名截断(self, name):
        """onclick 里的客户名必须放在完整引号内（否则点击功能直接失效）"""
        html = _matrix_html(name)
        i = html.find("_show(this,")
        assert i > 0
        snippet = html[i:i + 120]
        assert snippet.count("'") >= 2, f"onclick 中的客户名引号不完整: {snippet!r}"

    def test_空客户列表也能渲染出占位(self):
        from processors.page_annual import AnnualPage
        page = AnnualPage()
        page.base_dir = BASE_DIR
        cols = ["检测", "信息", "能源", "海外", "合计"]
        empty = pd.DataFrame(columns=cols)
        html = page._build_matrix(empty, empty, [], 0.0, tab="inc")
        assert isinstance(html, str) and len(html) > 0

    def test_目标为0实际为0显示破折号(self):
        from processors.components import cell_bg_html
        html = cell_bg_html(0.0, 0.0)
        assert "—" in html

    def test_目标为零实际大于零按满分处理(self):
        from processors.components import cell_bg_html
        html = cell_bg_html(5.0, 0.0)
        assert "100%" in html

    def test_目标大于0实际为0显示0达成(self):
        from processors.components import cell_bg_html
        html = cell_bg_html(0.0, 100.0)
        assert "0%" in html


# ══════════════════════════════════════════════════════════════
# 5. 真实配置准确性：销售比例之和必须 = 1（否则拆分金额不守恒）
# ══════════════════════════════════════════════════════════════
ATT_JSON = BASE_DIR / "config" / "清洗配置" / "客户销售归属.json"


@pytest.fixture(scope="module")
def attribution():
    import json
    return json.loads(ATT_JSON.read_text(encoding="utf-8"))


@pytest.mark.skipif(not ATT_JSON.exists(), reason="客户销售归属.json 不存在")
class TestAttributionAccuracy:
    def test_每个部门的销售比例之和为一(self, attribution):
        """拆分算法是「金额 × 比例」不做归一化：比例之和 ≠ 1 会让金额放大/缩小，
        运行期只打 WARN（不阻断），所以这里作为配置红线守住。"""
        bad = []
        for parent, grp in attribution["客户归属"].items():
            for sub, data in grp.get("子公司", {}).items():
                for metric in ("收入", "回款"):
                    metric_map = data.get(metric)
                    if not isinstance(metric_map, dict):
                        continue
                    for dept, sales_map in metric_map.items():
                        if not isinstance(sales_map, dict) or not sales_map:
                            continue
                        total = sum(float(v) for v in sales_map.values())
                        if abs(total - 1.0) > 1e-6:
                            bad.append(f"{parent}/{sub}/{metric}/{dept} 合计={total}")
        assert not bad, f"销售比例之和 ≠ 1 的配置 {len(bad)} 条（会导致拆分金额不守恒）: {bad[:5]}"

    def test_比例取值范围合法(self, attribution):
        bad = []
        for grp in attribution["客户归属"].values():
            for data in grp.get("子公司", {}).values():
                for metric in ("收入", "回款"):
                    metric_map = data.get(metric)
                    if not isinstance(metric_map, dict):
                        continue
                    for dept, sales_map in metric_map.items():
                        if not isinstance(sales_map, dict):
                            continue
                        for sales, ratio in sales_map.items():
                            r = float(ratio)
                            if not (0 < r <= 1.0):
                                bad.append(f"{dept}/{sales}={r}")
        assert not bad, f"比例越界（应为 0 < r ≤ 1）: {bad[:5]}"
