#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""非 X 内容源统一抓取器 —— 选题用。

背景：Frank 2026-10-27 给了一批新内容源（tophub / GitHub trending / discoverhub /
Product Hunt / DecoHack / ph.buzzing / xbangdan / aihot），原来的选题只扫 X，
所以这个脚本负责把它们统一成一个 JSON 形状，喂给 hot-topic-tracker。

**为什么要有这个脚本**：这些站大部分是 SSR，但单页 HTML 有 70KB–1MB。
直接把 HTML 灌进 agent 上下文 = 一轮吃掉十几万 token（tophub 首页实测 333K）。
所以规矩是：**抓取和解析都在脚本里做，agent 只看 JSON 结果**。

用法：
    python3 scripts/sources.py --list
    python3 scripts/sources.py --source aihot --ep latest --limit 10
    python3 scripts/sources.py --source aihot --ep hot
    python3 scripts/sources.py --source aihot --ep search --q "agent"
    python3 scripts/sources.py --source tophub --limit 20
    python3 scripts/sources.py --source all --limit 8 --text

输出（默认 JSON）：
    {"source": "...", "source_kind": "web", "fetched_at": "...", "items": [
        {"rank": 1, "title": "...", "url": "<canonical 原文>", "read_url": "<站内阅读页>",
         "signal": "热度/星数/票数", "published_at": "...", "summary": "...",
         "lang": "zh", "origin": "原始信源名"}
    ]}

