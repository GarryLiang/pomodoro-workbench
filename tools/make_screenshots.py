"""开发者工具：自动生成 README 真实界面截图（不是应用本体的一部分）。

用法：
    1. pip install pillow          # 仅本机开发需要，应用本身仍零第三方依赖
    2. python tools/make_screenshots.py

流程：启动真实程序窗口 → 填充演示数据 → 依次切换到四个页面并截取窗口画面，
再额外截取一张"阶段结束提醒"弹窗。输出到 screenshots/*.png。
仅在 Windows 桌面环境可用。
"""

import ctypes
import os
import sys
import tempfile
import time
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import ImageGrab  # noqa: E402

from app.context import AppContext  # noqa: E402
from app.todo import PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW  # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "screenshots")


def _set_dpi_aware():
    """让 Tk 与截屏使用同一套物理像素坐标（避免高分屏错位）。"""
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _seed(context):
    """写入一份"看起来用了两三周"的演示数据。"""
    today = date.today()

    # ---- 待办：6 条，含已完成/高优先级/逾期，番茄数不同 ----
    ctx = context
    tasks = [
        ("完成操作系统实验报告", "第三章 进程调度", PRIORITY_HIGH,
         (today + timedelta(days=2)).isoformat(), False),
        ("背 50 个英语单词", "四级核心词汇", PRIORITY_MEDIUM,
         today.isoformat(), False),
        ("整理机器学习笔记", "KNN / 决策树", PRIORITY_MEDIUM,
         (today + timedelta(days=5)).isoformat(), False),
        ("跑步 3 公里", "", PRIORITY_LOW, "", False),
        ("提交软工课程设计初稿", "", PRIORITY_HIGH,
         (today - timedelta(days=1)).isoformat(), False),
        ("阅读《代码整洁之道》第 4 章", "", PRIORITY_LOW, "", True),
    ]
    ids = []
    for title, note, prio, due, done in tasks:
        tid = ctx.todo.add(title, note=note, priority=prio, due=due)
        ids.append(tid)
        if done:
            ctx.todo.toggle_done(tid)
    # 给部分待办累计番茄
    ctx.todo.increment_pomodoro(ids[0])
    ctx.todo.increment_pomodoro(ids[0])
    ctx.todo.increment_pomodoro(ids[0])
    ctx.todo.increment_pomodoro(ids[1])
    ctx.todo.increment_pomodoro(ids[2])

    # ---- 番茄会话：近 7 天（今天少计，避免截图数字突兀）----
    day_minutes = [50, 100, 75, 0, 125, 75, 25]  # 从 6 天前到今天
    for offset, minutes in enumerate(day_minutes):
        day = today - timedelta(days=(len(day_minutes) - 1 - offset))
        for _ in range(0, minutes, 25):
            started = datetime(day.year, day.month, day.day, 10, 0, 0)
            context.storage.execute(
                "INSERT INTO sessions (task_id, kind, duration_min, "
                "started_at, ended_at) VALUES (?, 'focus', 25, ?, ?)",
                (ids[offset % 3], started.strftime("%Y-%m-%d %H:%M:%S"),
                 (started + timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M:%S")))

    # ---- 习惯：两个，70 天打卡记录（留少量断档，热力图更真实）----
    habit_a = context.habits.add_habit("早睡", color="#4ea1ff")
    habit_b = context.habits.add_habit("每日阅读 30 分钟", color="#3fb27f")
    for back in range(69, -1, -1):
        day = today - timedelta(days=back)
        # 早睡：周中全勤，偶尔周末破功
        if back % 11 not in (3, 8):
            context.habits.check_in(habit_a, day.isoformat())
        # 阅读：近期全勤，形成当前连续
        if back < 12 or back % 7 != 2:
            context.habits.check_in(habit_b, day.isoformat())
    context.habits.check_in(habit_a, today.isoformat())
    context.habits.check_in(habit_b, today.isoformat())


def _grab(widget, filename):
    widget.update_idletasks()
    widget.update()
    time.sleep(0.35)
    top = widget.winfo_toplevel()
    top.attributes("-topmost", True)
    widget.update()
    time.sleep(0.25)
    x = top.winfo_rootx()
    y = top.winfo_rooty()
    w = top.winfo_width()
    h = top.winfo_height()
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    os.makedirs(OUT_DIR, exist_ok=True)
    img.save(os.path.join(OUT_DIR, filename))
    top.attributes("-topmost", False)
    print("已截图:", filename, img.size)


def main():
    _set_dpi_aware()
    db_dir = os.path.join(tempfile.gettempdir(), "pwb_screenshots")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "demo.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    from ui.main_window import MainWindow
    from ui.reminder import show_phase_reminder, stop_active_alarm

    context = AppContext(db_path)
    _seed(context)

    win = MainWindow(context)
    win.geometry("1080x720+150+40")
    win.update()

    for key, filename in (
        ("pomodoro", "01-番茄专注.png"),
        ("todo", "02-待办清单.png"),
        ("habit", "03-习惯打卡.png"),
        ("stats", "04-数据统计.png"),
    ):
        win.switch(key)
        _grab(win, filename)

    # 阶段结束提醒弹窗（静音）
    win.switch("pomodoro")
    win.update()
    popup = show_phase_reminder(win, "专注结束 🎉",
                                "干得漂亮！起来活动一下、喝口水，好好休息吧。",
                                icon="🎉", sound="focus", play_sound=False)
    win.update()
    time.sleep(0.3)
    _grab(popup, "05-阶段结束提醒.png")
    stop_active_alarm()

    win.destroy()
    context.close()
    print("全部截图完成 ->", OUT_DIR)


if __name__ == "__main__":
    main()
