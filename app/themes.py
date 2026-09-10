"""主题调色板定义（纯数据，不依赖 tkinter，可被独立使用与测试）。

UI 层（ui/theme.py）负责把这些颜色应用到 ttk 样式与控件上；
这样调色板本身可以在无图形环境下被测试与复用。
"""

DEFAULT_THEME = "light"

# 主题显示名（界面下拉框使用）
THEME_LABELS = {
    "light": "默认浅色",
    "dark": "深色模式",
    "green": "护眼绿",
    "sakura": "樱花粉",
}

# 每套主题必须提供的颜色键
REQUIRED_KEYS = (
    "BG", "SIDEBAR_BG", "SIDEBAR_ACTIVE", "SIDEBAR_LINE", "SIDEBAR_TEXT",
    "SIDEBAR_TEXT_MUTED", "CARD_BG", "CARD_BORDER", "SEP", "TILE_BG",
    "TILE_BORDER", "TEXT_DARK", "TEXT_MUTED", "ACCENT", "ACCENT_DARK",
    "ACCENT_DISABLED", "GREEN", "RED", "YELLOW", "BLUE", "GRID_EMPTY",
    "GRID_L1", "GRID_L2", "GRID_L3", "GRID_L4", "PLOT_BG", "PLOT_BORDER",
    "PLOT_GRID", "SELECT_BG", "PROGRESS_TROUGH", "SCROLL_BG",
)

