# Author: naohua168 <bai_bai168@qq.com>
"""打包脚本 bin/package.py —— 清单与目录骨架

只测纯逻辑（不实际复制 110MB 运行时、不生成 zip）。
"""
import bin.package as pkg


class TestManifest:
    def test_core_code_included(self):
        rels = {rel.as_posix() for _, rel in pkg.build_manifest()}
        for name in ("engine", "processors", "config", "bin", "scripts", "docs"):
            assert name in rels
        assert "requirements.txt" in rels

    def test_entry_dir_has_no_bat(self):
        """入口层（bin/）已全 Python，不应再有 .bat 启动器"""
        assert not list((pkg.BASE_DIR / "bin").glob("*.bat"))

    def test_data_and_runtime(self):
        rels = {rel.as_posix() for _, rel in pkg.build_manifest()}
        assert "data/raw" in rels
        assert "data/sheets/手动维护" in rels


class TestSkeletons:
    def test_creates_output_and_clean_skeleton(self, tmp_path):
        pkg.make_skeletons(tmp_path)
        assert (tmp_path / "output" / "看板").is_dir()
        assert (tmp_path / "output" / "数据").is_dir()
        assert (tmp_path / "output" / "销售完成度").is_dir()
        assert (tmp_path / "output" / "客户矩阵").is_dir()
        assert (tmp_path / "logs").is_dir()
        for name in ("当年累计收入", "销售收入", "往年回款"):
            assert (tmp_path / "data" / "sheets" / "系统数据清理" / name).is_dir()

    def test_ignore_patterns_skip_pycache(self, tmp_path):
        """copytree 的忽略规则要挡住 __pycache__ / pyc / Excel 锁文件"""
        src = tmp_path / "src"
        (src / "__pycache__").mkdir(parents=True)
        (src / "__pycache__" / "a.pyc").write_bytes(b"x")
        (src / "a.pyc").write_bytes(b"x")
        (src / "~$lock.xlsx").write_bytes(b"x")
        (src / "keep.py").write_text("x", encoding="utf-8")
        dst = tmp_path / "dst"
        pkg.copy_item(src, dst)
        assert (dst / "keep.py").exists()
        assert not (dst / "__pycache__").exists()
        assert not (dst / "a.pyc").exists()
        assert not (dst / "~$lock.xlsx").exists()
