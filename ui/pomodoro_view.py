"""专注页：番茄钟主界面。"""

import tkinter as tk
from tkinter import ttk

from app import settings as settings_mod
from app.pomodoro import (
    PHASE_FOCUS, PHASE_SHORT, PHASE_LONG, PHASE_LABELS,
    EV_STARTED, EV_PAUSED, EV_PHASE_COMPLETE, EV_PHASE_SKIPPED,
    EV_RESET, EV_PHASE_CHANGED,
)
from . import theme
from .reminder import show_phase_reminder
from .widgets import make_card, card_title, card_muted

NONE_TASK = "（不关联待办）"


class PomodoroView(ttk.Frame):
    """番茄钟工作台页面。"""

    def __init__(self, master, context):
        super().__init__(master)
        self.context = context
        self.engine = context.engine
        self._current_task_id = None
        self._after_id = None
        self._task_map = {}
        self._build()
        self.engine.on(self._on_engine_event)
        self._poll()

    # ================================================================ 构建界面
    def _build(self):
        self.configure(style="TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        left = make_card(self, padding=24)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        card_title(left, "番茄专注").grid(row=0, column=0, sticky="w")

        # 中央倒计时区
        center = tk.Frame(left, bg=theme.CARD_BG)
        center.grid(row=1, column=0, sticky="nsew", pady=8)
        center.columnconfigure(0, weight=1)
        center.rowconfigure(2, weight=1)

        self.phase_label = tk.Label(center, text="就绪", bg=theme.CARD_BG,
                                    fg=theme.TEXT_MUTED, font=theme.FONT_SUB)
        self.phase_label.grid(row=0, column=0, pady=(14, 0))

        self.time_label = tk.Label(center, text="--:--", bg=theme.CARD_BG,
                                   fg=theme.TEXT_DARK, font=theme.FONT_TIME)
        self.time_label.grid(row=1, column=0)

        self.status_label = tk.Label(center, text="点击下方按钮开始一次专注",
                                     bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                                     font=theme.FONT_SUB)
        self.status_label.grid(row=2, column=0, pady=(0, 4))

        self.progress = ttk.Progressbar(center, mode="determinate",
                                        maximum=100, value=0)
        self.progress.grid(row=3, column=0, sticky="ew", padx=30, pady=(6, 10))

        # 操作按钮
        buttons = tk.Frame(center, bg=theme.CARD_BG)
        buttons.grid(row=4, column=0, pady=6)
        self.btn_toggle = ttk.Button(buttons, text="▶ 开始专注",
                                     style="Accent.TButton",
                                     command=self._on_toggle)
        self.btn_toggle.grid(row=0, column=0, padx=6)
        self.btn_reset = ttk.Button(buttons, text="重置", style="Ghost.TButton",
                                    command=self._on_reset)
        self.btn_reset.grid(row=0, column=1, padx=6)
        self.btn_skip = ttk.Button(buttons, text="跳过", style="Ghost.TButton",
                                   command=self._on_skip)
        self.btn_skip.grid(row=0, column=2, padx=6)

        # 任务关联区
        link_box = tk.LabelFrame(left, text=" 本次专注关联待办（可选） ",
                                 bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                                 font=theme.FONT_SUB, bd=0,
                                 highlightthickness=0)
        link_box.grid(row=2, column=0, sticky="ew", pady=(2, 8))
        link_box.columnconfigure(0, weight=1)
        self.task_combo = ttk.Combobox(link_box, state="readonly", width=40)
        self.task_combo.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=6)
        self.task_combo.bind("<<ComboboxSelected>>", self._on_task_selected)
        refresh_btn = ttk.Button(link_box, text="刷新列表", style="Ghost.TButton",
                                 command=self.refresh_tasks)
        refresh_btn.grid(row=0, column=1, padx=(0, 10), pady=6)

        self.today_label = tk.Label(left, text="", bg=theme.CARD_BG,
                                    fg=theme.TEXT_MUTED, font=theme.FONT_SMALL)
        self.today_label.grid(row=3, column=0, sticky="w", pady=(0, 4))

        # 右侧设置卡
        right = make_card(self, padding=16)
        right.grid(row=0, column=1, sticky="ns")
        right.columnconfigure(0, weight=1)

        card_title(right, "时长设置").pack(fill="x", pady=(0, 6))
        card_muted(right, "专注结束后自动进入休息，"
                          "休息结束后自动回到专注。").pack(fill="x", pady=(0, 10))

        self.var_focus = tk.StringVar(value="25")
        self.var_short = tk.StringVar(value="5")
        self.var_long = tk.StringVar(value="15")
        self.var_interval = tk.StringVar(value="4")
        self.var_auto = tk.BooleanVar(value=True)
        self.var_reminder = tk.BooleanVar(value=True)

        form = tk.Frame(right, bg=theme.CARD_BG)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self._add_row(form, 0, "专注时长（分）", self.var_focus, 3, 180)
        self._add_row(form, 1, "短休息（分）", self.var_short, 1, 60)
        self._add_row(form, 2, "长休息（分）", self.var_long, 1, 120)
        self._add_row(form, 3, "间隔（个专注）", self.var_interval, 1, 12)

        auto_row = tk.Frame(right, bg=theme.CARD_BG)
        auto_row.pack(fill="x", pady=(8, 0))
        tk.Checkbutton(auto_row, text="阶段结束后自动开始下一阶段",
                       variable=self.var_auto, bg=theme.CARD_BG,
                       fg=theme.TEXT_DARK, font=theme.FONT_BODY,
                       activebackground=theme.CARD_BG,
                       highlightthickness=0).pack(anchor="w")

        remind_row = tk.Frame(right, bg=theme.CARD_BG)
        remind_row.pack(fill="x", pady=(2, 10))
        tk.Checkbutton(remind_row, text="阶段结束响铃 + 弹窗提醒",
                       variable=self.var_reminder, bg=theme.CARD_BG,
                       fg=theme.TEXT_DARK, font=theme.FONT_BODY,
                       activebackground=theme.CARD_BG,
                       highlightthickness=0).pack(anchor="w")

        apply_btn = ttk.Button(right, text="应用设置", style="Accent.TButton",
                               command=self._on_apply_settings)
        apply_btn.pack(fill="x", pady=(4, 10))

        self.settings_hint = card_muted(right, "")
        self.settings_hint.pack(fill="x")

        self._load_settings()
        self.refresh_tasks()

    def _add_row(self, parent, row, text, var, lo, hi):
        tk.Label(parent, text=text, bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                 font=theme.FONT_BODY).grid(row=row, column=0, sticky="w", pady=3)
        spin = ttk.Spinbox(parent, from_=lo, to=hi, textvariable=var, width=8)
        spin.grid(row=row, column=1, sticky="e", padx=(10, 0), pady=3)

    # ================================================================ 设置
    def _load_settings(self):
        cfg = self.context.engine_settings()
        self.var_focus.set(str(cfg["focus_min"]))
        self.var_short.set(str(cfg["short_break_min"]))
        self.var_long.set(str(cfg["long_break_min"]))
        self.var_interval.set(str(cfg["long_break_after"]))
        self.var_auto.set(cfg["auto_start"])
        self.var_reminder.set(settings_mod.get_bool(
            self.context.storage, "reminder_enabled"))
        self.settings_hint.config(text="")

    def _on_apply_settings(self):
        def num(var, default):
            try:
                return max(1, int(var.get()))
            except (ValueError, tk.TclError):
                return default

        focus = num(self.var_focus, 25)
        short = num(self.var_short, 5)
        long_ = num(self.var_long, 15)
        interval = num(self.var_interval, 4)
        self.context.apply_engine_settings(
            focus, short, long_, min(interval, 12), bool(self.var_auto.get()))
        settings_mod.set_bool(self.context.storage, "reminder_enabled",
                              bool(self.var_reminder.get()))
        self._load_settings()
        self.settings_hint.config(text="设置已保存并生效", fg=theme.GREEN)
        self._refresh_ui()

    # ================================================================ 任务关联
    def refresh_tasks(self):
        """刷新待办下拉列表（只列出未完成任务）。"""
        selected = self._current_task_id
        self._task_map = {}
        values = [NONE_TASK]
        for todo in self.context.todo.list_todos(status="active"):
            title = todo.title if len(todo.title) <= 22 else todo.title[:21] + "…"
            display = "%s" % title
            self._task_map[display] = todo.id
            values.append(display)
        self.task_combo["values"] = values
        target = NONE_TASK
        for display, tid in self._task_map.items():
            if tid == selected:
                target = display
                break
        self.task_combo.set(target)
        self._current_task_id = self._task_map.get(target)

    def _on_task_selected(self, _event=None):
        display = self.task_combo.get()
        self._current_task_id = self._task_map.get(display)

    # ================================================================ 操作
    def _on_toggle(self):
        if self.engine.phase is None:
            self.engine.start(PHASE_FOCUS)
        else:
            self.engine.toggle()
        self._refresh_ui()

    def _on_reset(self):
        self.engine.reset()
        self._refresh_ui()

    def _on_skip(self):
        self.engine.skip()
        self._refresh_ui()

    # ================================================================ 引擎事件
    def _on_engine_event(self, event, data):
        if event == EV_PHASE_COMPLETE:
            self._on_phase_complete(data)
        self._refresh_ui()

    def _on_phase_complete(self, data):
        phase = data.get("phase")
        if phase == PHASE_FOCUS:
            duration_min = int(data.get("duration", 0)) // 60
            task_id = self._current_task_id
            self.context.record_focus_session(task_id=task_id,
                                              duration_min=duration_min)
        self._maybe_remind(phase)

    def _maybe_remind(self, phase):
        """阶段结束时：按设置弹出闹钟提醒，不同阶段播放不同铃声。"""
        if not settings_mod.get_bool(self.context.storage,
                                     "reminder_enabled"):
            return
        messages = {
            PHASE_FOCUS: ("专注结束 🎉",
                          "干得漂亮！起来活动一下、喝口水，好好休息吧。",
                          "🎉", "focus"),
            PHASE_SHORT: ("短休息结束",
                          "休息好了吗？收拾心情，开始下一轮专注吧。",
                          "🍅", "short_break"),
            PHASE_LONG: ("长休息结束",
                         "长时间休息结束，精力满满，开启新一轮冲刺吧！",
                         "⚡", "long_break"),
        }
        data = messages.get(phase)
        if data is None:
            return
        title, message, icon, sound = data
        show_phase_reminder(self.winfo_toplevel(), title, message, icon,
                            sound=sound)

    # ================================================================ 定时刷新
    def _poll(self):
        """每秒推进一次引擎并刷新界面。"""
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            if self.engine.running and self.engine.phase is not None:
                self.engine.tick()
            self._refresh_ui()
        except Exception:
            pass
        self._after_id = self.after(1000, self._poll)

    def destroy(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        super().destroy()

    # ================================================================ 界面刷新
    def _refresh_ui(self):
        engine = self.engine
        phase = engine.phase

        if phase is None:
            self.phase_label.config(text="就绪", fg=theme.TEXT_MUTED)
            self.time_label.config(text="--:--", fg=theme.TEXT_MUTED)
            self.status_label.config(text="点击「开始专注」进入番茄钟")
            self.progress.config(maximum=1, value=0)
            self.btn_toggle.config(text="▶ 开始专注")
            self.btn_reset.state(["disabled"])
            self.btn_skip.state(["disabled"])
        else:
            color = {PHASE_FOCUS: theme.ACCENT,
                     PHASE_SHORT: theme.GREEN,
                     PHASE_LONG: theme.BLUE}[phase]
            self.phase_label.config(text=PHASE_LABELS[phase], fg=color)
            self.time_label.config(text=engine.format_remaining(), fg=color)
            total = engine.duration_for(phase)
            done = total - engine.remaining
            self.progress.config(maximum=total, value=done)
            self.btn_reset.state(["!disabled"])
            self.btn_skip.state(["!disabled"])
            if engine.running:
                self.status_label.config(text="正在专注，保持节奏～", fg=color)
                self.btn_toggle.config(text="⏸ 暂停")
            else:
                self.status_label.config(text="已暂停，点击继续", fg=theme.TEXT_MUTED)
                self.btn_toggle.config(text="▶ 继续")

        summary = self.context.stats.focus_summary()
        self.today_label.config(
            text="今日已完成 %d 个番茄 · 专注 %d 分钟 ｜ 累计 %d 个番茄 · %d 分钟"
                 % (summary["today_count"], summary["today_minutes"],
                    summary["total_count"], summary["total_minutes"]))
