# -*- coding: utf-8 -*-
"""HUD 主题：现代极简线框风格。

图形用 Tk 原生图元绘制。Tk 在 Windows 上走 GDI 硬边光栅化，配合近黑色键
透明不会在描边周围产生彩色过渡像素。圆角用平滑多边形实现。
"""

from __future__ import annotations

BASE_W, BASE_H = 416, 344

LINE = "#8C8C98"
LINE_HI = "#FFFFFF"
TEXT = "#C8C8D2"
TEXT_HI = "#FFFFFF"
TEXT_DIM = "#7E7E8A"
ACCENT = "#C23A6E"
ACCENT_HI = "#F06BA0"
FILL_HI = "#2E2E3A"
SLOT = "#1E1E26"

FONT = "Segoe UI"

# box = 条的矩形范围；meter=True 的条带进度填充，dir 指定填充方向
BARS = {
    "lb": dict(box=(6, 8, 52, 30), label="LB", meter=False),
    "lt": dict(box=(58, 8, 154, 30), label="LT", meter=True, dir="ltr",
               val=(162, 19), anchor="w"),
    "rt": dict(box=(262, 8, 358, 30), label="RT", meter=True, dir="rtl",
               val=(254, 19), anchor="e"),
    "rb": dict(box=(364, 8, 410, 30), label="RB", meter=False),
}

LS = (100, 110)
LS_RING = 44
RS = (316, 220)
RS_RING = 40
CAP_R = 11

ABXY = {
    "y": (316, 68),
    "b": (342, 94),
    "a": (316, 120),
    "x": (290, 94),
}
BTN_R = 16

PAD = (80, 232)
PAD_ARM = (26, 40)

