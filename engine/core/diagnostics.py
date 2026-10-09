# Author: naohua168 <bai_bai168@qq.com>
"""运行期数据质量诊断 —— 丢弃行落盘 + 问题汇总（2026-09-29 新增）

解决的三个"静默"问题：
  1. 客户白名单未命中的行**直接被丢弃**，只在控制台留一行日志 → 现在写进诊断报告
     （`output/数据校验/数据质量摘要_<运行号>.xlsx` 的「未匹配明细」sheet：来源/客户名/金额/日期），
     收尾打印总行数与总金额；
  2. 关键来源（财务端主表 / 广东 / 湖南 / 南方韶关）**读取失败或空表**只在日志里 WARN → 现在记入问题清单，
     收尾统一红色汇总；
  3. 只校验 HTML、不校验交付物是否齐全 → 由 `scripts/verify_dashboard.py` 与 `main.py` 收尾摘要承接。

设计要点：
  · **一次运行只产出一个文件**（用户口径 2026-09-29）：`output/数据校验/数据质量摘要_<运行号>.xlsx`，
    含 概览 / 问题清单 / 丢弃汇总 / 未匹配明细 4 个 sheet；
  · 各步骤在**独立子进程**里跑，所以步骤先把诊断落成中间件 JSON（`数据质量摘要_<步骤>_<运行号>.json`），
    由 `main.py` 收尾 `finalize()` 合并成那唯一一个 xlsx 并删除中间件；单独跑某一步时该步骤自己合并；
  · 级别：`ERROR` = 会导致数据不完整（读取失败等），收尾返回非零；`WARN` = 需要人看一眼（空表、丢弃行等）；
  · 落盘目录读配置 `输出.数据校验`，缺省回落 `output/数据校验/`。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

LEVEL_ORDER = {"INFO": 0, "WARN": 1, "ERROR": 2}
DEFAULT_OUT_REL = "output/数据校验"
DEFAULT_OUTPUT_DIR_NAME = "数据校验"
SUMMARY_PREFIX = "数据质量摘要_"
# 批处理运行号：main.py 启动时设置并传给子进程；单独跑某一步时为空（该步骤自己合并报告）
RUN_ID_ENV = "VD_RUN_ID"
# 数据校验目录重定向（测试/临时运行用，优先于配置）：填相对路径按项目根解析
DIAG_DIR_ENV = "VD_DIAG_DIR"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class Diagnostics:
    """一次运行（或一个步骤）里攒下来的问题清单与丢弃行"""

    def __init__(self) -> None:
        self.issues: list[dict] = []   # {级别, 来源, 说明, 时间}
        self.rejects: list[dict] = []  # {来源, 客户名, 金额, 日期}

    # ── 记录 ──────────────────────────────────────────────────
    def note(self, level: str, source: str, message: str) -> None:
        """记一条问题（level: INFO/WARN/ERROR）"""
        self.issues.append({"级别": level, "来源": source, "说明": message, "时间": _now()})

    def note_rejects(self, source: str, rows) -> int:
        """记一批白名单未匹配行（rows 里每项含 客户名/金额/日期）"""
        for r in rows:
            self.rejects.append({
                "来源": source,
                "客户名": str(r.get("客户名", "")).strip(),
                "金额": float(r.get("金额", 0) or 0),
                "日期": str(r.get("日期", "") or ""),
            })
        return len(rows)

    # ── 汇总 ──────────────────────────────────────────────────
    def counts(self) -> dict[str, int]:
        out = {k: 0 for k in LEVEL_ORDER}
        for it in self.issues:
            lv = str(it.get("级别", "INFO")).upper()
            out[lv] = out.get(lv, 0) + 1
        return out

    def has_error(self) -> bool:
        return self.counts().get("ERROR", 0) > 0

    def reject_summary(self) -> list[dict]:
        """按来源汇总丢弃行 → [{来源, 行数, 金额}]"""
        if not self.rejects:
            return []
        df = pd.DataFrame(self.rejects)
        g = df.groupby("来源", as_index=False).agg(行数=("客户名", "size"), 金额=("金额", "sum"))
        return g.sort_values("行数", ascending=False).to_dict("records")

    def reject_totals(self) -> tuple[int, float]:
        return len(self.rejects), float(sum(r["金额"] for r in self.rejects))

    def summary_lines(self, limit: int = 8) -> list[str]:
        """控制台摘要（不含明细客户名，只给条数/金额）"""
        c = self.counts()
        n_rej, amt_rej = self.reject_totals()
        lines = []
        if n_rej:
            lines.append(f"白名单未匹配丢弃: {n_rej} 行 / {amt_rej / 10000:,.1f} 万元"
                         f"（明细见 数据校验 目录「未匹配明细」sheet）")
        for lv in ("ERROR", "WARN"):
            items = [it for it in self.issues if str(it.get("级别", "")).upper() == lv]
            if not items:
                continue
            icon = "❌" if lv == "ERROR" else "⚠️"
            lines.append(f"{icon} {lv} {len(items)} 条:")
            for it in items[:limit]:
                lines.append(f"    - [{it.get('来源', '')}] {it.get('说明', '')}")
            if len(items) > limit:
                lines.append(f"    … 另 {len(items) - limit} 条（见摘要文件）")
        if not lines:
            lines.append("✅ 未发现数据质量问题")
        lines.append(f"（问题合计 E{c.get('ERROR', 0)} / W{c.get('WARN', 0)}）")
        return lines

    # ── 序列化 / 落盘 ──────────────────────────────────────────
    def to_dict(self) -> dict:
        return {"issues": self.issues, "rejects": self.rejects,
                "counts": self.counts(), "生成时间": _now()}

    @classmethod
    def from_dict(cls, data: dict) -> "Diagnostics":
        d = cls()
        d.issues = list(data.get("issues", []))
        d.rejects = list(data.get("rejects", []))
        return d

    def merge(self, other: "Diagnostics") -> None:
        self.issues.extend(other.issues)
        self.rejects.extend(other.rejects)

    def write_reports(self, out_dir, step: str = "清洗", stamp: str | None = None) -> list[Path]:
        """落盘本步骤诊断 → 返回**本次运行最终交付的那个文件**

        批处理模式（main.py 已设 `VD_RUN_ID`）：只写中间件 JSON，返回 [json]；
        由 main.py 收尾 `finalize()` 合并成唯一一个 xlsx 并删除中间件。
        单独跑某一步（无运行号）：本步骤立刻合并，返回 [那一个 xlsx]。

        超过 RETENTION_DAYS 天的旧报告自动清理，目录不会无限堆积。
        """
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        prune_old_reports(out)
        rid = stamp or current_run_id() or _stamp()

        js = out / f"{SUMMARY_PREFIX}{step}_{rid}.json"
        js.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        if current_run_id():
            return [js]

        finalize(out, rid)
        return [report_path(out, rid)]


# ── 模块级单例（与 log_step 同风格，各步骤内部直接用） ──────────────
DIAG = Diagnostics()

RETENTION_DAYS = 14      # 诊断文件保留天数（只清理本模块产出的文件）


def current_run_id() -> str:
    """批处理运行号（main.py 通过环境变量传入）；单独跑某一步时为空串"""
    return os.environ.get(RUN_ID_ENV, "").strip()


def report_path(out_dir, rid: str) -> Path:
    """本次运行的唯一报告文件"""
    return Path(out_dir) / f"{SUMMARY_PREFIX}{rid}.xlsx"


def _pending_reports(out: Path, rid: str) -> list[Path]:
    """本次运行各步骤写的中间件（按步骤名排序，便于概览排列稳定）"""
    return sorted(out.glob(f"{SUMMARY_PREFIX}*_{rid}.json"))


def finalize(out_dir, rid: str | None = None) -> tuple[Diagnostics, Path | None]:
    """收尾：合并本次运行的中间件 → **唯一一个 xlsx**（概览/问题清单/丢弃汇总/未匹配明细）→ 删中间件

    Returns:
        (合并后的诊断, 落盘文件)；没有中间件时返回 (空诊断, None)（不生成空报告）

    注意：只有 xlsx 写成功了才删中间件 —— 写失败时保留证据，便于排查。
    """
    out = Path(out_dir)
    rid = (rid or current_run_id() or _stamp()).strip()
    merged = Diagnostics()
    rows: list[dict] = []
    files: list[Path] = []
    for f in _pending_reports(out, rid):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        part = Diagnostics.from_dict(data)
        merged.merge(part)
        c = part.counts()
        n_rej, amt_rej = part.reject_totals()
        step = f.name[len(SUMMARY_PREFIX):-(len(rid) + 1 + len(".json"))] or "?"
        rows.append({
            "步骤": step, "ERROR": c.get("ERROR", 0), "WARN": c.get("WARN", 0), "INFO": c.get("INFO", 0),
            "丢弃行数": n_rej, "丢弃金额(元)": round(amt_rej, 2), "生成时间": data.get("生成时间", ""),
        })
        files.append(f)

    if not files:
        return merged, None

    totals = {
        "步骤": "合计", "ERROR": sum(r["ERROR"] for r in rows), "WARN": sum(r["WARN"] for r in rows),
        "INFO": sum(r["INFO"] for r in rows), "丢弃行数": sum(r["丢弃行数"] for r in rows),
        "丢弃金额(元)": round(sum(r["丢弃金额(元)"] for r in rows), 2), "生成时间": _now(),
    }
    xls = report_path(out, rid)
    with pd.ExcelWriter(xls, engine="openpyxl") as w:
        pd.DataFrame([*rows, totals]).to_excel(w, sheet_name="概览", index=False)
        pd.DataFrame(merged.issues or [{"级别": "", "来源": "", "说明": "无", "时间": ""}]
                     ).to_excel(w, sheet_name="问题清单", index=False)
        pd.DataFrame(merged.reject_summary() or [{"来源": "", "行数": 0, "金额": 0.0}]
                     ).to_excel(w, sheet_name="丢弃汇总", index=False)
        pd.DataFrame(merged.rejects or [{"来源": "", "客户名": "（本次运行无丢弃行）", "金额": 0.0, "日期": ""}]
                     ).to_excel(w, sheet_name="未匹配明细", index=False)

    for f in files:  # 合并成功 → 中间件不留痕
        try:
            f.unlink()
        except OSError:
            pass
    return merged, xls


def prune_old_reports(out_dir, keep_days: int = RETENTION_DAYS) -> list[Path]:
    """清理过期的诊断文件；文件名里解析不出日期的（人工放的）一律不动

    含两类历史遗留命名（`白名单未匹配行_*.xlsx`、`数据质量摘要_<步骤>_*.json`）——
    它们只会在改版前产生的目录里出现，同样按日期淘汰，不再新产出。
    """
    out = Path(out_dir)
    if not out.exists():
        return []
    cutoff = datetime.now() - timedelta(days=keep_days)
    removed: list[Path] = []
    patterns = ("白名单未匹配行_*.xlsx", f"{SUMMARY_PREFIX}*.json", f"{SUMMARY_PREFIX}*.xlsx")
    for pattern in patterns:
        for f in out.glob(pattern):
            m = re.search(r"(\d{8})_\d{6}", f.name)
            if not m:
                continue
            try:
                made = datetime.strptime(m.group(1), "%Y%m%d")
            except ValueError:
                continue
            if made < cutoff:
                try:
                    f.unlink()
                    removed.append(f)
                except OSError:
                    continue
    return removed


def note_issue(level: str, source: str, message: str) -> None:
    DIAG.note(level, source, message)


def note_rejects(source: str, rows) -> int:
    return DIAG.note_rejects(source, rows)


def write_reports(out_dir, step: str = "清洗", stamp: str | None = None) -> list[Path]:
    """落盘本步骤诊断：批处理下只写中间件 JSON；单独运行时直接产出唯一报告"""
    return DIAG.write_reports(out_dir, step=step, stamp=stamp)


def summary_lines(limit: int = 8) -> list[str]:
    return DIAG.summary_lines(limit=limit)


def reset() -> None:
    """清空（测试用）"""
    global DIAG
    DIAG = Diagnostics()


def output_dir(config: dict | None = None, base_dir: Path | None = None) -> Path:
    """数据校验目录：环境变量 `VD_DIAG_DIR` 优先（测试/临时重定向），否则读配置 `输出.数据校验`，缺失回落 output/数据校验/

    为什么要环境变量：测试跑真实流水线时不能污染正式目录（否则 `output/数据校验/` 会
    被测试产出的报告塞满），子进程天然继承该变量。
    """
    root = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent
    redirect = os.environ.get(DIAG_DIR_ENV, "").strip()
    if redirect:
        p = Path(redirect)
        return p if p.is_absolute() else root / p
    rel = DEFAULT_OUT_REL
    try:
        rel = (config or {}).get("输出", {}).get(DEFAULT_OUTPUT_DIR_NAME, DEFAULT_OUT_REL)
    except Exception:
        rel = DEFAULT_OUT_REL
    return root / str(rel)


def print_summary(title: str = "数据质量汇总", limit: int = 8) -> bool:
    """打印摘要；返回是否含 ERROR（供调用方决定退出码）"""
    print(f"\n{'─' * 56}")
    print(f"  {title}")
    print(f"{'─' * 56}")
    for line in DIAG.summary_lines(limit=limit):
        print("  " + line)
    print(f"{'─' * 56}")
    return DIAG.has_error()


def collect_step_reports(out_dir, date_prefix: str | None = None) -> Diagnostics:
    """只读合并：把某天（默认今天）的中间件 JSON 合起来，**不写文件、不删除**

    历史行为保持（测试/排查用）。正式收尾请用 `finalize()` —— 它才会产出唯一报告并清中间件。
    """
    out = Path(out_dir)
    merged = Diagnostics()
    if not out.exists():
        return merged
    prefix = date_prefix or datetime.now().strftime("%Y%m%d")
    files = sorted(out.glob(f"{SUMMARY_PREFIX}*_{prefix}*.json"))
    for f in files:
        try:
            merged.merge(Diagnostics.from_dict(json.loads(f.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return merged
