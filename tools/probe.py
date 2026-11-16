# -*- coding: utf-8 -*-
"""枚举窗口，调试用"""
import ctypes
import ctypes.wintypes as wt

user32 = ctypes.windll.user32

EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


class RECT(ctypes.Structure):
    _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                ("right", wt.LONG), ("bottom", wt.LONG)]


found = []


def cb(hwnd, lparam):
    n = user32.GetWindowTextLengthW(hwnd)
    if n:
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value
        if "Pixel" in title or "像素" in title:
            r = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.append((title, hwnd, r.left, r.top,
                          r.right - r.left, r.bottom - r.top,
                          bool(user32.IsWindowVisible(hwnd)), pid.value))
    return True


user32.EnumWindows(EnumProc(cb), 0)
print("screen:", user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
if not found:
    print("no OverPad window found")
for f in found:
    print("title=%r hwnd=%s rect=(%d,%d,%d,%d) visible=%s pid=%s" % f)
