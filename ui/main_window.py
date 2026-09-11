"""主窗口：侧边导航 + 页面容器 + 主题切换 + 迷你悬浮窗。"""

import re
import tkinter as tk
from tkinter import ttk

from app import settings as settings_mod
from app.themes import DEFAULT_THEME, label_for, name_for_label, theme_names
from . import theme
from .float_window import FloatWindow
from .pomodoro_view import PomodoroView
from .todo_view import TodoView
from .habit_view import HabitView
from .stats_view import StatsView
from .reminder import stop_active_alarm

APP_TITLE = "番茄工作台"
APP_VERSION = "v1.3.1"

NAV_ITEMS = [
    ("pomodoro", "🍅  番茄专注"),
    ("todo", "☑  待办清单"),
    ("habit", "🔥  习惯打卡"),
    ("stats", "📊  数据统计"),
]

_PAGE_CLASSES = {
    "pomodoro": PomodoroView,
    "todo": TodoView,
    "habit": HabitView,
    "stats": StatsView,
}

# 主窗口 geometry 字符串形如 1040x680+120+60；允许负坐标（副屏在主屏左侧/上方）
_GEOMETRY_RE = re.compile(r"^\d{3,5}x\d{3,5}[+-]\d{1,5}[+-]\d{1,5}$")


def _geometry_ok(value):
    """校验保存的窗口 geometry 是否合法（避免异常配置导致窗口跑到屏幕外）。"""
    return bool(value) and bool(_GEOMETRY_RE.match(value.strip()))


