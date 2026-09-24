# -*- coding: utf-8 -*-
# Author: naohua168 <bai_bai168@qq.com>
"""列名命中日志测试 — 命中信息落盘 + 降级标记

覆盖 2026-09-17 新增能力：
  - extract_columns 记录 _hit_columns / _hit_candidates
  - format_hit_block 标注命中次序与降级命中
  - append_hit_block 按天追加落盘 logs/column_hits_YYYYMMDD.txt
"""
import datetime

import pandas as pd

from engine.core.column_resolver import extract_columns
from engine.core.hit_log import append_hit_block, format_hit_block, hit_log_path


class TestExtractColumnsAttrs:
    def test_records_hits_and_candidates(self):
        df = pd.DataFrame({"创建日期": ["2026-01-01"], "客户名称": ["A"], "含税金额": [100]})
        mapping = {
            "日期": ["创建时间", "创建日期"],
            "客户": ["客户.名称", "客户名称"],
            "金额": ["含税金额"],
        }
        out = extract_columns(df, mapping)
        assert out.attrs["_hit_columns"] == {
            "日期": "创建日期", "客户": "客户名称", "金额": "含税金额",
        }
        assert out.attrs["_hit_candidates"]["日期"] == ["创建时间", "创建日期"]
        assert out.attrs["_hit_candidates"]["金额"] == ["含税金额"]

    def test_skips_underscore_keys(self):
        df = pd.DataFrame({"日期": ["2026-01-01"]})
        out = extract_columns(df, {"_说明": ["x"], "日期": ["日期"]})
        assert list(out.columns) == ["日期"]
        assert "_说明" not in out.attrs["_hit_columns"]

    def test_hit_survives_dataframe_copy(self):
        """命中信息需跟随 .copy() 传递（清洗链路中会多次 copy/切片）"""
        df = pd.DataFrame({"日期": ["2026-01-01"]})
        out = extract_columns(df, {"日期": ["日期"]}).copy()
        assert out.attrs["_hit_columns"] == {"日期": "日期"}


class TestHitBlockFormat:
    def test_marks_degraded_hit(self):
        txt = format_hit_block("财务端收入", {"部门": "成本中心"},
                               {"部门": ["成本中心.名称", "成本中心"]})
        assert "财务端收入" in txt
        assert "降级命中" in txt
        assert "2/2" in txt

    def test_first_candidate_not_degraded(self):
        txt = format_hit_block("财务端收入", {"日期": "创建时间"},
                               {"日期": ["创建时间", "创建日期"]})
        assert "降级命中" not in txt
        assert "1/2" in txt

    def test_actual_not_in_candidates(self):
        txt = format_hit_block("X", {"金额": "金额合计"}, {"金额": ["金额"]})
        assert "不在候选列表内" in txt

    def test_no_candidates_no_mark(self):
        txt = format_hit_block("X", {"日期": "日期"})
        assert "候选" not in txt


class TestAppendHitBlock:
    def test_creates_and_appends_same_day_file(self, tmp_path):
        p1 = append_hit_block("来源A", {"日期": "日期"}, {"日期": ["日期"]},
                              log_dir=tmp_path,
                              when=datetime.datetime(2026, 9, 17, 10, 0, 0))
        p2 = append_hit_block("来源B", {"客户": "客户"}, {"客户": ["客户"]},
                              log_dir=tmp_path,
                              when=datetime.datetime(2026, 9, 17, 11, 0, 0))
        assert p1 == p2
        assert p1.name == "column_hits_20260917.txt"
        txt = p1.read_text(encoding="utf-8")
        assert "来源A" in txt and "来源B" in txt

    def test_different_day_different_file(self, tmp_path):
        p1 = append_hit_block("A", {"日期": "日期"}, log_dir=tmp_path,
                              when=datetime.datetime(2026, 9, 17))
        p2 = append_hit_block("A", {"日期": "日期"}, log_dir=tmp_path,
                              when=datetime.datetime(2026, 9, 18))
        assert p1 != p2

    def test_empty_hits_writes_nothing(self, tmp_path):
        p = append_hit_block("空", {}, log_dir=tmp_path,
                             when=datetime.datetime(2026, 9, 17))
        assert not p.exists()

    def test_hit_log_path_naming(self, tmp_path):
        p = hit_log_path(datetime.datetime(2026, 9, 17), log_dir=tmp_path)
        assert p.name == "column_hits_20260917.txt"
