"""通用界面小组件。"""

import tkinter as tk

from .theme import CARD_BG, FONT_TITLE, FONT_SMALL, TEXT_DARK, TEXT_MUTED


def make_card(parent, padding=16):
    """创建一个白色圆角卡片样式的容器（tk.Frame 实现圆角观感）。"""
    frame = tk.Frame(parent, bg=CARD_BG, bd=0,
                     highlightbackground="#e1e6ef", highlightthickness=1)
    frame.padding = padding
    return frame


def card_title(parent, text):
    """卡片标题。"""
    return tk.Label(parent, text=text, bg=CARD_BG, fg=TEXT_DARK,
                    font=FONT_TITLE, anchor="w")


def card_muted(parent, text):
    """卡片内的次要说明文字。"""
    return tk.Label(parent, text=text, bg=CARD_BG, fg=TEXT_MUTED,
                    font=FONT_SMALL, anchor="w", justify="left")
