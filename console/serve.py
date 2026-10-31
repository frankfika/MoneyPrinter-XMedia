#!/usr/bin/env python3
"""短文助手 · 本地控制台

只读地聚合 state/ outputs/ logs/ 里的既有事实源，另开两个受控动作：
  1. 跑现有闸门脚本 scripts/prepublish.py（不新增判据）
  2. 把指令交给 codex exec（判断层仍在 Codex 里）

不写任何 state 文件。唯一事实源永远是仓库里的 yaml/json。
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PORT = int(os.environ.get("SHORTBOT_CONSOLE_PORT", "8848"))
TZ = timezone(timedelta(hours=8))
MAX_BODY = 1 * 1024 * 1024        # 请求体上限 1MB
MAX_GATE_CHARS = 8000             # 闸门正文上限


# ────────────────────────── 小工具 ──────────────────────────
def jread(rel, default=None):
    p = os.path.join(ROOT, rel)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def yread(rel, default=None):
    p = os.path.join(ROOT, rel)
    try:
        import yaml
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f) or (default if default is not None else {})
    except Exception:
        return default if default is not None else {}


def tnow():
    return datetime.now(TZ)


def parse_ts(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            d = datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=TZ)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def ago(ts):
    d = parse_ts(ts)
    if not d:
        return None
    return tnow() - d


def human_delta(ts):
    delta = ago(ts)
    if delta is None:
        return "—", None
    sec = delta.total_seconds()
    if sec < 0:
        sec = 0
    h = sec / 3600
    if h < 1:
        return f"{int(sec // 60)} 分钟前", round(h, 2)
    if h < 48:
        return f"{h:.1f} 小时前", round(h, 2)
    return f"{h / 24:.1f} 天前", round(h, 2)


def sha256_file(path, strip=False):
    try:
        with open(path, "rb") as f:
            data = f.read()
        if strip:
            data = data.strip()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return None


META_LINE = re.compile(r"^\s*#")


def read_body(rel):
    """和 scripts/prepublish.py 的 read_body 同口径：去掉 # meta 行、strip。"""
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    try:
        with open(p, encoding="utf-8") as f:
            raw = f.read()
    except Exception:
        return None
    return "\n".join(l for l in raw.splitlines() if not META_LINE.match(l)).strip()


def read_text(rel, limit=None):
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    try:
        with open(p, encoding="utf-8") as f:
            s = f.read()
        return s if limit is None else s[:limit]
    except Exception:
        return None


def slug_words(text):
    if not text:
        return set()
    return {w for w in re.split(r"[^a-z0-9]+", str(text).lower()) if len(w) > 3}


# ────────────────────────── 数据装载 ──────────────────────────
def load_account():
    return yread("private/account-safety.yaml", {"x": {}, "xhs": {}})


def load_published():
    d = jread("state/published-posts.json", {})
    return d.get("entries", []) or []


def load_outbound():
    d = jread("state/outbound-actions.json", {})
    return d.get("entries", []) or []


def load_gate_receipts():
    d = jread("state/gate-receipts.json", {})
    r = d.get("receipts", []) or []
    r = sorted(r, key=lambda x: str(x.get("ts", "")))
    return r


