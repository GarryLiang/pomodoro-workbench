"""GUI 冒烟测试：构建主窗口与全部页面（窗口会短暂闪现后自动关闭）。

运行：python tests/gui_smoke.py
"""

import os
import sys
import tempfile
import time as time_mod

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import settings as settings_mod
from app.context import AppContext
from ui.main_window import MainWindow


def main():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = AppContext(os.path.join(tmp, "gui.db"))
        win = None
        try:
            # 预置演示数据，让各页面有内容可渲染
            ctx.todo.add("完成操作系统实验报告", note="第三章", priority=2)
            ctx.todo.add("背 50 个英语单词", priority=0)
            ctx.record_focus_session(duration_min=25)
            hid = ctx.habits.add_habit("早睡")
            ctx.habits.check_in(hid)
            ctx.habits.add_habit("每日阅读 30 分钟")

            win = MainWindow(ctx)
            win.update()
            for key in ("todo", "habit", "stats", "pomodoro"):
                win.switch(key)
                win.update()
                win.update_idletasks()
            # 模拟一次交互：加待办、切完成、打卡
            win.switch("todo")
            win.update()
            win.switch("habit")
            win.update()

            # 主题切换：每套主题都要能重建界面且不报错
            from ui import theme as theme_mod
            from app.themes import theme_names
            for name in theme_names():
                applied = win.apply_theme(name)
                assert applied == name, "主题切换失败: %s" % name
                win.update()
                for key in ("pomodoro", "todo", "habit", "stats"):
                    win.switch(key)
                    win.update()
                assert theme_mod.current == name
            win.apply_theme("light")
            win.update()

            # 提醒设置面板：保存一次设置（不弹窗、不响铃）
            win.switch("pomodoro")
            win.update()
            view = win._pages["pomodoro"]
            view.var_popup.set(True)
            view.var_sound.set(False)
            view.var_seconds.set("30")
            view._on_apply_settings()
            win.update()

            # 端到端：阶段自然结束应记录会话并累计待办番茄数（关掉提醒避免弹窗/响铃）
            settings_mod.set_bool(ctx.storage, "reminder_enabled", False)
            win.switch("pomodoro")
            win.update()
            view = win._pages["pomodoro"]
            tid = ctx.todo.add("集成测试任务", priority=1)
            view.refresh_tasks()
            view._current_task_id = tid
            before = ctx.stats.focus_summary()["total_count"]
            ctx.engine.start()
            ctx.engine._deadline = time_mod.monotonic() - 0.05   # 模拟时间到
            ctx.engine.refresh()
            win.update()
            after = ctx.stats.focus_summary()["total_count"]
            assert after == before + 1, "阶段结束应记录一次专注会话"
            assert ctx.todo.get(tid).pomodoros == 1, "关联待办应累计 1 个番茄"
            assert ctx.engine.phase != "focus", "专注结束后应进入休息阶段"

            # 迷你悬浮窗：显示 → 快捷操作 → 主题切换重建 → 隐藏
            win.show_float_window()
            win.update()
            assert win.float_window is not None and win.float_window.is_visible(), \
                "悬浮窗应处于显示状态"
            was_running = ctx.engine.running
            win.float_window._on_toggle()      # 快捷开始/暂停
            win.update()
            assert ctx.engine.running != was_running, "悬浮窗快捷开关应生效"
            win.float_window._on_skip()        # 快捷跳过
            win.update()
            win.apply_theme("dark")            # 主题切换应触发悬浮窗重建
            win.update()
            assert win.float_window.is_visible(), "主题切换后悬浮窗应仍然可见"
            assert theme_mod.current == "dark"
            win.apply_theme("light")
            win.update()
            win.restore_from_float()           # 返回主界面应隐藏悬浮窗
            win.update()
            assert not win.float_window.is_visible(), "返回主界面后悬浮窗应隐藏"
            if ctx.engine.running:
                ctx.engine.pause()

            # 悬浮窗置顶开关（📌）应持久化到设置
            win.float_window.toggle_topmost()
            win.update()
            assert settings_mod.get_bool(ctx.storage, "float_topmost") is False, \
                "关闭置顶后应写入设置"
            win.float_window.toggle_topmost()
            assert settings_mod.get_bool(ctx.storage, "float_topmost") is True

            # 首次使用引导：首启显示，标记后重建界面不再出现
            assert settings_mod.get_bool(ctx.storage, "welcome_shown") is False
            win.apply_theme("light")            # 重建页面走一次引导分支
            win.update()
            settings_mod.set_bool(ctx.storage, "welcome_shown", True)
            win.apply_theme("light")
            win.update()

            # 关闭窗口应保存窗口位置与尺寸
            win.geometry("1000x660+80+40")
            win.update()
            win._on_close()
            saved_geo = settings_mod.get_str(ctx.storage, "win_geometry")
            assert saved_geo, "关闭时应保存 win_geometry"
            assert "x" in saved_geo and "+" in saved_geo, \
                "geometry 格式应形如 1000x660+80+40，实际: %s" % saved_geo

            print("GUI 冒烟测试通过：4 个页面 + 4 套主题 + 提醒设置 + 悬浮窗"
                  "（置顶/位置记忆）+ 首启引导均正常")
        finally:
            if win is not None:
                try:
                    win.destroy()
                except Exception:
                    pass
            ctx.close()


if __name__ == "__main__":
    main()
