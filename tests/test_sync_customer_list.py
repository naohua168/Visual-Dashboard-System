# Author: naohua168 <bai_bai168@qq.com>
"""「销售归属 → 客户名单」自动同步测试（2026-11-02 用户口径）

规则：全量同步归属表客户 → 名单；**只加不删**；无新增不碰文件；有新增先备份；
      黑名单（法人自身名/占位行）不写；全角半角/空白/大小写视为同一家；
      名单文件被 Excel 占用 → status=locked，不抛异常。
"""
import importlib.util
from pathlib import Path

import openpyxl

_SPEC = importlib.util.spec_from_file_location(
    "sync_customer_list", Path(__file__).parent.parent / "scripts" / "sync_customer_list.py"
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)

quiet = lambda *a, **k: None  # noqa: E731


# ── 辅助 ──────────────────────────────────────────────────────
def _make_list(path: Path, names) -> Path:
    """造一份名单 Excel（第 1 行表头「客户」）"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.cell(row=1, column=1, value="客户")
    for i, n in enumerate(names, start=2):
        ws.cell(row=i, column=1, value=n)
    wb.save(path)
    return path


def _attr(*pairs) -> dict:
    """[(父组, 客户名), …] → 归属 dict（结构与 客户销售归属.json 一致）"""
    out: dict = {}
    for parent, name in pairs:
        out.setdefault(parent, {"子公司": {}})["子公司"][name] = {
            "收入": {"检测": {"王海龙": 1.0}},
            "回款": {"检测": {"王海龙": 1.0}},
        }
    return out


def _read(path: Path) -> list[str]:
    ws = openpyxl.load_workbook(path).active
    return [str(r[0]).strip() for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0]]


# ── 新增 / 幂等 ───────────────────────────────────────────────
class TestAdd:
    def test_adds_missing_only(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", ["甲科技有限公司"])
        att = _attr(("科技公司·王海龙", "甲科技有限公司"),
                    ("科技公司·王海龙", "乙科技有限公司"))
        res = mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["status"] == "updated"
        assert res["added"] == ["乙科技有限公司"]
        assert res["total"] == 2
        assert _read(f) == ["甲科技有限公司", "乙科技有限公司"]

    def test_idempotent_second_run_does_nothing(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", [])
        att = _attr(("科技公司·王海龙", "乙科技有限公司"))
        mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        mtime = f.stat().st_mtime_ns
        res = mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["status"] == "unchanged"
        assert res["added"] == []
        assert f.stat().st_mtime_ns == mtime, "无新增时不应重写文件"
        assert _read(f) == ["乙科技有限公司"]

    def test_empty_list_adds_header_first_row(self, tmp_path):
        """名单只有表头时也能正常追加（数据从第 2 行开始）"""
        f = _make_list(tmp_path / "客户名单.xlsx", [])
        res = mod.sync_customer_list(_attr(("A", "丙科技有限公司")), path=f,
                                     backup_dir=tmp_path / "bak", log=quiet)
        assert res["total"] == 1
        assert _read(f) == ["丙科技有限公司"]


# ── 只加不删 / 去重 ───────────────────────────────────────────
class TestKeep:
    def test_existing_customers_never_deleted(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", ["老客户有限公司", "甲科技有限公司"])
        att = _attr(("科技公司·王海龙", "甲科技有限公司"))
        res = mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["status"] == "unchanged"
        assert _read(f) == ["老客户有限公司", "甲科技有限公司"]

    def test_fullwidth_variant_not_added_twice(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", ["法雷奥汽车内部控制(深圳)有限公司"])
        att = _attr(("科技公司·王海龙", "法雷奥汽车内部控制（深圳）有限公司"))
        res = mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["status"] == "unchanged"
        assert len(_read(f)) == 1

    def test_same_customer_in_two_parents_added_once(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", [])
        att = _attr(("A 组", "丁科技有限公司"), ("B 组", "丁科技有限公司"))
        res = mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["added"] == ["丁科技有限公司"]


# ── 黑名单 / 排除父组 ────────────────────────────────────────
class TestExclude:
    def test_legal_entity_and_placeholders_skipped(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", [])
        att = _attr(("广东自有客户", "广东汽车检测中心有限公司"),
                    ("广东自有客户", "合计"),
                    ("科技公司·王海龙", "戊科技有限公司"))
        res = mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["added"] == ["戊科技有限公司"]

    def test_skip_parents_from_rules(self, tmp_path, monkeypatch):
        f = _make_list(tmp_path / "客户名单.xlsx", [])
        monkeypatch.setattr(mod.br, "customer_list_sync_rules",
                            lambda: {"排除父组": ["广东自有客户"], "排除客户": [], "备份保留份数": 5})
        att = _attr(("广东自有客户", "己科技有限公司"), ("科技公司·王海龙", "庚科技有限公司"))
        res = mod.sync_customer_list(att, path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["added"] == ["庚科技有限公司"]

    def test_collect_dedup_and_skip(self):
        att = _attr(("A", "甲"), ("B", "甲"), ("广东自有客户", "乙"))
        assert mod.collect_customers(att) == [("甲", "A"), ("乙", "广东自有客户")]
        assert mod.collect_customers(att, skip_parents=["广东自有客户"]) == [("甲", "A")]
        assert mod.collect_customers(att, skip_customers=["甲"]) == [("乙", "广东自有客户")]


# ── dry-run / 备份 / 文件占用 ────────────────────────────────
class TestSafety:
    def test_dry_run_does_not_write(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", ["甲科技有限公司"])
        before = f.read_bytes()
        res = mod.sync_customer_list(_attr(("A", "乙科技有限公司")), dry_run=True,
                                     path=f, backup_dir=tmp_path / "bak", log=quiet)
        assert res["status"] == "would_update"
        assert res["total"] == 2
        assert f.read_bytes() == before
        assert not (tmp_path / "bak").exists(), "dry-run 不应产生备份"

    def test_backup_created_and_pruned(self, tmp_path):
        f = _make_list(tmp_path / "客户名单.xlsx", [])
        bak = tmp_path / "bak"
        for i in range(4):
            mod.sync_customer_list(_attr(("A", f"客户{i}有限公司")), path=f,
                                   backup_dir=bak, keep=2, log=quiet)
        kept = list(bak.glob("*.xlsx"))
        assert len(kept) == 2, f"备份应只保留 2 份，实际 {len(kept)}"
        assert len(_read(f)) == 4

    def test_locked_file_returns_status(self, tmp_path, monkeypatch):
        f = _make_list(tmp_path / "客户名单.xlsx", [])

        def _raise(wb, p):
            raise PermissionError("文件被 Excel 占用")

        monkeypatch.setattr(mod, "save_workbook", _raise)
        res = mod.sync_customer_list(_attr(("A", "辛科技有限公司")), path=f,
                                     backup_dir=tmp_path / "bak", log=quiet)
        assert res["status"] == "locked"
        assert _read(f) == [], "写失败时原文件保持不变"

    def test_missing_list_returns_status(self, tmp_path):
        res = mod.sync_customer_list(_attr(("A", "壬科技有限公司")),
                                     path=tmp_path / "不存在.xlsx", log=quiet)
        assert res["status"] == "missing"