def load_drafts():
    """扫 outputs/ 下的备稿目录，判断：闸门过没过、发没发（分平台）。"""
    pub = load_published()
    receipts = load_gate_receipts()

    # 闸门回执：两种口径都能对上 —— sha 前 16 位（脚本的存法）或 origin 路径
    by_sha = {}
    by_origin = {}
    for rc in receipts:
        s = rc.get("sha256")
        if s:
            by_sha[s] = rc
        o = rc.get("origin")
        if o:
            by_origin[o] = rc

    outdir = os.path.join(ROOT, "outputs")
    drafts = []
    if not os.path.isdir(outdir):
        return drafts
    for name in sorted(os.listdir(outdir)):
        d = os.path.join(outdir, name)
        if not os.path.isdir(d) or name in ("archive",):
            continue
        mat = yread(os.path.join("outputs", name, "material.yaml"), {}) or {}
        orig = mat.get("original") or {}
        x_rel = os.path.join("outputs", name, "x.txt")
        xhs_rel = os.path.join("outputs", name, "xhs.txt")
        x_txt = read_body(x_rel)          # 正文（去掉 # meta 行，跟闸门口径一致）
        xhs_txt = read_body(xhs_rel)
        status_md = read_text(os.path.join("outputs", name, "status.md"))
        shots_dir = os.path.join("outputs", name, "screenshots")
        shots = sorted(os.listdir(shots_dir)) if os.path.isdir(shots_dir) else []

        # 闸门脚本对的是去掉 meta 行后的正文，回执 sha 就是那个值的 sha256 前 16 位
        sha = hashlib.sha256(x_txt.encode("utf-8")).hexdigest()[:16] if x_txt else None
        rc = (by_sha.get(sha[:16]) if sha else None)
        gate = {"state": "unknown", "checked_at": None, "soft_score": None,
                "hard_hits": [], "sha256": sha[:16] if sha else None, "origin": x_rel}
        if rc is None:
            # 只有 origin 对得上、sha 对不上 → 正文改过，回执已过期
            stale = by_origin.get(x_rel)
            if stale:
                gate["state"] = "stale"
                gate["checked_at"] = stale.get("ts")
                gate["stale_sha"] = stale.get("sha256")
                gate["note"] = "正文改过，闸门回执已过期（sha 不匹配），要重跑闸门"
        if rc:
            after = rc.get("after") or {}
            before = rc.get("before") or {}
            passed = after.get("passed", before.get("passed"))
            gate["state"] = "pass" if passed else "fail"
            gate["checked_at"] = rc.get("ts")
            gate["soft_score"] = after.get("soft_score", before.get("soft_score"))
            gate["hard_hits"] = after.get("hard_hits", before.get("hard_hits", [])) or []
            gate["all_hits"] = after.get("all_hits", before.get("all_hits", [])) or []
            gate["reasons"] = (after.get("reasons") or before.get("reasons") or [])[:6]

        # 已发判定：只认硬证据 —— 台账里明确提到这个备稿目录 / material_id / 原文 URL
        matches = []
        for e in pub:
            blob = json.dumps(e, ensure_ascii=False)
            plat = e.get("platform", "x")
            why = None
            src = e.get("source") or {}
            if src.get("material_id") == name:
                why = "material_id 精确匹配"
            elif src.get("canonical_url") and src.get("canonical_url") == orig.get("url"):
                why = "原文 URL 精确匹配"
            elif name in blob:
                why = "台账中出现该备稿路径"
            if why:
                matches.append({"id": e.get("id"), "url": e.get("url"), "platform": plat,
                                "timestamp": e.get("timestamp"), "why": why})

        plat_done = {m["platform"] for m in matches}
        oneline = None
        if status_md:
            m = re.search(r"## 一句话\s*\n+(.+)", status_md)
            if m:
                oneline = m.group(1).strip()

        drafts.append({
            "name": name,
            "material_id": mat.get("material_id"),
            "slot": mat.get("slot"),
            "scanned_at": mat.get("scanned_at"),
            "author": mat.get("author") or {},
            "summary": (mat.get("summary") or "")[:400],
            "signal": mat.get("signal"),
            "original_url": orig.get("url"),
            "source_name": mat.get("source_name"),
            "verified_facts": mat.get("verified_facts") or [],
            "has_material": bool(mat),
            "has_x": bool(x_txt),
            "has_xhs": bool(xhs_txt),
            "x_chars": len(x_txt) if x_txt else 0,
            "xhs_chars": len(xhs_txt) if xhs_txt else 0,
            "x_text": x_txt,
            "xhs_text": xhs_txt,
            "status_md": status_md,
            "one_line": oneline,
            "shots": shots,
            "gate": gate,
            "published": matches,
            "published_x": "x" in plat_done,
            "published_xhs": "xiaohongshu" in plat_done,
            "pending_x": bool(x_txt) and "x" not in plat_done,
            "pending_xhs": bool(xhs_txt) and "xiaohongshu" not in plat_done,
        })
    drafts.sort(key=lambda d: str(d.get("scanned_at") or d.get("name")), reverse=True)
    return drafts


