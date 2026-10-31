#!/usr/bin/env python3
"""短文助手控制台 · 自检

用法： .venv/bin/python console/selftest.py [base_url]
覆盖：全部 API 路由、边界输入、路径穿越防护、只读性（state/ 不被面板改动）。
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8848"

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✓ " if cond else "  ✗ ") + name + (f"  — {detail}" if detail and not cond else ""))


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def post(path, obj):
    body = json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def jget(path):
    st, body = get(path)
    try:
        return st, json.loads(body)
    except Exception:
        return st, None


def snapshot():
    """state/ 与 outputs/ 的指纹，用来证明面板只读。"""
    h = hashlib.sha256()
    for base in ("state", "outputs"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            dirnames.sort()
            for fn in sorted(filenames):
                p = os.path.join(dirpath, fn)
                if "__pycache__" in p:
                    continue
                try:
                    st = os.stat(p)
                    h.update(p.encode())
                    h.update(str(st.st_mtime_ns).encode())
                    h.update(str(st.st_size).encode())
                except OSError:
                    pass
    return h.hexdigest()


print(f"→ 目标 {BASE}\n")

print("[1] 静态资源")
st, _ = get("/")
check("GET / 返回 200", st == 200, f"got {st}")
for f in ("/static/app.js", "/static/style.css"):
    st, _ = get(f)
    check(f"GET {f}", st == 200, f"got {st}")

print("\n[2] 只读 API")
st, ov = jget("/api/overview")
check("GET /api/overview", st == 200 and isinstance(ov, dict))
if isinstance(ov, dict):
    check("  overview 有 channels / counts / pending",
          all(k in ov for k in ("channels", "counts", "pending", "x", "xhs")))

st, dr = jget("/api/drafts")
check("GET /api/drafts", st == 200 and isinstance(dr, dict) and isinstance(dr.get("entries"), list))
entries = dr.get("entries", []) if isinstance(dr, dict) else []
check("  drafts 非空", len(entries) > 0, f"got {len(entries)}")
if entries:
    name = entries[0]["name"]
    st, one = jget("/api/draft?name=" + name)
    check(f"GET /api/draft?name={name}", st == 200 and one.get("name") == name)
    shots = one.get("shots") or []
    if shots:
        st, _ = get(f"/api/draft/shot?name={name}&file={shots[0]}")
        check("  真截图可取回", st == 200, f"got {st}")

for path, keys in [("/api/published", ("total", "entries")),
                   ("/api/outbound", ("total", "entries", "kinds")),
                   ("/api/gate", ("total", "entries")),
                   ("/api/rules", ("forbidden", "style_x", "style_xhs", "filter")),
                   ("/api/schedule", None),
                   ("/api/memory?line=chuangzuo&rounds=2", ("line", "text"))]:
    st, d = jget(path)
    ok = st == 200 and isinstance(d, dict)
    if ok and keys:
        ok = all(k in d for k in keys)
    check(f"GET {path}", ok, f"got {st}")

st, d = jget("/api/published?q=cursor&limit=5")
check("  已发搜索 q=cursor 生效", st == 200 and isinstance(d.get("entries"), list))
st, d2 = jget("/api/outbound?q=like&limit=5")
check("  互动台账搜索生效", st == 200 and isinstance(d2.get("entries"), list))

print("\n[3] 边界与防护")
st, _ = get("/api/draft?name=" + urllib.parse.quote("../../../../etc/passwd"))
check("draft 参数穿越被挡（取不到 /etc/passwd）", st in (404, 400) or "root:" not in _)
st, body = get("/api/draft/shot?name=..%2F..%2F..&file=..%2Fetc%2Fpasswd")
check("shot 路径穿越被挡", st == 404 or "root:" not in body)
st, body = get("/static/../serve.py")
check("static 目录穿越被挡", st == 404 or "ThreadingHTTPServer" not in body)
st, d = jget("/api/draft?name=__not_exist__")
check("不存在的备稿 → 404", st == 404, f"got {st}")
st, d = jget("/api/nope")
check("未知路由 → 404", st == 404, f"got {st}")
st, body = post("/api/gate/check", {"text": ""})
check("空文本闸门 → 400", st == 400, f"got {st}")
st, body = post("/api/codex", {"prompt": ""})
check("空指令 → 400", st == 400, f"got {st}")

print("\n[4] 受控动作")
st, body = post("/api/gate/check", {"text": "这条写得还行，Cursor 的插件市场被投毒这件事挺典型的。"})
d = json.loads(body) if body else {}
check("闸门跑得通（有 exit code）", st == 200 and "exit_code" in d, body[:120])
st, body = post("/api/gate/check", {"text": "问题来了，这里转折展开一下。"})
d = json.loads(body) if body else {}
check("闸门能拦下 AI 味", st == 200 and d.get("passed") is False, f"passed={d.get('passed')}")

st, body = post("/api/codex", {"prompt": "只回答两个字：收到。不要做任何其他操作。"})
d = json.loads(body) if body else {}
check("codex 任务能启动", st == 200 and "job_id" in d, body[:120])
job = d.get("job_id")
if job:
    import time
    ok = False
    for _ in range(40):
        time.sleep(3)
        st, body = get(f"/api/codex/job?id={job}")
        j = json.loads(body) if body else {}
        if j.get("status") != "running":
            ok = (j.get("status") == "done" and j.get("code") == 0
                  and "收到" in (j.get("output") or ""))
            check("codex 任务跑完且答得对", ok,
                  f"status={j.get('status')} code={j.get('code')} out={(j.get('output') or '')[-120:]}")
            break
    else:
        check("codex 任务跑完且答得对", False, "超时未返回")

print("\n[5] 只读性（面板自身不改 state/ 和 outputs/）")
before = snapshot()
for p in ("/api/overview", "/api/drafts", "/api/published", "/api/outbound",
          "/api/gate", "/api/rules", "/api/schedule", "/api/memory"):
    get(p)
after = snapshot()
check("浏览全部页面后 state/outputs 指纹不变", before == after)

print(f"\n{'='*46}\n通过 {len(PASS)} · 失败 {len(FAIL)}")
if FAIL:
    print("失败项：")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("全部通过 ✓")
