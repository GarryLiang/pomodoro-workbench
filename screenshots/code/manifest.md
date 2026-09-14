# 关键代码截图清单

| 截图 | 文件 | 函数/方法 | 行号区间 | 有效行数 | 说明 |
|---|---|---|---|---|---|
| 01-番茄钟-状态控制.png | `app/pomodoro.py` | PomodoroEngine.start / PomodoroEngine.pause / PomodoroEngine.reset | 127-168 | 38 | 番茄钟状态机：开始 / 暂停 / 重置 |
| 02-番茄钟-墙钟计时核心.png | `app/pomodoro.py` | PomodoroEngine.tick / PomodoroEngine.refresh / PomodoroEngine._remaining_from_clock | 184-232 | 43 | 按单调时钟结算的计时核心（修复界面卡顿导致的计时漂移） |
| 03-三阶段铃声合成.png | `app/alarm.py` | _render_note / synthesize_alarm | 89-123 | 30 | 用标准库合成三阶段专属 WAV 铃声 |
| 04-提醒-铃声控制.png | `ui/reminder.py` | _stop_sound / _play_wav / _schedule_auto_stop | 25-88 | 56 | 阶段结束铃声：循环播放、定时停铃与跨平台回退 |
| 05-提醒-弹出提醒.png | `ui/reminder.py` | show_phase_reminder | 107-130 | 21 | 阶段结束提醒入口：按设置决定弹窗与响铃 |
| 06-迷你悬浮窗.png | `ui/float_window.py` | FloatWindow._restore_position / FloatWindow._save_position / FloatWindow.show / FloatWindow.hide / FloatWindow.toggle_topmost | 145-189 | 40 | 迷你悬浮窗：置顶开关、显隐与位置记忆 |
| 07-习惯热力图自绘.png | `ui/habit_view.py` | HabitView._draw_heatmap | 245-300 | 48 | Canvas 自绘 15 周打卡热力图 |
| 08-统计趋势图自绘.png | `ui/stats_view.py` | StatsView._draw_chart | 207-255 | 44 | Canvas 自绘近 7 天专注趋势柱状图 |
| 09-数据库结构版本与迁移.png | `app/storage.py` | Storage._stored_schema_version / Storage._apply_migrations | 81-112 | 29 | SQLite 结构版本与迁移通道 |
| 10-跨平台字体自适应.png | `ui/theme.py` | init_fonts | 41-66 | 23 | 按平台探测可用中文字体 |

共 10 张截图，覆盖有效代码 372 行（不含注释与空行）。
