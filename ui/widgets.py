"""通用界面小组件。"""

import tkinter as tk

from . import theme
from .theme import CARD_BG, FONT_TITLE, FONT_SMALL, TEXT_DARK, TEXT_MUTED


def make_card(parent, padding=16):
    """创建一个卡片样式容器（配色随当前主题）。"""
    frame = tk.Frame(parent, bg=theme.CARD_BG, bd=0,
                     highlightbackground=theme.CARD_BORDER, highlightthickness=1)
    frame.padding = padding
    return frame


def card_title(parent, text):
    """卡片标题。"""
    return tk.Label(parent, text=text, bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                    font=FONT_TITLE, anchor="w")


def card_muted(parent, text):
    """卡片内的次要说明文字。"""
    return tk.Label(parent, text=text, bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                    font=FONT_SMALL, anchor="w", justify="left")
