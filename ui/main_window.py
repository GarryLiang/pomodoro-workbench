"""主窗口：侧边导航 + 页面容器。"""

import tkinter as tk
from tkinter import ttk

from . import theme
from .pomodoro_view import PomodoroView
from .todo_view import TodoView
from .habit_view import HabitView
from .stats_view import StatsView
from .reminder import stop_active_alarm

APP_TITLE = "番茄工作台"
APP_VERSION = "v1.0.0"

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


class MainWindow(tk.Tk):
    """应用主窗口。"""

    def __init__(self, context):
        super().__init__()
        self.context = context
        self._pages = {}
        self._nav_buttons = {}
        self._current = None

        self.title("%s %s" % (APP_TITLE, APP_VERSION))
        self.geometry("1040x680")
        self.minsize(940, 620)
        theme.setup_style(self)

        self._build_sidebar()
        self._build_body()
        self.switch("pomodoro")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================================================================ 界面
    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=theme.SIDEBAR_BG, width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo = tk.Frame(sidebar, bg=theme.SIDEBAR_BG)
        logo.pack(fill="x", pady=(22, 6), padx=16)
        tk.Label(logo, text="🍅 番茄工作台", bg=theme.SIDEBAR_BG,
                 fg="#ffffff", font=(theme.FONT_FAMILY, 15, "bold")).pack(
            anchor="w")
        tk.Label(logo, text="专注 · 待办 · 习惯", bg=theme.SIDEBAR_BG,
                 fg="#8fa2bb", font=theme.FONT_SMALL).pack(anchor="w",
                                                           pady=(2, 0))

        line = tk.Frame(sidebar, bg="#33465f", height=1)
        line.pack(fill="x", padx=14, pady=10)

        for key, label in NAV_ITEMS:
            btn = ttk.Button(sidebar, text=label, style="Nav.TButton",
                             command=lambda k=key: self.switch(k))
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = btn

        tk.Label(sidebar, text=APP_VERSION + " ｜ 数据仅存本地", bg=theme.SIDEBAR_BG,
                 fg="#66788f", font=theme.FONT_SMALL).pack(side="bottom",
                                                           pady=14)

    def _build_body(self):
        body = tk.Frame(self, bg=theme.BG)
        body.pack(side="left", fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.body = body

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
        try:
            if self.context.engine.running:
                self.context.engine.pause()
        except Exception:
            pass
        self.destroy()
