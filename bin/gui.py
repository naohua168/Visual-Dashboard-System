# Author: naohua168 <bai_bai168@qq.com>
# -*- coding: utf-8 -*-
"""Python 图形运行控制台（tkinter，标准库实现，不依赖 PowerShell / WPF）

    python bin/app.py      # 默认打开本界面
    python bin/gui.py      # 直接打开（等价）

功能：
  · 运行全流程（8 步：预扫描 → 配置同步 → 年基线 → 清洗 → 拆分 → 渲染 → 汇总 → 校验）
  · 单步执行（下拉选择）
  · 实时进度 / 日志 / 退出码
  · 打开 output 目录、配置编辑器、最新看板
  · 运行中可请求停止（步骤之间生效）
"""
from __future__ import annotations

import contextlib
import ctypes
import io
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

BASE_DIR = Path(__file__).resolve().parent.parent   # 项目根
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bin.runner import STEPS, run_all  # noqa: E402

# ── 视觉常量 ──────────────────────────────────────────────
BG = "#f5f5f7"
CARD = "#ffffff"
LINE = "#e5e5ea"
TXT = "#1d1d1f"
MUTED = "#6e6e73"
BLUE = "#0a84ff"
GREEN = "#1a9e55"
RED = "#d93025"
ORANGE = "#c96a00"

# 字体在 DashboardApp.__init__ 里按 DPI 生成（像素负值，高 DPI 下不二次缩放 → 不模糊）
MAX_LOG_LINES = 4000


def enable_hidpi() -> None:
    """Windows 高 DPI：把进程设为 Per-Monitor V2 感知（必须在创建 Tk 之前调用）

    ⚠️ 关键：`SetProcessDpiAwarenessContext` 的参数是 **HANDLE**，-4 必须包成 `c_void_p`。
    直接传 int 时 ctypes 会**静默失败**（返回 False、不抛异常），进程仍是 unaware →
    150% 缩放下整个窗口被系统当位图拉伸，画面整体发糊（2026-10-19 实测）。
    """
    if os.name != "nt":
        return
    user32 = ctypes.windll.user32

    try:  # Win10 1703+：Per-Monitor V2（最清晰）
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass
    try:  # Win8.1+：Per-Monitor
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:  # S_OK
            return
    except Exception:
        pass
    try:  # 旧接口：System DPI Aware
        user32.SetProcessDPIAware()
    except Exception:
        pass


class _QueueWriter(io.TextIOBase):
    """把 print 输出送进队列（工作线程 → 主线程）"""

    def __init__(self, q: queue.Queue):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(("log", s))
        return len(s)

    def flush(self):
        pass


