"""迷你悬浮窗：置顶显示当前番茄阶段与剩余时间，无需展开主界面。

特点：
- 无边框 + 置顶（overrideredirect + -topmost），可用鼠标拖动到屏幕任意位置；
- 只占约 200×100 像素，显示阶段名称、剩余时间、进度条与三个快捷按钮；
- 位置自动保存，下次显示时回到原处；
- 配色跟随当前界面主题，切换主题后自动重建；
- 阶段结束提醒逻辑仍由主程序负责，悬浮窗只做展示与快捷操作。
"""

import tkinter as tk
from tkinter import ttk

from app import settings as settings_mod
from app.logger import log_exception
from app.pomodoro import PHASE_FOCUS, PHASE_SHORT, PHASE_LONG, PHASE_LABELS
from . import theme

FLOAT_WIDTH = 240
MARGIN = 24
# 坐标合理范围：多显示器下可能是负值，但不应离谱到离谱的越界值
_POS_LIMIT = 20000


def _position_in_sane_range(x, y, w=0, h=0):
    """校验悬浮窗坐标是否合理（允许副屏负坐标，拒绝越界值）。"""
    if not (-_POS_LIMIT <= x <= _POS_LIMIT and -_POS_LIMIT <= y <= _POS_LIMIT):
        return False
    # 至少有一部分要落在某个屏幕可能存在的范围内
    return x + w > -_POS_LIMIT and y + h > -_POS_LIMIT


