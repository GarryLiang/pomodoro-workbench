"""SQLite 持久化层。

负责创建数据库文件、建表以及提供最基础的读写封装。
数据库默认存放在用户主目录下的 .pomodoro_workbench 文件夹中，
可通过环境变量 PWB_DB 覆盖数据库路径（便于测试与移植）。
"""

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get(
    "PWB_DB",
    str(Path.home() / ".pomodoro_workbench" / "data.db"),
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS todos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    note        TEXT NOT NULL DEFAULT '',
    priority    INTEGER NOT NULL DEFAULT 1,
    due         TEXT NOT NULL DEFAULT '',
    done        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    finished_at TEXT NOT NULL DEFAULT '',
    pomodoros   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id      INTEGER,
    kind         TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    started_at   TEXT NOT NULL,
    ended_at     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS habits (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    color      TEXT NOT NULL DEFAULT '#4ea1ff',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS habit_logs (
    habit_id INTEGER NOT NULL,
    date     TEXT NOT NULL,
    count    INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (habit_id, date)
);
"""


class Storage:
    """SQLite 数据库的轻量封装，提供 execute / query / get / set 等基本方法。"""

    def __init__(self, db_path=None):
        self.path = db_path or DEFAULT_DB_PATH
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def execute(self, sql, params=()):
        """执行写入类 SQL，返回自增主键 id（无自增时返回 0）。"""
        cursor = self.conn.execute(sql, params)
        self.conn.commit()
        return cursor.lastrowid

    def query(self, sql, params=()):
        """执行查询 SQL，返回 sqlite3.Row 列表。"""
        return self.conn.execute(sql, params).fetchall()

    def query_one(self, sql, params=()):
        """执行查询 SQL，返回单行或 None。"""
        return self.conn.execute(sql, params).fetchone()

    def get(self, key, default=None):
        """读取一条设置项。"""
        row = self.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def set(self, key, value):
        """写入一条设置项（存在则覆盖）。"""
        self.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    def close(self):
        """关闭数据库连接。"""
        self.conn.close()
