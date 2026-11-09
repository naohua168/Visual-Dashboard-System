# Author: naohua168 <bai_bai168@qq.com>
"""根目录启动器 启动系统.py —— 解释器挑选与转交

只测纯函数与分发分支，不真的拉起 tkinter 界面、不真的换解释器。
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

import 启动系统 as launcher


@pytest.fixture(autouse=True)
def _reset_warnings(monkeypatch):
    """_WARNINGS 是模块级列表，逐例重置，避免互相污染"""
    monkeypatch.setattr(launcher, "_WARNINGS", [])


class TestInterpreterDetection:
    def test_current_env_is_usable(self):
        assert launcher.interpreter_ok() is True

    def test_python_path_txt_ignores_comments(self, tmp_path):
        f = tmp_path / "python_path.txt"
        f.write_text("# 注释\n\n   \n# 还是注释\n", encoding="utf-8")
        assert launcher.configured_python(f) is None

    def test_python_path_txt_directory(self, tmp_path):
        exe_name = "python.exe" if launcher.os.name == "nt" else "python"
        env_dir = tmp_path / "pyenv"
        env_dir.mkdir()
        (env_dir / exe_name).write_text("", encoding="utf-8")
        f = tmp_path / "python_path.txt"
        f.write_text(f"# 说明\n{env_dir}\n", encoding="utf-8")
        assert launcher.configured_python(f) == env_dir / exe_name

    def test_python_path_txt_directory_without_exe_warns(self, tmp_path):
        env_dir = tmp_path / "pyenv"
        env_dir.mkdir()
        f = tmp_path / "python_path.txt"
        f.write_text(f"{env_dir}\n", encoding="utf-8")
        assert launcher.configured_python(f) is None
        assert launcher._WARNINGS and "没有" in launcher._WARNINGS[0]

    def test_python_path_txt_missing_path_warns(self, tmp_path):
        f = tmp_path / "python_path.txt"
        f.write_text(str(tmp_path / "nope"), encoding="utf-8")
        assert launcher.configured_python(f) is None
        assert launcher._WARNINGS and "不存在" in launcher._WARNINGS[0]

    def test_candidates_are_existing_and_unique(self):
        cands = launcher.candidate_interpreters()
        assert cands, "至少要能给出一个候选（当前解释器兜底）"
        assert all(c.exists() for c in cands)
        keys = [launcher.os.path.normcase(str(c)) for c in cands]
        assert len(keys) == len(set(keys))
        assert launcher.os.path.normcase(str(Path(launcher.sys.executable))) in keys


class TestDispatch:
    def test_help(self, capsys):
        assert launcher.main(["--help"]) == 0
        assert "启动系统.py" in capsys.readouterr().out

    def test_delegate_forwards_argv(self, monkeypatch):
        import bin.start as st

        seen = {}
        monkeypatch.setattr(st, "main", lambda argv: (seen.setdefault("argv", argv), 0)[1])
        assert launcher.delegate(["list"]) == 0
        assert seen["argv"] == ["list"]

    def test_usable_env_delegates_directly(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(launcher, "interpreter_ok", lambda: True)
        monkeypatch.setattr(launcher, "delegate", lambda argv: (seen.setdefault("argv", argv), 0)[1])
        assert launcher.main(["--check"]) == 0
        assert seen["argv"] == ["--check"]

    def test_switches_to_candidate_when_current_unusable(self, monkeypatch):
        monkeypatch.setattr(launcher, "interpreter_ok", lambda: False)
        monkeypatch.delenv(launcher.REEXEC_FLAG, raising=False)
        fake = Path("C:/fake/python.exe")
        monkeypatch.setattr(launcher, "candidate_interpreters", lambda: [fake])
        monkeypatch.setattr(launcher, "probe", lambda exe, timeout=60.0: True)

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(launcher.subprocess, "run", fake_run)

        assert launcher.main(["--check"]) == 0
        cmd, kwargs = calls[-1]
        assert str(fake) in cmd[0]
        assert "--check" in cmd
        assert kwargs["env"][launcher.REEXEC_FLAG] == "1"

    def test_reexec_guard_prevents_loop(self, monkeypatch):
        """换过一次仍不合格时不再重启，直接交给 bin/start.py 报错"""
        monkeypatch.setattr(launcher, "interpreter_ok", lambda: False)
        monkeypatch.setenv(launcher.REEXEC_FLAG, "1")
        monkeypatch.setattr(launcher, "delegate", lambda argv: 2)
        assert launcher.main(["--check"]) == 2

    def test_all_candidates_fail(self, monkeypatch, capsys):
        monkeypatch.setattr(launcher, "interpreter_ok", lambda: False)
        monkeypatch.delenv(launcher.REEXEC_FLAG, raising=False)
        monkeypatch.setattr(launcher, "candidate_interpreters", lambda: [])
        assert launcher.main([]) == 2
        assert "没有找到可用的 Python" in capsys.readouterr().err
