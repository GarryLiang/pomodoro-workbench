"""界面主题：把 app.themes 的调色板应用到 ttk 样式与模块级颜色常量上。

支持运行时切换主题：调用 apply(name) 更新颜色常量，再调用 setup_style(root)
刷新 ttk 样式；调用方（主窗口）负责重建页面以应用新的 tk 控件配色。
字体由 init_fonts(root) 按平台自动选择（Windows/macOS/Linux 均可用）。
"""

from tkinter import font as tkfont
from tkinter import ttk

from app.themes import (  # noqa: F401  对外透出，便于其他模块直接使用
    DEFAULT_THEME, PALETTES, THEME_LABELS, get_palette, is_valid, label_for,
    name_for_label, theme_names,
)

# 各平台常见中文字体，按优先级探测（第一个存在的即被采用）
FONT_CANDIDATES = (
    "Microsoft YaHei UI", "Microsoft YaHei",      # Windows
    "PingFang SC", "Hiragino Sans GB",            # macOS
    "Noto Sans CJK SC", "Source Han Sans SC",     # Linux
    "WenQuanYi Micro Hei", "SimHei", "Arial Unicode MS",
)

# 字体（默认值；init_fonts() 会按实际可用字体重设）
FONT_FAMILY = "Microsoft YaHei UI"
FONT_TITLE = (FONT_FAMILY, 14, "bold")
FONT_SUB = (FONT_FAMILY, 10)
FONT_BODY = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_NAV = (FONT_FAMILY, 11)
FONT_TIME = (FONT_FAMILY, 44, "bold")
FONT_STAT = (FONT_FAMILY, 22, "bold")

PAD = 16

# 当前主题名与全部颜色常量（由 apply() 填充）
current = DEFAULT_THEME
globals().update(get_palette(DEFAULT_THEME))


def init_fonts(root):
    """按平台探测可用的中文字体，更新模块级字体常量。

    需在创建任何窗口控件之前调用（主窗口 __init__ 中先调用它再 setup_style）。
    找不到候选中文字体时回退到 Tk 默认字体，保证任何系统都能正常启动。
    """
    global FONT_FAMILY, FONT_TITLE, FONT_SUB, FONT_BODY, FONT_SMALL
    global FONT_NAV, FONT_TIME, FONT_STAT

    try:
        available = set(tkfont.families(root))
        family = next((f for f in FONT_CANDIDATES if f in available), None)
        if family is None:
            family = tkfont.nametofont("TkDefaultFont").actual("family")
    except Exception:
        family = FONT_FAMILY

    FONT_FAMILY = family
    FONT_TITLE = (family, 14, "bold")
    FONT_SUB = (family, 10)
    FONT_BODY = (family, 10)
    FONT_SMALL = (family, 9)
    FONT_NAV = (family, 11)
    FONT_TIME = (family, 44, "bold")
    FONT_STAT = (family, 22, "bold")
    return family


def apply(name):
    """切换当前主题，更新模块级颜色常量。返回实际生效的主题名。"""
    global current
    palette = get_palette(name)
    current = name if is_valid(name) else DEFAULT_THEME
    globals().update(palette)
    return current


def setup_style(root):
    """把当前调色板应用到 Tk 根窗口与 ttk 样式（可重复调用，用于主题切换）。"""
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=TEXT_DARK,
                    font=FONT_BODY, fieldbackground=CARD_BG)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD_BG)
    style.configure("TLabel", background=BG, foreground=TEXT_DARK)
    style.configure("Card.TLabel", background=CARD_BG)
    style.configure("Muted.TLabel", background=CARD_BG, foreground=TEXT_MUTED,
                    font=FONT_SMALL)

    style.configure("TLabelframe", background=BG, bordercolor=CARD_BORDER,
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=BG, foreground=TEXT_DARK,
                    font=FONT_SUB)

    style.configure("TButton", font=FONT_BODY, padding=(12, 6))
    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                    font=(FONT_FAMILY, 10, "bold"), padding=(18, 8))
    style.map("Accent.TButton",
              background=[("active", ACCENT_DARK), ("disabled", ACCENT_DISABLED)],
              foreground=[("disabled", "#ffffff")])
    style.configure("Ghost.TButton", background=CARD_BG, bordercolor=CARD_BORDER,
                    padding=(12, 6))
    style.map("Ghost.TButton", background=[("active", SEP)])

    style.configure("Nav.TButton", background=SIDEBAR_BG, foreground=SIDEBAR_TEXT,
                    font=FONT_NAV, padding=(14, 10), anchor="w", borderwidth=0)
    style.map("Nav.TButton",
              background=[("active", SIDEBAR_ACTIVE), ("pressed", SIDEBAR_ACTIVE)],
              foreground=[("active", "#ffffff")])
    style.configure("NavSelected.TButton", background=SIDEBAR_ACTIVE,
                    foreground="#ffffff", font=(FONT_FAMILY, 11, "bold"),
                    padding=(14, 10), anchor="w", borderwidth=0)

    style.configure("Treeview", background=CARD_BG, fieldbackground=CARD_BG,
                    foreground=TEXT_DARK, rowheight=30, font=FONT_BODY,
                    borderwidth=0)
    style.configure("Treeview.Heading", font=(FONT_FAMILY, 10, "bold"),
                    background=SEP, foreground=TEXT_DARK)
    style.map("Treeview", background=[("selected", SELECT_BG)],
              foreground=[("selected", TEXT_DARK)])

    style.configure("TEntry", fieldbackground=CARD_BG, foreground=TEXT_DARK,
                    padding=6)
    style.configure("TCombobox", fieldbackground=CARD_BG, foreground=TEXT_DARK,
                    padding=4)
    style.configure("Vertical.TScrollbar", background=SCROLL_BG,
                    troughcolor=BG, arrowcolor=TEXT_MUTED, borderwidth=0)
    style.configure("TProgressbar", background=ACCENT,
                    troughcolor=PROGRESS_TROUGH, borderwidth=0, thickness=14)
    style.configure("Green.Horizontal.TProgressbar", background=GREEN,
                    troughcolor=PROGRESS_TROUGH, borderwidth=0, thickness=10)

    root.option_add("*TCombobox*Listbox.font", FONT_BODY)
    root.option_add("*TCombobox*Listbox.background", CARD_BG)
    root.option_add("*TCombobox*Listbox.foreground", TEXT_DARK)