CENTRAL = {
    "view": (208, 134, 64, 22),
    "guide": (208, 168, 16, 0),
    "menu": (208, 200, 64, 22),
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

    def __init__(self, cv, zoom=1):
        self.cv = cv
        self.z = zoom
        self.last = None
        self.cap = {"ls": (0.0, 0.0), "rs": (0.0, 0.0)}
        self.build()

    def P(self, v):
        return int(round(v * self.z))

    def LW(self, v=1.0):
        return max(1, int(round(v * self.z)))

    def FS(self, px):
        return -max(7, int(round(px * self.z)))

    def rrect(self, x1, y1, x2, y2, r, **kw):
        """平滑多边形画圆角矩形"""
        r = min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0)
        pts = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1, x1 + r, y1,
        ]
        return self.cv.create_polygon([self.P(v) for v in pts],
                                      smooth=True, **kw)

    def build(self):
        cv = self.cv
        self.rings = {}
        self.labels = {}
        self.bars = {}
        self.pads = {}
        self.caps = {}
        self.sticks = {}

        for name, cfg in BARS.items():
            x1, y1, x2, y2 = cfg["box"]
            r = min(8, (y2 - y1) / 2.0)
            if cfg["meter"]:
                self.rrect(x1, y1, x2, y2, r, fill=SLOT, outline=LINE,
                           width=self.LW())
                fill = self.rrect(x1, y1, x1, y2, r, fill=ACCENT, outline="")
                self.bars[name] = (None, fill, x1, y1, x2, y2, r)
            else:
                ring = self.rrect(x1, y1, x2, y2, r, fill="", outline=LINE,
                                  width=self.LW())
                self.bars[name] = (ring, None, x1, y1, x2, y2, r)
            cv.create_text(self.P((x1 + x2) / 2), self.P((y1 + y2) / 2),
                           text=cfg["label"], fill=TEXT_HI,
                           font=(FONT, self.FS(10)))

        for name in ("lt", "rt"):
            cfg = BARS[name]
            vx, vy = cfg["val"]
            self.rings[name + "_val"] = cv.create_text(
                self.P(vx), self.P(vy), text="0", fill=TEXT_HI,
                anchor=cfg["anchor"], font=(FONT, self.FS(12)))

        for name, (cx, cy) in (("ls", LS), ("rs", RS)):
            ro = LS_RING if name == "ls" else RS_RING
            cv.create_oval(self.P(cx - ro), self.P(cy - ro),
                           self.P(cx + ro), self.P(cy + ro),
                           outline=LINE, width=self.LW(1.2), fill="")
            cap = cv.create_oval(self.P(cx - CAP_R), self.P(cy - CAP_R),
                                 self.P(cx + CAP_R), self.P(cy + CAP_R),
                                 fill=ACCENT, outline=ACCENT_HI,
                                 width=self.LW(0.8))
            lbl = cv.create_text(self.P(cx), self.P(cy + ro + 14),
                                 text="L3" if name == "ls" else "R3",
                                 fill=TEXT_DIM, font=(FONT, self.FS(9)))
            self.caps[name] = cap
            self.sticks[name] = (cx, cy, ro, lbl)

        for k, (cx, cy) in ABXY.items():
            ring = cv.create_oval(self.P(cx - BTN_R), self.P(cy - BTN_R),
                                  self.P(cx + BTN_R), self.P(cy + BTN_R),
                                  outline=LINE, width=self.LW(1.2), fill="")
            lbl = cv.create_text(self.P(cx), self.P(cy), text=k.upper(),
                                 fill=TEXT, font=(FONT, self.FS(11)))
            self.rings[k] = ring
            self.labels[k] = [lbl]

        px, py = PAD
        aw, al = PAD_ARM
        gap = 7
        for k, (rx1, ry1, rx2, ry2) in {
            "dpad_u": (px - aw // 2, py - al, px + aw // 2, py - gap),
            "dpad_d": (px - aw // 2, py + gap, px + aw // 2, py + al),
            "dpad_l": (px - al, py - aw // 2, px - gap, py + aw // 2),
            "dpad_r": (px + gap, py - aw // 2, px + al, py + aw // 2),
        }.items():
            self.pads[k] = self.rrect(rx1, ry1, rx2, ry2, 4, fill="",
                                      outline=LINE, width=self.LW())

        for key, (cx, cy, w, h) in CENTRAL.items():
            if key == "guide":
                self.rings["guide"] = cv.create_oval(
                    self.P(cx - w), self.P(cy - w),
                    self.P(cx + w), self.P(cy + w),
                    outline=LINE, width=self.LW(1.2), fill="")
                self.labels["guide"] = [cv.create_text(
                    self.P(cx), self.P(cy), text="G", fill=TEXT,
                    font=(FONT, self.FS(11)))]
            else:
                self.pads[key] = self.rrect(cx - w / 2, cy - h / 2,
                                            cx + w / 2, cy + h / 2, 6,
                                            outline=LINE, width=self.LW(),
                                            fill="")
                self.labels[key] = [cv.create_text(
                    self.P(cx), self.P(cy),
                    text="VIEW" if key == "view" else "MENU",
                    fill=TEXT, font=(FONT, self.FS(9)))]

        self.hint = [cv.create_text(
            self.P(BASE_W / 2), self.P(318), text="PRESS ANY BUTTON",
            fill=TEXT_DIM, font=(FONT, self.FS(10)))]

        self.apply(0, 0, 0, 0.0, 0.0, 0.0, 0.0, False)

    def _paint(self, key, on, with_label=True):
        cv = self.cv
        cv.itemconfig(self.rings[key], outline=LINE_HI if on else LINE,
                      fill=FILL_HI if on else "")
        if with_label:
            for i in self.labels[key]:
                cv.itemconfig(i, fill=TEXT_HI if on else TEXT)

    def apply(self, btn, lt, rt, lx, ly, rx, ry, connected):
        cv = self.cv
        key = (btn, lt // 4, rt // 4, round(lx, 1), round(ly, 1),
               round(rx, 1), round(ry, 1), connected)
        if key == self.last:
            return
        self.last = key

        for k in ABXY:
            self._paint(k, bool(btn & BTN_BITS[k]))

        for k in ("dpad_u", "dpad_d", "dpad_l", "dpad_r"):
            on = bool(btn & BTN_BITS[k])
            cv.itemconfig(self.pads[k], outline=LINE_HI if on else LINE,
                          fill=FILL_HI if on else "")

        for name in ("lb", "rb"):
            on = bool(btn & BTN_BITS[name])
            cv.itemconfig(self.bars[name][0], outline=LINE_HI if on else LINE,
                          fill=FILL_HI if on else "")

        for name in ("view", "menu"):
            on = bool(btn & BTN_BITS[name])
            cv.itemconfig(self.pads[name], outline=LINE_HI if on else LINE,
                          fill=FILL_HI if on else "")
            for i in self.labels[name]:
                cv.itemconfig(i, fill=TEXT_HI if on else TEXT)

        on = bool(btn & BTN_BITS["guide"])
        cv.itemconfig(self.rings["guide"], outline=LINE_HI if on else LINE,
                      fill=FILL_HI if on else "")
        for i in self.labels["guide"]:
            cv.itemconfig(i, fill=TEXT_HI if on else TEXT)

        for name in ("lt", "rt"):
            val = lt if name == "lt" else rt
            frac = max(0.0, min(1.0, val / 255.0))
            ring, fill, x1, y1, x2, y2, r = self.bars[name]
            if BARS[name]["dir"] == "rtl":
                fx1 = x2 - (x2 - x1) * frac
                fx2 = x2
            else:
                fx1 = x1
                fx2 = x1 + (x2 - x1) * frac
            rr = min(r, (fx2 - fx1) / 2.0)
            pts = [
                fx1 + rr, y1, fx2 - rr, y1, fx2, y1, fx2, y1 + rr,
                fx2, y2 - rr, fx2, y2, fx2 - rr, y2,
                fx1 + rr, y2, fx1, y2, fx1, y2 - rr,
                fx1, y1 + rr, fx1, y1, fx1 + rr, y1,
            ]
            cv.coords(fill, *[self.P(v) for v in pts])
            cv.itemconfig(fill, fill=ACCENT_HI if frac >= 0.99 else ACCENT)
            cv.itemconfig(self.rings[name + "_val"],
                          text=str(int(round(frac * 100))))

        for name, bit in (("ls", 0x0040), ("rs", 0x0080)):
            on = bool(btn & bit)
            cv.itemconfig(self.caps[name], fill=ACCENT_HI if on else ACCENT)
            cv.itemconfig(self.sticks[name][3],
                          fill=TEXT if on else TEXT_DIM)

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
                      self.P(cx + nx - CAP_R), self.P(cy + ny - CAP_R),
                      self.P(cx + nx + CAP_R), self.P(cy + ny + CAP_R))

        state = "hidden" if connected else "normal"
        for i in self.hint:
            cv.itemconfig(i, state=state)

    @staticmethod
    def _curve(v, dead=0.16):
        if abs(v) < dead:
            return 0.0
        s = 1.0 if v > 0 else -1.0
        return s * min(1.0, (abs(v) - dead) / (1.0 - dead))
