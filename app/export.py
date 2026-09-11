"""数据导出与一键备份（纯标准库实现）。

- 待办 / 习惯打卡 / 专注记录 导出为 CSV（UTF-8 带 BOM，Excel 直接打开不乱码）
- 数据库一键备份：把本地 SQLite 文件复制为用户指定的副本
"""

import csv
import io
import shutil
from datetime import datetime

from .pomodoro import PHASE_FOCUS

# CSV 表头与列宽说明（中文）
TODO_HEADERS = ["编号", "标题", "优先级", "截止日期", "状态", "番茄数",
                "备注", "创建时间", "完成时间"]
HABIT_HEADERS = ["编号", "习惯", "总打卡天数", "当前连续", "最长连续",
                 "本月完成率", "创建日期"]
SESSION_HEADERS = ["编号", "任务", "类型", "时长(分钟)", "开始时间", "结束时间"]


def _ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_csv(headers, rows):
    """把表头与数据行序列化为 CSV 文本（UTF-8 无 BOM，供再编码）。"""
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def todos_to_csv(todos):
    """待办列表 -> CSV 文本。todos 为 Todo 对象列表。"""
    rows = []
    for t in todos:
        rows.append([
            t.id, t.title, t.priority_name, t.due,
            "已完成" if t.done else "进行中", t.pomodoros,
            t.note, t.created_at,
            t.finished_at or "",
        ])
    return _write_csv(TODO_HEADERS, rows)


def habits_to_csv(habits, today=None):
    """习惯列表（Habit 对象，含统计字段）-> CSV 文本。"""
    rows = []
    for h in habits:
        rows.append([
            h.id, h.name, h.total_days(), h.current_streak(today),
            h.best_streak(), "%.0f%%" % (h.month_rate(today) * 100),
            h.created_at[:10],
        ])
    return _write_csv(HABIT_HEADERS, rows)


def sessions_to_csv(rows):
    """专注/休息记录行（sqlite3.Row）-> CSV 文本。"""
    out = []
    for r in rows:
        out.append([
            r["id"],
            r["task_title"] or "",
            r["kind"],
            r["duration_min"],
            r["started_at"],
            r["ended_at"],
        ])
    return _write_csv(SESSION_HEADERS, out)


def query_sessions(storage, kind=None):
    """查询 sessions 表并左连待办标题；kind=None 表示全部。"""
    sql = ("SELECT s.id, s.kind, s.duration_min, s.started_at, s.ended_at, "
           "t.title AS task_title FROM sessions s "
           "LEFT JOIN todos t ON t.id = s.task_id")
    params = []
    if kind:
        sql += " WHERE s.kind = ?"
        params.append(kind)
    sql += " ORDER BY s.id ASC"
    return storage.query(sql, params)


def export_focus_csv(storage):
    """专注记录（仅 focus）-> CSV 文本。"""
    return sessions_to_csv(query_sessions(storage, kind=PHASE_FOCUS))


def export_all_sessions_csv(storage):
    """全部阶段记录 -> CSV 文本。"""
    return sessions_to_csv(query_sessions(storage))


def save_text_file(path, text):
    """以 UTF-8-BOM 写出文本文件，返回写入字节数。Excel 打开不乱码。"""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        return fh.write(text)


def backup_database(storage, dest_path):
    """复制 SQLite 数据库文件到 dest_path，返回目标路径。"""
    shutil.copyfile(storage.path, dest_path)
    return dest_path
