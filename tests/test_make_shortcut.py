# Author: naohua168 <bai_bai168@qq.com>
"""快捷方式生成 bin/make_shortcut.py

只测计划与 --dry-run（真正创建 .lnk 需要 COM，交给人工验收）。
"""
import os

import pytest

import bin.make_shortcut as ms


class TestPlan:
    def test_target_prefers_bundled_runtime(self):
        target = ms.resolve_pythonw()
        assert target is not None
        assert target.name.lower() in ("pythonw.exe", "python.exe")

    def test_plan_fields(self, tmp_path):
        plan = ms.shortcut_plan("测试入口", tmp_path)
        assert plan.lnk == tmp_path / "测试入口.lnk"
        assert plan.arguments == r"bin\app.py"
        assert plan.workdir == ms.BASE_DIR
        assert plan.description


class TestMain:
    def test_dry_run_creates_nothing(self, tmp_path, capsys):
        rc = ms.main(["--dry-run", "--dest", str(tmp_path), "--name", "甲"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "未实际创建" in out
        assert not (tmp_path / "甲.lnk").exists()

    @pytest.mark.skipif(os.name != "nt", reason=".lnk 仅 Windows")
    def test_desktop_dir_is_absolute(self):
        assert ms.desktop_dir().is_absolute()
