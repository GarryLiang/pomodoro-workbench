"""通用界面小组件。"""

import tkinter as tk

from . import theme


def make_card(parent):
    """创建一个卡片样式的容器（配色随当前主题）。

    注意：卡片本身不设置内边距，内边距由调用方在布局时（grid/pack 的 padx/pady）
    或卡片内部子控件上设置。
    """
    return tk.Frame(parent, bg=theme.CARD_BG, bd=0,
                    highlightbackground=theme.CARD_BORDER, highlightthickness=1)


def card_title(parent, text):
    """卡片标题。"""
    return tk.Label(parent, text=text, bg=theme.CARD_BG, fg=theme.TEXT_DARK,
                    font=theme.FONT_TITLE, anchor="w")


def card_muted(parent, text):
    """卡片内的次要说明文字。"""
    return tk.Label(parent, text=text, bg=theme.CARD_BG, fg=theme.TEXT_MUTED,
                    font=theme.FONT_SMALL, anchor="w", justify="left")
