# Author: naohua168 <bai_bai168@qq.com>
"""年基线 `--source` 覆盖模式测试（2026-09-29 修复）

原问题：① 目录里没有 xlsx 时 `results` 未绑定 → UnboundLocalError；
        ② 同一类型下多个 xlsx 只取第一个（漏算）。
"""
import sys

import pandas as pd

import engine.yearly_baseline.run as yr


def test_source_empty_dir_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run", f"--source={tmp_path}"])
    assert yr.main() == 1                      # 以前是 UnboundLocalError
    out = capsys.readouterr().out
    assert "没有可用的 xlsx" in out


def test_source_missing_path_returns_1(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["run", f"--source={tmp_path / '不存在.xlsx'}"])
    assert yr.main() == 1


def test_source_multi_files_merged_per_type(tmp_path, monkeypatch):
    """同一类型两个文件 → 合并写入一份（行数 = 两文件之和）"""
    for name in ("2024-01月.xlsx", "2024-02月.xlsx"):
        (tmp_path / name).write_bytes(b"placeholder")   # 内容无所谓：clean_yearly 打桩
    frames = {"收入": pd.DataFrame({"金额": [1.0, 2.0]}), "回款": pd.DataFrame({"金额": [3.0]})}
    calls = []

    def _fake_clean(source_dir=None, mapper=None, **kw):
        calls.append(source_dir)
        return {k: v.copy() for k, v in frames.items()}

    monkeypatch.setattr(yr, "clean_yearly", _fake_clean)
    monkeypatch.setattr(sys, "argv", ["run", f"--source={tmp_path}"])

    assert yr.main() == 0
    # 无子目录时两种类型共用同一批文件 → 2 个文件 × 2 个类型 = 4 次调用（两个文件都处理了）
    assert len(calls) == 4

    inc = pd.read_excel(tmp_path / "往年收入" / "往年收入.xlsx")
    pay = pd.read_excel(tmp_path / "往年回款" / "往年回款.xlsx")
    assert len(inc) == 4                        # 2 文件 × 2 行
    assert len(pay) == 2


def test_source_subdirs(tmp_path, monkeypatch):
    """目录模式下优先用 往年收入数据/往年回款数据 子目录"""
    (tmp_path / "往年收入数据").mkdir()
    (tmp_path / "往年收入数据" / "a.xlsx").write_bytes(b"x")
    monkeypatch.setattr(yr, "clean_yearly",
                        lambda source_dir=None, mapper=None, **kw: {"收入": pd.DataFrame({"金额": [1.0]})})
    monkeypatch.setattr(sys, "argv", ["run", f"--source={tmp_path}"])
    assert yr.main() == 0
    assert (tmp_path / "往年收入数据" / "往年收入" / "往年收入.xlsx").exists()
