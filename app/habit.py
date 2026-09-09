"""习惯打卡数据模型、管理与统计逻辑（不依赖界面）。"""

from datetime import date, datetime, timedelta

# 热力图默认展示的天数（15 周 x 7 天）
HEATMAP_DAYS = 105


class Habit:
    """一个习惯项，携带数据库行字段与汇总统计。"""

    __slots__ = ("id", "name", "color", "created_at", "checked_dates")

    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.color = row["color"]
        self.created_at = row["created_at"]
        # date -> count 的映射，由 HabitManager.load 填充
        self.checked_dates = {}

    def is_checked(self, day):
        return day in self.checked_dates

    def total_days(self):
        return len(self.checked_dates)

    def current_streak(self, today=None):
        """从今天（或昨天，若今天尚未打卡）往前数的连续打卡天数。"""
        today = today or date.today()
        start = today if today in self.checked_dates else today - timedelta(days=1)
        streak = 0
        day = start
        while day in self.checked_dates:
            streak += 1
            day -= timedelta(days=1)
        return streak

    def best_streak(self):
        """历史最长连续打卡天数。"""
        dates = sorted(self.checked_dates)
        if not dates:
            return 0
        best = 1
        current = 1
        for prev, cur in zip(dates, dates[1:]):
            if (cur - prev).days == 1:
                current += 1
                best = max(best, current)
            else:
                current = 1
        return best

    def month_rate(self, today=None):
        """本月完成率：本月已打卡天数 / 本月已过去天数。"""
        today = today or date.today()
        first_day = today.replace(day=1)
        elapsed = (today - first_day).days + 1
        done = sum(1 for d in self.checked_dates
                   if d.year == today.year and d.month == today.month
                   and d <= today)
        return done / elapsed if elapsed else 0.0


class HabitManager:
    """习惯的增删改查与打卡。"""

    def __init__(self, storage):
        self.storage = storage

    def _now(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_habit(self, name, color="#4ea1ff"):
        """新增习惯，返回新习惯 id。"""
        name = (name or "").strip()
        if not name:
            raise ValueError("习惯名称不能为空")
        return self.storage.execute(
            "INSERT INTO habits (name, color, created_at) VALUES (?, ?, ?)",
            (name, color, self._now()),
        )

    def delete_habit(self, habit_id):
        """删除习惯及其全部打卡记录。"""
        self.storage.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        self.storage.execute("DELETE FROM habit_logs WHERE habit_id = ?", (habit_id,))

    def check_in(self, habit_id, day=None):
        """为习惯在指定日期（默认今天）打卡一次，重复打卡返回 False。"""
        day = day or date.today().isoformat()
        exists = self.storage.query_one(
            "SELECT 1 FROM habit_logs WHERE habit_id = ? AND date = ?",
            (habit_id, day),
        )
        if exists is not None:
            return False
        self.storage.execute(
            "INSERT INTO habit_logs (habit_id, date, count) VALUES (?, ?, 1)",
            (habit_id, day),
        )
        return True

    def uncheck(self, habit_id, day=None):
        """取消指定日期的打卡。"""
        day = day or date.today().isoformat()
        self.storage.execute(
            "DELETE FROM habit_logs WHERE habit_id = ? AND date = ?",
            (habit_id, day),
        )

    def load(self, habit_id):
        """加载单个习惯并填充打卡日期映射。"""
        row = self.storage.query_one("SELECT * FROM habits WHERE id = ?", (habit_id,))
        if row is None:
            return None
        habit = Habit(row)
        for log in self.storage.query(
            "SELECT date, count FROM habit_logs WHERE habit_id = ?", (habit_id,)
        ):
            try:
                habit.checked_dates[date.fromisoformat(log["date"])] = int(log["count"])
            except ValueError:
                continue
        return habit

    def list_habits(self):
        """返回全部习惯（含统计信息）。"""
        return [self.load(row["id"]) for row in self.storage.query(
            "SELECT id FROM habits ORDER BY id ASC"
        )]

    def summary(self):
        """所有习惯的汇总：数量、全部习惯的平均本月完成率。"""
        habits = self.list_habits()
        if not habits:
            return {"count": 0, "avg_rate": 0.0, "best_streak": 0}
        today = date.today()
        rates = [h.month_rate(today) for h in habits]
        best = max(h.best_streak() for h in habits)
        return {
            "count": len(habits),
            "avg_rate": sum(rates) / len(rates),
            "best_streak": best,
        }


def heatmap_range(days=HEATMAP_DAYS, end=None):
    """返回热力图覆盖的日期范围 [(start, end), 共 days+1 天]，含当天。

    用于把打卡记录铺到 7 行 x N 列的日历格子上。
    """
    end = end or date.today()
    start = end - timedelta(days=days - 1)
    return start, end
