"""待办清单数据模型与管理逻辑（不依赖界面）。"""

from datetime import datetime

# 优先级常量：数字越大越紧急
PRIORITY_LOW = 0
PRIORITY_MEDIUM = 1
PRIORITY_HIGH = 2

PRIORITY_NAMES = {
    PRIORITY_LOW: "低",
    PRIORITY_MEDIUM: "中",
    PRIORITY_HIGH: "高",
}

# 合法筛选状态
FILTER_ALL = "all"
FILTER_ACTIVE = "active"
FILTER_DONE = "done"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Todo:
    """一条待办记录。字段与数据库表 todos 一一对应。"""

    __slots__ = ("id", "title", "note", "priority", "due",
                 "done", "created_at", "finished_at", "pomodoros")

    def __init__(self, row):
        self.id = row["id"]
        self.title = row["title"]
        self.note = row["note"]
        self.priority = int(row["priority"])
        self.due = row["due"]
        self.done = bool(row["done"])
        self.created_at = row["created_at"]
        self.finished_at = row["finished_at"]
        self.pomodoros = int(row["pomodoros"])

    @property
    def priority_name(self):
        return PRIORITY_NAMES.get(self.priority, "中")

    @property
    def is_overdue(self):
        """是否有截止日期且已过期（未完成状态下才有意义）。"""
        if not self.due or self.done:
            return False
        try:
            return datetime.now().date() > datetime.strptime(self.due, "%Y-%m-%d").date()
        except ValueError:
            return False

    def as_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "note": self.note,
            "priority": self.priority,
            "priority_name": self.priority_name,
            "due": self.due,
            "done": self.done,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "pomodoros": self.pomodoros,
        }


class TodoManager:
    """基于 Storage 的待办增删改查。"""

    def __init__(self, storage):
        self.storage = storage

    def _row_to_todo(self, row):
        return Todo(row) if row else None

    def add(self, title, note="", priority=PRIORITY_MEDIUM, due=""):
        """新增一条待办，返回新记录 id。"""
        title = (title or "").strip()
        if not title:
            raise ValueError("待办内容不能为空")
        if priority not in PRIORITY_NAMES:
            raise ValueError("非法的优先级: %s" % priority)
        now = _now()
        return self.storage.execute(
            "INSERT INTO todos (title, note, priority, due, done, created_at, "
            "finished_at, pomodoros) VALUES (?, ?, ?, ?, 0, ?, '', 0)",
            (title, note.strip(), int(priority), due.strip(), now),
        )

    def update(self, todo_id, title=None, note=None, priority=None, due=None):
        """按需更新指定待办的非空字段。"""
        current = self.get(todo_id)
        if current is None:
            return None
        title = (title if title is not None else current.title).strip()
        if not title:
            raise ValueError("待办内容不能为空")
        self.storage.execute(
            "UPDATE todos SET title = ?, note = ?, priority = ?, due = ? WHERE id = ?",
            (
                title,
                note if note is not None else current.note,
                int(priority) if priority is not None else current.priority,
                due if due is not None else current.due,
                todo_id,
            ),
        )
        return self.get(todo_id)

    def get(self, todo_id):
        row = self.storage.query_one("SELECT * FROM todos WHERE id = ?", (todo_id,))
        return self._row_to_todo(row)

    def delete(self, todo_id):
        """删除待办并清理其在 sessions 中遗留的任务关联。"""
        self.storage.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self.storage.execute(
            "UPDATE sessions SET task_id = NULL WHERE task_id = ?", (todo_id,)
        )

    def toggle_done(self, todo_id):
        """切换完成状态，返回切换后的记录。"""
        current = self.get(todo_id)
        if current is None:
            return None
        done = 0 if current.done else 1
        finished = _now() if done else ""
        self.storage.execute(
            "UPDATE todos SET done = ?, finished_at = ? WHERE id = ?",
            (done, finished, todo_id),
        )
        return self.get(todo_id)

    def increment_pomodoro(self, todo_id):
        """为某个待办累计一个番茄数。"""
        if self.get(todo_id) is None:
            return
        self.storage.execute(
            "UPDATE todos SET pomodoros = pomodoros + 1 WHERE id = ?", (todo_id,)
        )

    def list_todos(self, status=FILTER_ALL, priority=None):
        """按状态 / 优先级过滤待办。

        status 取值 all / active / done；priority 为 None 时不过滤。
        """
        sql = "SELECT * FROM todos WHERE 1 = 1"
        params = []
        if status == FILTER_ACTIVE:
            sql += " AND done = 0"
        elif status == FILTER_DONE:
            sql += " AND done = 1"
        elif status != FILTER_ALL:
            raise ValueError("非法的状态筛选: %s" % status)
        if priority is not None:
            sql += " AND priority = ?"
            params.append(int(priority))
        sql += " ORDER BY done ASC, priority DESC, id DESC"
        return [Todo(row) for row in self.storage.query(sql, params)]

    def summary(self):
        """返回总数 / 进行中 / 已完成 / 完成率 汇总。"""
        row = self.storage.query_one(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN done = 0 THEN 1 ELSE 0 END) AS active, "
            "SUM(CASE WHEN done = 1 THEN 1 ELSE 0 END) AS done "
            "FROM todos"
        )
        total = int(row["total"] or 0)
        active = int(row["active"] or 0)
        done = int(row["done"] or 0)
        rate = (done / total * 100) if total else 0.0
        return {"total": total, "active": active, "done": done, "rate": rate}
