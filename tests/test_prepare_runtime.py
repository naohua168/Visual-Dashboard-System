# Author: naohua168 <bai_bai168@qq.com>
"""内置运行时构建脚本 scripts/prepare_runtime.py

只测纯逻辑（URL / _pth 命名与内容），不联网、不装包。
"""
import scripts.prepare_runtime as pr


class TestUrlAndPth:
    def test_embed_url(self):
        url = pr.embed_url("3.12.10")
        assert url == "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"

    def test_pth_name_strips_patch(self):
        assert pr.pth_name("3.12.10") == "python312._pth"
        assert pr.pth_name("3.13.0") == "python313._pth"


class TestWritePth:
    def test_content_enables_site_and_project_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pr, "EMBED_DIR", tmp_path)
        pth = pr.write_pth("3.12.10")

        assert pth.name == "python312._pth"
        lines = pth.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "python312.zip"
        assert "." in lines
        assert r"Lib\site-packages" in lines
        assert r"..\.." in lines            # 让 -m 模式能找到项目根
        assert lines[-1] == "import site"


class TestManifestDefaults:
    def test_core_deps_exclude_pytest(self):
        """运行时只需要跑系统，pytest 属开发依赖，不该打进交付包"""
        assert "pytest" not in pr.CORE_DEPS
        assert set(pr.CORE_DEPS) == {"pandas", "openpyxl", "xlrd"}
