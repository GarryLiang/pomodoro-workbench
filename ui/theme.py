"""界面主题：把 app.themes 的调色板应用到 ttk 样式与模块级颜色常量上。

支持运行时切换主题：调用 apply(name) 更新颜色常量，再调用 setup_style(root)
刷新 ttk 样式；调用方（主窗口）负责重建页面以应用新的 tk 控件配色。
"""

from tkinter import ttk

from app.themes import (  # noqa: F401  对外透出，便于其他模块直接使用
    DEFAULT_THEME, PALETTES, THEME_LABELS, get_palette, is_valid, label_for,
    name_for_label, theme_names,
)

# 字体
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


def hex_to_rgb(value):
    """把 #rrggbb 转为 (r, g, b) 元组。"""
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix_alpha(base, overlay, alpha):
    """把 overlay 颜色按 alpha 混合到 base 上，返回 #rrggbb 字符串。"""
    br, bg_, bb = hex_to_rgb(base)
    or_, og, ob = hex_to_rgb(overlay)
    return "#%02x%02x%02x" % (
        int(br * (1 - alpha) + or_ * alpha),
        int(bg_ * (1 - alpha) + og * alpha),
        int(bb * (1 - alpha) + ob * alpha),
    )