def channel_health(acc, drafts):
    """通道体检：能不能真发。"""
    x = acc.get("x") or {}
    xhs = acc.get("xhs") or {}
    rows = []

    x_login = x.get("login_state")
    x_chrome = x.get("chrome_login_state")
    x_chan = x.get("publish_channel") or ""
    if x_chrome == "logged_in":
        x_ok, x_state = True, f"{x_login}（内置浏览器） / {x_chrome}（Fang 本人 Chrome）"
    else:
        x_ok, x_state = x_login == "logged_in", x_login
    rows.append({
        "name": "X 发布通道",
        "ok": x_ok,
        "state": x_state + (f" · 实际通道={x_chan}" if x_chan else ""),
        "note": x.get("login_channel_status") or x.get("login_channel") or "",
    })

    xhs_login = xhs.get("login_state")
    rows.append({
        "name": "小红书发布通道",
        "ok": bool(xhs_login == "logged_in" and xhs.get("agent_publish_allowed")),
        "state": f"login={xhs_login} / agent_allowed={xhs.get('agent_publish_allowed')}",
        "note": xhs.get("login_channel_status") or "",
    })

    rows.append({
        "name": "小红书封禁",
        "ok": not xhs.get("is_banned"),
        "state": "banned" if xhs.get("is_banned") else "正常",
        "note": (xhs.get("ban_reason") or "")[:160],
    })

    pending = [d for d in drafts if (d.get("pending_x") or d.get("pending_xhs"))
               and d["gate"]["state"] == "pass"]
    rows.append({
        "name": "备稿积压",
        "ok": len(pending) == 0,
        "state": f"{len(pending)} 条过闸未发",
        "note": "、".join(d["name"] for d in pending[:4]) if pending else "无",
    })
    return rows


def build_overview():
    acc = load_account()
    x = acc.get("x") or {}
    xhs = acc.get("xhs") or {}
    drafts = load_drafts()
    pub = load_published()
    outbound = load_outbound()

    def card(section, keys):
        return {k: section.get(k) for k in keys}

    x_pub_at = x.get("last_published_at")
    x_delta, x_hours = human_delta(x_pub_at)
    reply_delta, reply_hours = human_delta(x.get("last_outbound_reply_at"))
    like_delta, like_hours = human_delta(x.get("last_outbound_like_at"))
    # 原创间隔下限从 schedule.yaml 读，别写死在代码里
    sched = build_schedule()
    gap_h = sched.get("chuangzuo_original_post_min_gap_hours") or 6

    today = tnow().strftime("%Y-%m-%d")
    pub_today = [e for e in pub if str(e.get("timestamp", "")).startswith(today)]
    out_today = [e for e in outbound if str(e.get("timestamp", "")).startswith(today)]

    pending = [d for d in drafts if d.get("pending_x") or d.get("pending_xhs")]
    pending_pass = [d for d in pending if d["gate"]["state"] == "pass"]

    # 最近几条已发
    recent = sorted(pub, key=lambda e: str(e.get("timestamp", "")), reverse=True)[:6]
    recent = [{
        "id": e.get("id"),
        "timestamp": e.get("timestamp"),
        "url": e.get("url"),
        "platform": e.get("platform", "x"),
        "topic_signature": e.get("topic_signature"),
        "treatment": e.get("treatment"),
        "media_count": e.get("media_count", 0),
    } for e in recent]

    return {
        "now": tnow().isoformat(),
        "x": card(x, ["account_label", "login_state", "publish_mode", "last_published_at",
                      "last_published_url", "last_outbound_reply_at", "last_outbound_like_at",
                      "last_inbound_reply_at", "last_login_check", "notes"]),
        "x_gap_hours": gap_h,
        "x_delta": {"published": x_delta, "published_hours": x_hours,
                    "reply": reply_delta, "reply_hours": reply_hours,
                    "like": like_delta, "like_hours": like_hours},
        "xhs": card(xhs, ["account_label", "login_state", "publish_mode", "is_banned",
                          "agent_publish_allowed", "publish_rhythm", "last_published_at",
                          "last_published_url", "last_published_title", "last_published_status",
                          "draft_title", "notes"]),
        "xhs_delta": {"published": human_delta(xhs.get("last_published_at"))[0]},
        "counts": {
            "published_total": len(pub),
            "published_today": len(pub_today),
            "outbound_total": len(outbound),
            "outbound_today": len(out_today),
            "seen_total": len((jread("state/seen-posts.json", {}).get("entries") or [])),
            "drafts_total": len(drafts),
            "drafts_pending": len(pending),
            "drafts_pending_passed": len(pending_pass),
        },
        "pending": [{"name": d["name"], "gate": d["gate"]["state"], "one_line": d["one_line"],
                     "x_chars": d["x_chars"], "has_xhs": d["has_xhs"],
                     "pending_x": d.get("pending_x"), "pending_xhs": d.get("pending_xhs"),
                     "scanned_at": d["scanned_at"]} for d in pending[:8]],
        "channels": channel_health(acc, drafts),
        "recent_published": recent,
    }


