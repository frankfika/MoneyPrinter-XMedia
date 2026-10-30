#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xb.py 自检。

    python3 scripts/browser/selftest.py            # 纯离线单元检查（不碰浏览器，<1s）
    python3 scripts/browser/selftest.py --live     # 再用临时 profile + headless 跑一遍
                                                   # 真实链路（fill/press/click/dom/截图），
                                                   # 不碰 FranK 的真实 profile，也不碰 x.com 写操作

退出码：0 全部通过；1 有失败。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import xb  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS  %s%s" % (name, ("  [" + detail + "]") if detail else ""))
    else:
        FAIL += 1
        print("  FAIL  %s%s" % (name, ("  [" + detail + "]") if detail else ""))


def unit_tests() -> None:
    print("== 单元检查 ==")

    # 1) action 集合必须与权威契约完全一致（多一个少一个都算违约）
    expected = ["navigate", "open_tab", "wait", "query", "inspect",
                "click", "fill", "press", "screenshot", "login_state"]
    check("action 契约集合一致", xb.ACTION_NAMES == expected, str(xb.ACTION_NAMES))
    check("HANDLERS 覆盖全部 action", set(xb.HANDLERS) == set(expected))

    # 2) 退出码
    check("退出码常量 0/1/2", (xb.EXIT_OK, xb.EXIT_ACTION_FAILED, xb.EXIT_BROWSER_UNAVAILABLE) == (0, 1, 2))
    check("XBError 默认 exit 1", xb.XBError("BAD_INPUT", "x").exit_code == 1)
    check("BrowserUnavailable exit 2", xb.BrowserUnavailable("x").exit_code == 2)
    check("BROWSER_UNAVAILABLE code", xb.BrowserUnavailable("x").code == "BROWSER_UNAVAILABLE")

    # 3) key 归一化（Cmd+Enter 必须变成 Meta+Enter）
    cases = {
        "Meta+Enter": "Meta+Enter",
        "Cmd+Enter": "Meta+Enter",
        "cmd+enter": "Meta+Enter",
        "command+Return": "Meta+Enter",
        "Enter": "Enter",
        "Control+A": "Control+A",
        "ctrl+shift+enter": "Control+Shift+Enter",
        "Escape": "Escape",
        "ArrowDown": "ArrowDown",
        "Backspace": "Backspace",
    }
    for raw, want in cases.items():
        got = xb.normalize_key(raw)
        check("normalize_key(%r)" % raw, got == want, "got=%r want=%r" % (got, want))
    try:
        xb.normalize_key("")
        check("normalize_key('') 抛 BAD_INPUT", False)
    except xb.XBError as exc:
        check("normalize_key('') 抛 BAD_INPUT", exc.code == "BAD_INPUT")

    # 4) 截断
    text, truncated, full = xb._truncate("abcdef", 3)
    check("_truncate 截断", (text, truncated, full) == ("abc", True, 6), str((text, truncated, full)))
    text, truncated, full = xb._truncate("abc", 100)
    check("_truncate 不截断", (text, truncated, full) == ("abc", False, 3))

    # 5) selector 提示按 host 区分（避免 cron 把两种原因混写）
    check("未命中提示(x.com) 提到数据口径", "data-testid" in xb._selector_hint("https://x.com/a"))
    check("未命中提示(其它站) 不提 testid", "data-testid" not in xb._selector_hint("https://example.com/"))

    # 6) action JSON 校验
    def expect_code(raw: str, code: str, label: str) -> None:
        try:
            xb.load_request({"action": raw, "action_file": None})
            check(label, False, "没有抛错")
        except xb.XBError as exc:
            check(label, exc.code == code, "code=%s" % exc.code)

    expect_code('{"action":"post_tweet","input":{}}', "UNKNOWN_ACTION", "未知 action → UNKNOWN_ACTION")
    try:
        name, inp = xb.load_request({"action": '{"action":"query","input":{"kind":"text"}}', "action_file": None})
        check("缺 input 时可解析", name == "query" and inp == {"kind": "text"}, str(inp))
    except Exception as exc:
        check("缺 input 时可解析", False, str(exc))
    expect_code('{"action":"query","input":{},"extra":1}', "BAD_INPUT", "多余字段 → BAD_INPUT")
    expect_code('not json', "BAD_INPUT", "非法 JSON → BAD_INPUT")
    expect_code('{"input":{}}', "BAD_INPUT", "缺 action → BAD_INPUT")

    # 7) 配置解析：极简 YAML 兜底（系统 python3 没 pyyaml 时走这条）
    parsed = xb._mini_yaml(
        "# comment\n"
        "cdp: http://127.0.0.1:9222\n"
        "user_data_dir: ~/.shortbot-browser-profile\n"
        "headless: false\n"
        "action_timeout_ms: 30000\n"
        "proxy_mode: auto  # 行尾注释\n"
    )
    check("mini_yaml cdp", parsed.get("cdp") == "http://127.0.0.1:9222", str(parsed.get("cdp")))
    check("mini_yaml headless bool", parsed.get("headless") is False)
    check("mini_yaml int", parsed.get("action_timeout_ms") == 30000)
    check("mini_yaml 行尾注释", parsed.get("proxy_mode") == "auto", str(parsed.get("proxy_mode")))

    # 8) 路径展开
    p = xb.expand_dir("~/.shortbot-browser-profile")
    check("expand_dir 展开 ~", str(p).startswith(str(Path.home())), str(p))
    check("默认 profile 不是 Chrome 默认目录",
          "Library/Application Support/Google/Chrome" not in str(p))

    # 9) 参数解析
    a = xb.parse_args(["--action", '{"action":"login_state"}', "--headless", "--ensure"])
    check("parse_args --headless", a["headless"] is True)
    check("parse_args --ensure", a["ensure"] is True)
    a = xb.parse_args(["--action={\"action\":\"login_state\"}", "--timeout-ms=5000", "--ephemeral"])
    check("parse_args '=' 形式", a["action"].startswith("{") and a["timeout_ms"] == 5000 and a["ephemeral"])

    # 10) 锁：本进程内可拿可放（用临时锁文件，避免和真实 cron 调用抢锁）
    tmp_lock_dir = Path(tempfile.mkdtemp(prefix="xb-selftest-lock-"))
    old_lock, old_state = xb.LOCK_FILE, xb.STATE_DIR
    xb.LOCK_FILE, xb.STATE_DIR = tmp_lock_dir / "xb.lock", tmp_lock_dir
    try:
        xb.acquire_lock(100)
        xb.release_lock()
        # 同一文件二次获取（证明可重入）
        xb.acquire_lock(100)
        xb.release_lock()
        check("acquire_lock / release_lock", True)
    finally:
        xb.LOCK_FILE, xb.STATE_DIR = old_lock, old_state

    # 11) 输出契约字段
    payload = {"ok": True, "action": "login_state", "data": {"logged_in": False, "handle": None, "url": "x"}}
    line = json.dumps(payload, ensure_ascii=False)
    check("输出单行 JSON", "\n" not in line and json.loads(line)["ok"] is True)


