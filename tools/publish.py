# -*- coding: utf-8 -*-
"""通过 GitHub REST API 发布 OverPad v1.0.0（绕过被阻断的 github.com 主站）

用法：python publish_overpad.py <TOKEN>
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
REPO = "overpad"
TAG = "v1.0.0"
TITLE = "OverPad v1.0.0"
DESC = "打游戏时实时显示手柄按键的透明悬浮窗，内置两套主题。"

BODY = """## OverPad v1.0.0

Windows 手柄输入悬浮窗：透明、置顶、不挡操作。支持两套主题实时切换。

### 功能
- 实时显示 ABXY、方向键、肩键、摇杆偏移、扳机按压深度（带百分比）
- 两套主题：现代线框 HUD / 像素风，`Ctrl+Alt+T` 一键切换
- 鼠标穿透锁定，锁定后不挡游戏点击
- 缩放 75%–300%，不透明度 55%–100%
- 单文件 exe，免安装，无运行库依赖

### 热键
| 热键 | 功能 |
| --- | --- |
| `Ctrl+Alt+T` | 切换主题 |
| `Ctrl+Alt+L` | 锁定 / 解锁（鼠标穿透） |
| `Ctrl+Alt+H` | 隐藏 / 显示 |
| `Ctrl+Alt+↑↓` | 放大 / 缩小 |
| `Ctrl+Alt+Q` | 退出 |

### 注意
游戏处于**独占全屏**时，置顶窗口不可见且全局热键会被屏蔽。
请把游戏改成**无边框窗口**或**窗口化**后使用。

仅支持 XInput 手柄；PS 手柄需配合 DS4Windows。
"""


def api(method, path, data=None, base=API, raw_body=None, content_type=None):
    url = path if path.startswith("http") else base + path
    if raw_body is not None:
        body = raw_body
    elif data is not None:
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "overpad-release")
    if content_type:
        req.add_header("Content-Type", content_type)
    elif body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise SystemExit("HTTP %s %s %s\n%s" % (e.code, method, path, detail))


def collect_files(root):
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    files = []
    for rel in out:
        rel = rel.strip()
        if not rel:
            continue
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                files.append((rel.replace("\\", "/"), f.read()))
    return files


def main():
    global TOKEN
    if len(sys.argv) < 2:
        raise SystemExit("usage: publish_overpad.py <TOKEN>")
    TOKEN = sys.argv[1].strip()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    me = api("GET", "/user")
    owner = me["login"]
    print("owner:", owner)

    # 1) 建仓库（已存在则复用）
    try:
        repo = api("POST", "/user/repos", {
            "name": REPO, "private": False, "auto_init": False,
            "description": DESC, "has_issues": True, "has_wiki": False,
        })
        print("repo created:", repo["full_name"])
    except SystemExit as e:
        if "422" not in str(e):
            raise
        repo = api("GET", "/repos/%s/%s" % (owner, REPO))
        print("repo exists:", repo["full_name"])

    # 2) 一次性提交所有文件（Git Data API）
    files = collect_files(root)
    print("uploading %d files..." % len(files))
    blobs = []
    for path, content in files:
        b = api("POST", "/repos/%s/%s/git/blobs" % (owner, REPO), {
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64",
        })
        blobs.append({"path": path, "mode": "100644",
                      "type": "blob", "sha": b["sha"]})

    tree = api("POST", "/repos/%s/%s/git/trees" % (owner, REPO), {"tree": blobs})
    commit = api("POST", "/repos/%s/%s/git/commits" % (owner, REPO), {
        "message": "feat: initial release v1.0.0",
        "tree": tree["sha"],
    })
    print("commit:", commit["sha"][:12])

    # 3) 建 main 分支（空仓库首次需要创建 ref）
    try:
        api("POST", "/repos/%s/%s/git/refs" % (owner, REPO), {
            "ref": "refs/heads/main", "sha": commit["sha"]})
        print("branch main created")
    except SystemExit as e:
        if "422" not in str(e):
            raise
        api("PATCH", "/repos/%s/%s/git/refs/heads/main" % (owner, REPO),
            {"sha": commit["sha"], "force": True})
        print("branch main updated")

    # 4) 发 Release
    rel = api("POST", "/repos/%s/%s/releases" % (owner, REPO), {
        "tag_name": TAG, "target_commitish": "main",
        "name": TITLE, "body": BODY,
        "draft": False, "prerelease": False,
    })
    print("release:", rel["html_url"])

    # 5) 上传 exe 作为附件
    exe = os.path.join(root, "dist", "OverPad.exe")
    if os.path.isfile(exe):
        with open(exe, "rb") as f:
            data = f.read()
        url = "%s/repos/%s/%s/releases/%d/assets?name=OverPad.exe" % (
            UPLOADS, owner, REPO, rel["id"])
        api("POST", url, raw_body=data,
            content_type="application/octet-stream")
        print("asset uploaded: OverPad.exe (%.1f MB)" % (len(data) / 1048576))
    else:
        print("WARN: dist/OverPad.exe not found, skip asset")

    print("\nDONE ->", rel["html_url"])


if __name__ == "__main__":
    main()