PALETTES = {
    # ---------------- 默认浅色 ----------------
    "light": {
        "BG": "#f3f5fa",
        "SIDEBAR_BG": "#26364f",
        "SIDEBAR_ACTIVE": "#3a5578",
        "SIDEBAR_LINE": "#33465f",
        "SIDEBAR_TEXT": "#cdd8e8",
        "SIDEBAR_TEXT_MUTED": "#66788f",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "#e1e6ef",
        "SEP": "#eef1f7",
        "TILE_BG": "#fff7ef",
        "TILE_BORDER": "#ffd9b8",
        "TEXT_DARK": "#2b3440",
        "TEXT_MUTED": "#8a93a3",
        "ACCENT": "#ff8c42",
        "ACCENT_DARK": "#e0731f",
        "ACCENT_DISABLED": "#eac2a4",
        "GREEN": "#3fb27f",
        "RED": "#e05d5d",
        "YELLOW": "#f2b134",
        "BLUE": "#4ea1ff",
        "GRID_EMPTY": "#e8ecf3",
        "GRID_L1": "#b7d7fb",
        "GRID_L2": "#7fb8f6",
        "GRID_L3": "#4a93e8",
        "GRID_L4": "#2a6fc4",
        "PLOT_BG": "#fafbfe",
        "PLOT_BORDER": "#e1e6ef",
        "PLOT_GRID": "#edf0f6",
        "SELECT_BG": "#dbe7f7",
        "PROGRESS_TROUGH": "#e6e9f0",
        "SCROLL_BG": "#cfd6e2",
    },
    # ---------------- 深色模式 ----------------
    "dark": {
        "BG": "#1b212b",
        "SIDEBAR_BG": "#161b24",
        "SIDEBAR_ACTIVE": "#2c3a50",
        "SIDEBAR_LINE": "#232c3a",
        "SIDEBAR_TEXT": "#c3cddc",
        "SIDEBAR_TEXT_MUTED": "#6b7a8f",
        "CARD_BG": "#232b38",
        "CARD_BORDER": "#333d4d",
        "SEP": "#313b4a",
        "TILE_BG": "#2c2620",
        "TILE_BORDER": "#4a3a2a",
        "TEXT_DARK": "#e6ebf2",
        "TEXT_MUTED": "#93a0b3",
        "ACCENT": "#ff9a56",
        "ACCENT_DARK": "#ff8c42",
        "ACCENT_DISABLED": "#5a4636",
        "GREEN": "#4ec98f",
        "RED": "#ef6b6b",
        "YELLOW": "#f2c14e",
        "BLUE": "#5aa9ff",
        "GRID_EMPTY": "#2c3543",
        "GRID_L1": "#2f5f8f",
        "GRID_L2": "#3b78b5",
        "GRID_L3": "#4a93e8",
        "GRID_L4": "#6fb0f5",
        "PLOT_BG": "#1f2733",
        "PLOT_BORDER": "#333d4d",
        "PLOT_GRID": "#2a3341",
        "SELECT_BG": "#2f4a6d",
        "PROGRESS_TROUGH": "#2f3948",
        "SCROLL_BG": "#3a4556",
    },
    # ---------------- 护眼绿 ----------------
    "green": {
        "BG": "#eef5ec",
        "SIDEBAR_BG": "#2f4a3a",
        "SIDEBAR_ACTIVE": "#3f6350",
        "SIDEBAR_LINE": "#3b5a47",
        "SIDEBAR_TEXT": "#d6e6da",
        "SIDEBAR_TEXT_MUTED": "#7f9c88",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "#d6e4d8",
        "SEP": "#e7f0e7",
        "TILE_BG": "#f2f8ee",
        "TILE_BORDER": "#cfe3c4",
        "TEXT_DARK": "#26362b",
        "TEXT_MUTED": "#7d8f84",
        "ACCENT": "#3f9e6b",
        "ACCENT_DARK": "#2f7d52",
        "ACCENT_DISABLED": "#bcd9c8",
        "GREEN": "#3fb27f",
        "RED": "#d95f5f",
        "YELLOW": "#dda520",
        "BLUE": "#4a93e8",
        "GRID_EMPTY": "#dfe9dd",
        "GRID_L1": "#c3e0c8",
        "GRID_L2": "#93c9a2",
        "GRID_L3": "#5faa7b",
        "GRID_L4": "#3d8a5d",
        "PLOT_BG": "#f7fbf5",
        "PLOT_BORDER": "#d6e4d8",
        "PLOT_GRID": "#e7f0e7",
        "SELECT_BG": "#d8ecdd",
        "PROGRESS_TROUGH": "#dfe9dd",
        "SCROLL_BG": "#c3d3c6",
    },
    # ---------------- 樱花粉 ----------------
    "sakura": {
        "BG": "#fdf1f4",
        "SIDEBAR_BG": "#57384a",
        "SIDEBAR_ACTIVE": "#6f4a5e",
        "SIDEBAR_LINE": "#664455",
        "SIDEBAR_TEXT": "#f2dde6",
        "SIDEBAR_TEXT_MUTED": "#a9849a",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "#f0dde3",
        "SEP": "#fae9ee",
        "TILE_BG": "#fff5f7",
        "TILE_BORDER": "#f6cdd9",
        "TEXT_DARK": "#3a2a31",
        "TEXT_MUTED": "#957f89",
        "ACCENT": "#ef7fa3",
        "ACCENT_DARK": "#d4608a",
        "ACCENT_DISABLED": "#f3c3d3",
        "GREEN": "#3fb27f",
        "RED": "#e05d5d",
        "YELLOW": "#f2b134",
        "BLUE": "#7f9ff0",
        "GRID_EMPTY": "#f2e2e8",
        "GRID_L1": "#f8c6d6",
        "GRID_L2": "#f0a0bb",
        "GRID_L3": "#e57a9d",
        "GRID_L4": "#cd5b83",
        "PLOT_BG": "#fffafb",
        "PLOT_BORDER": "#f0dde3",
        "PLOT_GRID": "#f7e8ee",
        "SELECT_BG": "#f8d9e3",
        "PROGRESS_TROUGH": "#f2e2e8",
        "SCROLL_BG": "#e0c6d0",
    },
}


def theme_names():
    """返回全部可用主题键，顺序即界面下拉展示顺序。"""
    return list(PALETTES.keys())


def is_valid(name):
    return name in PALETTES


def get_palette(name):
    """取得主题调色板；未知主题回退到默认主题（不会抛异常）。"""
    if name not in PALETTES:
        name = DEFAULT_THEME
    return dict(PALETTES[name])


def label_for(name):
    """主题显示名。"""
    return THEME_LABELS.get(name, THEME_LABELS[DEFAULT_THEME])


def name_for_label(label):
    """由显示名反查主题键，找不到返回 None。"""
    for key, text in THEME_LABELS.items():
        if text == label:
            return key
    return None