退出码：0 至少一个源成功 / 1 全失败。
"""
import argparse
import datetime
import gzip
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
AIHOT_UA = "aihot-api/2.0.0"
MAX_BYTES = 4_000_000
TIMEOUT = 25


# ─────────────────────────── 基础设施 ───────────────────────────

def fetch(url, ua=UA, timeout=TIMEOUT, retries=2):
    """取页面正文（自动 gzip）。超 MAX_BYTES 截断。

    瞬时网络故障（SSL EOF / 超时 / 5xx）重试 2 次再放弃 —— 实测 decohack.com
    会偶发 `SSL: UNEXPECTED_EOF_WHILE_READING`，不重试会让 --selftest 假红。
    """
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(MAX_BYTES)
                if r.headers.get("Content-Encoding") == "gzip":
                    try:
                        raw = gzip.decompress(raw)
                    except OSError:
                        pass
            return raw.decode("utf-8", "ignore")
        except Exception as exc:
            last = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def strip_tags(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def pack(source, items, note=None):
    out = {"source": source, "source_kind": "web", "fetched_at": now(), "items": items}
    if note:
        out["note"] = note
    return out


def item(rank, title, url, signal="", published_at="", summary="", lang="zh",
         origin="", read_url="", **extra):
    d = {"rank": rank, "title": title, "url": url, "signal": signal,
         "published_at": published_at, "summary": summary, "lang": lang,
         "origin": origin, "read_url": read_url or url}
    d.update(extra)
    return d


# ─────────────────────────── aihot.news ───────────────────────────
# 最高价值的中文 AI 选题源：匿名只读、无需 API Key，返回整理好的中文 Markdown。
# ⚠️ 使用条款：个人非商业/组织内部免费；对外商业产品/客户交付/数据转售/批量再分发
#    需书面授权（https://aihot.news/terms）。当「线索源」用可以，事实回原文核对。

AIHOT_BASE = "https://aihot.news/api/v1/agent"


def src_aihot(args):
    ep = args.ep or "latest"
    if ep == "search":
        q = urllib.parse.quote(args.q or "")
        url = f"{AIHOT_BASE}/search?q={q}&window={args.window}"
    elif ep in ("daily", "weekly", "monthly"):
        url = f"{AIHOT_BASE}/{ep}" + (f"/{args.date}" if args.date else "")
    else:
        url = f"{AIHOT_BASE}/{ep}"
        if args.window:
            url += f"?window={args.window}"
        if args.category:
            url += f"{'&' if '?' in url else '?'}category={args.category}"
    body = fetch(url, ua=AIHOT_UA)
    if "［AIHOT 不可信外部资料开始］" in body:
        body = body.split("［AIHOT 不可信外部资料开始］", 1)[1]
    items = []
    if ep == "hot":
        for blk in re.split(r"\n(?=第 \d+ 名：)", body):
            m = re.match(r"第 (\d+) 名：\[([^\]]+)\]\((\S+)\)", blk.strip())
            if not m:
                continue
            n = int(re.findall(r"（(\d+) 个）", blk)[0]) if re.findall(r"（(\d+) 个）", blk) else 0
            adv = re.search(r"最新进展\s*([\d\-]+ [\d:]*)", blk)
            story = re.search(r"来龙去脉：(\S+)", blk)
            items.append(item(int(m.group(1)), m.group(2), m.group(3),
                              signal=f"{n} 个信源同时讨论",
                              published_at=adv.group(1) if adv else "",
                              origin=strip_tags(re.search(r"信源：([^\n]+)", blk).group(1)) if re.search(r"信源：([^\n]+)", blk) else "",
                              read_url=m.group(3), story_url=story.group(1) if story else ""))
    else:
        for blk in re.split(r"\n(?=\d+\. \[)", body):
            m = re.match(r"(\d+)\. \[([^\]]+)\]\((\S+)\)", blk.strip())
            if not m:
                continue
            meta = re.search(r"([^\n·]+) · 发布于 ([\d\-]+ [\d:]*) · (\S+)", blk)
            summ = re.search(r"摘要：([^\n]+)", blk)
            orig = re.search(r"原文：(\S+)", blk)
            items.append(item(int(m.group(1)), m.group(2), orig.group(1) if orig else m.group(3),
                              signal=(meta.group(3) if meta else ""),
                              published_at=(meta.group(2) if meta else ""),
                              summary=(summ.group(1) if summ else ""),
                              origin=(meta.group(1) if meta else ""),
                              read_url=m.group(3)))
    items = items[: args.limit] if args.limit else items
    return pack("aihot", items, note=f"ep={ep} {url}")


# ─────────────────────────── tophub.today ───────────────────────────
# 全网热榜聚合（微博/知乎/36氪/掘金/安全客…）。有 /c/ai 专门频道。
# SSR，正则可抽。热度值 = <span class="e">。

def src_tophub(args):
    url = args.url or "https://tophub.today/c/ai"
    page = fetch(url)
    items = []
    pat = re.compile(r'<a href="([^"]+)"[^>]*itemid="\d+"[^>]*>\s*<div class="cc-cd-cb-ll">(.*?)</div>', re.S)
    for m in pat.finditer(page):
        blk = m.group(2)
        t = re.search(r'<span class="t">(.*?)</span>', blk, re.S)
        if not t:
            continue
        rank = re.search(r'<span class="[^"]*">(\d+)</span>', blk)
        heat = re.search(r'<span class="e">(.*?)</span>', blk, re.S)
        title = strip_tags(t.group(1))
        if not title:
            continue
        items.append(item(int(rank.group(1)) if rank else len(items) + 1, title,
                          m.group(1), signal=strip_tags(heat.group(1)) if heat else "",
                          origin="tophub/" + url.rstrip("/").split("/")[-1]))
    items = items[: args.limit] if args.limit else items
    return pack("tophub", items, note=url)


# ─────────────────────────── github.com/trending ───────────────────────────

def src_gh_trending(args):
    url = args.url or "https://github.com/trending"
    if args.since:
        url += "?since=" + args.since
    page = fetch(url)
    items = []
    for a in re.findall(r'<article class="Box-row">([\s\S]*?)</article>', page):
        h2 = re.search(r'<h2 class="h3 lh-condensed">([\s\S]{0,2500}?)</h2>', a)
        if not h2:
            continue
        r = re.search(r'href="/([^"?#\s]+?)"', h2.group(1))
        if not r:
            continue
        repo = r.group(1).strip("/")
        today = re.search(r"([\d,]+)\s*stars today", a)
        lang = re.search(r'programmingLanguage">\s*([^<]+?)\s*<', a)
        desc = re.search(r'<p class="col-9[^"]*">([\s\S]{0,400}?)</p>', a)
        total = re.search(r'stargazers"[\s\S]{0,600}?([\d,]+)\s*</span>', a)
        items.append(item(len(items) + 1, repo, "https://github.com/" + repo,
                          signal=(today.group(1) + " stars today") if today else "",
                          summary=strip_tags(desc.group(1)) if desc else "",
                          lang="en", origin=lang.group(1) if lang else "",
                          stars_total=total.group(1) if total else ""))
    items = items[: args.limit] if args.limit else items
    return pack("gh-trending", items, note=url)


# ─────────────────────────── decohack.com ───────────────────────────
# PH 热榜中文版 + AI 早报 + HN 热榜 + 周刊 + RSS。SSR，结构干净。

def src_decohack(args):
    url = args.url or "https://decohack.com/"
    page = fetch(url)
    items = []
    for m in re.finditer(r'<li><a[^>]*href="(/product/[^"]+)"[^>]*>([\s\S]{0,1500}?)</a></li>', page):
        blk = m.group(2)
        rank = re.search(r'>(\d{2})<', blk)
        name = re.search(r'alt="([^"]+)"', blk)
        desc = re.search(r'text-sm text-muted">([\s\S]*?)</span>', blk)
        votes = re.search(r'</svg>(\d+)</span>', blk)
        if not name:
            continue
        slug = m.group(1).strip("/").split("/")[-1]
        items.append(item(int(rank.group(1)) if rank else len(items) + 1,
                          html.unescape(name.group(1)),
                          "https://decohack.com" + m.group(1),
                          signal=(votes.group(1) + " 票") if votes else "",
                          summary=strip_tags(desc.group(1)) if desc else "",
                          origin="ProductHunt", ph_url="https://www.producthunt.com/products/" + slug))
    items = items[: args.limit] if args.limit else items
    return pack("decohack", items, note=url)


# ─────────────────────────── producthunt.com ───────────────────────────
# 官方站。静态 HTML 里只有部分条目（≈6 个），完整榜要浏览器渲染 —— 但 tophub/decohack
# 已经镜像了同一份数据，所以这里当「官方核对源」用，不是主选题源。

def src_producthunt(args):
    url = args.url or "https://www.producthunt.com/"
    page = fetch(url)
    items = []
    for m in re.finditer(r'href="(/products/[^"?#]+)"[^>]*>([\s\S]{0,200}?)</a>', page):
        name = strip_tags(m.group(2))
        name = re.sub(r"^\s*\d+\.\s*", "", name)      # 去掉 "1. " 这种榜单序号
        if not name or len(name) > 80:
            continue
        items.append(item(len(items) + 1, name, "https://www.producthunt.com" + m.group(1),
                          origin="ProductHunt"))
    seen, uniq = set(), []
    for it in items:
        if it["title"] in seen:
            continue
        seen.add(it["title"])
        uniq.append(it)
    uniq = uniq[: args.limit] if args.limit else uniq
    return pack("producthunt", uniq,
                note="静态 HTML 条目有限；要完整榜用内置浏览器渲染 / 或用 decohack 镜像")


# ─────────────────────────── ph.buzzing.cc ───────────────────────────
# PH + HN + 大量站点中文翻译聚合。噪音大，只取 Product Hunt 段落。

def src_ph_buzzing(args):
    url = args.url or "https://ph.buzzing.cc/"
    page = fetch(url)
    items = []
    # 结构: <article id="N" class="card article h-entry">
    #   <a class="p-name entry-title ..." href="https://www.producthunt.com/r/XXX"><span>1. </span>标题</a>
    #   ... <img class="u-photo" src="..."> ...
    #   <footer><time datetime="2026-10-27T07:01:00Z">15:01</time>
    #           <a href="https://www.producthunt.com/products/slug">↑ 118 PH Upvotes</a></footer>
    for art in re.findall(r'<article id="\d+" class="card article h-entry[^"]*">([\s\S]{0,4000}?)</article>', page):
        t = re.search(r'<a class="p-name entry-title[^"]*"[^>]*>([\s\S]{0,300}?)</a>', art)
        if not t:
            continue
        title = re.sub(r"^\s*\d+\.\s*", "", strip_tags(t.group(1)))
        if not title:
            continue
        prod = re.search(r'href="(https://www\.producthunt\.com/products/[^"]+)"', art)
        votes = re.search(r'([\d,]+)\s*PH Upvotes', art)
        tm = re.search(r'<time[^>]*datetime="([^"]+)"', art)
        img = re.search(r'<img[^>]*class="u-photo"[^>]*src="([^"]+)"', art)
        if not img:
            img = re.search(r'<img[^>]*src="([^"]+)"[^>]*class="u-photo"', art)
        items.append(item(len(items) + 1, title,
                          prod.group(1) if prod else url,
                          signal=(votes.group(1) + " 票") if votes else "",
                          published_at=(tm.group(1)[:16].replace("T", " ") if tm else ""),
                          origin="ProductHunt", lang="zh",
                          image=img.group(1) if img else "",
                          read_url=url))
    items = items[: args.limit] if args.limit else items
    return pack("ph-buzzing", items, note=url)


# ─────────────────────────── xbangdan.com/intel ───────────────────────────
# 基于 X 的情报系统（海外/中文区推文、话题、长文、X 日报）。页面大、噪音大，
# 当「补充线索」用，不要当主选题源。

def src_xbangdan(args):
    url = args.url or "https://xbangdan.com/intel/"
    page = fetch(url)
    items = []
    seen = set()
    # 结构: <a class="hzt-it" data-tk="ticker-m" href="/sidehustle/p/xxx/" data-len="46"
    #        title="标题"><span class="hzt-new">新</span><span class="hzt-num">2.5万</span>
    for m in re.finditer(
            r'<a class="hzt-it"[^>]*?href="([^"]+)"[^>]*?title="([^"]+)"[\s\S]{0,600}?'
            r'<span class="hzt-num">([^<]*)</span>', page):
        title = html.unescape(m.group(2)).strip()
        if not title or title in seen:
            continue
        seen.add(title)
        href = m.group(1)
        items.append(item(len(items) + 1, title,
                          href if href.startswith("http") else "https://xbangdan.com" + href,
                          signal=m.group(3).strip(), origin="xbangdan"))
    items = items[: args.limit] if args.limit else items
    return pack("xbangdan", items, note=url)


# ─────────────────────────── discoverhub.cn ───────────────────────────
# GitHub 开源趋势榜中文版。**页面是 JS 渲染的，curl 拿不到数据**（实测 HTML 里
# 没有任何 repo 条目）→ 必须用内置浏览器渲染，或抓它自己的接口。

def src_discoverhub(args):
    return pack("discoverhub", [],
                note=("HTML 是 JS 渲染的，curl 拿不到 repo 数据。要用内置浏览器打开 "
                      "https://discoverhub.cn/trend/github/rank 读 DOM；"
                      "或用 github.com/trending 当等价源（见 --source gh-trending）"))


SOURCES = {
    "aihot": src_aihot,
    "tophub": src_tophub,
    "gh-trending": src_gh_trending,
    "decohack": src_decohack,
    "producthunt": src_producthunt,
    "ph-buzzing": src_ph_buzzing,
    "xbangdan": src_xbangdan,
    "discoverhub": src_discoverhub,
}

TIER = {
    "aihot": "T1 主选题源（中文 AI，带原文链接）",
    "tophub": "T1 全网热榜（中文，带热度值）",
    "decohack": "T1 PH 热榜中文版 + AI 早报 + HN",
    "gh-trending": "T2 开源项目趋势（英文）",
    "producthunt": "T2 官方核对源（静态 HTML 条目少）",
    "ph-buzzing": "T2 聚合站，噪音大",
    "xbangdan": "T2 X 情报，噪音大",
    "discoverhub": "T2 JS 渲染，必须用内置浏览器",
}


def to_material(pk, it, slot="pm"):
    """把一条源条目转成素材包骨架（schemas/material-pack.schema.md 的 web 源形状）。

    agent 只需要再补 metrics 判断、evidence_links 里的原文、treatment_hint。
    """
    import hashlib
    url = it.get("url") or ""
    sig = hashlib.sha1(url.encode()).hexdigest()[:12]
    material_id = "MMDD-%s-%s" % (datetime.datetime.now().strftime("%m%d"), slot)
    return {
        "material_id": material_id,
        "slot": slot,
        "scanned_at": now(),
        "source_kind": "web",
        "source_name": pk["source"],
        "author": {"name": it.get("origin") or pk["source"], "handle": pk["source"], "lang": it.get("lang", "zh")},
        "original": {
            "url": url,
            "post_id": "url:" + sig,
            "posted_at": it.get("published_at", ""),
        },
        "metrics": None,
        "signal": it.get("signal", ""),
        "read_url": it.get("read_url", ""),
        "ai_match": True,
        "summary": it.get("summary", ""),
        "evidence_links": [{"label": "原文", "url": url}],
        "screenshots_needed": ["原文标题+关键段落", "关键数字所在位置"],
        "treatment_hint": "first_person_original",
        "dedup_hits": [],
        "_agent_must_fill": ["ai_match 复核", "evidence_links 补产品页/论文页", "treatment_hint 按内容改"],
    }


def render_text(packs):
    lines = []
    for pk in packs:
        lines.append(f"=== {pk['source']} ({len(pk['items'])} items) {pk.get('note','')}")
        for it in pk["items"]:
            sig = f"  [{it.get('signal','')}]" if it.get("signal") else ""
            pub = f"  {it['published_at']}" if it.get("published_at") else ""
            lines.append(f"  {it['rank']:>2}. {it['title']}{sig}{pub}\n      {it['url']}")
    return "\n".join(lines)


def selftest():
    """验收：每个 T1/T2 源都必须还能抽出条目。源站改版 → 这里立刻红。

    exit 0 = 全过；exit 1 = 有源挂了（选题能力降级，必须知道）。
    """
    must = ["aihot", "tophub", "decohack", "gh-trending", "producthunt",
            "ph-buzzing", "xbangdan"]
    ok = True
    for n in must:
        args = argparse.Namespace(
            source=n, ep="latest", q=None, window=None, category=None, date=None,
            url=None, since=None, limit=3, text=False, list=False)
        try:
            pk = SOURCES[n](args)
            cnt = len(pk["items"])
            good = cnt > 0
            ok = ok and good
            sample = pk["items"][0]["title"][:38] if good else (pk.get("note", "")[:60])
            print("%s %-13s %2d items  | %s" % ("PASS" if good else "FAIL", n, cnt, sample))
        except Exception as exc:
            ok = False
            print("FAIL %-13s 抓取异常: %s: %s" % (n, type(exc).__name__, exc))
    # discoverhub 是 JS 渲染，只验证它能返回「需要浏览器」的说明
    args = argparse.Namespace(source="discoverhub", ep=None, q=None, window=None,
                              category=None, date=None, url=None, since=None,
                              limit=3, text=False, list=False)
    pk = SOURCES["discoverhub"](args)
    note_ok = "浏览器" in pk.get("note", "")
    ok = ok and note_ok
    print("%s %-13s      n/a  | %s" % ("PASS" if note_ok else "FAIL", "discoverhub",
                                        "JS 渲染 → 需内置浏览器（预期）"))
    print("-" * 60)
    print("selftest: %s" % ("ALL PASS" if ok else "HAS FAILURES"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="非 X 内容源统一抓取器")
    ap.add_argument("--source", default="aihot", help="源名，或 all")
    ap.add_argument("--list", action="store_true", help="列出所有源")
    ap.add_argument("--selftest", action="store_true", help="验收：每个源都必须还能抽出条目")
    ap.add_argument("--ep", default=None, help="aihot 子接口: latest/hot/search/daily/weekly/monthly")
    ap.add_argument("--q", default=None, help="aihot search 的关键词")
    ap.add_argument("--window", default=None, help="24h / 7d")
    ap.add_argument("--category", default=None, help="ai-models/ai-products/industry/paper/tip/opinion")
    ap.add_argument("--date", default=None, help="aihot daily/weekly/monthly 的指定期")
    ap.add_argument("--url", default=None, help="覆盖源 URL")
    ap.add_argument("--since", default=None, help="github trending: daily/weekly/monthly")
    ap.add_argument("--limit", type=int, default=0, help="每源最多取几条（0=不限）")
    ap.add_argument("--text", action="store_true", help="紧凑文本输出（给 agent 读）")
    ap.add_argument("--material", action="store_true", help="输出第 1 条的素材包骨架（YAML，给 post-writer-x）")
    ap.add_argument("--slot", default="pm", help="素材包 slot（am/pm/noon/eve/night）")
    args = ap.parse_args()

    if args.list:
        for k, v in TIER.items():
            print(f"{k:14s} {v}")
        return 0
    if args.selftest:
        return selftest()

    names = list(SOURCES) if args.source == "all" else [args.source]
    packs, ok = [], 0
    for n in names:
        fn = SOURCES.get(n)
        if not fn:
            print(f"未知源: {n}（--list 看全部）", file=sys.stderr)
            continue
        try:
            pk = fn(args)
            packs.append(pk)
            if pk["items"]:
                ok += 1
        except Exception as exc:  # 单源失败不能拖垮整轮
            packs.append(pack(n, [], note=f"抓取失败: {type(exc).__name__}: {exc}"))
    if args.material:
        first = next((p for p in packs if p["items"]), None)
        if not first:
            print("# 没有可用条目：0 候选", file=sys.stderr)
            return 1
        mat = to_material(first, first["items"][0], args.slot)
        print("# 素材包骨架（source_kind=web）—— agent 补完 _agent_must_fill 里的项再交 post-writer-x")
        for k, v in mat.items():
            if k == "_agent_must_fill":
                print("# TODO: " + " / ".join(v))
                continue
            if isinstance(v, dict):
                print(f"{k}:")
                for k2, v2 in v.items():
                    if isinstance(v2, list):
                        inner = "; ".join(f"{x.get('label')}: {x.get('url')}" if isinstance(x, dict) else str(x) for x in v2)
                        print(f"  {k2}: [{inner}]")
                    else:
                        print(f"  {k2}: {v2}")
            elif isinstance(v, list):
                print(f"{k}: [{'; '.join(str(x) for x in v)}]")
            else:
                print(f"{k}: {v}")
        return 0
    if args.text:
        print(render_text(packs))
    else:
        print(json.dumps(packs if args.source == "all" else packs[0],
                         ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    import urllib.parse  # noqa: E402  (src_aihot 用)
    raise SystemExit(main())
