"""统计页：汇总数据与近 7 天专注趋势图。"""

import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app import export as export_mod
from . import theme
from .widgets import make_card, card_title, card_muted


class StatsView(ttk.Frame):
    """数据统计页面。"""

    def __init__(self, master, context):
        super().__init__(master)
        self.context = context
        self.stats = context.stats
        self._build()

    # ================================================================ 构建界面
    def _build(self):
        self.configure(style="TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        # ---- 指标卡
        top = make_card(self, padding=18)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        card_title(top, "数据总览").grid(row=0, column=0, columnspan=4,
                                        sticky="w", pady=(0, 12))
        for col in range(4):
            top.columnconfigure(col, weight=1)

        self.tiles = {}
        tiles = [
            ("today_count", "今日番茄", "0 个"),
            ("today_minutes", "今日专注", "0 分钟"),
            ("total_count", "累计番茄", "0 个"),
            ("total_hours", "累计专注", "0 小时"),
        ]
        for col, (key, caption, _placeholder) in enumerate(tiles):
            self.tiles[key] = self._tile(top, col, caption)

        sep = tk.Frame(top, height=1, bg=theme.SEP)
        sep.grid(row=2, column=0, columnspan=4, sticky="ew", pady=14)

        todo_box = tk.Frame(top, bg=theme.CARD_BG)
        todo_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 12))
        self.lb_todo = tk.Label(todo_box, text="", bg=theme.CARD_BG,
                                fg=theme.TEXT_DARK, font=theme.FONT_SUB)
        self.pb_todo = ttk.Progressbar(todo_box, mode="determinate",
                                       maximum=100,
                                       style="Green.Horizontal.TProgressbar")
        self._progress_line(todo_box, "待办完成率",
                            self.lb_todo, self.pb_todo)

        habit_box = tk.Frame(top, bg=theme.CARD_BG)
        habit_box.grid(row=3, column=2, columnspan=2, sticky="ew")
        self.lb_habit = tk.Label(habit_box, text="", bg=theme.CARD_BG,
                                 fg=theme.TEXT_DARK, font=theme.FONT_SUB)
        self.pb_habit = ttk.Progressbar(habit_box, mode="determinate",
                                        maximum=100,
                                        style="Green.Horizontal.TProgressbar")
        self._progress_line(habit_box, "习惯平均完成率",
                            self.lb_habit, self.pb_habit)

        # ---- 数据导出与备份
        export_row = tk.Frame(top, bg=theme.CARD_BG)
        export_row.grid(row=4, column=0, columnspan=4, sticky="ew",
                        pady=(14, 0))
        card_muted(export_row, "数据导出与备份（CSV 可用 Excel 直接打开）："
                               ).pack(anchor="w", pady=(0, 6))
        btns = tk.Frame(export_row, bg=theme.CARD_BG)
        btns.pack(anchor="w")
        export_items = [
            ("导出待办 CSV", self._on_export_todo),
            ("导出习惯 CSV", self._on_export_habits),
            ("导出专注记录 CSV", self._on_export_focus),
            ("导出全部记录 CSV", self._on_export_sessions),
            ("备份数据库", self._on_backup_db),
        ]
        for text, cmd in export_items:
            btn = ttk.Button(btns, text=text, style="Ghost.TButton",
                             command=cmd)
            btn.pack(side="left", padx=(0, 8))

        # ---- 趋势图卡
        chart_card = make_card(self, padding=18)
        chart_card.grid(row=1, column=0, sticky="nsew")
        chart_card.columnconfigure(0, weight=1)
        chart_card.rowconfigure(1, weight=1)

        card_title(chart_card, "近 7 天专注趋势（分钟）").grid(
            row=0, column=0, sticky="w", pady=(0, 8))
        self.canvas = tk.Canvas(chart_card, bg=theme.CARD_BG, height=210,
                                highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _e: self._draw_chart())

    def _tile(self, parent, col, caption):
        box = tk.Frame(parent, bg=theme.TILE_BG,
                       highlightbackground=theme.TILE_BORDER, highlightthickness=1)
        box.grid(row=1, column=col, sticky="ew", padx=4)
        value = tk.Label(box, text="…", bg=theme.TILE_BG, fg=theme.ACCENT_DARK,
                         font=theme.FONT_STAT)
        value.pack(pady=(10, 0))
        tk.Label(box, text=caption, bg=theme.TILE_BG, fg=theme.TEXT_MUTED,
                 font=theme.FONT_SMALL).pack(pady=(0, 8))
        return value

    def _progress_line(self, parent, caption, value_label, bar):
        head = tk.Frame(parent, bg=theme.CARD_BG)
        head.pack(fill="x")
        tk.Label(head, text=caption, bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                 font=theme.FONT_SMALL).pack(side="left")
        value_label.pack(side="right")
        bar.pack(fill="x", pady=(6, 0))

    # ================================================================ 数据导出与备份
    def _default_dir(self):
        return str(Path.home() / "Documents") if os.path.isdir(
            str(Path.home() / "Documents")) else str(Path.home())

    def _ask_save(self, title, defname):
        return filedialog.asksaveasfilename(
            title=title, initialdir=self._default_dir(),
            initialfile=defname, defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
            parent=self.winfo_toplevel())

    def _on_export_todo(self):
        path = self._ask_save("导出待办清单", "待办清单.csv")
        if not path:
            return
        text = export_mod.todos_to_csv(self.context.todo.list_todos())
        export_mod.save_text_file(path, text)
        messagebox.showinfo("导出成功", "待办已导出到：\n%s" % path)

    def _on_export_habits(self):
        path = self._ask_save("导出习惯打卡", "习惯打卡.csv")
        if not path:
            return
        habits = self.context.habits.list_habits()
        text = export_mod.habits_to_csv(habits)
        export_mod.save_text_file(path, text)
        messagebox.showinfo("导出成功", "习惯数据已导出到：\n%s" % path)

    def _on_export_focus(self):
        path = self._ask_save("导出专注记录", "专注记录.csv")
        if not path:
            return
        text = export_mod.export_focus_csv(self.context.storage)
        export_mod.save_text_file(path, text)
        messagebox.showinfo("导出成功", "专注记录已导出到：\n%s" % path)

    def _on_export_sessions(self):
        path = self._ask_save("导出全部阶段记录", "全部记录.csv")
        if not path:
            return
        text = export_mod.export_all_sessions_csv(self.context.storage)
        export_mod.save_text_file(path, text)
        messagebox.showinfo("导出成功", "全部记录已导出到：\n%s" % path)

    def _on_backup_db(self):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="备份数据库", initialdir=self._default_dir(),
            initialfile="番茄工作台备份_%s.db" % stamp,
            defaultextension=".db",
            filetypes=[("SQLite 数据库", "*.db"), ("所有文件", "*.*")],
            parent=self.winfo_toplevel())
        if not path:
            return
        export_mod.backup_database(self.context.storage, path)
        messagebox.showinfo("备份成功", "数据库已备份到：\n%s\n\n"
                                      "还原方法：关闭软件后，用该文件替换\n"
                                      "~/.pomodoro_workbench/data.db" % path)

    # ================================================================ 数据
    def refresh(self):
        data = self.stats.overall()
        focus = data["focus"]
        hours = focus["total_minutes"] / 60.0
        self.tiles["today_count"].config(text="%d 个" % focus["today_count"])
        self.tiles["today_minutes"].config(text="%d 分钟" % focus["today_minutes"])
        self.tiles["total_count"].config(text="%d 个" % focus["total_count"])
        self.tiles["total_hours"].config(
            text="%.1f 小时" % hours if hours else "0 小时")

        todo = data["todo"]
        self.lb_todo.config(text="%d / %d 项（%.0f%%）"
                                 % (todo["done"], todo["total"], todo["rate"]))
        self.pb_todo.config(value=todo["rate"])

        habit = data["habit"]
        habit_text = "共 %d 个习惯" % habit["count"] if habit["count"] else "还没有习惯"
        self.lb_habit.config(text="%s · %.0f%%" % (habit_text,
                                                   habit["avg_rate"] * 100))
        self.pb_habit.config(value=habit["avg_rate"] * 100)
        self._draw_chart()

    def _draw_chart(self):
        canvas = self.canvas
        canvas.delete("all")
        width = max(200, canvas.winfo_width() - 4)
        height = max(120, canvas.winfo_height() - 4)
        if width < 60:
            return

        margin_l, margin_r, margin_t, margin_b = 44, 12, 20, 30
        plot_w = width - margin_l - margin_r
        plot_h = height - margin_t - margin_b

        days = self.stats.last_days_focus(7)
        values = [d["minutes"] for d in days]
        peak = max(values) if values else 0
        scale = peak if peak > 0 else 1

        # 网格线
        canvas.create_rectangle(margin_l, margin_t,
                                margin_l + plot_w, margin_t + plot_h,
                                outline=theme.PLOT_BORDER, fill=theme.PLOT_BG)
        for i in range(5):
            y = margin_t + plot_h - plot_h * i / 4
            canvas.create_line(margin_l, y, margin_l + plot_w, y,
                               fill=theme.PLOT_GRID)
            canvas.create_text(margin_l - 8, y, text=str(round(scale * i / 4)),
                               anchor="e", fill=theme.TEXT_MUTED,
                               font=theme.FONT_SMALL)

        slot = plot_w / len(days)
        bar_w = min(44, slot * 0.5)
        for idx, day in enumerate(days):
            cx = margin_l + slot * idx + slot / 2
            v = day["minutes"]
            bar_h = plot_h * (v / scale) if v else 2
            x0 = cx - bar_w / 2
            y0 = margin_t + plot_h - bar_h
            color = theme.GREEN if idx == len(days) - 1 else theme.BLUE
            canvas.create_rectangle(x0, y0, x0 + bar_w, margin_t + plot_h,
                                    fill=color, outline=color)
            canvas.create_text(cx, margin_t + plot_h + 10,
                               text=day["label"], fill=theme.TEXT_DARK,
                               font=theme.FONT_SMALL)
            if v > 0:
                canvas.create_text(cx, y0 - 9, text=str(v), fill=theme.TEXT_MUTED,
                                   font=theme.FONT_SMALL)
            else:
                canvas.create_text(cx, margin_t + plot_h - 10, text="0",
                                   fill=theme.TEXT_MUTED, font=theme.FONT_SMALL)

    def on_show(self):
        self.refresh()
