"""核心逻辑冒烟测试（无需 pytest，直接运行：python tests/run_smoke.py）。

覆盖：存储层、设置、待办管理、习惯打卡统计、番茄钟状态机、统计服务。
"""

import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import Storage
from app import settings as settings_mod
from app import export as export_mod
from app import themes as themes_mod
from app.alarm import alarm_path_for, synthesize_alarm
import wave as wave_mod
from app.context import AppContext
from app.todo import TodoManager, PRIORITY_HIGH
from app.habit import HabitManager, heatmap_range
from app.pomodoro import (
    PomodoroEngine, PHASE_FOCUS, PHASE_SHORT, PHASE_LONG,
    EV_PHASE_COMPLETE, EV_PHASE_CHANGED,
)

PASS = 0


def check(name, condition):
    global PASS
    if not condition:
        raise AssertionError("失败: %s" % name)
    PASS += 1
    print("  [通过] %s" % name)


def test_storage_and_settings():
    print("[1] 存储与设置")
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        st = Storage(db)
        settings_mod.ensure_defaults(st)
        check("默认设置存在", st.get("focus_min") == "25")
        st.set("focus_min", "30")
        check("写入并读回", st.get("focus_min") == "30")
        check("get_int 生效", settings_mod.get_int(st, "focus_min") == 30)
        check("提醒默认开启",
              settings_mod.get_bool(st, "reminder_enabled") is True)
        settings_mod.set_bool(st, "reminder_enabled", False)
        check("提醒可关闭",
              settings_mod.get_bool(st, "reminder_enabled") is False)
        st.close()


def test_alarm():
    print("[6] 多阶段闹铃合成")
    import hashlib
    with tempfile.TemporaryDirectory() as tmp:
        fingerprints = {}
        for kind in ("focus", "short_break", "long_break"):
            path = synthesize_alarm(kind, os.path.join(tmp, kind + ".wav"))
            check("[%s] 生成 WAV 文件" % kind, os.path.exists(path))
            with wave_mod.open(path, "rb") as wf:
                check("[%s] 单声道 16bit 22050Hz" % kind,
                      wf.getnchannels() == 1 and wf.getsampwidth() == 2
                      and wf.getframerate() == 22050)
                frames = wf.getnframes()
                check("[%s] 时长 1 秒以上" % kind, frames / 22050.0 > 1.0)
            with open(path, "rb") as fh:
                data = fh.read()
            check("[%s] 含有非静音数据" % kind, any(b != 0 for b in data[100:]))
            fingerprints[kind] = hashlib.md5(data).hexdigest()
        check("三种铃声互不相同", len(set(fingerprints.values())) == 3)
        try:
            synthesize_alarm("unknown_kind")
            check("非法类型被拒绝", False)
        except ValueError:
            check("非法类型被拒绝", True)


def test_todo():
    print("[2] 待办管理")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = AppContext(os.path.join(tmp, "t.db"))
        try:
            m = ctx.todo
            tid = m.add("完成实验报告", note="操作系统课", priority=PRIORITY_HIGH,
                        due="2099-01-01")
            check("新增待办", tid > 0)
            m.add("背单词", priority=0)
            check("列表数量", len(m.list_todos()) == 2)
            check("按状态筛选", len(m.list_todos(status="active")) == 2)
            todo = m.toggle_done(tid)
            check("切换完成", todo.done is True)
            check("已完成筛选", len(m.list_todos(status="done")) == 1)
            m.increment_pomodoro(tid)
            check("番茄数累计", m.get(tid).pomodoros == 1)
            s = m.summary()
            check("完成率汇总", s["done"] == 1 and s["total"] == 2)
            m.update(tid, title="新标题")
            check("编辑标题", m.get(tid).title == "新标题")
            m.delete(tid)
            check("删除生效", len(m.list_todos()) == 1)
        finally:
            ctx.close()


