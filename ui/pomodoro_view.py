"""专注页：番茄钟主界面。"""

import os
import tkinter as tk
from tkinter import filedialog, ttk

from app import settings as settings_mod
from app.pomodoro import (
    PHASE_FOCUS, PHASE_SHORT, PHASE_LONG, PHASE_LABELS,
    EV_STARTED, EV_PAUSED, EV_PHASE_COMPLETE, EV_PHASE_SKIPPED,
    EV_RESET, EV_PHASE_CHANGED,
)
from . import theme
from .reminder import (custom_alarm_available, play_preview,
                       show_phase_reminder, stop_active_alarm)
from .widgets import make_card, card_title, card_muted
from app.logger import log_exception

NONE_TASK = "（不关联待办）"

# 试听铃声下拉框选项 -> 阶段常量
PREVIEW_KINDS = {
    "专注结束铃声（凯旋）": PHASE_FOCUS,
    "短休息结束铃声（双音）": PHASE_SHORT,
    "长休息结束铃声（号角）": PHASE_LONG,
}


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
        self._engine_off = self.engine.on(self._on_engine_event)
        self._poll()

    # ================================================================ 首次使用引导
    def _build_welcome(self):
        """首次运行显示一条使用引导，点击「知道了」后不再出现。返回内容起始行号。"""
        if settings_mod.get_bool(self.context.storage, "welcome_shown"):
            return 0
        banner = tk.Frame(self, bg=theme.TILE_BG,
                          highlightbackground=theme.TILE_BORDER,
                          highlightthickness=1)
        banner.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        tk.Label(
            banner,
            text="👋 欢迎使用番茄工作台！三步上手：① 到「待办清单」添加一条任务　"
                 "② 回本页选择任务后点「开始专注」　③ 侧边栏可开启「迷你悬浮窗」",
            bg=theme.TILE_BG, fg=theme.TEXT_DARK, font=theme.FONT_SMALL,
            justify="left", wraplength=720).pack(side="left", padx=12, pady=8)
        tk.Button(banner, text="知道了", relief="flat", bd=0, cursor="hand2",
                  bg=theme.ACCENT, fg="#ffffff",
                  activebackground=theme.ACCENT_DARK,
                  activeforeground="#ffffff",
                  font=(theme.FONT_FAMILY, 9, "bold"), padx=10, pady=3,
                  command=lambda: self._dismiss_welcome(banner)).pack(
            side="right", padx=10, pady=6)
        return 1

    def _dismiss_welcome(self, banner):
        settings_mod.set_bool(self.context.storage, "welcome_shown", True)
        try:
            banner.destroy()
        except tk.TclError:
            pass

    # ================================================================ 构建界面
    def _build(self):
        self.configure(style="TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        row_offset = self._build_welcome()   # 首次使用时展示引导条

        left = make_card(self)
        left.grid(row=row_offset, column=0, sticky="nsew", padx=(0, 10))
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
        right = make_card(self)
        right.grid(row=row_offset, column=1, sticky="ns")
        right.columnconfigure(0, weight=1)

        card_title(right, "时长设置").pack(fill="x", pady=(0, 6))
        card_muted(right, "专注结束后自动进入休息，"
                          "休息结束后自动回到专注。").pack(fill="x", pady=(0, 10))

        self.var_focus = tk.StringVar(value="25")
        self.var_short = tk.StringVar(value="5")
        self.var_long = tk.StringVar(value="15")
        self.var_interval = tk.StringVar(value="4")
        self.var_auto = tk.BooleanVar(value=True)
        self.var_popup = tk.BooleanVar(value=True)
        self.var_sound = tk.BooleanVar(value=True)
        self.var_seconds = tk.StringVar(value="20")
        self.var_preview = tk.StringVar(value=list(PREVIEW_KINDS)[0])
        self.var_custom = tk.StringVar(value="")

        form = tk.Frame(right, bg=theme.CARD_BG)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self._add_row(form, 0, "专注时长（分）", self.var_focus, 3, 180)
        self._add_row(form, 1, "短休息（分）", self.var_short, 1, 60)
        self._add_row(form, 2, "长休息（分）", self.var_long, 1, 120)
        self._add_row(form, 3, "间隔（个专注）", self.var_interval, 1, 12)
        self._add_row(form, 4, "停铃时长（秒）", self.var_seconds, 5, 120)

        auto_row = tk.Frame(right, bg=theme.CARD_BG)
        auto_row.pack(fill="x", pady=(8, 0))
        tk.Checkbutton(auto_row, text="阶段结束后自动开始下一阶段",
                       variable=self.var_auto, bg=theme.CARD_BG,
                       fg=theme.TEXT_DARK, font=theme.FONT_BODY,
                       activebackground=theme.CARD_BG,
                       highlightthickness=0).pack(anchor="w")

        # ---- 闹钟提醒设置 ----
        alarm_sep = tk.Frame(right, height=1, bg=theme.SEP)
        alarm_sep.pack(fill="x", pady=(10, 8))
        card_muted(right, "闹钟提醒（不同阶段铃声不同）").pack(fill="x")

        remind_row = tk.Frame(right, bg=theme.CARD_BG)
        remind_row.pack(fill="x", pady=(6, 0))
        tk.Checkbutton(remind_row, text="弹窗提醒", variable=self.var_popup,
                       bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                       font=theme.FONT_BODY, activebackground=theme.CARD_BG,
                       highlightthickness=0).pack(side="left")
        tk.Checkbutton(remind_row, text="响铃提醒", variable=self.var_sound,
                       bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                       font=theme.FONT_BODY, activebackground=theme.CARD_BG,
                       highlightthickness=0).pack(side="left", padx=(12, 0))

        preview_row = tk.Frame(right, bg=theme.CARD_BG)
        preview_row.pack(fill="x", pady=(8, 0))
        self.combo_preview = ttk.Combobox(preview_row, state="readonly",
                                          width=18,
                                          values=list(PREVIEW_KINDS))
        self.combo_preview.set(list(PREVIEW_KINDS)[0])
        self.combo_preview.pack(side="left", fill="x", expand=True)
        ttk.Button(preview_row, text="试听", style="Ghost.TButton",
                   command=self._on_preview_alarm).pack(side="left", padx=(6, 0))
        ttk.Button(preview_row, text="停止", style="Ghost.TButton",
                   command=self._on_stop_preview).pack(side="left", padx=(4, 0))

        custom_row = tk.Frame(right, bg=theme.CARD_BG)
        custom_row.pack(fill="x", pady=(8, 0))
        self.custom_label = tk.Label(custom_row, text="", bg=theme.CARD_BG,
                                     fg=theme.TEXT_MUTED, font=theme.FONT_SMALL,
                                     anchor="w")
        self.custom_label.pack(fill="x")
        custom_btns = tk.Frame(right, bg=theme.CARD_BG)
        custom_btns.pack(fill="x", pady=(4, 0))
        ttk.Button(custom_btns, text="选择自定义铃声…", style="Ghost.TButton",
                   command=self._on_choose_alarm).pack(side="left")
        ttk.Button(custom_btns, text="恢复内置", style="Ghost.TButton",
                   command=self._on_clear_alarm).pack(side="left", padx=(6, 0))

        apply_btn = ttk.Button(right, text="应用设置", style="Accent.TButton",
                               command=self._on_apply_settings)
        apply_btn.pack(fill="x", pady=(12, 10))

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
        storage = self.context.storage
        self.var_focus.set(str(cfg["focus_min"]))
        self.var_short.set(str(cfg["short_break_min"]))
        self.var_long.set(str(cfg["long_break_min"]))
        self.var_interval.set(str(cfg["long_break_after"]))
        self.var_auto.set(cfg["auto_start"])
        self.var_popup.set(settings_mod.get_bool(storage, "reminder_popup"))
        self.var_sound.set(settings_mod.get_bool(storage, "reminder_sound"))
        self.var_seconds.set(str(settings_mod.get_int(storage,
                                                     "reminder_seconds")))
        self.var_custom.set(storage.get("custom_alarm_path", "") or "")
        self._update_custom_label()
        self.settings_hint.config(text="")

    def _update_custom_label(self):
        path = self.var_custom.get().strip()
        if not path:
            self.custom_label.config(text="铃声：内置三阶段音效", fg=theme.TEXT_MUTED)
        elif custom_alarm_available(path):
            self.custom_label.config(text="铃声：自定义 %s"
                                          % os.path.basename(path),
                                     fg=theme.GREEN)
        else:
            self.custom_label.config(text="铃声：自定义文件不可用，将回退内置音效",
                                     fg=theme.RED)

    def _on_choose_alarm(self):
        path = filedialog.askopenfilename(
            title="选择铃声文件（WAV）",
            filetypes=[("WAV 音频", "*.wav"), ("所有文件", "*.*")],
            parent=self.winfo_toplevel())
        if not path:
            return
        self.var_custom.set(path)
        self._update_custom_label()

    def _on_clear_alarm(self):
        self.var_custom.set("")
        self._update_custom_label()

    def _on_preview_alarm(self):
        kind = PREVIEW_KINDS.get(self.combo_preview.get(), PHASE_FOCUS)
        custom = self.var_custom.get().strip() or None
        path = play_preview(self.winfo_toplevel(), kind, custom, seconds=15)
        self.settings_hint.config(text="正在试听：%s（15 秒后自动停止）"
                                       % os.path.basename(path), fg=theme.BLUE)

    def _on_stop_preview(self):
        stop_active_alarm()
        self.settings_hint.config(text="已停止试听", fg=theme.TEXT_MUTED)

    def _on_apply_settings(self):
        def num(var, default, lo=1, hi=999):
            try:
                return max(lo, min(hi, int(var.get())))
            except (ValueError, tk.TclError):
                return default

        focus = num(self.var_focus, 25, 1, 180)
        short = num(self.var_short, 5, 1, 60)
        long_ = num(self.var_long, 15, 1, 120)
        interval = num(self.var_interval, 4, 1, 12)
        seconds = num(self.var_seconds, 20, 5, 120)
        self.context.apply_engine_settings(
            focus, short, long_, min(interval, 12), bool(self.var_auto.get()))
        storage = self.context.storage
        popup = bool(self.var_popup.get())
        sound = bool(self.var_sound.get())
        settings_mod.set_bool(storage, "reminder_popup", popup)
        settings_mod.set_bool(storage, "reminder_sound", sound)
        settings_mod.set_int(storage, "reminder_seconds", seconds)
        settings_mod.set_bool(storage, "reminder_enabled", popup or sound)
        storage.set("custom_alarm_path", self.var_custom.get().strip())
        self._load_settings()
        if self.engine.phase is not None and self.engine.remaining > 0:
            self.settings_hint.config(
                text="设置已保存；当前阶段仍按原时长进行，新时长将在下一阶段生效",
                fg=theme.YELLOW)
        else:
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
        """阶段结束时：按设置弹出/播放提醒，不同阶段铃声不同。

        支持三种模式：弹窗+响铃 / 只弹窗 / 只响铃，以及自定义铃声文件与
        自定义自动停铃时长。
        """
        storage = self.context.storage
        if not settings_mod.get_bool(storage, "reminder_enabled"):
            return
        popup_on = settings_mod.get_bool(storage, "reminder_popup")
        sound_on = settings_mod.get_bool(storage, "reminder_sound")
        if not popup_on and not sound_on:
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
        seconds = settings_mod.get_int(storage, "reminder_seconds")
        custom = storage.get("custom_alarm_path", "") or None
        show_phase_reminder(
            self.winfo_toplevel(), title, message, icon,
            sound=sound, play_sound=sound_on, show_popup=popup_on,
            auto_close_ms=max(5, seconds) * 1000, custom_alarm=custom)

    # ================================================================ 定时刷新
    def _poll(self):
        """按真实时间刷新引擎与界面（每 250ms 一次，不会因界面卡顿而漂移）。"""
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            self.engine.refresh()
            self._refresh_ui()
        except tk.TclError:
            pass                     # 窗口销毁竞态，属预期情况
        except Exception:
            log_exception("专注页刷新失败")
        self._after_id = self.after(250, self._poll)

    def destroy(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        # 注销引擎监听，避免主题切换重建页面后残留回调
        if getattr(self, "_engine_off", None) is not None:
            try:
                self._engine_off()
            except Exception:
                pass
            self._engine_off = None
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
            # 进度基准取「进入阶段时的快照」，避免运行中改设置导致进度为负
            total = engine.progress_total()
            done = max(0, min(total, total - engine.remaining))
            self.progress.config(maximum=max(1, total), value=done)
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
