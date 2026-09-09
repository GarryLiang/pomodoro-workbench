"""番茄钟核心引擎。

与界面完全无关的纯逻辑状态机，可以被任何程序 import 后独立使用：
    1. 管理 专注 / 短休息 / 长休息 三种阶段
    2. 支持 开始 / 暂停 / 继续 / 重置 / 跳过
    3. 通过事件回调把状态变化（tick、阶段完成等）通知给调用方

示例（命令行中使用）：
    engine = PomodoroEngine(focus_min=25, auto_start=True)
    engine.on(lambda event, data: print(event, data))
    engine.start()
    for _ in range(engine.remaining):
        engine.tick()
"""

PHASE_FOCUS = "focus"
PHASE_SHORT = "short_break"
PHASE_LONG = "long_break"

PHASE_LABELS = {
    PHASE_FOCUS: "专注",
    PHASE_SHORT: "短休息",
    PHASE_LONG: "长休息",
}

# 按固定顺序排列的阶段，供界面展示使用
ALL_PHASES = (PHASE_FOCUS, PHASE_SHORT, PHASE_LONG)

# 事件名常量
EV_STARTED = "started"            # 开始 / 继续计时
EV_PAUSED = "paused"              # 暂停
EV_TICK = "tick"                  # 每秒推进
EV_PHASE_CHANGED = "phase_changed"  # 进入新阶段
EV_PHASE_COMPLETE = "phase_complete"  # 当前阶段自然结束
EV_PHASE_SKIPPED = "phase_skipped"    # 用户跳过当前阶段
EV_RESET = "reset"                # 重置当前阶段计时


class PomodoroEngine:
    """番茄钟状态机。"""

    def __init__(self, focus_min=25, short_break_min=5,
                 long_break_min=15, long_break_after=4, auto_start=True):
        # 各阶段时长（秒）
        self.focus_seconds = max(1, int(focus_min)) * 60
        self.short_seconds = max(1, int(short_break_min)) * 60
        self.long_seconds = max(1, int(long_break_min)) * 60
        # 每完成多少个专注后进入长休息
        self.long_break_after = max(1, int(long_break_after))
        # 阶段自然结束后是否自动进入下一阶段并开始计时
        self.auto_start = bool(auto_start)

        # 运行状态
        self.phase = None      # None 表示空闲（尚未开始任何阶段）
        self.remaining = 0     # 当前阶段剩余秒数
        self.running = False   # 是否正在倒计时
        # 自上次长休息结束以来已完成的专注数量（用于判定何时进入长休息）
        self._focus_since_long = 0
        self._listeners = []

    # ------------------------------------------------------------------ 事件
    def on(self, callback):
        """注册事件回调 callback(event: str, data: dict)。返回注销函数。"""
        self._listeners.append(callback)

        def off():
            if callback in self._listeners:
                self._listeners.remove(callback)

        return off

    def _emit(self, event, data=None):
        data = dict(data or {})
        data.setdefault("phase", self.phase)
        data.setdefault("remaining", self.remaining)
        data.setdefault("running", self.running)
        for listener in list(self._listeners):
            listener(event, data)

    # ------------------------------------------------------------- 时长换算
    def duration_for(self, phase):
        """返回指定阶段的完整时长（秒）。"""
        if phase == PHASE_FOCUS:
            return self.focus_seconds
        if phase == PHASE_SHORT:
            return self.short_seconds
        if phase == PHASE_LONG:
            return self.long_seconds
        raise ValueError("未知阶段: %s" % phase)

    def set_durations(self, focus_min, short_break_min,
                      long_break_min, long_break_after):
        """动态更新各阶段时长（分钟）。"""
        self.focus_seconds = max(1, int(focus_min)) * 60
        self.short_seconds = max(1, int(short_break_min)) * 60
        self.long_seconds = max(1, int(long_break_min)) * 60
        self.long_break_after = max(1, int(long_break_after))
        # 若当前正处于未运行的阶段，则同步刷新剩余时间
        if self.phase and not self.running and self.remaining <= 0:
            self.remaining = self.duration_for(self.phase)

    # ------------------------------------------------------------- 状态控制
    def start(self, phase=None):
        """开始倒计时。

        首次调用默认进入专注阶段；若当前已有阶段则从当前阶段继续，
        仅当剩余时间为 0 时才重新装载完整时长。
        """
        if self.running:
            return
        if self.phase is None:
            self.phase = phase or PHASE_FOCUS
        if self.remaining <= 0:
            self.remaining = self.duration_for(self.phase)
        self.running = True
        self._emit(EV_STARTED)

    def pause(self):
        """暂停倒计时。"""
        if self.phase is None or not self.running:
            return
        self.running = False
        self._emit(EV_PAUSED)

    def toggle(self):
        """开始 / 暂停 切换。"""
        if self.running:
            self.pause()
        else:
            self.start()

    def reset(self):
        """重置当前阶段到完整时长并停止计时。"""
        if self.phase is None:
            return
        self.remaining = self.duration_for(self.phase)
        self.running = False
        self._emit(EV_RESET)

    def skip(self):
        """跳过当前阶段：不记录本次专注，直接进入下一阶段（暂停等待）。"""
        if self.phase is None:
            return
        current = self.phase
        self.running = False
        self._emit(EV_PHASE_SKIPPED, {"duration": self.duration_for(current)})
        if current == PHASE_FOCUS:
            next_phase = self._pick_break(skip=True)
        else:
            next_phase = PHASE_FOCUS
        self._enter(next_phase, running=False)

    def tick(self):
        """推进 1 秒。由界面定时器每秒调用一次。"""
        if not self.running or self.phase is None:
            return
        self.remaining -= 1
        if self.remaining <= 0:
            self.remaining = 0
            self.running = False
            self._emit(EV_TICK)
            self._complete_current()
        else:
            self._emit(EV_TICK)

    # ------------------------------------------------------------- 内部实现
    def _pick_break(self, skip=False):
        """决定接下来进入短休息还是长休息。

        skip=True 表示用户在专注中途跳过，不消耗完成计数；
        反之专注自然完成时计数 +1。
        """
        if not skip:
            self._focus_since_long += 1
        if self._focus_since_long >= self.long_break_after:
            self._focus_since_long = 0
            return PHASE_LONG
        return PHASE_SHORT

    def _complete_current(self):
        """当前阶段自然结束：发事件并按规则进入下一阶段。"""
        current = self.phase
        self._emit(EV_PHASE_COMPLETE, {"duration": self.duration_for(current)})
        if current == PHASE_FOCUS:
            next_phase = self._pick_break(skip=False)
        else:
            next_phase = PHASE_FOCUS
        self._enter(next_phase, running=self.auto_start)

    def _enter(self, phase, running):
        """装载新阶段。"""
        self.phase = phase
        self.remaining = self.duration_for(phase)
        self.running = running
        self._emit(EV_PHASE_CHANGED)

    # ------------------------------------------------------------- 查询辅助
    def state_dict(self):
        """返回当前状态的普通 dict，便于界面展示或序列化。"""
        return {
            "phase": self.phase,
            "phase_label": PHASE_LABELS.get(self.phase, "空闲"),
            "remaining": self.remaining,
            "running": self.running,
            "focus_since_long": self._focus_since_long,
        }

    def format_remaining(self):
        """把剩余秒数格式化为 MM:SS。"""
        minutes, seconds = divmod(max(0, self.remaining), 60)
        return "%02d:%02d" % (minutes, seconds)