def test_habit():
    print("[3] 习惯打卡与统计")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = AppContext(os.path.join(tmp, "t.db"))
        try:
            m = ctx.habits
            hid = m.add_habit("早睡")
            check("新增习惯", hid > 0)
            today = date.today()
            # 连续打卡 3 天：今天、昨天、前天
            for i in range(3):
                day = today - timedelta(days=i)
                check("打卡第 %d 天" % (i + 1),
                      m.check_in(hid, day.isoformat()))
            # 重复打卡不生效
            check("重复打卡被忽略", m.check_in(hid, today.isoformat()) is False)
            habit = m.load(hid)
            check("总打卡 3 天", habit.total_days() == 3)
            check("当前连续 3 天", habit.current_streak(today) == 3)
            check("最长连续 3 天", habit.best_streak() == 3)
            check("今日已打卡", habit.is_checked(today))
            m.uncheck(hid, today.isoformat())
            habit = m.load(hid)
            check("取消后连续按昨日计 2 天", habit.current_streak(today) == 2)
            start, end = heatmap_range()
            check("热力图区间含今天", start <= today <= end)
            check("热力图共 %d 天" % ((end - start).days + 1),
                  (end - start).days + 1 == 105)
            m.delete_habit(hid)
            check("删除习惯", m.load(hid) is None)
        finally:
            ctx.close()


def test_engine():
    print("[4] 番茄钟状态机")
    events = []

    def on_event(event, data):
        events.append(event)

    e = PomodoroEngine(focus_min=1, short_break_min=1, long_break_min=1,
                       long_break_after=4, auto_start=False)
    e.on(on_event)
    check("初始空闲", e.phase is None)
    e.start()
    check("开始进入专注", e.phase == PHASE_FOCUS)
    check("运行中", e.running is True)
    check("剩余 60 秒", e.remaining == 60)
    e.tick()
    check("tick 推进", e.remaining == 59)
    e.pause()
    check("暂停生效", e.running is False)
    e.tick()
    check("暂停时不推进", e.remaining == 59)
    e.start()
    for _ in range(59):
        e.tick()
    check("专注完成进入短休息", e.phase == PHASE_SHORT)
    check("自动关闭时不运行", e.running is False)
    check("触发完成事件", EV_PHASE_COMPLETE in events)
    check("触发阶段切换", EV_PHASE_CHANGED in events)

    # 跳过专注不累计循环计数
    e2 = PomodoroEngine(focus_min=1, long_break_after=2, auto_start=False)
    e2.start()
    e2.skip()
    check("跳过进入休息", e2.phase == PHASE_SHORT)
    # 完整完成两次专注 -> 第二次后进入长休息
    e3 = PomodoroEngine(focus_min=1, short_break_min=1, long_break_min=1,
                        long_break_after=2, auto_start=False)
    e3.start()  # 专注 1
    for _ in range(60):
        e3.tick()
    check("第一次完成->短休", e3.phase == PHASE_SHORT)
    e3.start()  # 短休
    for _ in range(60):
        e3.tick()
    check("短休完成->专注", e3.phase == PHASE_FOCUS)
    e3.start()  # 专注 2
    for _ in range(60):
        e3.tick()
    check("第二次完成->长休", e3.phase == PHASE_LONG)

    # 格式
    e4 = PomodoroEngine(focus_min=1, short_break_min=1, long_break_min=1)
    e4.start()
    check("时间格式", e4.format_remaining() == "01:00")


def test_stats_and_context():
    print("[5] 统计服务与上下文联动")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = AppContext(os.path.join(tmp, "t.db"))
        try:
            ctx.record_focus_session(duration_min=25)
            ctx.record_focus_session(duration_min=25)
            s = ctx.stats.overall()
            check("今日 2 个番茄", s["focus"]["today_count"] == 2)
            check("今日 50 分钟", s["focus"]["today_minutes"] == 50)
            check("近7天含今日数据",
                  s["last_7"][-1]["count"] == 2)
            check("待办汇总存在", "todo" in s and "habit" in s)
            # 关联待办时累计番茄数
            tid = ctx.todo.add("写方案")
            ctx.record_focus_session(task_id=tid, duration_min=25)
            check("待办番茄累计", ctx.todo.get(tid).pomodoros == 1)
        finally:
            ctx.close()


