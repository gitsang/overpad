# -*- coding: utf-8 -*-
"""终端主题：等宽字体 + 方角框线 + 荧光绿单色，复古终端 HUD 的味道。"""

from __future__ import annotations

from theme_hud import HudTheme


class MonoTheme(HudTheme):
    PAL = {
        "line": "#1F6B3A",
        "line_hi": "#6BFF9A",
        "text": "#3BE07A",
        "text_hi": "#C8FFD8",
        "text_dim": "#1E7A45",
        "accent": "#2AE06A",
        "accent_hi": "#A0FFC0",
        "fill_hi": "#0A2412",
        "slot": "#041008",
        "glow": "",
    }

    FONT = "Consolas"
    GLOW = False
    ROUND = 2
    LABEL_SIZE = 10
    VALUE_SIZE = 12
    BTN_SIZE = 11
