# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""客户矩阵导出对话框 —— 控制面板「按客户清单导出」的界面

交互（2026-11-06 用户确认）：
  · 客户清单**不输入就不生成**（按需导出，不做默认全量）；
  · 默认一次出「月度-收入 / 月度-回款 / 季度-* / 年度-* / 说明」共 7 个 sheet；
  · 可指定数据版本（当前清洗结果 / 某一期的看板或数据总表）；
  · 生成走后台线程，日志回传到主控制台的运行日志区，界面不假死。
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from bin.snapshot_list import SNAP_LATEST, add_custom_choice, data_root, load_snapshot_choices
from processors.data_loader import load_all, load_from_workbook
from scripts.customer_matrix_core import (
    PERIOD_ORDER,
    PERIODS,
    build_workbook,
    default_out_file,
    latest_data_file,
    parse_customers,
    read_order_file,
)

LAST_CFG = Path("config") / "前端渲染" / "客户矩阵_上次.json"


class MatrixExportDialog(tk.Toplevel):
    def __init__(self, master, base_dir: Path, log=None):
        super().__init__(master)
        self.base_dir = Path(base_dir)
        self._log_cb = log or (lambda _s: None)
        self.queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.snap_map: dict[str, Path | None] = {SNAP_LATEST: None}
        self._busy = False
        # 按 DPI 缩放窗口尺寸（字体用点单位已自动缩放，窗口不缩放会显得局促）
        try:
            self.scale = max(1.0, float(self.winfo_fpixels("1i")) / 96.0)
        except tk.TclError:
            self.scale = 1.0

        self.title("按客户清单导出矩阵")
        self.configure(bg="#f5f5f7")
        self.transient(master)
        self.resizable(True, True)
        self._build()
        self._load_last()
        self._refresh_periods()
        self._refresh_count()
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

        # 周期：分片按钮（chip）
        # ttk 原生对勾在 125%/150% 缩放下会渲染成细线，看着像「×」→ 改为实心分片，
        # 且「选中」同时用「✓ 前缀 + 反色」两种信号，不只靠颜色（无障碍要求）。
        row1 = ttk.Frame(body)
        row1.pack(fill="x")
        ttk.Label(row1, text="统计周期", font=f_bold).pack(side="left")

        self.vars: dict[str, tk.BooleanVar] = {}
        self.chips: dict[str, tk.Label] = {}
        self._hovered: set[str] = set()
        self._focused: set[str] = set()

        for i, key in enumerate(PERIOD_ORDER):
            self.vars[key] = tk.BooleanVar(value=True)
            chip = self._new_chip(row1, key)
            chip.pack(side="left", padx=(int((12 if i == 0 else 6) * self.scale), 0))
            self.chips[key] = chip

        meta = ttk.Frame(body)
        meta.pack(fill="x", pady=(7, 0))
        self.lbl_periods = ttk.Label(meta, text="", font=f_sm)
        self.lbl_periods.pack(side="left")
        self.btn_all = ttk.Button(meta, text="全选", width=6, command=self._select_all)
        self.btn_all.pack(side="right")

        # 数据版本
        row2 = ttk.Frame(body)
        row2.pack(fill="x", pady=(10, 0))
        ttk.Label(row2, text="数据版本", font=f_bold).pack(side="left")
        self.cmb_snap = ttk.Combobox(row2, state="readonly", font=f_base, width=42)
        self.cmb_snap.pack(side="left", padx=(12, 6), fill="x", expand=True)
        ttk.Button(row2, text="选看板/总表…", command=self._pick_snapshot).pack(side="left")
        self._load_snapshots()

        # 客户清单
        ttk.Label(body, text="客户清单（一行一个，可从 Excel 直接粘贴一列）", font=f_bold).pack(
            anchor="w", pady=(12, 4))
        wrap = ttk.Frame(body)
        wrap.pack(fill="both", expand=True)
        self.txt = tk.Text(wrap, height=14, font=f_base, wrap="none", undo=True,
                           relief="solid", borderwidth=1, padx=8, pady=6)
        ys = ttk.Scrollbar(wrap, orient="vertical", command=self.txt.yview)
        self.txt.configure(yscrollcommand=ys.set)
        self.txt.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.txt.bind("<<Modified>>", self._on_modified)
        self.txt.edit_modified(False)

        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(6, 0))
        self.lbl_count = ttk.Label(bar, text="", font=f_sm, foreground="#6e6e73")
        self.lbl_count.pack(side="left")
        ttk.Button(bar, text="清空", width=6, command=self._clear).pack(side="right")
        ttk.Button(bar, text="导入文件…", width=11, command=self._import).pack(side="right", padx=(0, 6))

        # 输出路径
        row4 = ttk.Frame(body)
        row4.pack(fill="x", pady=(12, 0))
        ttk.Label(row4, text="输出文件", font=f_bold).pack(side="left")
        self.ent_out = ttk.Entry(row4, font=f_base)
        self.ent_out.pack(side="left", padx=(12, 6), fill="x", expand=True)
        ttk.Button(row4, text="浏览…", width=7, command=self._pick_out).pack(side="left")

        # 底部
        foot = ttk.Frame(body)
        foot.pack(fill="x", pady=(14, 0))
        self.lbl_state = ttk.Label(foot, text="就绪", font=f_sm, foreground="#6e6e73")
        self.lbl_state.pack(side="left")
        self.btn_gen = ttk.Button(foot, text="生成", width=12, command=self._on_generate)
        self.btn_gen.pack(side="right")
        ttk.Button(foot, text="关闭", width=8, command=self._on_close).pack(side="right", padx=(0, 8))

        self.geometry(f"{int(820 * self.scale)}x{int(620 * self.scale)}")
        self.minsize(int(680 * self.scale), int(520 * self.scale))

    def _center(self, master) -> None:
        try:
            x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
            y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
            self.geometry(f"+{max(x, 40)}+{max(y, 40)}")
        except tk.TclError:
            pass

    # 分片配色（深底反白选中态；边框用于键盘焦点）
    CHIP_OFF_BG = "#ffffff"
    CHIP_OFF_FG = "#374151"
    CHIP_OFF_BORDER = "#d0d5dd"
    CHIP_HOVER_BG = "#f2f4f7"
    CHIP_ON_BG = "#1e293b"
    CHIP_ON_FG = "#ffffff"
    CHIP_FOCUS = "#2563eb"

    def _new_chip(self, parent, key: str) -> tk.Label:
        """一个周期分片：整块可点（热区远大于 16px 的方框），支持键盘空格/回车"""
        s = getattr(self, "scale", 1.0)
        chip = tk.Label(parent, text="", font=("Microsoft YaHei UI", 10),
                        padx=int(14 * s), pady=int(5 * s),
                        bd=0, highlightthickness=1, cursor="hand2", takefocus=1)
        chip.bind("<Button-1>", lambda _e, k=key: self._toggle_period(k))
        chip.bind("<space>", lambda _e, k=key: self._toggle_period(k))
        chip.bind("<Return>", lambda _e, k=key: self._toggle_period(k))
        chip.bind("<Enter>", lambda _e, k=key: self._set_hover(k, True))
        chip.bind("<Leave>", lambda _e, k=key: self._set_hover(k, False))
        chip.bind("<FocusIn>", lambda _e, k=key: self._set_focus(k, True))
        chip.bind("<FocusOut>", lambda _e, k=key: self._set_focus(k, False))
        return chip

    def _paint_chip(self, key: str) -> None:
        on = bool(self.vars[key].get())
        if on:
            bg, fg, border = self.CHIP_ON_BG, self.CHIP_ON_FG, self.CHIP_ON_BG
        else:
            bg = self.CHIP_HOVER_BG if key in self._hovered else self.CHIP_OFF_BG
            fg, border = self.CHIP_OFF_FG, self.CHIP_OFF_BORDER
        if key in self._focused:            # 键盘焦点环优先
            border = self.CHIP_FOCUS
        self.chips[key].configure(
            text=("✓  " if on else "") + PERIODS[key].label,   # 形状信号，不只靠颜色
            bg=bg, fg=fg, highlightbackground=border, highlightcolor=border,
        )

    def _toggle_period(self, key: str) -> None:
        self.vars[key].set(not self.vars[key].get())
        self._refresh_periods()

    def _set_hover(self, key: str, on: bool) -> None:
        (self._hovered.add if on else self._hovered.discard)(key)
        self._paint_chip(key)

    def _set_focus(self, key: str, on: bool) -> None:
        (self._focused.add if on else self._focused.discard)(key)
        self._paint_chip(key)

    def _select_all(self) -> None:
        for k in PERIOD_ORDER:
            self.vars[k].set(True)
        self._refresh_periods()

    def _refresh_periods(self) -> None:
        """重绘分片 + 下方回显（解决"到底选中没有"的歧义）"""
        for key in PERIOD_ORDER:
            self._paint_chip(key)
        picked = [PERIODS[k].label for k in PERIOD_ORDER if self.vars[k].get()]
        if picked:
            self.lbl_periods.configure(text="已选：" + "、".join(picked), foreground="#4b5563")
        else:
            self.lbl_periods.configure(text="请至少选择 1 个统计周期", foreground="#c0392b")
        self._sync_gen_state()

    def _sync_gen_state(self) -> None:
        """没选周期就禁用「生成」，避免点了才报错"""
        ready = any(self.vars[k].get() for k in PERIOD_ORDER) and not getattr(self, "_busy", False)
        self.btn_gen.configure(state="normal" if ready else "disabled")

    # ── 数据版本 ────────────────────────────────────────────
    def _load_snapshots(self) -> None:
        self.snap_map = load_snapshot_choices(self.base_dir)
        self.cmb_snap.configure(values=list(self.snap_map))
        self.cmb_snap.current(0)

    def _pick_snapshot(self) -> None:
        init = str(data_root(self.base_dir))
        path = filedialog.askopenfilename(
            parent=self, title="选择看板 HTML 或数据总表",
            initialdir=init,
            filetypes=[("看板/数据总表", "*.html;data_*.xlsx"), ("所有文件", "*.*")],
        )
        if not path:
            return
        label = add_custom_choice(self.snap_map, Path(path))
        self.cmb_snap.configure(values=list(self.snap_map))
        self.cmb_snap.set(label)

    # ── 清单 ────────────────────────────────────────────────
    def _on_modified(self, _event=None) -> None:
        if self.txt.edit_modified():
            self._refresh_count()
            self.txt.edit_modified(False)

    def _refresh_count(self) -> None:
        n = len(parse_customers(self.txt.get("1.0", "end-1c")))
        self.lbl_count.configure(
            text=f"已输入 {n} 个客户" if n else "未输入 —— 本功能按需生成，不填不会生成文件")

    def _clear(self) -> None:
        self.txt.delete("1.0", "end")
        self._refresh_count()

    def _import(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="导入客户清单（txt / csv 一行一个）",
            filetypes=[("文本", "*.txt;*.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            names = read_order_file(Path(path))
        except Exception as e:
            messagebox.showerror("导入失败", str(e), parent=self)
            return
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "\n".join(names))
        self._refresh_count()

    def _pick_out(self) -> None:
        cur = self.base_dir / self.ent_out.get().strip()
        path = filedialog.asksaveasfilename(
            parent=self, title="保存矩阵", defaultextension=".xlsx",
            initialdir=str(cur.parent if cur.parent.exists() else self.base_dir),
            initialfile=cur.name, filetypes=[("Excel", "*.xlsx")],
        )
        if path:
            self.ent_out.delete(0, "end")
            self.ent_out.insert(0, path)

    # ── 生成 ────────────────────────────────────────────────
    def _on_generate(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        names = parse_customers(self.txt.get("1.0", "end-1c"))
        if not names:
            messagebox.showwarning(
                "未输入客户", "请先在清单里粘贴客户名称（一行一个）。\n本功能是可选导出，不做默认全量。",
                parent=self)
            return
        periods = [k for k in PERIOD_ORDER if self.vars[k].get()]
        if not periods:
            messagebox.showwarning("未选周期", "至少勾选一个统计周期。", parent=self)
            return
        out_text = self.ent_out.get().strip()
        if not out_text:
            messagebox.showwarning("未填输出", "请填写输出文件路径。", parent=self)
            return
        out = Path(out_text)
        if not out.is_absolute():
            out = self.base_dir / out
        if out.suffix.lower() != ".xlsx":
            out = out.with_suffix(".xlsx")
        if out.exists() and not messagebox.askyesno("覆盖确认", f"{out.name} 已存在，覆盖吗？", parent=self):
            return

        snap = self.snap_map.get(self.cmb_snap.get())
        self._save_last(periods, out)
        self._set_busy(True)
        self.worker = threading.Thread(target=self._work, args=(names, periods, out, snap), daemon=True)
        self.worker.start()
        self.after(100, self._poll)

    def _work(self, names, periods, out: Path, snap: Path | None) -> None:
        try:
            label = snap.name if snap else latest_data_file(self.base_dir)
            self.queue.put(("log", f"读取数据：{label}"))
            data = load_from_workbook(snap) if snap else load_all(self.base_dir)
            wb, stats = build_workbook(
                data, periods, names, self.base_dir,
                order_label="对话框输入", data_label=label,
                on_log=lambda m: self.queue.put(("log", m)),
            )
            out.parent.mkdir(parents=True, exist_ok=True)
            wb.save(out)
            self.queue.put(("done", (out, stats)))
        except Exception as e:  # 单次失败不能让界面崩
            self.queue.put(("error", f"{type(e).__name__}: {e}"))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self.lbl_state.configure(text=payload.strip())
                    self._log_cb(f"  {payload}\n")
                elif kind == "done":
                    self._finish(*payload)
                    return
                elif kind == "error":
                    self._set_busy(False)
                    self.lbl_state.configure(text="生成失败")
                    self._log_cb(f"❌ 矩阵导出失败: {payload}\n")
                    messagebox.showerror("生成失败", payload, parent=self)
                    return
        except queue.Empty:
            pass
        if self.worker is not None and self.worker.is_alive():
            self.after(120, self._poll)

    def _finish(self, out: Path, stats: list[dict]) -> None:
        self._set_busy(False)
        self.lbl_state.configure(text=f"已生成：{out.name}")
        unmatched = stats[0].get("未识别", 0) if stats else 0
        self._log_cb(f"✅ 客户矩阵已生成: {out}\n")
        if unmatched:
            self._log_cb(f"   ⚠️ {unmatched} 个客户名未匹配到系统实体，详见「说明」sheet\n")

        msg = f"已生成：\n{out}\n\n共 {len(stats)} 个 sheet（含说明）"
        if unmatched:
            names = "、".join(stats[0].get("未识别清单", [])[:6])
            msg += f"\n\n⚠️ {unmatched} 个客户名未识别：{names}"
            msg += "\n（已在「说明」sheet 列出）"
        if messagebox.askyesno("生成完成", msg + "\n\n现在打开文件吗？", parent=self):
            self._open(out)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._sync_gen_state()
        if busy:
            self.lbl_state.configure(text="正在生成…")

    @staticmethod
    def _open(path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as e:
            messagebox.showerror("打开失败", str(e))

    # ── 上次选择 ────────────────────────────────────────────
    def _cfg_path(self) -> Path:
        return self.base_dir / LAST_CFG

    def _load_last(self) -> None:
        periods = list(PERIOD_ORDER)
        out = ""
        try:
            raw = json.loads(self._cfg_path().read_text(encoding="utf-8"))
            periods = [k for k in raw.get("周期", periods) if k in PERIODS] or periods
            out = str(raw.get("输出", ""))
        except Exception:
            pass
        for k, var in self.vars.items():
            var.set(k in periods)
        if not out:
            suffix = "".join({"monthly": "月", "quarterly": "季", "annual": "年"}[k] for k in periods)
            out = str(default_out_file(self.base_dir, f"客户矩阵_{suffix}"))
        self.ent_out.delete(0, "end")
        self.ent_out.insert(0, out)

    def _save_last(self, periods: list[str], out: Path) -> None:
        try:
            p = self._cfg_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"周期": periods, "输出": str(out)}, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        except Exception:
            pass

    def _on_close(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            if not messagebox.askyesno("正在生成", "还在生成中，确定关闭吗？", parent=self):
                return
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