class FloatWindow(tk.Toplevel):
    """置顶迷你悬浮窗。"""

    def __init__(self, master, context, on_restore=None):
        super().__init__(master)
        self.context = context
        self.engine = context.engine
        self._on_restore = on_restore
        self._after_id = None
        self._drag_offset = (0, 0)
        self._dragged = False
        self._topmost = settings_mod.get_bool(context.storage, "float_topmost")
        self.overrideredirect(True)
        self.attributes("-topmost", self._topmost)
        self.resizable(False, False)
        self.configure(bg=theme.CARD_BG)
        self._build()
        self._restore_position()
        self._poll()

    # ================================================================ 构建
    def _build(self):
        outer = tk.Frame(self, bg=theme.CARD_BG,
                         highlightbackground=theme.ACCENT, highlightthickness=2)
        outer.pack(fill="both", expand=True)

        head = tk.Frame(outer, bg=theme.CARD_BG)
        head.pack(fill="x", padx=10, pady=(8, 0))
        self.phase_dot = tk.Label(head, text="🍅", bg=theme.CARD_BG,
                                  font=(theme.FONT_FAMILY, 11))
        self.phase_dot.pack(side="left")
        self.phase_label = tk.Label(head, text="就绪", bg=theme.CARD_BG,
                                    fg=theme.TEXT_MUTED, font=theme.FONT_SMALL)
        self.phase_label.pack(side="left", padx=(5, 0))

        pin_btn = tk.Label(head, text="📌", bg=theme.CARD_BG,
                           fg=theme.ACCENT if self._topmost else theme.TEXT_MUTED,
                           cursor="hand2", font=(theme.FONT_FAMILY, 10))
        pin_btn.pack(side="right", padx=(0, 8))
        pin_btn.bind("<Button-1>", lambda _e: self.toggle_topmost())
        self.pin_label = pin_btn

        close_btn = tk.Label(head, text="×", bg=theme.CARD_BG,
                             fg=theme.TEXT_MUTED, cursor="hand2",
                             font=(theme.FONT_FAMILY, 12))
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda _e: self.hide())

        self.time_label = tk.Label(outer, text="--:--", bg=theme.CARD_BG,
                                   fg=theme.TEXT_DARK,
                                   font=(theme.FONT_FAMILY, 26, "bold"))
        self.time_label.pack(anchor="w", padx=12)

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100,
                                        value=0)
        self.progress.pack(fill="x", padx=12, pady=(2, 6))

        btns = tk.Frame(outer, bg=theme.CARD_BG)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        def mini_button(parent, text, command, *, bg, fg, active_bg):
            """悬浮窗小按钮：统一字号、内边距与扁平样式。"""
            btn = tk.Button(parent, text=text, command=command,
                            relief="flat", bd=0, cursor="hand2",
                            bg=bg, fg=fg, activebackground=active_bg,
                            activeforeground="#ffffff",
                            font=(theme.FONT_FAMILY, 10, "bold"),
                            padx=6, pady=3)
            return btn

        self.btn_toggle = mini_button(
            btns, "开始", self._on_toggle, bg=theme.ACCENT, fg="#ffffff",
            active_bg=theme.ACCENT_DARK)
        self.btn_toggle.pack(side="left", fill="x", expand=True)
        # 跳过与回主界面统一为浅灰底、无边框的次要按钮风格
        self.btn_skip = mini_button(
            btns, "跳过", self._on_skip, bg=theme.SEP, fg=theme.TEXT_DARK,
            active_bg=theme.BLUE)
        self.btn_skip.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.btn_restore = mini_button(
            btns, "回主界面", self._on_restore_clicked, bg=theme.SEP,
            fg=theme.TEXT_DARK, active_bg=theme.BLUE)
        self.btn_restore.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # 拖动：按住任意空白/文字区域移动窗口
        for widget in (outer, head, self.phase_dot, self.phase_label,
                       self.time_label):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<ButtonRelease-1>", self._end_drag)

        self.bind("<Button-3>", lambda _e: self.hide())

    # ================================================================ 拖动
    def _start_drag(self, event):
        self._dragged = False
        self._drag_offset = (event.x_root - self.winfo_x(),
                             event.y_root - self.winfo_y())

    def _on_drag(self, event):
        self._dragged = True
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        # 允许多显示器下的负坐标（主屏左侧/上方的副屏），仅做合理范围校验
        if _position_in_sane_range(x, y):
            self.geometry("+%d+%d" % (x, y))

    def _end_drag(self, _event=None):
        if self._dragged:
            self._save_position()

    # ================================================================ 位置
    def _restore_position(self):
        saved = self.context.storage.get("float_pos", "") or ""
        self.update_idletasks()
        w = max(FLOAT_WIDTH, self.winfo_reqwidth())
        h = self.winfo_reqheight()
        if "," in saved:
            try:
                x, y = (int(v) for v in saved.split(",", 1))
                if _position_in_sane_range(x, y, w, h):
                    self.geometry("%dx%d+%d+%d" % (w, h, x, y))
                    return
            except ValueError:
                pass
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry("%dx%d+%d+%d" % (w, h, screen_w - w - MARGIN,
                                       screen_h - h - MARGIN * 3))

    def _save_position(self):
        self.context.storage.set("float_pos", "%d,%d"
                                 % (self.winfo_x(), self.winfo_y()))

    # ================================================================ 显隐
    def show(self):
        """显示悬浮窗并记录开关状态。"""
        self.deiconify()
        self.attributes("-topmost", self._topmost)
        self.lift()
        self._refresh()
        settings_mod.set_bool(self.context.storage, "float_enabled", True)

    def hide(self):
        """隐藏悬浮窗并记录开关状态。"""
        self._save_position()
        self.withdraw()
        settings_mod.set_bool(self.context.storage, "float_enabled", False)

    def toggle_topmost(self):
        """切换置顶状态（📌）：关掉后悬浮窗可被其他窗口遮挡。"""
        self._topmost = not self._topmost
        self.attributes("-topmost", self._topmost)
        settings_mod.set_bool(self.context.storage, "float_topmost", self._topmost)
        if hasattr(self, "pin_label"):
            self.pin_label.config(fg=theme.ACCENT if self._topmost
                                  else theme.TEXT_MUTED)

    def is_visible(self):
        try:
            return bool(self.winfo_exists() and self.winfo_ismapped())
        except tk.TclError:
            return False

    # ================================================================ 交互
    def _on_toggle(self):
        if self.engine.phase is None:
            self.engine.start(PHASE_FOCUS)
        else:
            self.engine.toggle()
        self._refresh()

    def _on_skip(self):
        self.engine.skip()
        self._refresh()

    def _on_restore_clicked(self):
        if callable(self._on_restore):
            self._on_restore()

    # ================================================================ 刷新
    def _poll(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        # 隐藏状态下不必刷新界面（仍保留定时器，显示时立即恢复）
        if self.is_visible():
            try:
                self._refresh()
            except tk.TclError:
                pass
            except Exception:
                log_exception("悬浮窗刷新失败")
        self._after_id = self.after(500, self._poll)

    def _refresh(self):
        engine = self.engine
        phase = engine.phase
        if phase is None:
            self.phase_dot.config(text="🍅")
            self.phase_label.config(text="就绪", fg=theme.TEXT_MUTED)
            self.time_label.config(text="--:--", fg=theme.TEXT_MUTED)
            self.progress.config(maximum=1, value=0)
            self.btn_toggle.config(text="开始")
            return

        color = {PHASE_FOCUS: theme.ACCENT,
                 PHASE_SHORT: theme.GREEN,
                 PHASE_LONG: theme.BLUE}[phase]
        icon = {PHASE_FOCUS: "🍅", PHASE_SHORT: "☕", PHASE_LONG: "🌿"}[phase]
        self.phase_dot.config(text=icon)
        self.phase_label.config(text=PHASE_LABELS[phase], fg=color)
        self.time_label.config(text=engine.format_remaining(), fg=color)
        total = engine.progress_total()
        done = max(0, min(total, total - engine.remaining))
        self.progress.config(maximum=max(1, total), value=done)
        self.btn_toggle.config(text="暂停" if engine.running else "继续")

    # ================================================================ 主题
    def rebuild_for_theme(self):
        """主题切换后重建控件，使配色跟随新主题。"""
        was_visible = self.is_visible()
        self._save_position()
        for child in self.winfo_children():
            child.destroy()
        self.configure(bg=theme.CARD_BG)
        self._build()
        self._restore_position()
        if was_visible:
            self.show()

    def destroy(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        super().destroy()
