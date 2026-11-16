# -*- coding: utf-8 -*-
"""
OverPad - 手柄按键悬浮窗（多主题）

用法：
    python overpad.py            正常启动
    python overpad.py --demo     无手柄时演示动画
    python overpad.py --preview  生成像素主题预览图

全局快捷键：
    Ctrl+Alt+L   锁定 / 解锁（锁定后鼠标穿透）
    Ctrl+Alt+H   隐藏 / 显示
    Ctrl+Alt+T   切换主题
    Ctrl+Alt+↑   放大
    Ctrl+Alt+↓   缩小
    Ctrl+Alt+Q   退出
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk

import layout as L
from theme_hud import HudTheme
from theme_pixel import PixelTheme

APP = "OverPad"
__version__ = "1.0.0"
CONFIG_NAME = "overpad.json"

THEMES = {"hud": HudTheme, "pixel": PixelTheme}
ZOOMS = (0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)

KEY_COLOR = "#010203"

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
GW_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
GA_ROOT = 2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CFG_PATH = os.path.join(app_dir(), CONFIG_NAME)

DEFAULT_CFG = {
    "theme": "hud",
    "zoom": None,
    "x": None,
    "y": None,
    "opacity": 1.0,
    "locked": False,
}


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    cfg.pop("scale", None)
    return cfg


def save_cfg(cfg):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def auto_zoom():
    """按系统 DPI 推一个视觉大小合适的缩放倍数"""
    try:
        u = ctypes.windll.user32
        hdc = u.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        u.ReleaseDC(0, hdc)
    except Exception:
        dpi = 96
    if not dpi or dpi < 48:
        dpi = 96
    z = dpi / 96.0
    return max(0.75, min(2.0, round(z * 4) / 4.0))


class _GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_ulong), ("Gamepad", _GAMEPAD)]


def _resolve_get_state(dll):
    """优先取 XInputGetStateEx（序号 100），它能返回 Guide 键；
    取不到时退回标准 XInputGetState（此时 Guide 不可用）。"""
    if dll is None:
        return None, False
    try:
        k32 = ctypes.windll.kernel32
        k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        k32.GetProcAddress.restype = ctypes.c_void_p
        addr = k32.GetProcAddress(ctypes.c_void_p(dll._handle),
                                  ctypes.c_void_p(100))
        if addr:
            proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_ulong,
                                       ctypes.POINTER(_STATE))
            return proto(addr), True
    except Exception:
        pass
    try:
        return dll.XInputGetState, False
    except AttributeError:
        return None, False


class PadReader(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.lock = threading.Lock()
        self.dll = None
        for name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
            try:
                self.dll = ctypes.WinDLL(name)
                break
            except OSError:
                continue
        self.get_state, self.has_guide = _resolve_get_state(self.dll)
        self.state = {"connected": False, "buttons": 0, "lt": 0, "rt": 0,
                      "lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}

    def run(self):
        if self.get_state is None:
            return
        st = _STATE()
        while True:
            try:
                ok = self.get_state(0, ctypes.byref(st)) == 0
            except Exception:
                ok = False
            if ok:
                g = st.Gamepad
                new = {"connected": True, "buttons": g.wButtons,
                       "lt": g.bLeftTrigger, "rt": g.bRightTrigger,
                       "lx": g.sThumbLX / 32768.0, "ly": -g.sThumbLY / 32768.0,
                       "rx": g.sThumbRX / 32768.0, "ry": -g.sThumbRY / 32768.0}
            else:
                new = {"connected": False, "buttons": 0, "lt": 0, "rt": 0,
                       "lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}
            with self.lock:
                self.state = new
            time.sleep(0.008)

    def read(self):
        with self.lock:
            return dict(self.state)


class DemoReader:
    """没有手柄时的演示输入源"""

    def __init__(self):
        self.t0 = time.time()

    def read(self):
        t = (time.time() - self.t0) % 9.0
        btn = 0
        lt = rt = 0
        lx = ly = rx = ry = 0.0
        if t < 1.2:
            btn = 0x1000
        elif t < 2.0:
            btn = 0x1000 | 0x0100
            lt = 200
        elif t < 3.0:
            btn = 0x0001
        elif t < 4.0:
            lx, ly = 0.75, -0.6
        elif t < 5.0:
            btn = 0x2000 | 0x0200
            rt = 255
        elif t < 5.7:
            btn = 0x2000
            rt = 150
        elif t < 6.3:
            lt = 110
        elif t < 6.0:
            btn = 0x4000
            ry = 0.8
        elif t < 6.6:
            btn = 0x8000
            lt = 90
            rt = 40
        elif t < 7.4:
            btn = 0x0020
        elif t < 8.1:
            btn = 0x0010
        elif t < 8.6:
            btn = 0x0400
        else:
            rx, ry = -0.7, 0.5
        return {"connected": True, "buttons": btn, "lt": lt, "rt": rt,
                "lx": lx, "ly": ly, "rx": rx, "ry": ry}

    def start(self):
        pass


def hotkey_worker(q):
    user32 = ctypes.windll.user32
    combos = [
        (1, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x4C, "lock"),    # L
        (2, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x48, "hide"),    # H
        (3, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x54, "theme"),   # T
        (4, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x26, "bigger"),  # Up
        (5, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x28, "smaller"), # Down
        (6, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 0x51, "quit"),    # Q
    ]
    ok = {}
    for hid, mod, vk, name in combos:
        try:
            if user32.RegisterHotKey(None, hid, mod, vk):
                ok[hid] = name
        except Exception:
            pass
    if not ok:
        return
    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY:
            name = ok.get(int(msg.wParam))
            if name:
                q.put(name)


class Overlay:
    def __init__(self, demo=False):
        self.cfg = load_cfg()
        name = self.cfg.get("theme")
        self.theme_name = name if name in THEMES else "hud"
        z = self.cfg.get("zoom")
        self.zoom = float(z) if z else auto_zoom()
        if demo:
            self.reader = DemoReader()
        else:
            self.reader = PadReader()
        self.reader.start()
        self.events = queue.Queue()
        self.hidden = False
        self.locked = bool(self.cfg.get("locked"))
        self.cur_alpha = -1.0
        self.beat = 0
        self._drag = None

        self.w, self.h = self.theme_size()
        self.pos = (0, 0)

        self.root = tk.Tk()
        self.root.title(APP)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=KEY_COLOR)
        self.root.geometry("%dx%d" % (self.w, self.h))
        self.cv = tk.Canvas(self.root, width=self.w, height=self.h,
                            bg=KEY_COLOR, highlightthickness=0, bd=0)
        self.cv.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.hwnd = self._hwnd()
        self.place_window()
        try:
            self.root.attributes("-transparentcolor", KEY_COLOR)
            self.root.attributes("-alpha", float(self.cfg.get("opacity", 1.0)))
        except Exception:
            pass

        self.theme = None
        self.rebuild()
        self.bind_events()
        if self.locked:
            self.set_click_through(True)
        self.cfg["theme"] = self.theme_name
        self.cfg["zoom"] = self.zoom
        save_cfg(self.cfg)
        threading.Thread(target=hotkey_worker, args=(self.events,),
                         daemon=True).start()
        self.root.after(16, self.tick)

    def theme_size(self):
        cls = THEMES[self.theme_name]
        return (int(round(cls.BASE_W * self.zoom)),
                int(round(cls.BASE_H * self.zoom)))

    def rebuild(self):
        self.w, self.h = self.theme_size()
        self.cv.delete("all")
        self.cv.configure(width=self.w, height=self.h)
        self.theme = THEMES[self.theme_name](self.cv, self.zoom)
        self.win_pos()

    def _hwnd(self):
        try:
            u = ctypes.windll.user32
            h = self.root.winfo_id()
            anc = u.GetAncestor(h, GA_ROOT)
            return anc or h
        except Exception:
            return self.root.winfo_id()

    def win_pos(self):
        """用 Win32 直接摆窗口，绕开 tk 在 DPI 缩放下的坐标问题"""
        try:
            u = ctypes.windll.user32
            u.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_uint]
            u.SetWindowPos.restype = ctypes.c_bool
            u.SetWindowPos(self.hwnd, None, int(self.pos[0]), int(self.pos[1]),
                           int(self.w), int(self.h),
                           SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        except Exception:
            pass

    def place_window(self):
        sw = ctypes.windll.user32.GetSystemMetrics(0)
        sh = ctypes.windll.user32.GetSystemMetrics(1)
        if sw <= 0:
            sw = self.root.winfo_screenwidth()
        if sh <= 0:
            sh = self.root.winfo_screenheight()
        x = self.cfg.get("x")
        y = self.cfg.get("y")
        if x is None:
            x = sw - self.w - 32
        if y is None:
            y = sh - self.h - 96
        x = max(-self.w + 60, min(int(x), sw - 60))
        y = max(0, min(int(y), sh - 60))
        self.pos = (int(x), int(y))
        self.win_pos()

    def tick(self):
        try:
            while True:
                self.handle_event(self.events.get_nowait())
        except queue.Empty:
            pass

        self.beat += 1
        if self.beat % 300 == 0 and not self.hidden:
            self.keep_top()

        st = self.reader.read()
        self.theme.apply(st["buttons"], st["lt"], st["rt"],
                         st["lx"], st["ly"], st["rx"], st["ry"],
                         st["connected"])

        want = (float(self.cfg.get("opacity", 1.0))
                * (1.0 if st["connected"] else 0.55))
        if abs(want - self.cur_alpha) > 0.01:
            self.cur_alpha = want
            try:
                self.root.attributes("-alpha", want)
            except Exception:
                pass

        self.root.after(16, self.tick)

    def handle_event(self, name):
        if name == "lock":
            self.set_click_through(not self.locked)
        elif name == "hide":
            self.toggle_hide()
        elif name == "theme":
            self.next_theme()
        elif name == "bigger":
            self.change_zoom(1)
        elif name == "smaller":
            self.change_zoom(-1)
        elif name == "quit":
            self.quit()

    def next_theme(self):
        keys = list(THEMES.keys())
        i = keys.index(self.theme_name)
        self.set_theme(keys[(i + 1) % len(keys)])

    def set_theme(self, name):
        if name not in THEMES or name == self.theme_name:
            return
        self.theme_name = name
        self.cfg["theme"] = name
        save_cfg(self.cfg)
        self.rebuild()

    def keep_top(self):
        try:
            u = ctypes.windll.user32
            u.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       ctypes.c_uint]
            u.SetWindowPos(self.hwnd, wt.HWND(-1), 0, 0, 0, 0,
                           SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        except Exception:
            pass

    def toggle_hide(self):
        if self.hidden:
            self.root.deiconify()
            self.root.attributes("-topmost", True)
            self.hidden = False
        else:
            self.root.withdraw()
            self.hidden = True

    def change_zoom(self, step):
        i = ZOOMS.index(self.zoom) if self.zoom in ZOOMS else 1
        i = max(0, min(len(ZOOMS) - 1, i + step))
        if ZOOMS[i] == self.zoom:
            return
        self.zoom = ZOOMS[i]
        self.cfg["zoom"] = self.zoom
        save_cfg(self.cfg)
        self.rebuild()

    def set_zoom(self, z):
        if z == self.zoom:
            return
        self.zoom = float(z)
        self.cfg["zoom"] = self.zoom
        save_cfg(self.cfg)
        self.rebuild()

    def set_click_through(self, on):
        self.locked = on
        self.cfg["locked"] = on
        save_cfg(self.cfg)
        try:
            u = ctypes.windll.user32
            ex = u.GetWindowLongW(self.hwnd, GW_EXSTYLE)
            if on:
                ex |= WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                ex &= ~WS_EX_TRANSPARENT
            u.SetWindowLongW(self.hwnd, GW_EXSTYLE, ex)
        except Exception:
            pass

    def bind_events(self):
        cv = self.cv

        def press(e):
            self._drag = (e.x_root - self.pos[0], e.y_root - self.pos[1])

        def move(e):
            if self._drag:
                self.pos = (e.x_root - self._drag[0], e.y_root - self._drag[1])
                self.win_pos()

        def release(e):
            if self._drag:
                self._drag = None
                self.cfg["x"] = self.pos[0]
                self.cfg["y"] = self.pos[1]
                save_cfg(self.cfg)

        cv.bind("<Button-1>", press)
        cv.bind("<B1-Motion>", move)
        cv.bind("<ButtonRelease-1>", release)
        cv.bind("<Button-3>", self.popup)
        self.root.bind("<Escape>", lambda e: self.quit())

    def popup(self, e):
        m = tk.Menu(self.root, tearoff=0)

        tsub = tk.Menu(m, tearoff=0)
        tv = tk.StringVar(value=self.theme_name)
        tsub.add_radiobutton(label="HUD 线框", value="hud", variable=tv,
                             command=lambda: self.set_theme("hud"))
        tsub.add_radiobutton(label="像素风", value="pixel", variable=tv,
                             command=lambda: self.set_theme("pixel"))
        m.add_cascade(label="主题", menu=tsub)

        zsub = tk.Menu(m, tearoff=0)
        zv = tk.DoubleVar(value=self.zoom)
        for z in ZOOMS:
            zsub.add_radiobutton(label="%d%%" % round(z * 100), value=z,
                                 variable=zv,
                                 command=lambda z=z: self.set_zoom(z))
        m.add_cascade(label="缩放", menu=zsub)

        asub = tk.Menu(m, tearoff=0)
        av = tk.DoubleVar(value=float(self.cfg.get("opacity", 1.0)))
        for label, val in (("100%", 1.0), ("85%", 0.85),
                           ("70%", 0.7), ("55%", 0.55)):
            asub.add_radiobutton(label=label, value=val, variable=av,
                                 command=lambda v=val: self.set_opacity(v))
        m.add_cascade(label="不透明度", menu=asub)

        m.add_separator()
        m.add_command(label="解除锁定" if self.locked else "锁定位置（鼠标穿透）",
                      command=lambda: self.set_click_through(not self.locked))
        m.add_command(label="隐藏", command=self.toggle_hide)
        m.add_separator()
        m.add_command(label="退出", command=self.quit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def set_opacity(self, v):
        self.cfg["opacity"] = v
        save_cfg(self.cfg)
        self.cur_alpha = -1.0

    def quit(self):
        self.cfg["x"] = self.pos[0]
        self.cfg["y"] = self.pos[1]
        self.cfg["theme"] = self.theme_name
        self.cfg["zoom"] = self.zoom
        save_cfg(self.cfg)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    if "--preview" in sys.argv:
        out = os.path.join(app_dir(), "preview.png")
        L.preview(out, 5)
        print("preview saved:", out)
        return

    Overlay(demo="--demo" in sys.argv).run()


if __name__ == "__main__":
    main()
