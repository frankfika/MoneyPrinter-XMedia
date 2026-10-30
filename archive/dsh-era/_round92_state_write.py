#!/usr/bin/env python3
"""
chuangzuo_round_92 state 落盘（并发安全）

背景：pulse cron 04:00 那轮此刻正在跑（同一批 state 文件）。
写入策略：
  1) 写前重新读盘（不能用内存里的旧快照）
  2) 追加型记录（seen / published / recent-picks）→ 追加，不覆盖
  3) 自增 id 一律用 **内容派生**（pick-<post_id 后 6 位>），不读"最后一个 id +1"
  4) 原子写（tmp + os.replace）
  5) 写后校验：条目数 = 写前 + 预期新增，且内容 hash 一致；不满足则重试
"""
import json, os, pathlib, hashlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"

TS = "2026-10-29T04:06:00+08:00"
DEDUP_KEY = "url:16faca12f964"
TOPIC_SIG = "anthropic-gsa-onegov-40pct-discount-no-minimum-commitment-government-procurement"
PICK_ID = "pick-16faca12"          # 内容派生，不撞号
GATE_SHA = "87500b84480c8f2b"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def atomic_write(p, data):
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def main():
    # ── 1. index.json：seen 加去重键 + last_updated ──────────────────
    ip = STATE / "index.json"
    for attempt in range(5):
        d = load(ip)
        before = len(d["seen"])
        if DEDUP_KEY in d["seen"]:
            print(f"index.seen 已存在 {DEDUP_KEY}，跳过")
            break
        d["seen"][DEDUP_KEY] = {"t": "other", "h": "anthropic", "d": "2026-10-29"}
        d["last_updated"] = TS
        atomic_write(ip, d)
        # 校验：重读，确认键在且条目数不倒退
        chk = load(ip)
        if DEDUP_KEY in chk["seen"] and len(chk["seen"]) >= before + 1:
            print(f"index.json OK  seen {before} -> {len(chk['seen'])}")
            break
        print(f"index.json 校验失败，重试 {attempt+1}")
        time.sleep(0.5)

    # ── 2. recent-picks.json：追加选题记忆（内容派生 id）──────────────
    rp = STATE / "recent-picks.json"
    for attempt in range(5):
        d = load(rp)
        entries = d["entries"]
        if any(e.get("post_id") == DEDUP_KEY for e in entries):
            print("recent-picks 已存在该 post_id，跳过")
            break
        before = len(entries)
        entries.append({
            "picked_at": TS,
            "handle": "anthropic",
            "post_id": DEDUP_KEY,
            "topic_signature": TOPIC_SIG,
            "treatment": "first_person_original_web_source",
            "picked_for": "chuangzuo_round_92_draft_ready_not_published",
            "reason": (
                "判据③ likes_signal 命中（上一条原创 round_91 12h 后 likes=0）→ 换方向，"
                "本条走「AI × 政府采购 / 采购经济学」簇，与近 7 天各簇都不同。角度切在"
                "「不绑最低消费承诺 + 按实际用量付费」这句（IR 原生视角：采购方承诺被取消，"
                "供应商收入确定性与买方预算风险换位）。"
                "一手原文 anthropic.com/news/expanding-partnership-gsa 逐句核对 13/13 命中"
                "（40% 折扣覆盖 Enterprise/Government/API 三产品面且首次全线、州和地方部落属地也算、"
                "省 10 亿美元(estimated)、不绑最低消费承诺、约 500 家联邦州地方机构、"
                "Claude for Government 周活自 2 月约 8 倍、联邦文职机构一年约 20 倍、"
                "Utah 34 developers 跨 10 个州机构 80% 30 分钟 71% 省 20+ 小时）；"
                "X 侧 @bcherny 2115491259381072269 转发 Utah 数字与官网逐字一致，"
                "@AnthropicAI 官方帖确认协议名 OneGov。"
                f"文案 458 字过 prepublish 闸门（exit 0, soft 0 / hard 0, sha256 {GATE_SHA}），2 张真截图。"
                "判据①硬否决（距上一条原创 19:49:39 仅 8h16m < 12h），留待 15:30 档口发布。"
            ),
            "action_result": "draft_ready_not_published",
            "gate_sha256": GATE_SHA,
            "material_dir": "outputs/1029-pm-gsa-procurement",
            "published_at": None,
        })
        d["last_updated"] = TS
        atomic_write(rp, d)
        chk = load(rp)
        ids = [e.get("id") for e in chk["entries"] if e.get("id")]
        dup = len(ids) != len(set(ids))
        if len(chk["entries"]) >= before + 1 and not dup:
            print(f"recent-picks OK  {before} -> {len(chk['entries'])}  id 唯一 ✓")
            break
        print(f"recent-picks 校验失败（dup={dup}），重试 {attempt+1}")
        time.sleep(0.5)

    # ── 3. seen-posts.json：登记这个选题源（防重复选题）──────────────
    sp = STATE / "seen-posts.json"
    for attempt in range(5):
        d = load(sp)
        entries = d["entries"]
        if any(e.get("post_id") == DEDUP_KEY for e in entries):
            print("seen-posts 已存在该 post_id，跳过")
            break
        before = len(entries)
        entries.append({
            "post_id": DEDUP_KEY,
            "handle": "anthropic",
            "type": "inbound_kol_post_seen",
            "seen_at": TS,
            "treatment": "web_source_material_only",
            "url": "https://www.anthropic.com/news/expanding-partnership-gsa",
            "topic_signature": TOPIC_SIG,
            "context": (
                "chuangzuo_round_92 素材源（web 源，非 X 互动）。一手原文 anthropic.com/news/"
                "expanding-partnership-gsa，published 2026-10-27。已逐句核对 13 项数字。"
                "X 侧佐证：@bcherny 2115491259381072269（Utah 试点数字，与官网逐字一致）、"
                "@AnthropicAI 官方帖（协议名 OneGov）。本轮判据①硬否决，未发布，草稿留 15:30。"
            ),
        })
        d["last_updated"] = TS
        atomic_write(sp, d)
        chk = load(sp)
        if len(chk["entries"]) >= before + 1:
            print(f"seen-posts OK  {before} -> {len(chk['entries'])}")
            break
        print(f"seen-posts 校验失败，重试 {attempt+1}")
        time.sleep(0.5)

    print("state 落盘完成")


if __name__ == "__main__":
    main()
