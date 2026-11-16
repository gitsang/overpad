# -*- coding: utf-8 -*-
"""从像素几何生成 exe 图标（多尺寸 ICO，无第三方依赖）"""
import struct

import layout as L

SIZES = (16, 32, 48, 64, 128, 256)


def raster(size):
    ops = L.frame_ops(0x1000, 220, 0, 0.4, -0.5, 0.0, 0.0)
    grid = [[(0, 0, 0, 0)] * L.GW for _ in range(L.GH)]
    for (x1, y1, x2, y2), hexc in ops:
        r = int(hexc[1:3], 16)
        g = int(hexc[3:5], 16)
        b = int(hexc[5:7], 16)
        for gy in range(max(0, y1), min(L.GH, y2)):
            for gx in range(max(0, x1), min(L.GW, x2)):
                grid[gy][gx] = (r, g, b, 255)

    # 内容包围盒，居中裁成正方形
    minx, maxx, miny, maxy = L.GW, 0, L.GH, 0
    for y in range(L.GH):
        for x in range(L.GW):
            if grid[y][x][3]:
                minx = min(minx, x)
                maxx = max(maxx, x)
                miny = min(miny, y)
                maxy = max(maxy, y)
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    span = max(maxx - minx, maxy - miny) + 3

    out = bytearray(size * size * 4)
    for py in range(size):
        for pxx in range(size):
            gx = int(round(cx - span / 2 + (pxx + 0.5) * span / size))
            gy = int(round(cy - span / 2 + (py + 0.5) * span / size))
            if not (0 <= gx < L.GW and 0 <= gy < L.GH):
                continue
            r, g, b, a = grid[gy][gx]
            i = (py * size + pxx) * 4
            out[i:i + 4] = bytes((b, g, r, a))
    return bytes(out)


def bmp_entry(size):
    """返回 ICO 中的 DIB 数据（BITMAPINFOHEADER + BGRA + AND mask）"""
    pixels = raster(size)
    hdr = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                      len(pixels), 0, 0, 0, 0)
    rows = []
    for y in range(size - 1, -1, -1):
        rows.append(pixels[y * size * 4:(y + 1) * size * 4])
    body = b"".join(rows)
    mask_row = ((size + 31) // 32) * 4
    mask = b"\x00" * (mask_row * size)
    return hdr + body + mask


def make(path):
    entries = [(s, bmp_entry(s)) for s in SIZES]
    n = len(entries)
    header = struct.pack("<HHH", 0, 1, n)
    offset = 6 + 16 * n
    dirs = b""
    blobs = b""
    for size, data in entries:
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        dirs += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        blobs += data
    with open(path, "wb") as f:
        f.write(header + dirs + blobs)
    return path


if __name__ == "__main__":
    print(make("app.ico"))