class DashboardApp:
    def __init__(self, root: tk.Tk, scale: float = 1.0):
        self.root = root
        self.scale = max(1.0, float(scale))
        # 用「点」单位（正数）：交给 Windows 字体引擎按 DPI 渲染，自带 ClearType；
        # ⚠️ 不要用像素负值（-13），那会绕过字体平滑，笔画边缘发毛
        self.f_base = ("Microsoft YaHei UI", 10)
        self.f_sm = ("Microsoft YaHei UI", 9)
        self.f_title = ("Microsoft YaHei UI", 15, "bold")
        # 日志区含大量中文：用雅黑（Consolas 的中文回退字体在高分屏上更虚）
        self.f_mono = ("Microsoft YaHei UI", 10)

        self.queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.t0 = 0.0

        self._build_style()
        self._build_ui()
        self._refresh_status()
        self.root.after(80, self._drain)

    # ────────────────────────────── UI ──────────────────────────────
    def _build_style(self):
        self.root.title("销售运营可视化看板系统 — 运行控制台")
        # 按 DPI 放大窗口，但不超过屏幕可用区域（150% 缩放下 1080p 屏会超height）
        w = min(int(1140 * self.scale), self.root.winfo_screenwidth() - 80)
        h = min(int(780 * self.scale), self.root.winfo_screenheight() - 120)
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(min(int(1000 * self.scale), w), min(int(700 * self.scale), h))
        self.root.configure(bg=BG)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=self.f_base)      # 所有 ttk 控件统一字体（按钮/下拉/进度条）
        style.configure("TButton", padding=(10, 5))
        self.root.option_add("*TCombobox*Listbox.font", self.f_base)
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("Bg.TFrame", background=BG)
        style.configure("Title.TLabel", background=CARD, foreground=TXT, font=self.f_title)
        style.configure("Sub.TLabel", background=CARD, foreground=MUTED, font=self.f_base)
        style.configure("Card.TLabel", background=CARD, foreground=TXT, font=self.f_base)
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=self.f_sm)
        style.configure("Bar.Horizontal.TProgressbar",
                        troughcolor="#e9e9ee", background=BLUE,
                        bordercolor="#e9e9ee", lightcolor=BLUE, darkcolor=BLUE)

    def _build_ui(self):
        # 顶部标题
        header = ttk.Frame(self.root, style="Card.TFrame", padding=(20, 14))
        header.pack(fill="x", side="top")
        ttk.Label(header, text="销售运营可视化看板系统", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="  ·  Python 运行控制台", style="Sub.TLabel").pack(side="left", padx=(6, 0))
        self.lbl_env = ttk.Label(header, text="", style="Sub.TLabel")
        self.lbl_env.pack(side="right")

        body = ttk.Frame(self.root, style="Bg.TFrame", padding=(16, 14))
        body.pack(fill="both", expand=True)

        # 左侧：状态 + 操作
        left = ttk.Frame(body, style="Card.TFrame", padding=16, width=int(268 * self.scale))
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        ttk.Label(left, text="环境状态", style="Card.TLabel").pack(anchor="w")
        self.status_labels: dict[str, ttk.Label] = {}
        for key, title in (("data", "原始数据"), ("config", "配置编辑器"), ("output", "最新产物")):
            row = ttk.Frame(left, style="Card.TFrame")
            row.pack(fill="x", pady=(8, 0))
            ttk.Label(row, text=f"{title}：", style="Muted.TLabel", width=9).pack(side="left")
            lbl = ttk.Label(row, text="—", style="Muted.TLabel", wraplength=int(150 * self.scale), justify="left")
            lbl.pack(side="left")
            self.status_labels[key] = lbl

        ttk.Separator(left).pack(fill="x", pady=14)

        self.btn_run = ttk.Button(left, text="▶  运行全流程", command=self._on_run_all)
        self.btn_run.pack(fill="x", ipady=5)

        ttk.Label(left, text="单步执行", style="Muted.TLabel").pack(anchor="w", pady=(16, 4))
        self.cmb_step = ttk.Combobox(
            left, state="readonly", values=[f"{s.name}（{s.key}）" for s in STEPS]
        )
        self.cmb_step.current(3)
        self.cmb_step.pack(fill="x")
        self.btn_step = ttk.Button(left, text="执行选中步骤", command=self._on_run_step)
        self.btn_step.pack(fill="x", pady=(6, 0))

        ttk.Separator(left).pack(fill="x", pady=14)

        self.btn_out = ttk.Button(left, text="打开 output 目录", command=lambda: self._open(BASE_DIR / "output"))
        self.btn_out.pack(fill="x", pady=2)
        self.btn_cfg = ttk.Button(left, text="打开配置编辑器", command=lambda: self._open(BASE_DIR / "config" / "配置编辑器.xlsx"))
        self.btn_cfg.pack(fill="x", pady=2)
        self.btn_board = ttk.Button(left, text="打开最新看板", command=self._open_latest_board)
        self.btn_board.pack(fill="x", pady=2)

        ttk.Separator(left).pack(fill="x", pady=12)
        self.btn_stop = ttk.Button(left, text="停止", command=self._on_stop, state="disabled")
        self.btn_stop.pack(fill="x", pady=2)
        ttk.Button(left, text="退出", command=self._on_close).pack(fill="x", pady=(2, 0))

        # 右侧
        right = ttk.Frame(body, style="Bg.TFrame")
        right.pack(side="left", fill="both", expand=True)

        prog_card = ttk.Frame(right, style="Card.TFrame", padding=16)
        prog_card.pack(fill="x")
        top = ttk.Frame(prog_card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="运行进度", style="Card.TLabel").pack(side="left")
        self.lbl_phase = ttk.Label(top, text="待运行", style="Muted.TLabel")
        self.lbl_phase.pack(side="right")

        self.progress = ttk.Progressbar(prog_card, style="Bar.Horizontal.TProgressbar",
                                        mode="determinate", maximum=len(STEPS), value=0)
        self.progress.pack(fill="x", pady=(10, 10))

        chips = ttk.Frame(prog_card, style="Card.TFrame")
        chips.pack(fill="x")
        self.chips: list[tk.Label] = []
        for i, step in enumerate(STEPS):
            lbl = tk.Label(chips, text=f"○ {step.name}", font=self.f_base,
                           bg=CARD, fg=MUTED, anchor="w", padx=4)
            lbl.grid(row=i // 4, column=i % 4, sticky="ew", padx=(0, 8), pady=3)
            self.chips.append(lbl)
        for c in range(4):
            chips.columnconfigure(c, weight=1)

        log_card = ttk.Frame(right, style="Card.TFrame", padding=16)
        log_card.pack(fill="both", expand=True, pady=(14, 0))
        bar = ttk.Frame(log_card, style="Card.TFrame")
        bar.pack(fill="x")
        ttk.Label(bar, text="运行日志", style="Card.TLabel").pack(side="left")
        ttk.Button(bar, text="清空", width=6, command=self._clear_log).pack(side="right")
        ttk.Button(bar, text="复制全部", width=9, command=self._copy_log).pack(side="right", padx=(0, 6))

        wrap = ttk.Frame(log_card, style="Card.TFrame")
        wrap.pack(fill="both", expand=True, pady=(8, 0))
        self.log = tk.Text(wrap, bg="#0f1115", fg="#d7dae0", insertbackground="#d7dae0",
                           font=self.f_mono, relief="flat", wrap="none",
                           padx=10, pady=8, state="disabled")
        ys = ttk.Scrollbar(wrap, orient="vertical", command=self.log.yview)
        xs = ttk.Scrollbar(wrap, orient="horizontal", command=self.log.xview)
        self.log.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        # 底部状态栏
        footer = tk.Frame(self.root, bg=CARD, height=34)
        footer.pack(fill="x", side="bottom")
        self.lbl_state = tk.Label(footer, text="就绪", bg=CARD, fg=MUTED, font=self.f_sm, anchor="w")
        self.lbl_state.pack(side="left", padx=16, pady=8)
        self.lbl_meta = tk.Label(footer, text="", bg=CARD, fg=MUTED, font=self.f_sm, anchor="e")
        self.lbl_meta.pack(side="right", padx=16, pady=8)

        self.lbl_env.configure(text=f"Python {sys.version.split()[0]}  ·  {BASE_DIR.name}")

    # ────────────────────────────── 状态 ──────────────────────────────
    def _refresh_status(self):
        raw = BASE_DIR / "data" / "raw"
        n_raw = sum(1 for _ in raw.rglob("*.xls*") if not _.name.startswith("~$")) if raw.exists() else 0
        self._set_status("data", f"✓ {n_raw} 个源表" if n_raw else "⚠ 未找到", ok=bool(n_raw))

        cfg = BASE_DIR / "config" / "配置编辑器.xlsx"
        self._set_status("config", "✓ 已就绪" if cfg.exists() else "⚠ 缺失", ok=cfg.exists())

        board = self._latest_board()
        if board is not None:
            self._set_status("output", f"✓ {board.name}", ok=True)
        else:
            self._set_status("output", "— 未生成", ok=False)

    def _set_status(self, key: str, text: str, ok: bool):
        self.status_labels[key].configure(text=text, foreground=GREEN if ok else ORANGE)

    def _latest_board(self) -> Path | None:
        board_dir = BASE_DIR / "output" / "看板"
        files = sorted((f for f in board_dir.glob("看板_*.html") if not f.name.startswith("~$")),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        return files[0] if files else None

    # ────────────────────────────── 运行 ──────────────────────────────
    def _on_run_all(self):
        self._start(None)

    def _on_run_step(self):
        idx = self.cmb_step.current()
        if 0 <= idx < len(STEPS):
            self._start([STEPS[idx].key])

    def _start(self, keys: list[str] | None):
        if self.worker is not None and self.worker.is_alive():
            return
        self.stop_event.clear()
        self._set_running(True)
        self._reset_steps(len(keys) if keys else len(STEPS))
        self.t0 = time.time()
        self._set_state("运行中…")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        self.worker = threading.Thread(target=self._run_worker, args=(keys,), daemon=True)
        self.worker.start()

    def _run_worker(self, keys: list[str] | None):
        buf = _QueueWriter(self.queue)
        rc = 1
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = run_all(
                    log=buf.write,
                    keys=keys,
                    on_step_start=lambda step, index: self.queue.put(("step_start", step.key, index)),
                    on_step_done=lambda res: self.queue.put(("step_done", res.key, res.ok, res.seconds)),
                    stop_event=self.stop_event,
                )
        except Exception as e:  # 兜底：界面不能因单次异常退出
            buf.write(f"\n❌ 运行线程异常: {e}\n")
            rc = 1
        finally:
            self.queue.put(("done", rc))

    def _on_stop(self):
        self.stop_event.set()
        self._set_state("已请求停止（当前步骤结束后生效）")

    # ────────────────────────────── 队列 ──────────────────────────────
    def _drain(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._append_log(item[1])
                elif kind == "step_start":
                    self._mark_step(item[1], "running")
                    self.lbl_phase.configure(text=item[1])
                    self._set_state(f"正在执行：{item[1]}")
                elif kind == "step_done":
                    self._mark_step(item[1], "ok" if item[2] else "fail")
                elif kind == "done":
                    self._finish(item[1])
        except queue.Empty:
            pass
        self.root.after(80, self._drain)

    def _append_log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        lines = int(self.log.index("end-1c").split(".")[0])
        if lines > MAX_LOG_LINES:
            self.log.delete("1.0", f"{lines - MAX_LOG_LINES}.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _reset_steps(self, total: int):
        self.progress.configure(maximum=max(total, 1), value=0)
        self.lbl_phase.configure(text="待运行")
        for lbl, step in zip(self.chips, STEPS):
            lbl.configure(text=f"○ {step.name}", fg=MUTED)

    def _mark_step(self, key: str, state: str):
        keys = [s.key for s in STEPS]
        if key not in keys:
            return
        i = keys.index(key)
        text = self.chips[i].cget("text").split(" ", 1)[-1]
        if state == "running":
            self.chips[i].configure(text=f"▶ {text}", fg=BLUE)
        elif state == "ok":
            self.chips[i].configure(text=f"✓ {text}", fg=GREEN)
            self.progress.configure(value=min(self.progress["value"] + 1, int(self.progress["maximum"])))
        else:
            self.chips[i].configure(text=f"✗ {text}", fg=RED)
            self.progress.configure(value=min(self.progress["value"] + 1, int(self.progress["maximum"])))

    def _finish(self, rc: int):
        self._set_running(False)
        elapsed = time.time() - self.t0 if self.t0 else 0
        self.lbl_meta.configure(text=f"退出码 {rc}  ·  耗时 {elapsed:.1f}s")
        if rc == 0:
            self._set_state("✅ 全部完成")
        elif rc == 4:
            self._set_state("⚠️ 完成，但存在数据质量问题（见数据校验报告）")
        else:
            self._set_state(f"❌ 运行失败（退出码 {rc}）")
        self._refresh_status()

    def _set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.btn_run.configure(state=state)
        self.btn_step.configure(state=state)
        self.cmb_step.configure(state="disabled" if running else "readonly")
        self.btn_stop.configure(state="normal" if running else "disabled")

    def _set_state(self, text: str):
        self.lbl_state.configure(text=text)

    # ────────────────────────────── 打开 ──────────────────────────────
    def _open(self, path: Path):
        if not path.exists():
            messagebox.showwarning("未找到", f"路径不存在：\n{path}")
            return
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as e:
            messagebox.showerror("打开失败", str(e))

    def _open_latest_board(self):
        board = self._latest_board()
        if board is None:
            messagebox.showinfo("暂无看板", "还没有生成看板，请先运行全流程。")
            return
        self._open(board)

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log.get("1.0", "end-1c"))

    def _on_close(self):
        if self.worker is not None and self.worker.is_alive():
            if not messagebox.askyesno("正在运行", "流程仍在运行，确定退出吗？\n（当前步骤会在后台跑完）"):
                return
            self.stop_event.set()
        self.root.destroy()


def main() -> int:
    enable_hidpi()                          # 必须在创建 Tk 之前
    root = tk.Tk()
    dpi = root.winfo_fpixels("1i")
    try:  # DPI 感知下 Tk 一般会自动设，这里显式对齐，保证点单位换算准确
        root.tk.call("tk", "scaling", max(1.0, dpi / 72.0))
    except Exception:
        pass
    scale = dpi / 96.0                        # 96dpi→1.0；150% 缩放→1.5
    DashboardApp(root, scale=scale)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
