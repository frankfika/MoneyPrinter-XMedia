#!/usr/bin/env bash
# 短文助手 · 单 slot 扫描（lite 版）
#
# ⚠️ 局限性：mmx search 是全网搜索，不支持 from: X 操作符；
#    真正的「X 时间线 + 实时浏览量」需要走 browser use 路径
#    （skills/hot-topic-tracker/SKILL.md 描述的那种）。
#    本脚本只能产生 AI 相关全网新闻的命中项，作为「选题素材」粗筛，
#    不替代真 X 时间线扫描。
#
# 用法：bash scripts/scan-slot.sh <slot-id>
#   slot-id: am | noon | pm | eve | night

set -euo pipefail
cd "$(dirname "$0")/.."

SLOT="${1:-pm}"
DATE="$(date +%m%d)"
TS="$(date '+%Y-%m-%dT%H:%M:%S+08:00')"

LOG="logs/scan/${DATE}-${SLOT}.log"
mkdir -p "${LOG%/*}"

echo "[$(date -Iseconds)] scan-slot.sh SLOT=${SLOT} DATE=${DATE} (lite: web search only)" | tee -a "${LOG}"

# 单次聚合查询：覆盖 watchlist 里高价值 handle
SEARCH_Q="OpenAI Anthropic Karpathy NVIDIA DeepMind latest AI announcement"
RAW=$(mmx search query --q "${SEARCH_Q}" --output json 2>>"${LOG}" || echo '{"organic":[]}')

# 解析 + 落 material.yaml
# ⚠️ 之前 `echo RAW | python3 - args <<PY` 被 bash heredoc 抢占 stdin，pipe 进来的 RAW 丢失 → 永远 0 候选
# 改：RAW 写临时文件，python 从 argv 读。
RAW_FILE="$(mktemp -t scan-slot-raw.XXXXXX.json)"
printf '%s' "${RAW}" > "${RAW_FILE}"
python3 - "${SLOT}" "${DATE}" "${TS}" "${LOG}" "${RAW_FILE}" <<'PY'
import json, sys, re, pathlib, yaml

slot, date, ts, log_path, raw_path = sys.argv[1:6]
try:
    raw = pathlib.Path(raw_path).read_text().strip()
except Exception:
    raw = ""
try:
    d = json.loads(raw) if raw else {"organic": []}
except Exception as e:
    pathlib.Path(log_path).write_text(pathlib.Path(log_path).read_text() + f"JSON err: {e}\n")
    sys.exit(0)

rules = yaml.safe_load(pathlib.Path("state/filter-rules.yaml").read_text())
seen = json.loads(pathlib.Path("state/seen-posts.json").read_text())["entries"]
seen_ids = {e.get("post_id") for e in seen if e.get("post_id") and e["post_id"] != "unknown"}
keywords = rules["ai_keywords"]["en"] + rules["ai_keywords"]["zh"]
watchlist = {a["handle"].lower() for a in yaml.safe_load(pathlib.Path("state/watchlist.yaml").read_text())["accounts"] if a["status"] == "active"}

candidates = []
for r in d.get("organic", []):
    url = r.get("link", "")
    title = r.get("title", "")
    snippet = r.get("snippet", "")
    if "x.com/" not in url and "twitter.com/" not in url:
        continue
    text = (title + " " + snippet).lower()
    if not any(k.lower() in text for k in keywords):
        continue
    m = re.search(r"x\.com/([^/]+)/status/(\d+)", url)
    if not m: continue
    handle, post_id = m.group(1).lower(), m.group(2)
    if handle not in watchlist: continue
    if post_id in seen_ids: continue
    candidates.append({
        "handle": m.group(1), "url": url, "title": title[:120],
        "snippet": snippet[:160], "date": r.get("date", ""), "post_id": post_id,
    })

with open(log_path, "a") as f:
    f.write(f"  found {len(candidates)} candidate(s)\n")

out_root = pathlib.Path(f"outputs/{date}-{slot}")
out_root.mkdir(parents=True, exist_ok=True)
for i, h in enumerate(candidates[:3], 1):
    topic = re.sub(r"[^a-zA-Z0-9\-_]", "-", h["title"][:30]).strip("-").lower() or h["handle"]
    topic_dir = out_root / topic
    topic_dir.mkdir(parents=True, exist_ok=True)
    (topic_dir / "screenshots").mkdir(exist_ok=True)
    material = {
        "material_id": f"{date}-{slot}-{i:02d}",
        "slot": slot, "scanned_at": ts,
        "author": {"name": h["handle"], "handle": h["handle"], "lang": "en"},
        "original": {"url": h["url"], "post_id": h["post_id"], "posted_at": h["date"]},
        "metrics": {"views": 0, "likes": 0, "retweets": 0, "replies": 0},
        "ai_match": True,
        "summary": h["title"] + " " + h["snippet"][:80],
        "evidence_links": [],
        "screenshots_needed": ["原帖正文+配图区"],
        "treatment_hint": "quote_retweet",
        "dedup_hits": [],
        "source": "scan-slot.sh lite (mmx web search)",
    }
    (topic_dir / "material.yaml").write_text(yaml.dump(material, allow_unicode=True, sort_keys=False))
    with open(log_path, "a") as f:
        f.write(f"  → outputs/{date}-{slot}/{topic}/material.yaml\n")
PY

echo "[$(date -Iseconds)] scan-slot done." | tee -a "${LOG}"
