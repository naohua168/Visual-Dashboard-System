# Author: naohua168 <bai_bai168@qq.com>
"""Python 原生入口 bin/app.py —— 子命令分发 / 参数解析 / 退出码"""
import bin.runner as runner
from bin import app


def test_no_args_launches_gui(monkeypatch):
    called = {}

    def fake_gui():
        called["gui"] = True
        return 0

    monkeypatch.setattr(app, "cmd_gui", fake_gui)
    assert app.main([]) == 0
    assert called.get("gui") is True


def test_help_returns_zero(capsys):
    assert app.main(["--help"]) == 0
    assert "python bin/app.py run" in capsys.readouterr().out


def test_unknown_command_returns_2(capsys):
    assert app.main(["bogus"]) == 2
    assert "未知命令" in capsys.readouterr().out


def test_parse_step():
    assert app._parse_keys(["--step=clean"]) == ["clean"]


def test_parse_from():
    assert app._parse_keys(["--from=split"]) == ["split", "render", "report", "verify"]


def test_parse_to():
    assert app._parse_keys(["--to=config"]) == ["scan", "config"]


def test_parse_from_to():
    assert app._parse_keys(["--from=yearly", "--to=split"]) == ["yearly", "clean", "split"]


def test_parse_invalid_step(capsys):
    assert app._parse_keys(["--step=bogus"]) is False
    assert "未知步骤" in capsys.readouterr().out


def test_parse_unknown_arg(capsys):
    """--type 等参数属于 bin/main.py，入口层应提示而不是静默忽略"""
    assert app._parse_keys(["--type=收入"]) is False
    assert "未知参数" in capsys.readouterr().out


def test_run_delegates_to_runner(monkeypatch):
    seen = {}

    def fake_run_all(log=print, keys=None, **kwargs):
        seen["keys"] = keys
        return 0

    monkeypatch.setattr(runner, "run_all", fake_run_all)
    assert app.main(["run", "--step=clean"]) == 0
    assert seen["keys"] == ["clean"]


def _keys(steps):
    return [s.key for s in steps]


def test_sync_prereq_prepended_for_data_steps():
    """分步跑数据处理时，自动补「配置预扫描 + 配置同步」在最前（2026-11-02 用户要求）"""
    pick = lambda k: [s for s in runner.STEPS if s.key == k]  # noqa: E731
    assert _keys(runner.with_sync_prereq(pick("render"), ["render"])) == ["scan", "config", "render"]
    assert _keys(runner.with_sync_prereq(pick("clean") + pick("split"),
                                         ["clean", "split"])) == ["scan", "config", "clean", "split"]
    # 只跑同步类步骤（--to=config）→ 不重复插入
    assert _keys(runner.with_sync_prereq(pick("scan") + pick("config"),
                                         ["scan", "config"])) == ["scan", "config"]
    # 全量运行（keys=None）→ 原样（本身已含两步）
    assert _keys(runner.with_sync_prereq(list(runner.STEPS), None)) == _keys(runner.STEPS)


def test_sync_prereq_skipped_when_no_data_step():
    """只跑 verify / report 时不强行前置（它们不产生清洗结果）"""
    pick = lambda k: [s for s in runner.STEPS if s.key == k]  # noqa: E731
    assert _keys(runner.with_sync_prereq(pick("verify"), ["verify"])) == ["verify"]


def test_board_without_files(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(app, "BASE_DIR", tmp_path)
    assert app.main(["board"]) == 2
    assert "未找到看板文件" in capsys.readouterr().out


def test_gui_failure_falls_back(monkeypatch, capsys):
    """无 tkinter / 界面异常 → 回退传统控制台（回退结果置 2，避免真的弹窗）"""
    import bin.gui as gui_mod

    def boom():
        raise RuntimeError("no tk")

    monkeypatch.setattr(gui_mod, "main", boom)
    monkeypatch.setattr(app, "_fallback_ps_gui", lambda: 2)
    assert app.main(["gui"]) == 2
    assert "回退传统控制台" in capsys.readouterr().out


def test_fallback_without_ps1(monkeypatch, tmp_path):
    """回退脚本不存在时返回 2（不抛异常）"""
    monkeypatch.setattr(app, "BASE_DIR", tmp_path)
    assert app._fallback_ps_gui() == 2
