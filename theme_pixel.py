# -*- coding: utf-8 -*-
"""像素主题：在 104x86 网格上绘制，每个网格单元按整数倍放大成色块。

像素画本身没有半透明像素，配合 Windows 色键透明可以做到边缘零毛边。
"""

from __future__ import annotations

import layout as L

GW, GH = L.GW, L.GH
UNIT = 4


class PixelTheme:
    BASE_W = GW * UNIT
    BASE_H = GH * UNIT

    def __init__(self, cv, zoom=1):
        self.cv = cv
        self.z = zoom
        self.px = UNIT * zoom
        self.last_btn = -1
        self.cap_off = {"ls": (0, 0), "rs": (0, 0)}
        self.meter_hh = {"lt": -1, "rt": -1}
        self.build()

    def sr(self, rect):
        x1, y1, x2, y2 = rect
        p = self.px
        return (x1 * p, y1 * p, x2 * p, y2 * p)

    def rect(self, rect, color, tags=None):
        return self.cv.create_rectangle(*self.sr(rect), fill=color,
                                        outline="", tags=tags or ())

    def build(self):
        cv = self.cv
        cv.delete("all")
        cells = L.body_cells()
        edges = L.edge_of(cells)
        inner = cells - edges

        for run in L.to_runs(L.outer_ring(cells)):
            self.rect(run, L.C["outer"])
        for run in L.to_runs(inner):
            col = L.C["body_hi"] if run[1] < 36 else L.C["body"]
            self.rect(run, col)
        for run in L.to_runs(edges):
            self.rect(run, L.C["outline"])

        for k, (x1, y1, x2, y2) in L.DPAD.items():
            self.rect((x1, y1, x2, y2), L.C["btn_off"], tags=("c_" + k,))
        cross = set()
        for (x1, y1, x2, y2) in L.DPAD.values():
            for gy in range(y1, y2):
                for gx in range(x1, x2):
                    cross.add((gx, gy))
        for run in L.to_runs(L.edge_of(cross)):
            self.rect(run, L.C["outline"])

        for k, (cx, cy, col) in L.ABXY.items():
            for q in L.disc_runs(cx, cy, 4.65):
                self.rect(q, L.C["outline"])
            for q in L.disc_runs(cx, cy, 4):
                self.rect(q, L.C["btn_off"], tags=("c_" + k,))
            for q in L.text_runs(k, cx - 1, cy - 2):
                self.rect(q, L.C["lbl_off"], tags=("t_" + k,))

        for q in L.disc_runs(L.GUIDE[0], L.GUIDE[1], 3.65):
            self.rect(q, L.C["outline"])
        for q in L.disc_runs(L.GUIDE[0], L.GUIDE[1], 3):
            self.rect(q, L.C["guide"], tags=("guide",))

        self.meter_ids = {}
        for name, (sx, sy) in (("ls", L.LS), ("rs", L.RS)):
            for q in L.disc_runs(sx, sy, 10.65):
                self.rect(q, L.C["outline"])
            for q in L.disc_runs(sx, sy, 10):
                self.rect(q, L.C["well"])
            for q in L.disc_runs(sx, sy, 6):
                self.rect(q, L.C["stick"],
                          tags=("cap_" + name, "capfill_" + name))

        for name, cfg in L.TRIGGERS.items():
            x1, y1, x2, y2 = cfg["box"]
            self.rect((x1 - 1, y1 - 1, x2 + 1, y2 + 1), L.C["outline"])
            self.rect((x1, y1, x2, y2), L.C["meter_bg"])
            fx1, fy1, fx2, fy2 = cfg["fill"]
            self.meter_ids[name] = cv.create_rectangle(
                fx1 * self.px, (fy2 - 1) * self.px, fx2 * self.px, fy2 * self.px,
                fill=L.C["meter_fg"], outline="", state="hidden")
            for t in range(1, 4):
                ty = fy1 + int((fy2 - fy1) * t / 4)
                self.rect((fx1, ty, fx2, ty + 1), L.C["tick"])
            for q in L.text_runs(cfg["label"], cfg["lx"], cfg["ly"]):
                self.rect(q, L.C["text"])

        for name, cfg in L.SHOULDERS.items():
            x1, y1, x2, y2 = cfg["box"]
            self.rect((x1 - 1, y1 - 1, x2 + 1, y2 + 1), L.C["outline"])
            self.rect((x1, y1, x2, y2), L.C["shoulder_off"],
                      tags=("s_" + name,))
            for q in L.text_runs(cfg["label"], cfg["lx"], cfg["ly"]):
                self.rect(q, L.C["lbl_off"], tags=("st_" + name,))

    def apply(self, btn, lt, rt, lx, ly, rx, ry, connected):
        cv = self.cv
        if not connected:
            cv.itemconfig("guide", fill="#6E3346")
        else:
            cv.itemconfig("guide", fill=L.C["guide"])

        if btn != self.last_btn:
            self.last_btn = btn
            for k, (cx, cy, col) in L.ABXY.items():
                on = bool(btn & L.BTN_BITS[k])
                cv.itemconfig("c_" + k, fill=col if on else L.C["btn_off"])
                cv.itemconfig("t_" + k,
                              fill=L.C["lbl_on"] if on else L.C["lbl_off"])
            for k in L.DPAD:
                on = bool(btn & L.BTN_BITS[k])
                cv.itemconfig("c_" + k,
                              fill=L.C["shoulder"] if on else L.C["btn_off"])
            for k in L.SHOULDERS:
                on = bool(btn & L.BTN_BITS[k])
                cv.itemconfig("s_" + k,
                              fill=L.C["shoulder"] if on else L.C["shoulder_off"])
                cv.itemconfig("st_" + k,
                              fill=L.C["lbl_on"] if on else L.C["lbl_off"])
            for name, bit in (("ls", 0x0040), ("rs", 0x0080)):
                on = bool(btn & bit)
                cv.itemconfig("capfill_" + name,
                              fill=L.C["stick_on"] if on else L.C["stick"])

        for name, (sx, sy), vx, vy in (("ls", L.LS, lx, ly),
                                       ("rs", L.RS, rx, ry)):
            ox = int(round(L.stick_delta(vx)))
            oy = int(round(L.stick_delta(vy)))
            if (ox, oy) != self.cap_off[name]:
                dx = (ox - self.cap_off[name][0]) * self.px
                dy = (oy - self.cap_off[name][1]) * self.px
                cv.move("cap_" + name, dx, dy)
                self.cap_off[name] = (ox, oy)

        for name, cfg in L.TRIGGERS.items():
            val = lt if name == "lt" else rt
            frac = max(0.0, min(1.0, val / 255.0))
            fx1, fy1, fx2, fy2 = cfg["fill"]
            hh = int(round(frac * (fy2 - fy1)))
            if hh == self.meter_hh[name]:
                continue
            self.meter_hh[name] = hh
            rid = self.meter_ids[name]
            if hh <= 0:
                cv.itemconfig(rid, state="hidden")
            else:
                col = L.C["meter_max"] if frac >= 0.99 else L.C["meter_fg"]
                cv.coords(rid, fx1 * self.px, (fy2 - hh) * self.px,
                          fx2 * self.px, fy2 * self.px)
                cv.itemconfig(rid, state="normal", fill=col)
