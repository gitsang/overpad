# -*- coding: utf-8 -*-
"""极简主题：纯灰白单色，去掉所有填充，只靠轮廓和线条明暗表达状态。

按键按下时仅描边提亮到纯白，不做填充，视觉负担最低。
"""

from __future__ import annotations

from theme_hud import HudTheme


class MinimalTheme(HudTheme):
    PAL = {
        "line": "#6A6A72",
        "line_hi": "#FFFFFF",
        "text": "#9A9AA4",
        "text_hi": "#FFFFFF",
        "text_dim": "#55555D",
        "accent": "#C2C2CA",
        "accent_hi": "#FFFFFF",
        "fill_hi": "#2A2A34",
        "slot": "#16161C",
        "glow": "",
    }

    GLOW = False
    ROUND = 11
    LABEL_SIZE = 9
    VALUE_SIZE = 11
    BTN_SIZE = 10
