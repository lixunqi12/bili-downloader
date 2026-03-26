"""
B站视频下载 + 字幕生成 GUI
支持从浏览器拖入链接，或直接粘贴 URL

依赖安装:
  pip install yt-dlp faster-whisper imageio-ffmpeg
  pip install tkinterdnd2   # 可选，启用拖拽功能
"""

import sys
import os
import re
import threading
import queue
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

# 高分屏 DPI 适配，避免字体模糊（Windows）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# 尝试加载 tkinterdnd2（支持从浏览器拖拽 URL）
try:
    from tkinterdnd2 import DND_TEXT, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

MODELS = ["large-v3", "large-v2", "medium", "small", "base", "tiny"]
DEFAULT_ROOT = "D:/Downloads/bili"

log_queue = queue.Queue()


def extract_urls(raw: str) -> list[str]:
    """从任意文本中提取 B 站视频链接"""
    pattern = r'https?://(?:www\.)?bilibili\.com/video/BV\w+'
    found = re.findall(pattern, raw)
    seen = set()
    result = []
    for u in found:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def redirect_print():
    """把 print 输出重定向到 GUI 日志队列"""
    class Writer:
        encoding = "utf-8"
        def write(self, msg):
            if msg:
                log_queue.put(msg)
        def flush(self):
            pass
        def reconfigure(self, **_):
            pass

    sys.stdout = Writer()
    sys.stderr = Writer()


def run_task(folder, urls, model, root_path, mode, done_callback):
    """在子线程中运行下载/字幕任务"""
    import bili_download_and_subtitle as core
    core.FOLDER = folder
    core.URLS = urls
    core.MODEL = model
    core.ROOT = root_path
    core.CLASS_ROOT = Path(root_path)

    try:
        if mode in ("download", "both"):
            print("=" * 60)
            print("  第一步: 下载视频")
            print("=" * 60)
            core.step1_download()

        if mode in ("subtitle", "both"):
            print("\n" + "=" * 60)
            print("  第二步: 生成字幕")
            print("=" * 60)
            core.step2_subtitle()

        print("\n✅ 全部完成！")
    except Exception as e:
        print(f"\n❌ 出错: {e}")
    finally:
        done_callback()


