"""应用设置：默认值定义与带类型的读写辅助。"""

from .storage import Storage

# 默认设置项。番茄钟时长单位为分钟。
DEFAULT_SETTINGS = {
    "focus_min": "25",        # 单次专注时长（分钟）
    "short_break_min": "5",   # 短休息时长（分钟）
    "long_break_min": "15",   # 长休息时长（分钟）
    "long_break_after": "4",  # 每完成多少个专注后进入长休息
    "auto_start": "1",        # 阶段结束后是否自动开始下一阶段（1/0）
    "reminder_enabled": "1",  # 阶段结束是否提醒（总开关，1/0）
    "reminder_popup": "1",    # 阶段结束弹窗提醒（1/0）
    "reminder_sound": "1",    # 阶段结束响铃提醒（1/0）
    "reminder_seconds": "20",  # 提醒自动停铃秒数（5~120）
    "custom_alarm_path": "",  # 自定义铃声文件（WAV），为空表示用内置三阶段铃声
    "theme": "light",         # 界面主题（light / dark / green / sakura）
    "float_enabled": "0",       # 是否显示迷你悬浮窗（1/0）
    "float_auto_minimize": "1",  # 主窗口最小化时自动显示悬浮窗（1/0）
    "float_pos": "",            # 悬浮窗位置 "x,y"（空表示默认右下角）
    "float_topmost": "1",       # 悬浮窗是否置顶（1/0，界面上的 📌 可切换）
    "win_geometry": "",         # 主窗口位置与尺寸 "WxH+X+Y"（空表示默认）
    "welcome_shown": "0",       # 是否已展示首次使用引导（1/0）
}


def ensure_defaults(storage):
    """把尚未写入数据库的设置项补齐为默认值。"""
    for key, value in DEFAULT_SETTINGS.items():
        if storage.get(key) is None:
            storage.set(key, value)


def _raw(storage, key):
    value = storage.get(key)
    if value is None:
        return DEFAULT_SETTINGS[key]
    return value


def get_int(storage, key):
    """读取整型设置，非法值回退为默认值。"""
    try:
        return int(_raw(storage, key))
    except (TypeError, ValueError):
        return int(DEFAULT_SETTINGS[key])


def get_bool(storage, key):
    """读取布尔设置：'1' / 'true' 视为 True。"""
    return _raw(storage, key).strip().lower() in ("1", "true", "yes")


def set_int(storage, key, value):
    """写入整型设置。"""
    storage.set(key, int(value))


def set_bool(storage, key, value):
    """写入布尔设置。"""
    storage.set(key, "1" if value else "0")


def get_str(storage, key):
    """读取字符串设置。"""
    return _raw(storage, key)


def set_str(storage, key, value):
    """写入字符串设置。"""
    storage.set(key, value or "")


def load_all(storage):
    """读取全部设置，返回 dict[str, str]。"""
    return {key: storage.get(key, DEFAULT_SETTINGS[key]) for key in DEFAULT_SETTINGS}
