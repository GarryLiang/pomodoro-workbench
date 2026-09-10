"""阶段结束提醒：按阶段播放专属铃声 + 置顶弹窗（支持自定义铃声与试听）。

- 铃声：默认使用 app.alarm 现场合成的三阶段专属 WAV；若用户在设置中
  指定了自定义 WAV，则统一使用自定义铃声。
- 弹窗：非模态置顶窗口，点击按钮或到达设定秒数后自动关闭，关闭即停铃。
- 也支持"只响铃不弹窗"与"只弹窗不响铃"两种模式。
- 提供 play_preview() 供设置界面随时试听。
"""

import os
import tkinter as tk

from app.alarm import DEFAULT_KIND, alarm_path_for
from . import theme

DEFAULT_AUTO_CLOSE_MS = 20 * 1000

_active_popup = None
_playing_wav = False
_stop_after_id = None
_stop_after_widget = None


# ------------------------------------------------------------------ 声音控制
def _stop_sound():
    """停止循环铃声（Windows PlaySound 路径）。"""
    global _playing_wav
    if not _playing_wav:
        return
    try:
        import winsound
        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass
    finally:
        _playing_wav = False


def _cancel_stop_timer():
    global _stop_after_id, _stop_after_widget
    if _stop_after_id is not None and _stop_after_widget is not None:
        try:
            _stop_after_widget.after_cancel(_stop_after_id)
        except tk.TclError:
            pass
    _stop_after_id = None
    _stop_after_widget = None


def stop_active_alarm():
    """停止铃声、取消定时停铃并关闭提醒弹窗（应用关闭时也会调用）。"""
    global _active_popup
    _cancel_stop_timer()
    _stop_sound()
    if _active_popup is not None:
        try:
            if _active_popup.winfo_exists():
                _active_popup.destroy()
        except tk.TclError:
            pass
        _active_popup = None


def _play_wav(path):
    """播放 WAV（循环），成功返回 True。"""
    global _playing_wav
    try:
        import winsound
        winsound.PlaySound(
            path,
            winsound.SND_FILENAME | winsound.SND_ASYNC
            | winsound.SND_LOOP | winsound.SND_NODEFAULT)
        _playing_wav = True
        return True
    except Exception:
        return False


def _schedule_auto_stop(widget, milliseconds):
    """到点自动停铃（即使没有弹窗，也要能停下来）。"""
    global _stop_after_id, _stop_after_widget
    _cancel_stop_timer()
    try:
        _stop_after_widget = widget
        _stop_after_id = widget.after(int(milliseconds), _stop_sound)
    except tk.TclError:
        _stop_after_widget = None
        _stop_after_id = None


def play_preview(root, kind=DEFAULT_KIND, custom_path=None,
                 seconds=15):
    """试听指定阶段的铃声（先停掉当前响铃），返回实际播放的文件路径。"""
    stop_active_alarm()
    path = alarm_path_for(kind, custom_path)
    if _play_wav(path):
        _schedule_auto_stop(root, seconds * 1000)
    else:
        try:
            root.bell()
        except tk.TclError:
            pass
    return path


# ------------------------------------------------------------------ 提醒入口
def show_phase_reminder(root, phase_label, message, icon="🍅",
                        sound=DEFAULT_KIND, play_sound=True, show_popup=True,
                        auto_close_ms=None, custom_alarm=None):
    """阶段结束提醒。

    show_popup=False 时只响铃不弹窗；play_sound=False 时只弹窗不响铃。
    两者都为 False 时不做任何事（由调用方提前判断更省事）。
    """
    global _active_popup
    stop_active_alarm()
    auto_close_ms = int(auto_close_ms or DEFAULT_AUTO_CLOSE_MS)

    if not show_popup:
        if play_sound:
            path = alarm_path_for(sound, custom_alarm)
            if _play_wav(path):
                _schedule_auto_stop(root, auto_close_ms)
        return None

    popup = ReminderPopup(root, phase_label, message, icon, sound,
                          play_sound=play_sound, auto_close_ms=auto_close_ms,
                          custom_alarm=custom_alarm)
    _active_popup = popup
    return popup


class ReminderPopup(tk.Toplevel):
    """置顶的提醒弹窗。"""

    def __init__(self, master, phase_label, message, icon="🍅",
                 sound=DEFAULT_KIND, play_sound=True, auto_close_ms=None,
                 custom_alarm=None):
        super().__init__(master)
        self._sound_kind = sound
        self._play_sound_flag = play_sound
        self._custom_alarm = custom_alarm
        self._auto_close_ms = int(auto_close_ms or DEFAULT_AUTO_CLOSE_MS)
        self._auto_close_id = None
        self.overrideredirect(False)
        self.title("阶段结束提醒")
        self.configure(bg=theme.CARD_BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.close)

        box = tk.Frame(self, bg=theme.CARD_BG)
        box.pack(padx=30, pady=24)
        tk.Label(box, text=icon, bg=theme.CARD_BG,
                 font=(theme.FONT_FAMILY, 40)).pack()
        tk.Label(box, text=phase_label, bg=theme.CARD_BG,
                 fg=theme.ACCENT_DARK, font=theme.FONT_TITLE).pack(pady=(6, 2))
        tk.Label(box, text=message, bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                 font=theme.FONT_SUB, wraplength=300, justify="center").pack(
            pady=(0, 14))
        tk.Button(box, text="🔔 知道了（停铃）", bg=theme.ACCENT,
                  fg="#ffffff", activebackground=theme.ACCENT_DARK,
                  activeforeground="#ffffff", relief="flat",
                  font=(theme.FONT_FAMILY, 10, "bold"),
                  padx=18, pady=6, cursor="hand2",
                  command=self.close).pack()

        self._center_on(master)
        self.lift()
        self.focus_force()
        self._play()
        self._auto_close_id = self.after(self._auto_close_ms, self._auto_close)

    # ------------------------------------------------------------------
    def _center_on(self, master):
        self.update_idletasks()
        try:
            mx = master.winfo_rootx()
            my = master.winfo_rooty()
            mw = master.winfo_width()
            mh = master.winfo_height()
        except tk.TclError:
            mx = my = mw = mh = 0
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = mx + max(0, (mw - w) // 2)
        y = my + max(0, (mh - h) // 3)
        self.geometry("+%d+%d" % (x, y))

    def _play(self):
        if not self._play_sound_flag:
            return
        path = alarm_path_for(self._sound_kind, self._custom_alarm)
        if not _play_wav(path):
            # 跨平台回退：铃音几声
            try:
                for _ in range(3):
                    self.bell()
            except tk.TclError:
                pass

    def _auto_close(self):
        self._auto_close_id = None
        self.close()

    def close(self):
        """关闭弹窗并停止铃声。"""
        global _active_popup
        _stop_sound()
        if self._auto_close_id is not None:
            try:
                self.after_cancel(self._auto_close_id)
            except tk.TclError:
                pass
            self._auto_close_id = None
        if _active_popup is self:
            _active_popup = None
        try:
            self.destroy()
        except tk.TclError:
            pass


def custom_alarm_available(path):
    """判断自定义铃声文件是否可用（供界面显示状态）。"""
    return bool(path) and os.path.isfile(path) and os.path.getsize(path) > 100
