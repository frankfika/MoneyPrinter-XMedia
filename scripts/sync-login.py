#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync-login.py — 把日常 Chrome 里 X + 小红书的登录 cookie 搬进短文助手自动化 profile。

谁跑：**Fang 本人**（涉及登录凭证，AI 不代跑）。
原理：同一台 Mac 上所有 Chrome profile 共用同一把钥匙串密钥（Chrome Safe Storage），
所以加密的 cookie 可以跨 profile 直接复制，搬过去就是已登录状态，一次都不用手动登录。

用法：
  1. 完全退出日常 Chrome（⌘Q，确保菜单栏没有 Chrome 图标）
  2. python3 scripts/sync-login.py
  3. 重新打开 Chrome 什么都不用动；自动化那边直接就是登录态

跑完可用复核：python3 scripts/browser/xb.py --action '{"action":"login_state"}'
"""

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

SRC = Path.home() / "Library/Application Support/Google/Chrome/Default/Network/Cookies"
DST_PROFILE = Path.home() / ".shortbot-browser-profile"
DST = DST_PROFILE / "Default/Network/Cookies"

HOST_PATTERNS = ["%.x.com", "%.twitter.com", "%.twimg.com", "%.xiaohongshu.com", "xhslink.com"]


def main() -> int:
    if not SRC.exists():
        print(f"✗ 找不到日常 Chrome 的 cookie 库：{SRC}")
        print("  （确定 Chrome 完全退出了？路径不对的话改本文件顶部的 SRC）")
        return 1
    if not DST.exists():
        print(f"✗ 找不到自动化 profile 的 cookie 库：{DST}")
        print("  （先让自动化 Chrome 跑过一次；或跑 bash scripts/browser/setup.sh 后再试）")
        return 1

    # 先把源库快照出来（避免锁文件/WAL 问题），再从中读
    with tempfile.TemporaryDirectory() as td:
        snap = Path(td) / "Cookies"
        shutil.copy2(SRC, snap)
        src = sqlite3.connect(snap)
        rows = []
        for pat in HOST_PATTERNS:
            rows += src.execute(
                "SELECT host_key, name, encrypted_value, value, path, expires_utc, "
                "is_secure, is_httponly, samesite, creation_utc, last_access_utc, "
                "has_expires, is_persistent, priority, top_frame_site_key "
                "FROM cookies WHERE host_key LIKE ?", (pat,)
            ).fetchall()
        src.close()

    if not rows:
        print("✗ 日常 Chrome 里没有 X / 小红书的 cookie —— 那边本身没登录？")
        return 1

    hosts = sorted({r[0] for r in rows})
    print(f"源（日常 Chrome）：{len(rows)} 条 cookie，host：{hosts}")

    dst = sqlite3.connect(DST)
    dst.execute("BEGIN")
    for pat in HOST_PATTERNS:
        dst.execute("DELETE FROM cookies WHERE host_key LIKE ?", (pat,))
    for r in rows:
        dst.execute(
            "INSERT INTO cookies (host_key, name, encrypted_value, value, path, expires_utc, "
            "is_secure, is_httponly, samesite, creation_utc, last_access_utc, "
            "has_expires, is_persistent, priority, top_frame_site_key) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", r
        )
    dst.commit()
    dst.close()

    print(f"✓ 已写入 {DST}")
    print("复核：python3 scripts/browser/xb.py --action '{\"action\":\"login_state\"}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
