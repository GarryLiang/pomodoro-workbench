"""应用设置：默认值定义与带类型的读写辅助。"""

from .storage import Storage

# 默认设置项。番茄钟时长单位为分钟。
DEFAULT_SETTINGS = {
    "focus_min": "25",        # 单次专注时长（分钟）
    "short_break_min": "5",   # 短休息时长（分钟）
    "long_break_min": "15",   # 长休息时长（分钟）
    "long_break_after": "4",  # 每完成多少个专注后进入长休息
    "auto_start": "1",        # 阶段结束后是否自动开始下一阶段（1/0）
    "reminder_enabled": "1",  # 阶段结束是否弹出提醒（闹钟+弹窗）（1/0）
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


def load_all(storage):
    """读取全部设置，返回 dict[str, str]。"""
    return {key: storage.get(key, DEFAULT_SETTINGS[key]) for key in DEFAULT_SETTINGS}
