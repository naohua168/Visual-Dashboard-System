# Author: naohua168 <bai_bai168@qq.com>
"""启动引导 bin/start.py —— 环境自检与转交逻辑

只测纯函数与分发分支，不真的拉起 tkinter 界面。
"""
import bin.start as st


class TestChecks:
    def test_python_version_ok_on_this_env(self):
        assert st.check_python().status == st.OK

    def test_python_version_blocks_when_too_new_requirement(self):
        c = st.check_python(minimum=(99, 0))
        assert c.status == st.FAIL
        assert "需要 99.0" in c.hint

    def test_packages_present(self):
        assert st.check_packages().status == st.OK

    def test_tkinter_never_fails_the_startup(self):
        """tkinter 缺失只降级（回退 WPF），不能拦启动"""
        assert st.check_tkinter().status in (st.OK, st.WARN)

    def test_collect_checks_covers_core_items(self):
        names = [c.name for c in st.collect_checks()]
        assert "Python 版本" in names
        assert "依赖包" in names
        assert "输出目录" in names


class TestFormat:
    def test_has_blocking(self):
        assert st.has_blocking([st.Check("x", st.FAIL)])
        assert not st.has_blocking([st.Check("x", st.OK), st.Check("y", st.WARN)])

    def test_format_contains_name_and_hint(self):
        text = st.format_checks([st.Check("依赖包", st.FAIL, "缺少 pandas", "pip install pandas")])
        assert "依赖包" in text
        assert "pip install pandas" in text


class TestDispatch:
    def test_help(self):
        assert st.main(["--help"]) == 0

    def test_check_only_passes_in_repo(self):
        assert st.main(["--check"]) == 0

    def test_blocking_check_stops_before_gui(self, monkeypatch, capsys):
        monkeypatch.setattr(st, "collect_checks", lambda: [st.Check("依赖包", st.FAIL, "缺少 pandas")])
        called = {}
        monkeypatch.setitem(__import__("sys").modules, "bin.app",
                            type("M", (), {"main": staticmethod(lambda argv: called.setdefault("hit", True) or 0)}))
        assert st.main([]) == 2
        assert "自检未通过" in capsys.readouterr().out
        assert "hit" not in called

    def test_argv_passthrough(self, monkeypatch):
        """非 --cli 参数原样转交 bin/app.py（report / list / board / run ...）"""
        seen = {}
        import bin.app as app_mod

        monkeypatch.setattr(st, "collect_checks", lambda: [st.Check("x", st.OK)])

        def fake_app(argv):
            seen["argv"] = argv
            return 0

        monkeypatch.setattr(app_mod, "main", fake_app)
        assert st.main(["report"]) == 0
        assert seen["argv"] == ["report"]

    def test_cli_flag_maps_to_run(self, monkeypatch):
        seen = {}
        import bin.app as app_mod

        monkeypatch.setattr(st, "collect_checks", lambda: [st.Check("x", st.OK)])

        def fake_app(argv):
            seen["argv"] = argv
            return 0

        monkeypatch.setattr(app_mod, "main", fake_app)
        assert st.main(["--cli", "--step=render"]) == 0
        assert seen["argv"] == ["run", "--step=render"]
