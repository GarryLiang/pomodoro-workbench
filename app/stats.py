"""统计服务：汇总番茄钟 / 待办 / 习惯三块数据供统计页展示。"""

from collections import defaultdict
from datetime import date, datetime, timedelta

from .pomodoro import PHASE_FOCUS
from .habit import HabitManager, HEATMAP_DAYS, heatmap_range


def _today_str():
    return date.today().isoformat()


class StatsService:
    """从数据库中汇总各类指标。"""

    def __init__(self, storage):
        self.storage = storage
        self.habits = HabitManager(storage)

    # ------------------------------------------------------------ 番茄钟
    def focus_summary(self):
        """今日 / 累计番茄数量与专注分钟数。"""
        today = _today_str()
        row_today = self.storage.query_one(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(duration_min), 0) AS mins "
            "FROM sessions WHERE kind = ? AND started_at LIKE ?",
            (PHASE_FOCUS, today + "%"),
        )
        row_total = self.storage.query_one(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(duration_min), 0) AS mins "
            "FROM sessions WHERE kind = ?",
            (PHASE_FOCUS,),
        )
        return {
            "today_count": int(row_today["cnt"] or 0),
            "today_minutes": int(row_today["mins"] or 0),
            "total_count": int(row_total["cnt"] or 0),
            "total_minutes": int(row_total["mins"] or 0),
        }

    def last_days_focus(self, days=7):
        """返回最近 days 天的专注数据，含今天。

        返回 [ {date, label, minutes, count}, ... ]，按时间升序。
        """
        end = date.today()
        start = end - timedelta(days=days - 1)
        rows = self.storage.query(
            "SELECT started_at, duration_min FROM sessions "
            "WHERE kind = ? AND started_at >= ?",
            (PHASE_FOCUS, start.isoformat()),
        )
        buckets = defaultdict(lambda: {"minutes": 0, "count": 0})
        start_key, end_key = start.isoformat(), end.isoformat()
        for row in rows:
            day = row["started_at"][:10]
            if start_key <= day <= end_key:
                buckets[day]["minutes"] += int(row["duration_min"] or 0)
                buckets[day]["count"] += 1
        result = []
        for i in range(days):
            day = start + timedelta(days=i)
            key = day.isoformat()
            item = buckets.get(key, {"minutes": 0, "count": 0})
            result.append({
                "date": key,
                "label": "今天" if i == days - 1 else day.strftime("%m-%d"),
                "minutes": item["minutes"],
                "count": item["count"],
            })
        return result

    # ------------------------------------------------------------ 待办
    def todo_summary(self):
        row = self.storage.query_one(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done "
            "FROM todos"
        )
        total = int(row["total"] or 0)
        done = int(row["done"] or 0)
        return {"total": total, "done": done,
                "rate": (done / total * 100) if total else 0.0}

    # ------------------------------------------------------------ 习惯
    def habit_summary(self):
        return self.habits.summary()

    def habit_heatmap(self, habit_id):
        """返回某习惯在热力图时间范围内的 date -> count 字典。"""
        start, end = heatmap_range()
        habit = self.habits.load(habit_id)
        if habit is None:
            return {}
        return {
            d: habit.checked_dates[d]
            for d in habit.checked_dates if start <= d <= end
        }

    # ------------------------------------------------------------ 汇总面板
    def overall(self):
        return {
            "focus": self.focus_summary(),
            "last_7": self.last_days_focus(7),
            "todo": self.todo_summary(),
            "habit": self.habit_summary(),
        }
