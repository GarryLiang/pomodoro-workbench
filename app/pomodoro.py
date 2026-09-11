"""番茄钟核心引擎。

与界面完全无关的纯逻辑状态机，可以被任何程序 import 后独立使用：
    1. 管理 专注 / 短休息 / 长休息 三种阶段
    2. 支持 开始 / 暂停 / 继续 / 重置 / 跳过
    3. 通过事件回调把状态变化（tick、阶段完成等）通知给调用方

计时方式：
    - 界面运行时调用 refresh()，引擎按**单调时钟**计算真实剩余时间，
      因此界面卡顿、弹窗阻塞或系统延迟都不会让计时变慢；
    - 也保留 tick() 用于手动/无界面场景（例如测试或第三方程序自己驱动）。

示例（命令行中使用）：
    engine = PomodoroEngine(focus_min=25, auto_start=True)
    engine.on(lambda event, data: print(event, data))
    engine.start()
    for _ in range(engine.remaining):
        engine.tick()
"""

import math
import time

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
EV_TICK = "tick"                  # 时间推进
EV_PHASE_CHANGED = "phase_changed"  # 进入新阶段
EV_PHASE_COMPLETE = "phase_complete"  # 当前阶段自然结束
EV_PHASE_SKIPPED = "phase_skipped"    # 用户跳过当前阶段
EV_RESET = "reset"                # 重置当前阶段计时

# 时钟取整误差容限（秒）：避免浮点舍入让剩余时间多出 1 秒
CLOCK_EPSILON = 1e-6


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
        self.phase = None       # None 表示空闲（尚未开始任何阶段）
        self.remaining = 0      # 当前阶段剩余秒数（整数，供界面显示）
        self.phase_total = 0    # 进入阶段时的总秒数（进度条基准，运行中不随设置变化）
        self.running = False    # 是否正在倒计时
        # 单调时钟截止点：运行中由它推算真实剩余时间
        self._deadline = None
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
        """返回指定阶段在**当前设置**下的完整时长（秒）。"""
        if phase == PHASE_FOCUS:
            return self.focus_seconds
        if phase == PHASE_SHORT:
            return self.short_seconds
        if phase == PHASE_LONG:
            return self.long_seconds
        raise ValueError("未知阶段: %s" % phase)

    def progress_total(self):
        """当前阶段的进度基准秒数（进入阶段时快照，运行中不受设置变化影响）。"""
        if self.phase is None:
            return 0
        return self.phase_total or self.duration_for(self.phase)

    def set_durations(self, focus_min, short_break_min,
                      long_break_min, long_break_after):
        """动态更新各阶段时长（分钟）。

        正在进行的阶段保持原有节奏（避免进度条出现负值与显示错乱），
        新时长从下一个阶段开始生效；空闲状态则立即按新时长准备。
        """
        self.focus_seconds = max(1, int(focus_min)) * 60
        self.short_seconds = max(1, int(short_break_min)) * 60
        self.long_seconds = max(1, int(long_break_min)) * 60
        self.long_break_after = max(1, int(long_break_after))
        if self.phase is not None and self.remaining <= 0:
            self.phase_total = self.duration_for(self.phase)
            self.remaining = self.phase_total

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
            self.phase_total = self.duration_for(self.phase)
            self.remaining = self.phase_total
        self.running = True
        self._deadline = time.monotonic() + self.remaining
        self._emit(EV_STARTED)

    def pause(self):
        """暂停倒计时（剩余时间按真实经过时间结算）。"""
        if self.phase is None or not self.running:
            return
        self.remaining = self._remaining_from_clock()
        self.running = False
        self._deadline = None
        self._emit(EV_PAUSED)

    def toggle(self):
        """开始 / 暂停 切换。"""
        if self.running:
            self.pause()
        else:
            self.start()

    def reset(self):
        """重置当前阶段到完整时长（按**当前设置**）并停止计时。"""
        if self.phase is None:
            return
        self.phase_total = self.duration_for(self.phase)
        self.remaining = self.phase_total
        self.running = False
        self._deadline = None
        self._emit(EV_RESET)

    def skip(self):
        """跳过当前阶段：不记录本次专注，直接进入下一阶段（暂停等待）。"""
        if self.phase is None:
            return
        current = self.phase
        self.running = False
        self._deadline = None
        self._emit(EV_PHASE_SKIPPED, {"duration": self.progress_total()})
        if current == PHASE_FOCUS:
            next_phase = self._pick_break(skip=True)
        else:
            next_phase = PHASE_FOCUS
        self._enter(next_phase, running=False)

    def tick(self):
        """手动推进 1 秒（用于无界面场景或测试）。

        界面运行时应改用 refresh()：它按真实时间结算，不会因界面卡顿而漂移。
        """
        if not self.running or self.phase is None:
            return
        self.remaining = max(0, self.remaining - 1)
        if self.remaining <= 0:
            self.running = False
            self._deadline = None
            self._emit(EV_TICK)
            self._complete_current()
        else:
            self._deadline = time.monotonic() + self.remaining
            self._emit(EV_TICK)

    def refresh(self):
        """按真实时间刷新剩余时间（界面定时器调用，可重复调用且幂等）。

        与 tick() 的区别：refresh() 依据单调时钟计算，界面卡顿、系统休眠唤醒或
        定时器延迟都不会导致计时变慢；多次重复调用也不会重复扣减时间。
        """
        if not self.running or self.phase is None:
            return
        new_remaining = self._remaining_from_clock()
        if new_remaining <= 0:
            self.remaining = 0
            self.running = False
            self._deadline = None
            self._emit(EV_TICK)
            self._complete_current()
            return
        if new_remaining != self.remaining:
            self.remaining = new_remaining
            self._emit(EV_TICK)

    # ------------------------------------------------------------- 内部实现
    def _remaining_from_clock(self):
        """按单调时钟计算剩余秒数（向上取整，避免显示提前跳秒）。

        注意：必须减去一个极小量再取整。因为 deadline = t1 + N，
        而 t2 与 t1 可能只差浮点舍入误差，直接 ceil((t1+N)-t1) 有概率得到
        N+1（例如 59.000000000000007 → 60），会让"刚扣减 1 秒"又变回原值。
        """
        if self._deadline is None:
            return max(0, int(self.remaining))
        left = self._deadline - time.monotonic() - CLOCK_EPSILON
        return max(0, int(math.ceil(left)))

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
        self._emit(EV_PHASE_COMPLETE, {"duration": self.progress_total()})
        if current == PHASE_FOCUS:
            next_phase = self._pick_break(skip=False)
        else:
            next_phase = PHASE_FOCUS
        self._enter(next_phase, running=self.auto_start)

    def _enter(self, phase, running):
        """装载新阶段（同时快照该阶段总时长，作为进度条基准）。"""
        self.phase = phase
        self.phase_total = self.duration_for(phase)
        self.remaining = self.phase_total
        self.running = running
        self._deadline = (time.monotonic() + self.remaining) if running else None
        self._emit(EV_PHASE_CHANGED)

    # ------------------------------------------------------------- 查询辅助
    def state_dict(self):
        """返回当前状态的普通 dict，便于界面展示或序列化。"""
        return {
            "phase": self.phase,
            "phase_label": PHASE_LABELS.get(self.phase, "空闲"),
            "remaining": self.remaining,
            "phase_total": self.progress_total(),
            "running": self.running,
            "focus_since_long": self._focus_since_long,
        }

    def format_remaining(self):
        """把剩余秒数格式化为 MM:SS。"""
        minutes, seconds = divmod(max(0, int(self.remaining)), 60)
        return "%02d:%02d" % (minutes, seconds)
