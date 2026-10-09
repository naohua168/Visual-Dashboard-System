# Author: naohua168 <bai_bai168@qq.com>
"""Excel 落盘防护测试（2026-09-29 新增）—— engine/core/io_utils.py

覆盖：单表/多表写入、目录自动创建、被占用（PermissionError）→ ExcelBusyError + 中文提示。
"""
import pandas as pd
import pytest

from engine.core.io_utils import ExcelBusyError, save_excel


def test_save_single_sheet(tmp_path):
    path = tmp_path / "out" / "demo.xlsx"           # 目录不存在应自动创建
    save_excel(pd.DataFrame({"客户": ["甲"], "金额": [1.5]}), path)
    assert path.exists()
    back = pd.read_excel(path)
    assert list(back.columns) == ["客户", "金额"] and len(back) == 1


def test_save_multi_sheet(tmp_path):
    path = tmp_path / "multi.xlsx"
    save_excel({"收入": pd.DataFrame({"a": [1]}), "回款": pd.DataFrame({"b": [2]})}, path)
    book = pd.read_excel(path, sheet_name=None)
    assert sorted(book) == ["回款", "收入"] and len(book["收入"]) == 1


def test_busy_raises_friendly_error(tmp_path, monkeypatch):
    """被 Excel 占用 → ExcelBusyError，文案含文件名与「关闭后重跑」"""
    path = tmp_path / "busy.xlsx"

    def _boom(*a, **k):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(pd.DataFrame, "to_excel", _boom)
    with pytest.raises(ExcelBusyError) as ei:
        save_excel(pd.DataFrame({"a": [1]}), path)
    assert "busy.xlsx" in str(ei.value)
    assert "关闭该文件后重跑" in str(ei.value)
    assert ei.value.path == path


def test_busy_in_multi_sheet_mode(tmp_path, monkeypatch):
    class _BadWriter:
        def __enter__(self):
            raise PermissionError(13, "locked")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(pd, "ExcelWriter", lambda *a, **k: _BadWriter())
    with pytest.raises(ExcelBusyError):
        save_excel({"s": pd.DataFrame({"a": [1]})}, tmp_path / "locked.xlsx")