TEXT = "一段只在 fixture 里的文字"

FIXTURE = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>xb selftest fixture</title></head>
<body>
<article data-testid="tweet">
  <div data-testid="tweetText">fixture</div>
  <div role="group">
    <button data-testid="reply" aria-label="12 Replies. Reply" onclick="mark('reply')">12</button>
    <button data-testid="like" aria-label="1,234 Likes. Like" onclick="mark('like')">1.2K</button>
  </div>
</article>
<textarea id="compose"></textarea><div id="out">（未发送）</div>
<script>
 function mark(w){document.getElementById('out').textContent='clicked:'+w}
 document.getElementById('compose').addEventListener('keydown',e=>{
   if((e.metaKey||e.ctrlKey)&&e.key==='Enter'){document.getElementById('out').textContent='submit:'+document.getElementById('compose').value.length+'chars'}
 });
</script></body></html>
"""


def live_tests() -> None:
    print("\n== 实链路检查（临时 profile + headless，不碰真实 profile / 不碰 x.com 写操作）==")
    tmp = Path(tempfile.mkdtemp(prefix="xb-selftest-"))
    fixture = tmp / "fixture.html"
    fixture.write_text(FIXTURE, encoding="utf-8")
    cfg = tmp / "browser.yaml"
    cfg.write_text(
        "cdp: http://127.0.0.1:9555\n"          # 故意指向一个没人监听的端口
        "user_data_dir: %s\n" % (tmp / "profile") +
        "locale: en-US\ntimezone_id: Asia/Shanghai\n"
        "action_timeout_ms: 30000\nnavigate_timeout_ms: 30000\nsettle_ms: 200\n"
        "headless: true\nproxy_mode: never\n",
        encoding="utf-8",
    )

    # 不用 --ephemeral：走常驻路径（spawn Chrome → 后续 attach），这样 fill 的文本
    # 在下一个 press 调用里还在（ephemeral 每次都是新进程、页面会重新加载）
    env = dict(os.environ, XB_STATE_DIR=str(tmp / "state"))  # 不污染真实 .state
    base = [sys.executable, str(HERE / "xb.py"), "--config", str(cfg), "--headless",
            "--ensure", "--lock-wait-ms", "40000"]

    def run(action: dict, extra: list | None = None) -> tuple[int, dict, str]:
        cmd = base + ["--action", json.dumps(action, ensure_ascii=False)] + (extra or [])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
        try:
            out = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
        except Exception:
            out = {}
        return proc.returncode, out, proc.stdout + proc.stderr

    t0 = time.time()
    code, out, raw = run({"action": "navigate", "input": {"url": fixture.as_uri()}})
    check("live navigate", code == 0 and out.get("ok") is True, "exit=%d" % code)

    code, out, raw = run({"action": "query", "input": {"kind": "dom", "selector": "[data-testid='like']"}})
    aria = (out.get("data") or {}).get("aria_label")
    check("live §8.5 aria-label 读取", code == 0 and aria == "1,234 Likes. Like", "aria=%r" % aria)

    code, out, raw = run({"action": "query", "input": {"kind": "dom", "selector": "[data-testid='reply']"}})
    aria = (out.get("data") or {}).get("aria_label")
    check("live replies aria-label", code == 0 and aria == "12 Replies. Reply", "aria=%r" % aria)

    code, out, raw = run({"action": "fill", "input": {"selector": "#compose", "text": TEXT}})
    ok_fill = code == 0 and (out.get("data") or {}).get("filled_chars") == len(TEXT)
    check("live fill（自动清空）", ok_fill, raw.splitlines()[-1][:120])

    code, out, raw = run({"action": "press", "input": {"key": "Cmd+Enter"}})
    check("live press Cmd+Enter", code == 0 and (out.get("data") or {}).get("key") == "Meta+Enter")

    code, out, raw = run({"action": "query", "input": {"kind": "text", "selector": "#out"}})
    text = (out.get("data") or {}).get("text", "")
    check("live Cmd+Enter 真的送到页面", text == "submit:%dchars" % len(TEXT), "text=%r" % text)

    code, out, raw = run({"action": "inspect", "input": {"selector": "[data-testid='like']"}})
    els = (out.get("data") or {}).get("elements") or []
    ref = els[0].get("ref") if els else None
    check("live inspect 拿 ref", code == 0 and bool(ref), "ref=%s" % ref)
    if ref:
        code, out, raw = run({"action": "click", "input": {"ref": ref}})
        check("live click by ref", code == 0 and (out.get("data") or {}).get("clicked", {}).get("ref") == ref)

    shot = tmp / "shot.png"
    code, out, raw = run({"action": "screenshot", "input": {"path": str(shot)}})
    check("live screenshot", code == 0 and shot.is_file() and shot.stat().st_size > 0,
          "%d bytes" % (shot.stat().st_size if shot.is_file() else 0))

    # 浏览器不可用 → exit 2
    bad_cfg = tmp / "bad.yaml"
    bad_cfg.write_text("cdp: http://127.0.0.1:9556\nuser_data_dir: /dev/null/nope\nproxy_mode: never\n",
                       encoding="utf-8")
    env_bad = dict(env, XB_STATE_DIR=str(tmp / "state-bad"))  # 独立 state，避免被 endpoint.json 兜底
    proc = subprocess.run([sys.executable, str(HERE / "xb.py"), "--config", str(bad_cfg),
                           "--action", '{"action":"login_state"}'],
                          capture_output=True, text=True, timeout=120, env=env_bad)
    try:
        err = json.loads(proc.stdout.strip().splitlines()[-1])["error"]["code"]
    except Exception:
        err = "?"
    check("live 浏览器不可用 → exit 2 / BROWSER_UNAVAILABLE",
          proc.returncode == 2 and err == "BROWSER_UNAVAILABLE", "exit=%d code=%s" % (proc.returncode, err))

    # 清理：只杀 user-data-dir 指向本临时目录的 Chrome（先核对命令行再杀）
    profile = tmp / "profile"
    killed = []
    try:
        pids = subprocess.run(["pgrep", "-f", "user-data-dir=%s" % profile],
                              capture_output=True, text=True, timeout=10).stdout.split()
        for pid in pids:
            try:
                cmd = subprocess.run(["ps", "-o", "command=", "-p", pid],
                                     capture_output=True, text=True, timeout=10).stdout
            except Exception:
                continue
            if "Google Chrome --user-data-dir=%s" % profile in cmd:
                subprocess.run(["kill", pid], timeout=10)
                killed.append(pid)
    except Exception as exc:
        print("  WARN 清理测试 Chrome 失败: %s" % exc)
    check("live 测试 Chrome 已清理", True, "killed=%s" % (",".join(killed) or "无（未 spawn）"))

    print("  （实链路耗时 %.1fs，临时目录 %s，可手动删）" % (time.time() - t0, tmp))


def main() -> int:
    print("xb.py selftest · python=%s" % sys.version.split()[0])
    unit_tests()
    if "--live" in sys.argv[1:]:
        live_tests()
    print("\n结果：PASS %d / FAIL %d" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
