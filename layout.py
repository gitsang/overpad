# -*- coding: utf-8 -*-
"""
OverPad 像素几何与调色板

所有图形都在 104x86 的网格上定义，坐标单位是"格"，
渲染时乘以 scale 得到屏幕像素，保证每个色块都是整数倍缩放、零抗锯齿。
"""

from __future__ import annotations

import struct
import zlib

GW, GH = 104, 86

KEY_COLOR = "#ff00fe"

C = {
    "outer":     "#7983B0",
    "outline":   "#0B0C12",
    "body":      "#333852",
    "body_hi":   "#39405E",
    "body_lo":   "#282C42",
    "well":      "#1C2030",
    "btn_off":   "#22263A",
    "lbl_off":   "#8E96BC",
    "lbl_on":    "#0A0B10",
    "a":         "#4FBF5B",
    "b":         "#E2544F",
    "x":         "#4A90E2",
    "y":         "#EBC94A",
    "shoulder":  "#8E99BF",
    "shoulder_off": "#22263A",
    "guide":     "#AEB8D8",
    "stick":     "#454C70",
    "stick_on":  "#7C8CC0",
    "meter_bg":  "#262B3E",
    "meter_fg":  "#F0A63C",
    "meter_max": "#E2544F",
    "tick":      "#4A5278",
    "text":      "#C6CCE0",
}