class MainWindow(tk.Tk):
    """应用主窗口。"""

    def __init__(self, context):
        super().__init__()
        self.context = context
        self._pages = {}
        self._nav_buttons = {}
        self._current = None
        self._theme_var = tk.StringVar(value="")
        self.float_window = None
        self._float_auto_shown = False

        # 字体按平台自动选择（Windows / macOS / Linux），需在创建控件前完成
        theme.init_fonts(self)
        # 启动时按保存的设置为准（未知主题自动回退默认）
        saved_theme = context.storage.get("theme", DEFAULT_THEME)
        theme.apply(saved_theme)
        theme.setup_style(self)

        self.title("%s %s" % (APP_TITLE, APP_VERSION))
        saved_geometry = context.storage.get("win_geometry", "") or ""
        self.geometry(saved_geometry if _geometry_ok(saved_geometry)
                      else "1040x680")
        self.minsize(940, 620)
        self._build_sidebar()
        self._build_body()
        self.switch("pomodoro")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 最小化时按用户设置自动弹出悬浮窗
        self.bind("<Unmap>", self._on_root_unmap)
        self.bind("<Map>", self._on_root_map)
        # 上次退出时开启了悬浮窗，则恢复显示
        if settings_mod.get_bool(context.storage, "float_enabled"):
            self.after(300, self.show_float_window)

    # ================================================================ 界面
    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=theme.SIDEBAR_BG, width=186)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        logo = tk.Frame(sidebar, bg=theme.SIDEBAR_BG)
        logo.pack(fill="x", pady=(22, 6), padx=16)
        tk.Label(logo, text="🍅 番茄工作台", bg=theme.SIDEBAR_BG,
                 fg="#ffffff", font=(theme.FONT_FAMILY, 15, "bold")).pack(
            anchor="w")
        tk.Label(logo, text="专注 · 待办 · 习惯", bg=theme.SIDEBAR_BG,
                 fg=theme.SIDEBAR_TEXT_MUTED,
                 font=theme.FONT_SMALL).pack(anchor="w", pady=(2, 0))

        line = tk.Frame(sidebar, bg=theme.SIDEBAR_LINE, height=1)
        line.pack(fill="x", padx=14, pady=10)

        for key, label in NAV_ITEMS:
            btn = ttk.Button(sidebar, text=label, style="Nav.TButton",
                             command=lambda k=key: self.switch(k))
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = btn

        # ---- 主题切换 ----
        theme_box = tk.Frame(sidebar, bg=theme.SIDEBAR_BG)
        theme_box.pack(side="bottom", fill="x", padx=14, pady=(0, 6))
        tk.Label(theme_box, text="🎨 界面主题", bg=theme.SIDEBAR_BG,
                 fg=theme.SIDEBAR_TEXT, font=theme.FONT_SMALL).pack(anchor="w")
        self._theme_var.set(label_for(theme.current))
        self.theme_combo = ttk.Combobox(
            theme_box, state="readonly", width=14,
            values=[label_for(name) for name in theme_names()])
        self.theme_combo.set(label_for(theme.current))
        self.theme_combo.pack(fill="x", pady=(4, 0))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)

        # ---- 迷你悬浮窗 ----
        float_box = tk.Frame(sidebar, bg=theme.SIDEBAR_BG)
        float_box.pack(side="bottom", fill="x", padx=14, pady=(0, 6))
        tk.Label(float_box, text="🪟 迷你悬浮窗", bg=theme.SIDEBAR_BG,
                 fg=theme.SIDEBAR_TEXT, font=theme.FONT_SMALL).pack(anchor="w")
        self.var_float = tk.BooleanVar(
            value=settings_mod.get_bool(self.context.storage, "float_enabled"))
        self.var_float_auto = tk.BooleanVar(
            value=settings_mod.get_bool(self.context.storage,
                                        "float_auto_minimize"))
        tk.Checkbutton(float_box, text="显示悬浮窗", variable=self.var_float,
                       command=self._on_float_toggle, bg=theme.SIDEBAR_BG,
                       fg=theme.SIDEBAR_TEXT, selectcolor=theme.SIDEBAR_ACTIVE,
                       activebackground=theme.SIDEBAR_BG,
                       activeforeground="#ffffff", font=theme.FONT_SMALL,
                       highlightthickness=0).pack(anchor="w")
        tk.Checkbutton(float_box, text="最小化时自动显示", variable=self.var_float_auto,
                       command=self._on_float_auto_toggle, bg=theme.SIDEBAR_BG,
                       fg=theme.SIDEBAR_TEXT_MUTED, selectcolor=theme.SIDEBAR_ACTIVE,
                       activebackground=theme.SIDEBAR_BG,
                       activeforeground="#ffffff", font=theme.FONT_SMALL,
                       highlightthickness=0).pack(anchor="w")

        tk.Label(sidebar, text=APP_VERSION + " ｜ 数据仅存本地",
                 bg=theme.SIDEBAR_BG, fg=theme.SIDEBAR_TEXT_MUTED,
                 font=theme.FONT_SMALL).pack(side="bottom", pady=12)

    def _build_body(self):
        body = tk.Frame(self, bg=theme.BG)
        body.pack(side="left", fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.body = body

    # ================================================================ 主题
    def _on_theme_selected(self, _event=None):
        name = name_for_label(self.theme_combo.get())
        if name is None:
            return
        self.apply_theme(name)

    def apply_theme(self, name):
        """切换主题：保存设置 → 应用调色板 → 重建界面。"""
        name = theme.apply(name)
        settings_mod.set_str(self.context.storage, "theme", name)
        theme.setup_style(self)
        self._rebuild_ui()
        return name

    def _rebuild_ui(self):
        """主题切换后重建侧边栏与页面，使 tk 控件的配色全部刷新。"""
        current = self._current or "pomodoro"
        for page in self._pages.values():
            try:
                page.destroy()
            except tk.TclError:
                pass
        self._pages.clear()
        self._nav_buttons.clear()
        try:
            self.sidebar.destroy()
            self.body.destroy()
        except tk.TclError:
            pass
        self._build_sidebar()
        self._build_body()
        self.switch(current)
        if self.float_window is not None:
            self.float_window.rebuild_for_theme()

    # ================================================================ 悬浮窗
    def show_float_window(self):
        """创建（如需要）并显示迷你悬浮窗。"""
        if self.float_window is None:
            self.float_window = FloatWindow(self, self.context,
                                            on_restore=self.restore_from_float)
        self.float_window.show()
        self.var_float.set(True)

    def hide_float_window(self):
        """隐藏迷你悬浮窗。"""
        if self.float_window is not None:
            self.float_window.hide()
        self.var_float.set(False)

    def _on_float_toggle(self):
        if self.var_float.get():
            self.show_float_window()
        else:
            self.hide_float_window()

    def _on_float_auto_toggle(self):
        settings_mod.set_bool(self.context.storage, "float_auto_minimize",
                              bool(self.var_float_auto.get()))

    def restore_from_float(self):
        """从悬浮窗返回主界面：还原窗口并隐藏悬浮窗。"""
        try:
            self.deiconify()
            self.state("normal")
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass
        self._float_auto_shown = False
        self.hide_float_window()

    def _on_root_unmap(self, event):
        """主窗口被最小化时，按设置自动显示悬浮窗。"""
        if event.widget is not self:
            return
        self.after(200, self._auto_show_float)

    def _auto_show_float(self):
        try:
            iconic = self.state() == "iconic"
        except tk.TclError:
            return
        if iconic and settings_mod.get_bool(self.context.storage,
                                            "float_auto_minimize"):
            self._float_auto_shown = True
            self.show_float_window()

    def _on_root_map(self, event):
        """主窗口恢复显示时，收起此前自动弹出的悬浮窗。"""
        if event.widget is not self or not self._float_auto_shown:
            return
        self._float_auto_shown = False
        self.hide_float_window()

    # ================================================================ 页面切换
    def switch(self, key):
        page = self._pages.get(key)
        if page is None:
            page = _PAGE_CLASSES[key](self.body, self.context)
            page.grid(row=0, column=0, sticky="nsew",
                      padx=theme.PAD, pady=theme.PAD)
            self._pages[key] = page
        page.tkraise()
        self._current = key
        for nav_key, btn in self._nav_buttons.items():
            btn.configure(style="NavSelected.TButton" if nav_key == key
                          else "Nav.TButton")
        if hasattr(page, "on_show"):
            page.on_show()

    # ================================================================ 关闭
    def _on_close(self):
        stop_active_alarm()
        # 记住窗口位置与尺寸，下次启动恢复
        try:
            geometry = self.geometry()
            if _geometry_ok(geometry):
                self.context.storage.set("win_geometry", geometry)
        except tk.TclError:
            pass
        try:
            if self.context.engine.running:
                self.context.engine.pause()
        except Exception:
            pass
        if self.float_window is not None:
            try:
                self.float_window.destroy()
            except tk.TclError:
                pass
            self.float_window = None
        self.destroy()