def build_published(q="", limit=60):
    pub = load_published()
    pub.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
    if q:
        ql = q.lower()
        pub = [e for e in pub if ql in json.dumps(e, ensure_ascii=False).lower()]
    out = []
    for e in pub[:limit]:
        out.append({
            "id": e.get("id"),
            "timestamp": e.get("timestamp"),
            "platform": e.get("platform", "x"),
            "url": e.get("url"),
            "post_id": e.get("post_id"),
            "topic_signature": e.get("topic_signature"),
            "treatment": e.get("treatment"),
            "media_count": e.get("media_count", 0),
            "source": (e.get("source") or {}).get("trigger") or (e.get("source") or {}).get("note") or "",
            "verification": (e.get("verification") or {}).get("evidence") or "",
        })
    return {"total": len(pub), "entries": out}


def build_outbound(q="", limit=80):
    acts = load_outbound()
    acts.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
    kinds = {}
    for e in acts:
        kinds[e.get("action", "?")] = kinds.get(e.get("action", "?"), 0) + 1
    if q:
        ql = q.lower()
        acts = [e for e in acts if ql in json.dumps(e, ensure_ascii=False).lower()]
    out = []
    for e in acts[:limit]:
        out.append({
            "id": e.get("id"),
            "timestamp": e.get("timestamp"),
            "action": e.get("action"),
            "target_handle": e.get("target_handle"),
            "target_post_url": e.get("target_post_url"),
            "own_reply_url": e.get("own_reply_url"),
            "topic_signature": e.get("topic_signature"),
            "verification": e.get("verification"),
            "risk_notes": (e.get("risk_notes") or "")[:200],
        })
    return {"total": len(acts), "kinds": kinds, "entries": out}


def build_gate(limit=40):
    rcs = load_gate_receipts()
    rcs = list(reversed(rcs))[:limit]
    out = []
    for rc in rcs:
        after = rc.get("after") or {}
        before = rc.get("before") or {}
        passed = after.get("passed", before.get("passed"))
        out.append({
            "ts": rc.get("ts"),
            "origin": rc.get("origin"),
            "sha256": rc.get("sha256"),
            "chars": rc.get("chars"),
            "rewritten": rc.get("rewritten"),
            "passed": passed,
            "soft_score": after.get("soft_score", before.get("soft_score")),
            "hard_hits": after.get("hard_hits", before.get("hard_hits", [])) or [],
            "reasons": (after.get("reasons") or before.get("reasons") or [])[:5],
        })
    return {"total": len(rcs), "entries": out}


def build_rules():
    forb = yread("state/forbidden.yaml", {}) or {}
    style_x = yread("state/style-x.yaml", {}) or {}
    style_xhs = yread("state/style-xhs.yaml", {}) or {}
    filt = yread("state/filter-rules.yaml", {}) or {}
    return {
        "forbidden": forb,
        "style_x": style_x,
        "style_xhs": style_xhs,
        "filter": filt,
    }


def build_memory(line="chuangzuo", rounds=3):
    p = os.path.join("state", "memory", f"{line}.md")
    r = subprocess.run([sys.executable, "scripts/tail-rounds.py", p, "--rounds", str(rounds)],
                       cwd=ROOT, capture_output=True, text=True, timeout=30)
    return {"line": line, "text": r.stdout or r.stderr}


def build_schedule():
    return yread("state/schedule.yaml", {}) or {}


# ────────────────────────── 受控动作 ──────────────────────────
def run_gate_check(text):
    r = subprocess.run(
        [sys.executable, "scripts/prepublish.py", "--text", text, "--no-rewrite", "--json"],
        cwd=ROOT, capture_output=True, text=True, timeout=120)
    payload = None
    try:
        payload = json.loads(r.stdout)
    except Exception:
        pass
    return {
        "exit_code": r.returncode,
        "passed": r.returncode == 0,
        "json": payload,
        "stdout": (r.stdout or "")[:6000],
        "stderr": (r.stderr or "")[:3000],
    }


JOBS = {}
JOBS_LOCK = threading.Lock()


