"""界面主题：配色、字体与 ttk 样式集中定义。"""

import tkinter as tk
from tkinter import ttk

# 配色
BG = "#f3f5fa"            # 主背景
SIDEBAR_BG = "#26364f"    # 侧边栏背景
SIDEBAR_ACTIVE = "#3a5578"  # 侧边栏选中项背景
CARD_BG = "#ffffff"       # 卡片背景
TEXT_DARK = "#2b3440"     # 主文字
TEXT_MUTED = "#8a93a3"    # 次要文字
ACCENT = "#ff8c42"        # 主强调色（番茄橙）
ACCENT_DARK = "#e0731f"
GREEN = "#3fb27f"         # 成功 / 已完成
RED = "#e05d5d"           # 高优先级 / 警告
YELLOW = "#f2b134"        # 中优先级
BLUE = "#4ea1ff"          # 强调 / 图表
GRID_EMPTY = "#e8ecf3"    # 热力图空格子
GRID_L1 = "#b7d7fb"
GRID_L2 = "#7fb8f6"
GRID_L3 = "#4a93e8"
GRID_L4 = "#2a6fc4"

FONT_FAMILY = "Microsoft YaHei UI"
FONT_TITLE = (FONT_FAMILY, 14, "bold")
FONT_SUB = (FONT_FAMILY, 10)
FONT_BODY = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_NAV = (FONT_FAMILY, 11)
FONT_TIME = (FONT_FAMILY, 44, "bold")
FONT_STAT = (FONT_FAMILY, 22, "bold")

PAD = 16


def setup_style(root):
    """在 Tk 根窗口上应用全局样式。"""
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

    style.configure("TLabelframe", background=BG, bordercolor="#d7dce8",
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=BG, foreground=TEXT_DARK,
                    font=FONT_SUB)

    style.configure("TButton", font=FONT_BODY, padding=(12, 6))
    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                    font=(FONT_FAMILY, 10, "bold"), padding=(18, 8))
    style.map("Accent.TButton",
              background=[("active", ACCENT_DARK), ("disabled", "#eac2a4")],
              foreground=[("disabled", "#ffffff")])
    style.configure("Ghost.TButton", background=CARD_BG, bordercolor="#c9d0dd",
                    padding=(12, 6))
    style.map("Ghost.TButton", background=[("active", "#eef1f7")])

    style.configure("Nav.TButton", background=SIDEBAR_BG, foreground="#cdd8e8",
                    font=FONT_NAV, padding=(14, 10), anchor="w", borderwidth=0)
    style.map("Nav.TButton",
              background=[("active", SIDEBAR_ACTIVE), ("pressed", SIDEBAR_ACTIVE)],
              foreground=[("active", "#ffffff")])
    style.configure("NavSelected.TButton", background=SIDEBAR_ACTIVE,
                    foreground="#ffffff", font=(FONT_FAMILY, 11, "bold"),
                    padding=(14, 10), anchor="w", borderwidth=0)

    style.configure("Treeview", background=CARD_BG, fieldbackground=CARD_BG,
                    rowheight=30, font=FONT_BODY, borderwidth=0)
    style.configure("Treeview.Heading", font=(FONT_FAMILY, 10, "bold"),
                    background="#eef1f7", foreground=TEXT_DARK)
    style.map("Treeview", background=[("selected", "#dbe7f7")],
              foreground=[("selected", TEXT_DARK)])

    style.configure("TEntry", fieldbackground=CARD_BG, padding=6)
    style.configure("TCombobox", fieldbackground=CARD_BG, padding=4)
    style.configure("Vertical.TScrollbar", background="#cfd6e2",
                    troughcolor=BG, arrowcolor=TEXT_MUTED, borderwidth=0)
    style.configure("TProgressbar", background=ACCENT, troughcolor="#e6e9f0",
                    borderwidth=0, thickness=14)
    style.configure("Green.Horizontal.TProgressbar", background=GREEN,
                    troughcolor="#e6e9f0", borderwidth=0, thickness=10)

    # 让 ttk.Entry / Combobox 在只读场景下背景统一
    root.option_add("*TCombobox*Listbox.font", FONT_BODY)


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
