"""应用上下文：把存储层、设置、各业务模块与番茄钟引擎组装在一起。"""

from .storage import Storage
from . import settings as settings_mod
from .pomodoro import PomodoroEngine, PHASE_FOCUS
from .todo import TodoManager
from .habit import HabitManager
from .stats import StatsService
from datetime import datetime


class AppContext:
    """整个应用共享的依赖容器，UI 层只与它交互。"""

    def __init__(self, db_path=None):
        self.storage = Storage(db_path)
        settings_mod.ensure_defaults(self.storage)
        self.todo = TodoManager(self.storage)
        self.habits = HabitManager(self.storage)
        self.stats = StatsService(self.storage)
        self.engine = self.build_engine()

    # ------------------------------------------------------------ 设置读写
    def engine_settings(self):
        """从数据库读取番茄钟相关设置。"""
        s = self.storage
        return {
            "focus_min": settings_mod.get_int(s, "focus_min"),
            "short_break_min": settings_mod.get_int(s, "short_break_min"),
            "long_break_min": settings_mod.get_int(s, "long_break_min"),
            "long_break_after": settings_mod.get_int(s, "long_break_after"),
            "auto_start": settings_mod.get_bool(s, "auto_start"),
        }

    def build_engine(self):
        """根据当前设置构建番茄钟引擎。"""
        cfg = self.engine_settings()
        return PomodoroEngine(
            focus_min=cfg["focus_min"],
            short_break_min=cfg["short_break_min"],
            long_break_min=cfg["long_break_min"],
            long_break_after=cfg["long_break_after"],
            auto_start=cfg["auto_start"],
        )

    def apply_engine_settings(self, focus_min, short_break_min,
                              long_break_min, long_break_after, auto_start):
        """把新设置写入数据库并同步到运行中的引擎。"""
        s = self.storage
        settings_mod.set_int(s, "focus_min", focus_min)
        settings_mod.set_int(s, "short_break_min", short_break_min)
        settings_mod.set_int(s, "long_break_min", long_break_min)
        settings_mod.set_int(s, "long_break_after", long_break_after)
        settings_mod.set_bool(s, "auto_start", auto_start)
        self.engine.set_durations(focus_min, short_break_min,
                                  long_break_min, long_break_after)
        self.engine.auto_start = bool(auto_start)

    # ------------------------------------------------------------ 会话记录
    def record_focus_session(self, task_id=None, duration_min=None):
        """记录一次完成的专注会话，可选关联到某个待办。"""
        if duration_min is None:
            cfg = self.engine_settings()
            duration_min = int(cfg["focus_min"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_id = int(task_id) if task_id else None
        self.storage.execute(
            "INSERT INTO sessions (task_id, kind, duration_min, started_at, "
            "ended_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, PHASE_FOCUS, max(1, int(duration_min)), now, now),
        )
        if task_id is not None and self.todo.get(task_id) is not None:
            self.todo.increment_pomodoro(task_id)

    def close(self):
        self.storage.close()
