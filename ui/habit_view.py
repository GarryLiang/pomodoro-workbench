"""习惯页：习惯打卡与日历热力图。"""

from datetime import date, timedelta

import tkinter as tk
from tkinter import ttk, messagebox

from app.habit import heatmap_range
from . import theme
from .widgets import make_card, card_title, card_muted

# 热力图格子尺寸
_CELL = 13
_GAP = 3


class HabitView(ttk.Frame):
    """习惯打卡页面。"""

    def __init__(self, master, context):
        super().__init__(master)
        self.context = context
        self.manager = context.habits
        self._habits = []
        self._selected_id = None
        self._build()
        self.refresh()

    # ================================================================ 构建界面
    def _build(self):
        self.configure(style="TFrame")
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = make_card(self, padding=14)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        card_title(left, "我的习惯").pack(fill="x", pady=(0, 4))
        card_muted(left, "每天坚持一点点，看见自己的进步。").pack(
            fill="x", pady=(0, 10))

        add_row = tk.Frame(left, bg=theme.CARD_BG)
        add_row.pack(fill="x", pady=(0, 8))
        self.entry_name = ttk.Entry(add_row, width=18)
        self.entry_name.pack(side="left", fill="x", expand=True)
        self.entry_name.bind("<Return>", lambda _e: self._on_add())
        ttk.Button(add_row, text="添加", style="Accent.TButton",
                   command=self._on_add).pack(side="left", padx=(6, 0))

        self.listbox = tk.Listbox(left, height=12, width=24,
                                  bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                                  font=theme.FONT_BODY,
                                  selectbackground="#dbe7f7",
                                  selectforeground=theme.TEXT_DARK,
                                  highlightthickness=1,
                                  highlightbackground="#e1e6ef",
                                  bd=0, activestyle="none")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        ops = tk.Frame(left, bg=theme.CARD_BG)
        ops.pack(fill="x", pady=(10, 0))
        self.btn_today = ttk.Button(ops, text="今日打卡", style="Accent.TButton",
                                    command=self._on_toggle_today)
        self.btn_today.pack(fill="x", pady=2)
        self.btn_delete = ttk.Button(ops, text="删除该习惯", style="Ghost.TButton",
                                     command=self._on_delete)
        self.btn_delete.pack(fill="x", pady=2)

        # 右侧详情 + 热力图
        right = make_card(self, padding=16)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        self.detail_title = card_title(right, "选择一个习惯查看详情")
        self.detail_title.pack(fill="x", pady=(0, 4))
        self.detail_muted = card_muted(right, "")
        self.detail_muted.pack(fill="x")

        stats_row = tk.Frame(right, bg=theme.CARD_BG)
        stats_row.pack(fill="x", pady=8)
        self.lb_total = self._stat_box(stats_row, 0, "总打卡天数")
        self.lb_current = self._stat_box(stats_row, 1, "当前连续")
        self.lb_best = self._stat_box(stats_row, 2, "最长连续")
        self.lb_month = self._stat_box(stats_row, 3, "本月完成率")

        month_bar = tk.Frame(right, bg=theme.CARD_BG)
        month_bar.pack(fill="x", pady=(0, 8))
        tk.Label(month_bar, text="本月进度", bg=theme.CARD_BG,
                 fg=theme.TEXT_MUTED, font=theme.FONT_SMALL).pack(side="left")
        self.month_progress = ttk.Progressbar(month_bar, mode="determinate",
                                              style="Green.Horizontal.TProgressbar",
                                              maximum=100, value=0)
        self.month_progress.pack(side="left", fill="x", expand=True,
                                 padx=10)

        tk.Label(right, text="打卡热力图（近 15 周）", bg=theme.CARD_BG,
                 fg=theme.TEXT_MUTED, font=theme.FONT_SUB).pack(
            anchor="w", pady=(4, 2))
        self.canvas = tk.Canvas(right, bg=theme.CARD_BG, height=180,
                                highlightthickness=0)
        self.canvas.pack(fill="x", pady=(0, 4))

        legend = tk.Frame(right, bg=theme.CARD_BG)
        legend.pack(anchor="e")
        tk.Label(legend, text="少", bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                 font=theme.FONT_SMALL).pack(side="left")
        for color in (theme.GRID_EMPTY, theme.GRID_L1, theme.GRID_L2,
                      theme.GRID_L3, theme.GRID_L4):
            cell = tk.Frame(legend, width=_CELL, height=_CELL, bg=color)
            cell.pack(side="left", padx=2)
            cell.pack_propagate(False)
        tk.Label(legend, text="多", bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                 font=theme.FONT_SMALL).pack(side="left")

        self._disable_ops()

    def _stat_box(self, parent, col, caption):
        box = tk.Frame(parent, bg=theme.CARD_BG,
                       highlightbackground="#eef1f7", highlightthickness=1)
        box.grid(row=0, column=col, sticky="ew", padx=3, pady=2)
        parent.columnconfigure(col, weight=1)
        value = tk.Label(box, text="0", bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                         font=theme.FONT_STAT)
        value.pack()
        tk.Label(box, text=caption, bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                 font=theme.FONT_SMALL).pack()
        return value

    # ================================================================ 数据
    def _reload_habits(self):
        self._habits = self.manager.list_habits()
        self.listbox.delete(0, "end")
        for habit in self._habits:
            self.listbox.insert("end", "%s   🔥%d" % (habit.name,
                                                      habit.current_streak()))
        if not self._habits:
            self._selected_id = None
            self.listbox.selection_clear(0, "end")
        elif self._selected_id is None or not any(
                h.id == self._selected_id for h in self._habits):
            self._selected_id = self._habits[0].id
        self._sync_selection()
        self._update_detail()

    def _sync_selection(self):
        for idx, habit in enumerate(self._habits):
            if habit.id == self._selected_id:
                self.listbox.selection_clear(0, "end")
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                return

    def _selected_habit(self):
        if self._selected_id is None:
            return None
        for habit in self._habits:
            if habit.id == self._selected_id:
                return habit
        return None

    def _update_detail(self):
        habit = self._selected_habit()
        today = date.today()
        if habit is None:
            self.detail_title.config(text="还没有习惯，在左侧添加一个吧")
            self.detail_muted.config(text="")
            self.lb_total.config(text="-")
            self.lb_current.config(text="-")
            self.lb_best.config(text="-")
            self.lb_month.config(text="-")
            self.month_progress.config(value=0)
            self.canvas.delete("all")
            self._disable_ops()
            return

        checked_today = habit.is_checked(today)
        self.detail_title.config(text=habit.name)
        self.detail_muted.config(
            text="创建于 %s · 本月已完成 %d 天"
                 % (habit.created_at[:10],
                    sum(1 for d in habit.checked_dates
                        if d.year == today.year and d.month == today.month)))
        self.lb_total.config(text=str(habit.total_days()))
        self.lb_current.config(text=str(habit.current_streak(today)))
        self.lb_best.config(text=str(habit.best_streak()))
        rate = habit.month_rate(today)
        self.lb_month.config(text="%.0f%%" % (rate * 100))
        self.month_progress.config(value=rate * 100)
        self.btn_today.state(["!disabled"])
        self.btn_today.config(
            text="已打卡（点击取消）" if checked_today else "✓ 今日打卡")
        self.btn_delete.state(["!disabled"])
        self._draw_heatmap(habit)

    def _disable_ops(self):
        self.btn_today.state(["disabled"])
        self.btn_delete.state(["disabled"])
        self.btn_today.config(text="今日打卡")

    # ================================================================ 操作
    def _on_add(self):
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("提示", "请填写习惯名称")
            return
        if len(name) > 20:
            messagebox.showwarning("提示", "习惯名称请控制在 20 字以内")
            return
        habit_id = self.manager.add_habit(name)
        self.entry_name.delete(0, "end")
        self._selected_id = habit_id
        self._reload_habits()

    def _on_select(self, _event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        habit = self._habits[sel[0]]
        self._selected_id = habit.id
        self._update_detail()

    def _on_toggle_today(self):
        habit = self._selected_habit()
        if habit is None:
            return
        today = date.today()
        if habit.is_checked(today):
            self.manager.uncheck(habit.id, today.isoformat())
        else:
            self.manager.check_in(habit.id, today.isoformat())
        self._reload_habits()

    def _on_delete(self):
        habit = self._selected_habit()
        if habit is None:
            return
        if messagebox.askyesno("删除确认",
                               "确定删除习惯「%s」及全部打卡记录吗？" % habit.name):
            self.manager.delete_habit(habit.id)
            self._selected_id = None
            self._reload_habits()

    # ================================================================ 热力图
    def _draw_heatmap(self, habit):
        canvas = self.canvas
        canvas.delete("all")
        today = date.today()
        start, _end = heatmap_range()

        # 从 start 所在周的周一开始排布
        first_monday = start - timedelta(days=start.weekday())
        col_count = (today - first_monday).days // 7 + 1

        origin_x = 40  # 给星期标签留出空间
        origin_y = 24  # 给月份标签留出空间
        step = _CELL + _GAP
        width = origin_x + col_count * step + 8
        height = origin_y + 7 * step + 10
        canvas.configure(width=width, height=height)

        # 星期标签（周一 / 周三 / 周五 / 周日）
        for weekday, label in ((0, "一"), (2, "三"), (4, "五"), (6, "日")):
            y = origin_y + weekday * step + _CELL // 2
            canvas.create_text(20, y, text=label, fill=theme.TEXT_MUTED,
                               font=theme.FONT_SMALL)

        # 月份标签：仅在列首月的第一天列上方标注
        prev_month = None
        for col in range(col_count):
            monday = first_monday + timedelta(days=col * 7)
            if monday > today:
                continue
            month_key = (monday.year, monday.month)
            if month_key != prev_month:
                canvas.create_text(
                    origin_x + col * step + _CELL // 2, 10,
                    text="%d月" % monday.month, fill=theme.TEXT_MUTED,
                    font=theme.FONT_SMALL)
                prev_month = month_key

        for col in range(col_count):
            for row in range(7):
                day = first_monday + timedelta(days=col * 7 + row)
                if day < start or day > today:
                    continue
                count = habit.checked_dates.get(day, 0)
                if count <= 0:
                    color = theme.GRID_EMPTY
                else:
                    color = (theme.GRID_L1, theme.GRID_L2,
                             theme.GRID_L3, theme.GRID_L4)[min(4, count) - 1]
                x = origin_x + col * step
                y = origin_y + row * step
                canvas.create_rectangle(x, y, x + _CELL, y + _CELL,
                                        fill=color, outline=color)
                if day == today:
                    canvas.create_rectangle(x - 1, y - 1, x + _CELL + 1,
                                            y + _CELL + 1, outline=theme.ACCENT,
                                            width=2)

    # ================================================================ 对外
    def on_show(self):
        self.refresh()

    def refresh(self):
        self._reload_habits()
