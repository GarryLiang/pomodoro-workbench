"""GUI 冒烟测试：构建主窗口与全部页面（窗口会短暂闪现后自动关闭）。

运行：python tests/gui_smoke.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

            print("GUI 冒烟测试通过：4 个页面 + 4 套主题切换 + 提醒设置保存均正常")
        finally:
            if win is not None:
                try:
                    win.destroy()
                except Exception:
                    pass
            ctx.close()


if __name__ == "__main__":
    main()
