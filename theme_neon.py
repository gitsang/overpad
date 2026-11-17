# -*- coding: utf-8 -*-
"""霓虹主题：青色主线 + 品红强调，圆环带外发光。

Tk 不支持半透明，发光效果用一层更宽的暗色描边垫在亮线外侧模拟，
在深色背景上会呈现柔和的光晕。
"""

from __future__ import annotations

from theme_hud import HudTheme


class NeonTheme(HudTheme):
    PAL = {
        "line": "#2396AD",
        "line_hi": "#8CFBFF",
        "text": "#63D8EA",
        "text_hi": "#EAFEFF",
        "text_dim": "#2E7A8A",
        "accent": "#FF2D78",
        "accent_hi": "#FF85B8",
        "fill_hi": "#0A2A33",
        "slot": "#04141A",
        "glow": "#12626F",
    }

    GLOW = True
    ROUND = 9
    LABEL_SIZE = 10
    VALUE_SIZE = 12
    BTN_SIZE = 11
