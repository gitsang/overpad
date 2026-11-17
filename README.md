# OverPad

打游戏时在屏幕上实时显示手柄按键的悬浮窗。透明、置顶、不挡操作。

内置五套主题：HUD 线框、霓虹、极简、终端绿、像素风，可随时切换。基于 Windows XInput，不注入游戏进程，不读写游戏内存。

> A transparent, always-on-top gamepad input overlay for Windows. Shows buttons, stick positions and trigger travel in real time. Five switchable themes. Pure XInput, no DLL injection, no third-party dependencies.

---

## 特性

- **透明置顶悬浮**：背景完全透明，只留下手柄图形浮在游戏画面上
- **完整输入可视化**：ABXY、方向键、肩键、摇杆偏移、扳机按压深度（带百分比）
- **五套主题**：HUD 线框 / 霓虹 / 极简 / 终端绿 / 像素风，一键切换
- **鼠标穿透锁定**：锁定后鼠标可以点穿到底下的游戏
- **可调**：缩放 75%–300%，不透明度 55%–100%
- **单文件 exe**：12 MB，免安装，无运行库依赖

## 下载

到 [Releases](../../releases) 页面下载 `OverPad.exe`，双击即可运行。

## 使用

窗口默认出现在屏幕右下角，鼠标左键按住任意位置即可拖动。

### 全局热键

| 热键 | 功能 |
| --- | --- |
| `Ctrl + Alt + T` | 切换主题 |
| `Ctrl + Alt + L` | 锁定 / 解锁（鼠标穿透） |
| `Ctrl + Alt + H` | 隐藏 / 显示 |
| `Ctrl + Alt + ↑` | 放大 |
| `Ctrl + Alt + ↓` | 缩小 |
| `Ctrl + Alt + Q` | 退出 |

右键菜单里可以调整主题、缩放、不透明度和锁定状态。

### 五套主题

| 主题 | 风格 |
| --- | --- |
| **HUD 线框**（默认） | 细线描边 + 系统字体，暗色极简。扳机显示进度条与百分比，摇杆中心圆点实时反映方向 |
| **霓虹** | 青色主线配品红强调，圆环带外发光光晕，适合深色游戏画面 |
| **极简** | 纯灰白单色，去掉填充只留轮廓，视觉负担最低 |
| **终端绿** | 等宽字体 + 方角框线 + 荧光绿，复古终端 HUD |
| **像素风** | 在像素网格上逐格绘制的手柄，按键整块变色 |

## 从源码运行

需要 Windows + Python 3.10 以上，无第三方依赖：

```bash
python overpad.py
```

无手柄时可以用演示模式预览动画：

```bash
python overpad.py --demo
```

## 构建 exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=app.ico --name=OverPad overpad.py
```

产物在 `dist/OverPad.exe`。

## 技术说明

几个实现上值得记录的点：

- **输入**：`ctypes` 直连 `xinput1_4.dll`，8 ms 轮询。Guide 键（西瓜键）不在标准 `XInputGetState` 的返回里，需要按序号 100 取隐藏导出 `XInputGetStateEx`。
- **透明**：无边框窗口 + 色键抠图。色键刻意选近黑色而非品红——系统字体的抗锯齿过渡像素混进近黑色只会形成极轻的暗边，混进品红则会出现一圈显眼的脏边。
- **渲染**：HUD 系列主题全部用 Tk 原生图元（GDI 硬边光栅化，无抗锯齿），像素主题在 104×86 网格上按整数倍放大绘制。除像素主题外，其余四套全部继承同一个基类，只覆盖配色 / 字体 / 圆角 / 是否发光几个类属性即可长出新皮肤。
- **不注入**：程序只是一个普通置顶窗口，不挂接游戏进程、不读写游戏内存，不会触发反作弊。

## 已知限制

- **独占全屏**（Exclusive Fullscreen）下悬浮窗不可见，Windows 的置顶窗口盖不住它。把游戏改成**无边框窗口**或**窗口化**即可，画质帧数基本无损。
- 游戏处于独占全屏时，系统也会**屏蔽全局热键**；改成无边框窗口后恢复正常。
- 仅支持 **XInput** 手柄（Xbox 系列及兼容型号）。PS4/PS5 手柄需配合 DS4Windows 之类的工具模拟成 Xbox 手柄。
- 没有识别到手柄时，窗口会降到 55% 不透明度并在中央显示 `PRESS ANY BUTTON`。

## 目录结构

```
overpad.py        主程序：窗口、输入、热键、配置
theme_hud.py      HUD 主题基类（配色/字体/圆角/发光都可配置）
theme_neon.py     霓虹主题（继承 HUD 基类）
theme_minimal.py  极简主题（继承 HUD 基类）
theme_mono.py     终端绿主题（继承 HUD 基类）
theme_pixel.py    像素主题
layout.py         像素主题的几何与调色板
make_ico.py       生成多尺寸 ico
tools/            开发调试脚本（窗口探测、抓屏、按窗口自身内容抓图）
```

## License

[MIT](LICENSE)