def start_codex_job(prompt, label=""):
    job_id = uuid.uuid4().hex[:8]
    with JOBS_LOCK:
        JOBS[job_id] = {"id": job_id, "label": label, "prompt": prompt,
                        "status": "running", "started_at": time.time(),
                        "output": "", "error": None, "code": None}

    def run():
        cmd = ["codex", "exec", "-C", ROOT, "--approve-for-me",
               "--skip-git-repo-check", prompt]
        try:
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
            with JOBS_LOCK:
                JOBS[job_id].update({
                    "status": "done",
                    "output": (p.stdout or "")[-40000:],
                    "error": (p.stderr or "")[-8000:] or None,
                    "code": p.returncode,
                    "finished_at": time.time(),
                })
        except subprocess.TimeoutExpired:
            with JOBS_LOCK:
                JOBS[job_id].update({"status": "timeout", "error": "超过 30 分钟未结束",
                                      "finished_at": time.time()})
        except Exception as e:
            with JOBS_LOCK:
                JOBS[job_id].update({"status": "error", "error": str(e), "finished_at": time.time()})

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


def get_job(job_id):
    with JOBS_LOCK:
        return JOBS.get(job_id)


# ────────────────────────── HTTP ──────────────────────────
class Handler(BaseHTTPRequestHandler):
    server_version = "shortbot-console"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str))

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        p = u.path
        try:
            if p == "/" or p == "/index.html":
                return self._file("index.html")
            if p.startswith("/static/"):
                return self._file(p[len("/static/"):])
            if p == "/api/overview":
                return self._json(build_overview())
            if p == "/api/drafts":
                return self._json({"entries": load_drafts()})
            if p == "/api/draft":
                name = os.path.basename(q.get("name", ""))
                for d in load_drafts():
                    if d["name"] == name:
                        return self._json(d)
                return self._json({"error": "not found"}, 404)
            if p == "/api/draft/shot":
                name = os.path.basename(q.get("name", ""))
                fn = os.path.basename(q.get("file", ""))
                full = os.path.join(ROOT, "outputs", name, "screenshots", fn)
                if not os.path.isfile(full):
                    return self._json({"error": "not found"}, 404)
                with open(full, "rb") as f:
                    return self._send(200, f.read(), "image/png")
            if p == "/api/published":
                return self._json(build_published(q.get("q", ""), int(q.get("limit", 60))))
            if p == "/api/outbound":
                return self._json(build_outbound(q.get("q", ""), int(q.get("limit", 80))))
            if p == "/api/gate":
                return self._json(build_gate(int(q.get("limit", 40))))
            if p == "/api/rules":
                return self._json(build_rules())
            if p == "/api/memory":
                return self._json(build_memory(q.get("line", "chuangzuo"), int(q.get("rounds", 3))))
            if p == "/api/schedule":
                return self._json(build_schedule())
            if p == "/api/codex/job":
                job = get_job(q.get("id", ""))
                return self._json(job or {"error": "no job"}, 200 if job else 404)
            return self._json({"error": "no route", "path": p}, 404)
        except Exception as e:
            import traceback
            return self._json({"error": str(e), "trace": traceback.format_exc()[-2000:]}, 500)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            # 先把请求体读掉再回 413，否则客户端会看到 broken pipe 而不是状态码
            left = min(n, 32 * 1024 * 1024)
            while left > 0:
                chunk = self.rfile.read(min(65536, left))
                if not chunk:
                    break
                left -= len(chunk)
            self.close_connection = True
            return self._json({"error": f"请求体过大（{n} 字节），上限 {MAX_BODY}"}, 413)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            data = {}
        try:
            if u.path == "/api/gate/check":
                text = (data.get("text") or "").strip()
                if not text:
                    return self._json({"error": "空文本"}, 400)
                if len(text) > MAX_GATE_CHARS:
                    return self._json({"error": f"正文过长（{len(text)} 字），闸门只处理 ≤{MAX_GATE_CHARS} 字的正文"}, 400)
                try:
                    return self._json(run_gate_check(text))
                except subprocess.TimeoutExpired:
                    return self._json({"error": "闸门超时（120s）"}, 504)
            if u.path == "/api/codex":
                prompt = (data.get("prompt") or "").strip()
                if not prompt:
                    return self._json({"error": "空指令"}, 400)
                return self._json(start_codex_job(prompt, data.get("label", "")))
            return self._json({"error": "no route"}, 404)
        except Exception as e:
            import traceback
            return self._json({"error": str(e), "trace": traceback.format_exc()[-2000:]}, 500)

    def _file(self, rel):
        full = os.path.normpath(os.path.join(STATIC, rel))
        if not full.startswith(STATIC) or not os.path.isfile(full):
            return self._send(404, "not found", "text/plain; charset=utf-8")
        ext = os.path.splitext(full)[1]
        ctype = {".html": "text/html; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8",
                 ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            return self._send(200, f.read(), ctype)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"短文助手控制台 → http://127.0.0.1:{PORT}   (Ctrl+C 退出)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
