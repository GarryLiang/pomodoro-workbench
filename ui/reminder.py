"""阶段结束提醒：按阶段播放专属闹钟铃声 + 置顶弹窗。

- 铃声：播放 app.alarm 现场合成的 WAV（Windows 异步循环播放，
  其他平台回退为系统铃音）；每个阶段（专注/短休息/长休息）旋律不同。
- 弹窗：非模态置顶窗口，显示当前结束的阶段，点击按钮或 20 秒后自动关闭，
  关闭即停铃。
"""

import tkinter as tk

from app.alarm import ensure_alarm_wav, DEFAULT_KIND
from . import theme

_AUTO_CLOSE_MS = 20 * 1000
_active_popup = None
_playing_wav = False


def _stop_sound():
    """停止循环铃声（仅 Windows PlaySound 路径）。"""
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


def stop_active_alarm():
    """应用关闭等场景下强制停铃并关闭弹窗。"""
    global _active_popup
    _stop_sound()
    if _active_popup is not None:
        try:
            if _active_popup.winfo_exists():
                _active_popup.destroy()
        except tk.TclError:
            pass
        _active_popup = None


def show_phase_reminder(root, phase_label, message, icon="🍅", sound=DEFAULT_KIND,
                        play_sound=True):
    """弹出阶段结束提醒，并循环播放该阶段专属闹铃。

    若已有提醒弹窗则先关闭旧弹窗，保证同一时刻只有一个提醒。
    sound 取值：focus / short_break / long_break（见 app.alarm.KINDS）。
    play_sound=False 时只弹窗不响铃（用于截图等静默场景）。
    """
    global _active_popup
    stop_active_alarm()
    popup = ReminderPopup(root, phase_label, message, icon, sound, play_sound)
    _active_popup = popup
    return popup


class ReminderPopup(tk.Toplevel):
    """置顶的提醒弹窗。"""

    def __init__(self, master, phase_label, message, icon="🍅",
                 sound=DEFAULT_KIND, play_sound=True):
        super().__init__(master)
        self._sound_kind = sound
        self._play_sound_flag = play_sound
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
        ttk_ok = tk.Button(box, text="🔔 知道了（停铃）", bg=theme.ACCENT,
                           fg="#ffffff", activebackground=theme.ACCENT_DARK,
                           activeforeground="#ffffff", relief="flat",
                           font=(theme.FONT_FAMILY, 10, "bold"),
                           padx=18, pady=6, cursor="hand2",
                           command=self.close)
        ttk_ok.pack()

        self._center_on(master)
        self.lift()
        self.focus_force()
        self._play_sound()
        self._auto_close_id = self.after(_AUTO_CLOSE_MS, self._auto_close)

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

    def _play_sound(self):
        if not self._play_sound_flag:
            return
        global _playing_wav
        try:
            import winsound
            wav_path = ensure_alarm_wav(self._sound_kind)
            winsound.PlaySound(
                wav_path,
                winsound.SND_FILENAME | winsound.SND_ASYNC
                | winsound.SND_LOOP | winsound.SND_NODEFAULT)
            _playing_wav = True
            return
        except Exception:
            pass
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