GLYPHS = {
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "L": ("100", "100", "100", "100", "111"),
    "R": ("110", "101", "110", "101", "101"),
    "T": ("111", "010", "010", "010", "010"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
}

ABXY = {
    "y": (73, 34, C["y"]),
    "b": (82, 43, C["b"]),
    "a": (73, 52, C["a"]),
    "x": (64, 43, C["x"]),
}

DPAD = {
    "dpad_u": (29, 50, 33, 57),
    "dpad_d": (29, 57, 33, 64),
    "dpad_l": (24, 55, 29, 59),
    "dpad_r": (33, 55, 38, 59),
}

TRIGGERS = {
    "lt": dict(box=(8, 2, 21, 26), fill=(9, 9, 20, 25), label="LT", lx=11, ly=3),
    "rt": dict(box=(83, 2, 96, 26), fill=(84, 9, 95, 25), label="RT", lx=86, ly=3),
}

SHOULDERS = {
    "lb": dict(box=(28, 19, 46, 26), label="LB", lx=33, ly=20),
    "rb": dict(box=(58, 19, 76, 26), label="RB", lx=63, ly=20),
}

LS = (31, 40)
RS = (57, 57)
GUIDE = (52, 31)

BTN_BITS = {
    "dpad_u": 0x0001, "dpad_d": 0x0002, "dpad_l": 0x0004, "dpad_r": 0x0008,
    "start": 0x0010, "back": 0x0020, "ls": 0x0040, "rs": 0x0080,
    "lb": 0x0100, "rb": 0x0200,
    "a": 0x1000, "b": 0x2000, "x": 0x4000, "y": 0x8000,
}

DEADZONE = 0.18
CAP_RANGE = 4.0


def ell(cx, cy, ex, ey, rx, ry):
    return ((cx - ex) / rx) ** 2 + ((cy - ey) / ry) ** 2 <= 1.0


def rrect(cx, cy, x1, y1, x2, y2, r):
    if cx < x1 or cx > x2 or cy < y1 or cy > y2:
        return False
    qx = min(max(cx, x1 + r), x2 - r)
    qy = min(max(cy, y1 + r), y2 - r)
    return (cx - qx) ** 2 + (cy - qy) ** 2 <= r * r


def body_cells():
    cells = set()
    for y in range(GH):
        for x in range(GW):
            cx, cy = x + 0.5, y + 0.5
            if not (rrect(cx, cy, 12, 26, 92, 70, 20)
                    or ell(cx, cy, 23, 68, 14, 15)
                    or ell(cx, cy, 81, 68, 14, 15)):
                continue
            if ell(cx, cy, 52, 78, 22, 14):
                continue
            cells.add((x, y))
    return cells


def to_runs(cells):
    rows = {}
    for (x, y) in cells:
        rows.setdefault(y, []).append(x)
    out = []
    for y in sorted(rows):
        xs = sorted(rows[y])
        s = p = xs[0]
        for x in xs[1:]:
            if x == p + 1:
                p = x
            else:
                out.append((s, y, p + 1, y + 1))
                s = p = x
        out.append((s, y, p + 1, y + 1))
    return out


def edge_of(cells):
    out = set()
    for (x, y) in cells:
        if ((x + 1, y) not in cells or (x - 1, y) not in cells
                or (x, y + 1) not in cells or (x, y - 1) not in cells):
            out.add((x, y))
    return out


def outer_ring(cells):
    out = set()
    for (x, y) in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (x + dx, y + dy)
                if p in cells:
                    continue
                if 0 <= p[0] < GW and 0 <= p[1] < GH:
                    out.add(p)
    return out


def disc_runs(cx, cy, r):
    out = []
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        xs = [x for x in range(int(cx - r) - 1, int(cx + r) + 2)
              if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r]
        if xs:
            out.append((min(xs), y, max(xs) + 1, y + 1))
    return out


def text_runs(text, gx, gy):
    out = []
    cx = gx
    for ch in text:
        g = GLYPHS.get(ch.upper())
        if not g:
            cx += 4
            continue
        for ry, row in enumerate(g):
            start = None
            for rx, c in enumerate(row):
                if c == "1" and start is None:
                    start = rx
                elif c != "1" and start is not None:
                    out.append((cx + start, gy + ry, cx + rx, gy + ry + 1))
                    start = None
            if start is not None:
                out.append((cx + start, gy + ry, cx + len(row), gy + ry + 1))
        cx += 4
    return out


def ring(cx, cy, r, color, edge_color):
    """带 1 格描边的圆：返回 [(rect, color), ...]"""
    out = [(q, edge_color) for q in disc_runs(cx, cy, r + 0.65)]
    out += [(q, color) for q in disc_runs(cx, cy, r)]
    return out


def boxed(x1, y1, x2, y2, color, edge_color):
    return [((x1 - 1, y1 - 1, x2 + 1, y2 + 1), edge_color), ((x1, y1, x2, y2), color)]


def stick_delta(value, span=CAP_RANGE):
    if abs(value) < DEADZONE:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    norm = (abs(value) - DEADZONE) / (1.0 - DEADZONE)
    return sign * min(norm, 1.0) * span


def frame_ops(btn, lt, rt, lx, ly, rx, ry, cells=None, edges=None):
    """生成整帧绘制指令 [(rect, color)]，rect 为网格坐标。
    供 canvas 首帧与 PNG 预览共用。"""
    if cells is None:
        cells = body_cells()
    if edges is None:
        edges = edge_of(cells)
    inner = cells - edges
    ops = []

    for run in to_runs(outer_ring(cells)):
        ops.append((run, C["outer"]))
    for run in to_runs(inner):
        ops.append((run, C["body_hi"] if run[1] < 36 else C["body"]))
    for run in to_runs(edges):
        ops.append((run, C["outline"]))

    cross = set()
    for k, (x1, y1, x2, y2) in DPAD.items():
        on = btn & BTN_BITS[k]
        ops.append(((x1, y1, x2, y2), C["shoulder"] if on else C["btn_off"]))
        for gy in range(y1, y2):
            for gx in range(x1, x2):
                cross.add((gx, gy))
    for run in to_runs(edge_of(cross)):
        ops.append((run, C["outline"]))

    for k, (cx, cy, col) in ABXY.items():
        on = btn & BTN_BITS[k]
        for q, c2 in ring(cx, cy, 4, col if on else C["btn_off"], C["outline"]):
            ops.append((q, c2))
        lc = C["lbl_on"] if on else C["lbl_off"]
        for q in text_runs(k, cx - 1, cy - 2):
            ops.append((q, lc))

    for q, c2 in ring(GUIDE[0], GUIDE[1], 3, C["guide"], C["outline"]):
        ops.append((q, c2))

    for name, (sx, sy) in (("ls", LS), ("rs", RS)):
        on = btn & BTN_BITS[name]
        for q, c2 in ring(sx, sy, 10, C["well"], C["outline"]):
            ops.append((q, c2))
        ox = int(round(stick_delta(lx if name == "ls" else rx)))
        oy = int(round(stick_delta(ly if name == "ls" else ry)))
        for q in disc_runs(sx + ox, sy + oy, 6):
            ops.append((q, C["stick_on"] if on else C["stick"]))

    for name, cfg in TRIGGERS.items():
        x1, y1, x2, y2 = cfg["box"]
        for q, c2 in boxed(x1, y1, x2, y2, C["meter_bg"], C["outline"]):
            ops.append((q, c2))
        fx1, fy1, fx2, fy2 = cfg["fill"]
        val = lt if name == "lt" else rt
        frac = max(0.0, min(1.0, val / 255.0))
        hh = int(round(frac * (fy2 - fy1)))
        if hh > 0:
            col = C["meter_max"] if frac >= 0.99 else C["meter_fg"]
            ops.append(((fx1, fy2 - hh, fx2, fy2), col))
        for t in range(1, 4):
            ty = fy1 + int((fy2 - fy1) * t / 4)
            ops.append(((fx1, ty, fx2, ty + 1), C["tick"]))
        for q in text_runs(cfg["label"], cfg["lx"], cfg["ly"]):
            ops.append((q, C["text"]))

    for name, cfg in SHOULDERS.items():
        x1, y1, x2, y2 = cfg["box"]
        on = btn & BTN_BITS[name]
        for q, c2 in boxed(x1, y1, x2, y2,
                           C["shoulder"] if on else C["shoulder_off"], C["outline"]):
            ops.append((q, c2))
        for q in text_runs(cfg["label"], cfg["lx"], cfg["ly"]):
            ops.append((q, C["lbl_on"] if on else C["lbl_off"]))

    return ops


def png_write(path, w, h, pixels):
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw.extend(pixels[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(chunk(b"IEND", b""))


def preview(path, scale=4, state=None, bg=(52, 54, 64)):
    st = dict(btn=0x1000, lt=190, rt=60, lx=0.42, ly=-0.55, rx=0.2, ry=0.3)
    if state:
        st.update(state)
    W, H = GW * scale, GH * scale
    buf = bytearray(bytes(bg) + b"\xff") * (W * H)

    def fill(q, hexc):
        x1, y1, x2, y2 = q
        r = int(hexc[1:3], 16)
        g = int(hexc[3:5], 16)
        b = int(hexc[5:7], 16)
        for gy in range(max(0, y1), min(GH, y2)):
            py0 = gy * scale
            for gx in range(max(0, x1), min(GW, x2)):
                px0 = gx * scale
                for sy in range(scale):
                    base = ((py0 + sy) * W + px0) * 4
                    for sx in range(scale):
                        i = base + sx * 4
                        buf[i] = r
                        buf[i + 1] = g
                        buf[i + 2] = b

    for q, col in frame_ops(st["btn"], st["lt"], st["rt"],
                            st["lx"], st["ly"], st["rx"], st["ry"]):
        fill(q, col)

    png_write(path, W, H, buf)
    return path