def test_export():
    print("[7] 数据导出与备份")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = AppContext(os.path.join(tmp, "t.db"))
        try:
            tid = ctx.todo.add("导出一号待办", note="备注A", priority=1)
            ctx.todo.add("完成事项", priority=0)
            ctx.todo.toggle_done(tid)
            ctx.todo.increment_pomodoro(tid)
            hid = ctx.habits.add_habit("喝水")
            ctx.habits.check_in(hid)

            todo_csv = export_mod.todos_to_csv(ctx.todo.list_todos())
            check("待办 CSV 含表头", "标题" in todo_csv and "优先级" in todo_csv)
            check("待办 CSV 含数据", "导出一号待办" in todo_csv
                  and "已完成" in todo_csv)

            habit_csv = export_mod.habits_to_csv(ctx.habits.list_habits())
            check("习惯 CSV 含表头与数据", "习惯" in habit_csv
                  and "喝水" in habit_csv and "总打卡天数" in habit_csv)

            ctx.record_focus_session(task_id=tid, duration_min=25)
            focus_csv = export_mod.export_focus_csv(ctx.storage)
            check("专注 CSV 含记录", "focus" in focus_csv and "25" in focus_csv)
            all_csv = export_mod.export_all_sessions_csv(ctx.storage)
            check("全部记录 CSV 正常", "sessions" not in all_csv and len(all_csv) > 0)

            # 写文件（UTF-8-BOM）
            out_csv = os.path.join(tmp, "导出.csv")
            export_mod.save_text_file(out_csv, todo_csv)
            with open(out_csv, "rb") as fh:
                head = fh.read(3)
            check("文件带 UTF-8 BOM", head == b"\xef\xbb\xbf")

            # 数据库备份
            bak = os.path.join(tmp, "backup.db")
            export_mod.backup_database(ctx.storage, bak)
            check("备份文件存在且可打开", os.path.exists(bak)
                  and os.path.getsize(bak) > 0)
            bak_storage = Storage(bak)
            check("备份可独立读取", bak_storage.get("focus_min") is not None)
            bak_storage.close()
        finally:
            ctx.close()


def test_themes():
    print("[8] 主题调色板")
    names = themes_mod.theme_names()
    check("提供 4 套主题", len(names) == 4)
    for name in names:
        palette = themes_mod.get_palette(name)
        missing = [k for k in themes_mod.REQUIRED_KEYS if k not in palette]
        check("[%s] 颜色键齐全（%d 个）" % (name, len(themes_mod.REQUIRED_KEYS)),
              not missing)
        check("[%s] 颜色格式为 #rrggbb" % name,
              all(isinstance(v, str) and len(v) == 7 and v.startswith("#")
                  for v in palette.values()))
    check("每套主题都有显示名",
          all(n in themes_mod.THEME_LABELS for n in names))
    check("未知主题回退默认",
          themes_mod.get_palette("not-exist") ==
          themes_mod.get_palette(themes_mod.DEFAULT_THEME))
    check("显示名可反查主题键",
          themes_mod.name_for_label(themes_mod.label_for("dark")) == "dark")
    check("浅色与深色背景不同",
          themes_mod.get_palette("light")["BG"]
          != themes_mod.get_palette("dark")["BG"])


def test_reminder_settings():
    print("[9] 提醒设置与自定义铃声")
    with tempfile.TemporaryDirectory() as tmp:
        ctx = AppContext(os.path.join(tmp, "t.db"))
        try:
            st = ctx.storage
            check("弹窗/响铃开关默认开启",
                  settings_mod.get_bool(st, "reminder_popup")
                  and settings_mod.get_bool(st, "reminder_sound"))
            check("停铃秒数默认 20",
                  settings_mod.get_int(st, "reminder_seconds") == 20)
            settings_mod.set_int(st, "reminder_seconds", 35)
            check("停铃秒数可修改",
                  settings_mod.get_int(st, "reminder_seconds") == 35)
            settings_mod.set_bool(st, "reminder_sound", False)
            check("响铃可单独关闭",
                  settings_mod.get_bool(st, "reminder_sound") is False)
            check("主题默认值存在",
                  settings_mod.get_str(st, "theme") == "light")
            check("悬浮窗默认关闭",
                  settings_mod.get_bool(st, "float_enabled") is False)
            check("最小化自动显示悬浮窗默认开启",
                  settings_mod.get_bool(st, "float_auto_minimize") is True)
            settings_mod.set_bool(st, "float_enabled", True)
            st.set("float_pos", "120,80")
            check("悬浮窗开关与位置可保存",
                  settings_mod.get_bool(st, "float_enabled") is True
                  and settings_mod.get_str(st, "float_pos") == "120,80")

            custom = os.path.join(tmp, "my_alarm.wav")
            synthesize_alarm("focus", custom)
            check("自定义铃声优先",
                  alarm_path_for("short_break", custom) == custom)
            check("自定义失效时回退内置",
                  alarm_path_for("focus", os.path.join(tmp, "nope.wav"))
                  .endswith(".wav"))
        finally:
            ctx.close()


if __name__ == "__main__":
    test_storage_and_settings()
    test_todo()
    test_habit()
    test_engine()
    test_stats_and_context()
    test_alarm()
    test_export()
    test_themes()
    test_reminder_settings()
    print("\n全部 %d 项检查通过 ✔" % PASS)