class App:
    def __init__(self, root):
        self.root = root
        root.title("B站视频下载 + 字幕生成")
        root.resizable(True, True)
        self._build_ui()
        self._poll_log()
        redirect_print()

    def _build_ui(self):
        pad = dict(padx=8, pady=4)

        # ── 顶部配置区 ───────────────────────────────────────────
        cfg = ttk.LabelFrame(self.root, text="配置", padding=8)
        cfg.pack(fill="x", **pad)
        cfg.columnconfigure(1, weight=1)

        ttk.Label(cfg, text="文件夹名:").grid(row=0, column=0, sticky="w")
        self.folder_var = tk.StringVar(value="新下载")
        ttk.Entry(cfg, textvariable=self.folder_var).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ttk.Label(cfg, text="根目录:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.root_var = tk.StringVar(value=DEFAULT_ROOT)
        root_frame = ttk.Frame(cfg)
        root_frame.grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=(4, 0))
        root_frame.columnconfigure(0, weight=1)
        ttk.Entry(root_frame, textvariable=self.root_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(root_frame, text="浏览", width=5,
                   command=self._browse_root).grid(row=0, column=1, padx=(4, 0))

        ttk.Label(cfg, text="Whisper 模型:").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.model_var = tk.StringVar(value=MODELS[0])
        ttk.Combobox(cfg, textvariable=self.model_var,
                     values=MODELS, state="readonly", width=12).grid(
            row=2, column=1, sticky="w", padx=(4, 0), pady=(4, 0))

        # ── URL 输入区 ───────────────────────────────────────────
        url_frame = ttk.LabelFrame(self.root, text="视频链接（拖入 / 粘贴 / 手动输入，每行一个）", padding=8)
        url_frame.pack(fill="both", expand=False, **pad)

        if HAS_DND:
            self.drop_label = tk.Label(
                url_frame,
                text="⬇  把浏览器标签页或链接拖到这里",
                relief="groove", bg="#f0f4ff", height=2, cursor="hand2"
            )
            self.drop_label.pack(fill="x", pady=(0, 6))
            self.drop_label.drop_target_register(DND_TEXT)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        else:
            ttk.Label(url_frame,
                      text="(未安装 tkinterdnd2，无法拖拽 — 请直接粘贴链接)",
                      foreground="gray").pack(anchor="w", pady=(0, 4))

        self.url_box = scrolledtext.ScrolledText(url_frame, height=6, wrap="word",
                                                  font=("Consolas", 9))
        self.url_box.pack(fill="both", expand=True)
        self.url_box.insert("1.0", "# 每行一个链接，或粘贴含链接的任意文本\n")

        btn_row = ttk.Frame(url_frame)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="清空", command=self._clear_urls).pack(side="left")
        self.url_count_var = tk.StringVar(value="")
        ttk.Label(btn_row, textvariable=self.url_count_var,
                  foreground="gray").pack(side="left", padx=8)

        # ── 操作按钮 ─────────────────────────────────────────────
        action = ttk.Frame(self.root)
        action.pack(fill="x", **pad)

        self.btn_dl = ttk.Button(action, text="仅下载", width=12,
                                  command=lambda: self._start("download"))
        self.btn_dl.pack(side="left", padx=(0, 4))

        self.btn_sub = ttk.Button(action, text="仅生成字幕", width=12,
                                   command=lambda: self._start("subtitle"))
        self.btn_sub.pack(side="left", padx=4)

        self.btn_all = ttk.Button(action, text="▶  下载 + 字幕", width=16,
                                   command=lambda: self._start("both"))
        self.btn_all.pack(side="left", padx=4)

        self.btn_stop = ttk.Button(action, text="■  停止", width=10,
                                    command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(action, textvariable=self.status_var,
                  foreground="#555").pack(side="right")

        # ── 日志区 ───────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=8)
        log_frame.pack(fill="both", expand=True, **pad)

        self.log_box = scrolledtext.ScrolledText(log_frame, state="disabled",
                                                  wrap="word", font=("Consolas", 9),
                                                  bg="#1e1e1e", fg="#d4d4d4",
                                                  insertbackground="white")
        self.log_box.pack(fill="both", expand=True)

        ttk.Button(log_frame, text="清空日志",
                   command=self._clear_log).pack(anchor="e", pady=(4, 0))

        self.url_box.bind("<<Modified>>", self._update_url_count)

    def _on_drop(self, event):
        raw = event.data or ""
        urls = extract_urls(raw)
        if urls:
            self.url_box.insert("end", "\n".join(urls) + "\n")
            self._update_url_count()
        else:
            self._log(f"[拖入内容中未找到 B站链接]\n原始内容: {raw[:200]}\n")

    def _browse_root(self):
        d = filedialog.askdirectory(initialdir=self.root_var.get())
        if d:
            self.root_var.set(d)

    def _clear_urls(self):
        self.url_box.delete("1.0", "end")
        self.url_count_var.set("")

    def _update_url_count(self, event=None):
        raw = self.url_box.get("1.0", "end")
        urls = extract_urls(raw)
        self.url_count_var.set(f"已识别 {len(urls)} 个链接" if urls else "")
        if event:
            self.url_box.edit_modified(False)

    def _start(self, mode):
        raw = self.url_box.get("1.0", "end")
        urls = extract_urls(raw)
        folder = self.folder_var.get().strip()
        root_path = self.root_var.get().strip()
        model = self.model_var.get()

        if mode != "subtitle" and not urls:
            messagebox.showwarning("没有链接", "请先输入至少一个 B 站视频链接")
            return
        if not folder:
            messagebox.showwarning("缺少文件夹名", "请填写保存文件夹名")
            return

        self._set_running(True)
        self._log(f"\n{'='*60}\n文件夹: {folder}  模式: {mode}  模型: {model}\n")
        if urls:
            for u in urls:
                self._log(f"  {u}\n")

        self._worker = threading.Thread(
            target=run_task,
            args=(folder, urls, model, root_path, mode, self._on_done),
            daemon=True
        )
        self._worker.start()

    def _stop(self):
        self.status_var.set("正在尝试停止…（等待当前任务结束）")

    def _on_done(self):
        self.root.after(0, lambda: self._set_running(False))

    def _set_running(self, running: bool):
        state_off = "disabled" if running else "normal"
        state_on = "normal" if running else "disabled"
        for btn in (self.btn_dl, self.btn_sub, self.btn_all):
            btn.config(state=state_off)
        self.btn_stop.config(state=state_on)
        self.status_var.set("运行中…" if running else "就绪")

    def _log(self, msg: str):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg)
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _poll_log(self):
        while True:
            try:
                msg = log_queue.get_nowait()
                self._log(msg)
            except queue.Empty:
                break
        self.root.after(100, self._poll_log)


def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    root.geometry("720x680")
    app = App(root)

    if not HAS_DND:
        app._log("提示: 安装 tkinterdnd2 可启用拖拽功能\n  pip install tkinterdnd2\n\n")

    root.mainloop()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    main()
