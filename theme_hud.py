# -*- coding: utf-8 -*-
"""HUD 主题基类：现代极简线框风格。

图形用 Tk 原生图元绘制。Tk 在 Windows 上走 GDI 硬边光栅化，配合近黑色键
透明不会在描边周围产生彩色过渡像素。圆角用平滑多边形实现。

配色 / 字体 / 圆角 / 发光都通过类属性配置，子类改几行就能长出新主题。
"""

from __future__ import annotations

BASE_W, BASE_H = 416, 344

# box = 条的矩形范围；meter=True 的条带进度填充，dir 指定填充方向
BARS = {
    "lb": dict(box=(8, 8, 54, 30), label="LB", meter=False),
    "lt": dict(box=(60, 8, 156, 30), label="LT", meter=True, dir="ltr",
               val=(164, 19), anchor="w"),
    "rt": dict(box=(260, 8, 356, 30), label="RT", meter=True, dir="rtl",
               val=(252, 19), anchor="e"),
    "rb": dict(box=(362, 8, 408, 30), label="RB", meter=False),
}

# 左右两列元素按同一基线对齐，整体在 416 宽度内居中
LS = (100, 108)
LS_RING = 44
RS = (330, 224)
RS_RING = 40
CAP_R = 11

ABXY = {
    "y": (330, 74),
    "b": (356, 100),
    "a": (330, 126),
    "x": (304, 100),
}
BTN_R = 16

PAD = (80, 236)
PAD_ARM = (28, 37)

CENTRAL = {
    "view": (208, 140, 64, 22),
    "guide": (208, 174, 16, 0),
    "menu": (208, 206, 64, 22),
}

BTN_BITS = {
    "dpad_u": 0x0001, "dpad_d": 0x0002, "dpad_l": 0x0004, "dpad_r": 0x0008,
    "menu": 0x0010, "view": 0x0020, "ls": 0x0040, "rs": 0x0080,
    "lb": 0x0100, "rb": 0x0200, "guide": 0x0400,
    "a": 0x1000, "b": 0x2000, "x": 0x4000, "y": 0x8000,
}


