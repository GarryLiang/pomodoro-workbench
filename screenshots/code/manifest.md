# 关键代码截图清单

| 截图 | 文件 | 函数/方法 | 行号区间 | 有效行数 | 说明 |
|---|---|---|---|---|---|
| 01-番茄钟-开始专注.png | `app/pomodoro.py` | PomodoroEngine.start | 127-142 | 15 | 番茄钟状态机：开始 / 继续计时 |
| 02-番茄钟-暂停重置.png | `app/pomodoro.py` | PomodoroEngine.pause / PomodoroEngine.reset | 144-168 | 23 | 番茄钟状态机：暂停 / 开始暂停切换 / 重置 |
| 03-番茄钟-手动推进.png | `app/pomodoro.py` | PomodoroEngine.tick | 184-199 | 15 | 手动推进 1 秒（无界面场景与第三方程序可用） |
| 04-番茄钟-墙钟刷新.png | `app/pomodoro.py` | PomodoroEngine.refresh | 201-219 | 18 | 按真实时间刷新剩余时间（幂等，界面卡顿不影响计时） |
| 05-番茄钟-时钟取整.png | `app/pomodoro.py` | PomodoroEngine._remaining_from_clock | 222-232 | 10 | 单调时钟剩余秒数计算与浮点取整容限 |
| 06-铃声-波形与包络.png | `app/alarm.py` | _envelope / _render_note | 79-100 | 20 | 标准库合成铃声：包络（防爆音）与正弦波形生成 |
| 07-铃声-WAV写出.png | `app/alarm.py` | synthesize_alarm | 103-123 | 18 | 按阶段旋律写出循环 WAV 文件 |
| 08-提醒-播放铃声.png | `ui/reminder.py` | _play_wav | 64-76 | 13 | Windows 异步循环播放铃声（跨平台回退） |
| 09-提醒-提醒入口.png | `ui/reminder.py` | show_phase_reminder | 107-130 | 21 | 阶段结束提醒入口：按设置决定弹窗 / 响铃 |
| 10-悬浮窗-位置记忆.png | `ui/float_window.py` | FloatWindow._restore_position | 145-161 | 17 | 悬浮窗位置恢复：多显示器坐标校验与默认位置 |
| 11-悬浮窗-显隐与置顶.png | `ui/float_window.py` | FloatWindow.show / FloatWindow.hide / FloatWindow.toggle_topmost | 168-189 | 20 | 悬浮窗显示、隐藏与 📌 置顶开关 |
| 12-习惯热力图-绘制.png | `ui/habit_view.py` | HabitView._draw_heatmap 绘制部分 | 269-292 | 23 | Canvas 自绘热力图：颜色分级、今日高亮 |
| 13-统计趋势图-柱条.png | `ui/stats_view.py` | StatsView._draw_chart 柱条部分 | 229-250 | 21 | Canvas 自绘趋势图：柱条、数值与日期标签 |
| 14-数据库-结构迁移.png | `app/storage.py` | Storage._apply_migrations | 94-112 | 18 | SQLite 结构版本迁移通道 |
| 15-跨平台字体.png | `ui/theme.py` | init_fonts | 41-66 | 23 | 按平台探测可用中文字体并回退 |

共 15 张截图，覆盖有效代码 275 行（不含注释与空行）。
