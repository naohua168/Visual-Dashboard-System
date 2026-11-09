# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""销售完成度表 · 生成对话框（可选数据版本）

2026-11-06 用户要求：这张表也要能指定「哪一期看板」的数据，而不是只能用当前清洗结果。
交互与「按客户清单导出矩阵」保持一致：数据版本下拉（最新 / 历史 `data_*.xlsx` / 手工选看板）。
"""
from __future__ import annotations

import datetime
import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from bin.snapshot_list import SNAP_LATEST, add_custom_choice, data_root, load_snapshot_choices
from engine.core.output_paths import snapshot_day
from scripts.sales_summary_report import generate, output_dir


class SalesReportDialog(tk.Toplevel):
    def __init__(self, master, base_dir: Path, log=None):
        super().__init__(master)
        self.base_dir = Path(base_dir)
        self._log_cb = log or (lambda _s: None)
        self.queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.snap_map: dict[str, Path | None] = {}
        self._auto_out = True
        self._busy = False
        try:   # 按 DPI 缩放窗口（字体用点单位已自动缩放）
            self.scale = max(1.0, float(self.winfo_fpixels("1i")) / 96.0)
        except tk.TclError:
            self.scale = 1.0

        self.title("生成销售完成度表")
        self.configure(bg="#f5f5f7")
        self.transient(master)
        self.resizable(False, False)
        self._build()
        self._load_snapshots()
        self.update_idletasks()
        self._center(master)
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 布局 ────────────────────────────────────────────────
    def _build(self) -> None:
        f_base = ("Microsoft YaHei UI", 10)
        f_sm = ("Microsoft YaHei UI", 9)
        f_bold = ("Microsoft YaHei UI", 10, "bold")

        body = ttk.Frame(self, padding=(16, 14))
        body.pack(fill="both", expand=True)

        row1 = ttk.Frame(body)
        row1.pack(fill="x")
        ttk.Label(row1, text="数据版本", font=f_bold).pack(side="left")
        self.cmb_snap = ttk.Combobox(row1, state="readonly", font=f_base, width=38)
        self.cmb_snap.pack(side="left", padx=(12, 6), fill="x", expand=True)
        self.cmb_snap.bind("<<ComboboxSelected>>", self._on_snap_change)
        ttk.Button(row1, text="选看板/总表…", command=self._pick_snapshot).pack(side="left")

        ttk.Label(body, text="选择某一期的看板（或数据总表）→ 按那一期出表；默认用当前清洗结果。",
                  font=f_sm, foreground="#6e6e73").pack(anchor="w", pady=(6, 0))

        row2 = ttk.Frame(body)
        row2.pack(fill="x", pady=(12, 0))
        ttk.Label(row2, text="输出文件", font=f_bold).pack(side="left")
        self.ent_out = ttk.Entry(row2, font=f_base, width=52)
        self.ent_out.pack(side="left", padx=(12, 6), fill="x", expand=True)
        self.ent_out.bind("<KeyRelease>", self._mark_manual)
        ttk.Button(row2, text="浏览…", width=7, command=self._pick_out).pack(side="left")

        foot = ttk.Frame(body)
        foot.pack(fill="x", pady=(14, 0))
        self.lbl_state = ttk.Label(foot, text="就绪", font=f_sm, foreground="#6e6e73")
        self.lbl_state.pack(side="left")
        self.btn_gen = ttk.Button(foot, text="生成", width=12, command=self._on_generate)
        self.btn_gen.pack(side="right")
        ttk.Button(foot, text="关闭", width=8, command=self._on_close).pack(side="right", padx=(0, 8))

        self.geometry(f"{int(760 * self.scale)}x{int(230 * self.scale)}")
        self.minsize(int(680 * self.scale), int(230 * self.scale))

    def _center(self, master) -> None:
        try:
            x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
            y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
            self.geometry(f"+{max(x, 40)}+{max(y, 40)}")
        except tk.TclError:
            pass

    # ── 数据版本 ────────────────────────────────────────────
    def _load_snapshots(self) -> None:
        self.snap_map = load_snapshot_choices(self.base_dir)
        self.cmb_snap.configure(values=list(self.snap_map))
        self.cmb_snap.set(SNAP_LATEST)
        self._refresh_default_out()

    def _current_snapshot(self) -> Path | None:
        return self.snap_map.get(self.cmb_snap.get())

    def _on_snap_change(self, _event=None) -> None:
        if self._auto_out:
            self._refresh_default_out()

    def _pick_snapshot(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="选择看板 HTML 或数据总表",
            initialdir=str(data_root(self.base_dir)),
            filetypes=[("看板/数据总表", "*.html;data_*.xlsx"), ("所有文件", "*.*")],
        )
        if not path:
            return
        label = add_custom_choice(self.snap_map, Path(path))
        self.cmb_snap.configure(values=list(self.snap_map))
        self.cmb_snap.set(label)
        if self._auto_out:
            self._refresh_default_out()

    # ── 输出路径 ────────────────────────────────────────────
    def _default_out(self) -> Path:
        snap = self._current_snapshot()
        day = (snapshot_day(snap) if snap else None) or datetime.date.today().strftime("%Y%m%d")
        when = datetime.datetime.strptime(day, "%Y%m%d").date()
        return output_dir(when) / f"销售完成度汇总_{day}.xlsx"

    def _refresh_default_out(self) -> None:
        self.ent_out.delete(0, "end")
        self.ent_out.insert(0, str(self._default_out()))
        self._auto_out = True

    def _mark_manual(self, _event=None) -> None:
        self._auto_out = False

    def _pick_out(self) -> None:
        cur = Path(self.ent_out.get().strip() or self._default_out())
        path = filedialog.asksaveasfilename(
            parent=self, title="保存销售完成度表", defaultextension=".xlsx",
            initialdir=str(cur.parent if cur.parent.exists() else self.base_dir),
            initialfile=cur.name, filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            self.ent_out.delete(0, "end")
            self.ent_out.insert(0, path)
            self._auto_out = False

    # ── 生成 ────────────────────────────────────────────────
    def _on_generate(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        text = self.ent_out.get().strip()
        if not text:
            messagebox.showwarning("未填输出", "请填写输出文件路径。", parent=self)
            return
        out = Path(text)
        if not out.is_absolute():
            out = self.base_dir / out
        if out.suffix.lower() != ".xlsx":
            out = out.with_suffix(".xlsx")
        if out.exists() and not messagebox.askyesno("覆盖确认", f"{out.name} 已存在，覆盖吗？", parent=self):
            return

        snap = self._current_snapshot()
        self._set_busy(True)
        self.lbl_state.configure(text=f"正在生成（{'最新数据' if snap is None else snap.name}）…")
        self.worker = threading.Thread(target=self._work, args=(out, snap), daemon=True)
        self.worker.start()
        self.after(100, self._poll)

    def _work(self, out: Path, snap: Path | None) -> None:
        try:
            path = generate(out, snapshot=snap)
            self.queue.put(("done", path))
        except SystemExit as e:      # 文件被 Excel/WPS 占用
            self.queue.put(("error", f"写入失败（退出码 {e.code}）：目标文件可能正被 Excel/WPS 打开"))
        except Exception as e:
            self.queue.put(("error", f"{type(e).__name__}: {e}"))

    def _poll(self) -> None:
        try:
            kind, payload = self.queue.get_nowait()
        except queue.Empty:
            if self.worker is not None and self.worker.is_alive():
                self.after(120, self._poll)
            return
        self._set_busy(False)
        if kind == "done":
            self.lbl_state.configure(text=f"已生成：{payload.name}")
            self._log_cb(f"✅ 销售完成度表已生成: {payload}\n")
            if messagebox.askyesno("生成完成", f"已生成：\n{payload}\n\n现在打开文件吗？", parent=self):
                self._open(Path(payload))
        else:
            self.lbl_state.configure(text="生成失败")
            self._log_cb(f"❌ 销售完成度表生成失败: {payload}\n")
            messagebox.showerror("生成失败", payload, parent=self)

    def _set_busy(self, busy: bool) -> None:
        self.btn_gen.configure(state="disabled" if busy else "normal")

    @staticmethod
    def _open(path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as e:
            messagebox.showerror("打开失败", str(e))

    def _on_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            if not messagebox.askyesno("正在生成", "还在生成中，确定关闭吗？", parent=self):
                return
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