class HudTheme:
    BASE_W = BASE_W
    BASE_H = BASE_H

    PAL = {
        "line": "#8C8C98",
        "line_hi": "#FFFFFF",
        "text": "#C8C8D2",
        "text_hi": "#FFFFFF",
        "text_dim": "#7E7E8A",
        "accent": "#C23A6E",
        "accent_hi": "#F06BA0",
        "fill_hi": "#2E2E3A",
        "slot": "#1E1E26",
        "glow": "",
    }

    FONT = "Segoe UI"
    GLOW = False
    ROUND = 8
    LABEL_SIZE = 10
    VALUE_SIZE = 12
    BTN_SIZE = 12

    def __init__(self, cv, zoom=1):
        self.cv = cv
        self.z = zoom
        self.P = self.PAL
        self.last = None
        self.cap = {"ls": (0.0, 0.0), "rs": (0.0, 0.0)}
        self.build()

    # --- 坐标与尺寸 -------------------------------------------------
    def X(self, v):
        return int(round(v * self.z))

    def LW(self, v=1.0):
        return max(1, int(round(v * self.z)))

    def FS(self, px):
        return -max(7, int(round(px * self.z)))

    def rrect(self, x1, y1, x2, y2, r, **kw):
        r = min(r * self.ROUND / 8.0, (x2 - x1) / 2.0, (y2 - y1) / 2.0)
        if r <= 0:
            return self.cv.create_rectangle(self.X(x1), self.X(y1),
                                            self.X(x2), self.X(y2), **kw)
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1, x1 + r, y1,
        ]
        return self.cv.create_polygon([self.X(v) for v in pts],
                                      smooth=True, **kw)

    def oval(self, cx, cy, r, color, width, fill=""):
        if self.GLOW and self.P["glow"]:
            self.cv.create_oval(self.X(cx - r), self.X(cy - r),
                                self.X(cx + r), self.X(cy + r),
                                outline=self.P["glow"],
                                width=int(width * 4), fill="")
        return self.cv.create_oval(self.X(cx - r), self.X(cy - r),
                                   self.X(cx + r), self.X(cy + r),
                                   outline=color, width=width, fill=fill)

    # --- 构建 -------------------------------------------------------
    def build(self):
        cv, P = self.cv, self.P
        self.rings = {}
        self.labels = {}
        self.bars = {}
        self.pads = {}
        self.caps = {}
        self.sticks = {}

        for name, cfg in BARS.items():
            x1, y1, x2, y2 = cfg["box"]
            h = y2 - y1
            if cfg["meter"]:
                self.rrect(x1, y1, x2, y2, h / 2.0, fill=P["slot"],
                           outline=P["line"], width=self.LW())
                # 填充条必须固定为 polygon：宽度为 0 时 rrect 会退化成
                # rectangle，后续就没法用多边形坐标更新了
                fill = cv.create_polygon(
                    self.X(x1), self.X(y1), self.X(x1 + 1), self.X(y1),
                    self.X(x1 + 1), self.X(y2), self.X(x1), self.X(y2),
                    fill=P["accent"], outline="")
                self.bars[name] = (None, fill, x1, y1, x2, y2, h / 2.0)
            else:
                ring = self.rrect(x1, y1, x2, y2, h / 2.0, fill="",
                                  outline=P["line"], width=self.LW())
                self.bars[name] = (ring, None, x1, y1, x2, y2, h / 2.0)
            cv.create_text(self.X((x1 + x2) / 2), self.X((y1 + y2) / 2),
                           text=cfg["label"], fill=P["text_hi"],
                           font=(self.FONT, self.FS(self.LABEL_SIZE)))

        for name in ("lt", "rt"):
            vx, vy = BARS[name]["val"]
            self.rings[name + "_val"] = cv.create_text(
                self.X(vx), self.X(vy), text="0", fill=P["text_hi"],
                anchor=BARS[name]["anchor"],
                font=(self.FONT, self.FS(self.VALUE_SIZE)))

        for name, (cx, cy) in (("ls", LS), ("rs", RS)):
            ro = LS_RING if name == "ls" else RS_RING
            self.oval(cx, cy, ro, P["line"], self.LW(1.4))
            cap = self.oval(cx, cy, CAP_R, P["accent_hi"], self.LW(0.8),
                            fill=P["accent"])
            lbl = cv.create_text(self.X(cx), self.X(cy + ro + 14),
                                 text="L3" if name == "ls" else "R3",
                                 fill=P["text_dim"],
                                 font=(self.FONT, self.FS(9)))
            self.caps[name] = cap
            self.sticks[name] = (cx, cy, ro, lbl)

        for k, (cx, cy) in ABXY.items():
            ring = self.oval(cx, cy, BTN_R, P["line"], self.LW(1.2))
            lbl = cv.create_text(self.X(cx), self.X(cy), text=k.upper(),
                                 fill=P["text"],
                                 font=(self.FONT, self.FS(self.BTN_SIZE)))
            self.rings[k] = ring
            self.labels[k] = [lbl]

        px, py = PAD
        aw, al = PAD_ARM
        half = aw / 2.0
        # 整体十字轮廓（一条闭合折线），四个臂的填充块互不重叠地盖在上面
        cross_pts = [
            px - half, py - al, px + half, py - al,
            px + half, py - half, px + al, py - half,
            px + al, py + half, px + half, py + half,
            px + half, py + al, px - half, py + al,
            px - half, py + half, px - al, py + half,
            px - al, py - half, px - half, py - half,
        ]
        self.pads["cross"] = cv.create_polygon(
            [self.X(v) for v in cross_pts], outline=P["line"], fill="",
            width=self.LW(), joinstyle="round")
        for k, (rx1, ry1, rx2, ry2) in {
            "dpad_u": (px - half, py - al, px + half, py - half),
            "dpad_d": (px - half, py + half, px + half, py + al),
            "dpad_l": (px - al, py - half, px - half, py + half),
            "dpad_r": (px + half, py - half, px + al, py + half),
        }.items():
            self.pads[k] = cv.create_rectangle(
                self.X(rx1), self.X(ry1), self.X(rx2), self.X(ry2),
                fill=P["fill_hi"] or P["slot"], outline="", state="hidden")

        for key, (cx, cy, w, h) in CENTRAL.items():
            if key == "guide":
                self.rings["guide"] = self.oval(cx, cy, w, P["line"],
                                                self.LW(1.2))
                self.labels["guide"] = [cv.create_text(
                    self.X(cx), self.X(cy), text="G", fill=P["text"],
                    font=(self.FONT, self.FS(self.BTN_SIZE)))]
            else:
                self.pads[key] = self.rrect(cx - w / 2, cy - h / 2,
                                            cx + w / 2, cy + h / 2, 6,
                                            outline=P["line"], width=self.LW(),
                                            fill="")
                self.labels[key] = [cv.create_text(
                    self.X(cx), self.X(cy),
                    text="VIEW" if key == "view" else "MENU",
                    fill=P["text"], font=(self.FONT, self.FS(9)))]

        self.hint = [cv.create_text(
            self.X(BASE_W / 2), self.X(316), text="PRESS ANY BUTTON",
            fill=P["text_dim"], font=(self.FONT, self.FS(10)))]

        self.apply(0, 0, 0, 0.0, 0.0, 0.0, 0.0, False)

    # --- 状态更新 ---------------------------------------------------
    def _paint(self, key, on):
        cv, P = self.cv, self.P
        cv.itemconfig(self.rings[key],
                      outline=P["line_hi"] if on else P["line"],
                      fill=P["fill_hi"] if on else "")
        for i in self.labels[key]:
            cv.itemconfig(i, fill=P["text_hi"] if on else P["text"])

    def apply(self, btn, lt, rt, lx, ly, rx, ry, connected):
        cv, P = self.cv, self.P
        key = (btn, lt // 4, rt // 4, round(lx, 1), round(ly, 1),
               round(rx, 1), round(ry, 1), connected)
        if key == self.last:
            return
        self.last = key

        for k in ABXY:
            self._paint(k, bool(btn & BTN_BITS[k]))

        dpad_keys = ("dpad_u", "dpad_d", "dpad_l", "dpad_r")
        for k in dpad_keys:
            cv.itemconfig(self.pads[k],
                          state="normal" if btn & BTN_BITS[k] else "hidden")
        any_dpad = any(btn & BTN_BITS[k] for k in dpad_keys)
        cv.itemconfig(self.pads["cross"],
                      outline=P["line_hi"] if any_dpad else P["line"])

        for name in ("lb", "rb"):
            on = bool(btn & BTN_BITS[name])
            cv.itemconfig(self.bars[name][0],
                          outline=P["line_hi"] if on else P["line"],
                          fill=P["fill_hi"] if on else "")

        for name in ("view", "menu"):
            on = bool(btn & BTN_BITS[name])
            cv.itemconfig(self.pads[name],
                          outline=P["line_hi"] if on else P["line"],
                          fill=P["fill_hi"] if on else "")
            for i in self.labels[name]:
                cv.itemconfig(i, fill=P["text_hi"] if on else P["text"])

        on = bool(btn & BTN_BITS["guide"])
        cv.itemconfig(self.rings["guide"],
                      outline=P["line_hi"] if on else P["line"],
                      fill=P["fill_hi"] if on else "")
        for i in self.labels["guide"]:
            cv.itemconfig(i, fill=P["text_hi"] if on else P["text"])

        for name in ("lt", "rt"):
            val = lt if name == "lt" else rt
            frac = max(0.0, min(1.0, val / 255.0))
            _, fill, x1, y1, x2, y2, r = self.bars[name]
            if BARS[name]["dir"] == "rtl":
                fx1, fx2 = x2 - (x2 - x1) * frac, x2
            else:
                fx1, fx2 = x1, x1 + (x2 - x1) * frac
            rr = min(r, (fx2 - fx1) / 2.0)
            pts = [
                fx1 + rr, y1, fx2 - rr, y1, fx2, y1, fx2, y1 + rr,
                fx2, y2 - rr, fx2, y2, fx2 - rr, y2,
                fx1 + rr, y2, fx1, y2, fx1, y2 - rr,
                fx1, y1 + rr, fx1, y1, fx1 + rr, y1,
            ]
            cv.coords(fill, *[self.X(v) for v in pts])
            cv.itemconfig(fill, fill=P["accent_hi"] if frac >= 0.99
                          else P["accent"])
            cv.itemconfig(self.rings[name + "_val"],
                          text=str(int(round(frac * 100))))

        for name, bit in (("ls", 0x0040), ("rs", 0x0080)):
            on = bool(btn & bit)
            cv.itemconfig(self.caps[name],
                          fill=P["accent_hi"] if on else P["accent"],
                          outline=P["line_hi"] if on else P["accent_hi"])
            cv.itemconfig(self.sticks[name][3],
                          fill=P["text"] if on else P["text_dim"])

        for name in ("ls", "rs"):
            cx, cy, ro, _ = self.sticks[name]
            vx, vy = (lx, ly) if name == "ls" else (rx, ry)
            span = ro - CAP_R - 2
            nx = self._curve(vx) * span
            ny = self._curve(vy) * span
            if abs(nx - self.cap[name][0]) < 0.6 and \
                    abs(ny - self.cap[name][1]) < 0.6:
                continue
            self.cap[name] = (nx, ny)
            cv.coords(self.caps[name],
                      self.X(cx + nx - CAP_R), self.X(cy + ny - CAP_R),
                      self.X(cx + nx + CAP_R), self.X(cy + ny + CAP_R))

        state = "hidden" if connected else "normal"
        for i in self.hint:
            cv.itemconfig(i, state=state)

    @staticmethod
    def _curve(v, dead=0.16):
        if abs(v) < dead:
            return 0.0
        s = 1.0 if v > 0 else -1.0
        return s * min(1.0, (abs(v) - dead) / (1.0 - dead))
