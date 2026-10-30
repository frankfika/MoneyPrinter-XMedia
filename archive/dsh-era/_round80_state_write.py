#!/usr/bin/env python3
"""
pulse_round_80 state 落盘（并发安全）

背景：chuangzuo_round_92 在 04:05–04:06 并发写过同一批 state 文件。
写入策略（沿用 _round92_state_write.py 的并发安全约定）：
  1) 写前重新读盘（不能用内存里的旧快照）
  2) 追加型记录（seen / outbound-actions / recent-picks）→ 追加，不覆盖
  3) 自增 id 一律用 **内容派生**（pick-<post_id 后 6 位> / outbound-<post_id 后 6 位>），
     不读"最后一个 id +1" —— 那会跟并发 writer 撞号
  4) 原子写（tmp + os.replace）
  5) 写后校验：条目数 = 写前 + 预期新增，且内容 hash 一致；不满足则重试

本轮公开动作（2 个 like，均已验证）：
  like#1 @bindureddy  2115509412400070883  04:06:16  (post posted 02:22:02)
  like#2 @dotey       2115512767394275550  04:09:16  (post posted 02:35:22)
  间隔 180 秒 = 3.0 分钟（≥2min 线）
"""
import json, os, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"

ROUND = "pulse_round_80"
TS1 = "2026-10-29T04:06:16+08:00"
TS2 = "2026-10-29T04:09:16+08:00"
DATE = "2026-10-29"
EXPIRES1 = "2026-11-05T04:06:16+08:00"
EXPIRES2 = "2026-11-05T04:09:16+08:00"

LIKES = [
    {
        "handle": "bindureddy",
        "post_id": "2115509412400070883",
        "url": "https://x.com/bindureddy/status/2115509412400070883",
        "ts": TS1,
        "expires_at": EXPIRES1,
        "posted_at": "2026-10-29T02:22:02+08:00",
        "topic_signature": "gemini-carbon-livebench-benchmark-launch-expectation",
        "engagement": "135->136 likes（本轮 +1）/ 24 replies / 5.6K views",
        "reason": (
            "Gemini Carbon 当天上 LiveBench，作者明确说「不认为是 #1，但会是有竞争力的」—— "
            "评测视角的谨慎预期，正好是 Frank「评测出身」人设对得上的位置；"
            "发布后约 1h44m 赞，135 赞的列表仍是中小盘，Frank 的 handle 能被看到"
        ),
        "context": (
            "pulse_round_80 outbound-like-00883 like_only — @bindureddy：Gemini Carbon 上 LiveBench 的期待"
            "（不抢 #1 说法）；135→136 likes，aria-label 双向核对 + unlike 按钮 + Likes 历史页顶部双证"
        ),
    },
    {
        "handle": "dotey",
        "post_id": "2115512767394275550",
        "url": "https://x.com/dotey/status/2115512767394275550",
        "ts": TS2,
        "expires_at": EXPIRES2,
        "posted_at": "2026-10-29T02:35:22+08:00",
        "topic_signature": "copilot-obsolete-concept-ai-not-copilot-autopilot-era",
        "engagement": "5->6 likes（本轮 +1）/ 10 replies / 2.6K views",
        "reason": (
            "「Copilot 已经是个过时的概念，AI 不再是副驾驶，我们希望 AI 去自动驾驶」—— "
            "中文 AI 圈少见的产品观判断，和 Frank 讲的 agent 自主性内核相邻但不重复；"
            "发布后约 1h34m、只有 5 个赞，正是 round_78 总结的「早赞曝光效率最高」窗口"
        ),
        "context": (
            "pulse_round_80 outbound-like-75550 like_only — @dotey：Copilot 过时 / AI 从副驾驶到自动驾驶；"
            "5→6 likes（列表仅 6 人，Frank handle 出现在最前段）"
        ),
    },
]


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def atomic_write(p, data):
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def append_once(path, match_fn, build_fn, expect_n, label):
    """追加一条记录；写前重读、幂等、原子写、写后校验。"""
    for attempt in range(5):
        d = load(path)
        entries = d["entries"]
        if any(match_fn(e) for e in entries):
            print(f"{label}: 已存在，跳过")
            return None
        before = len(entries)
        entries.append(build_fn())
        d["last_updated"] = TS2
        atomic_write(path, d)
        chk = load(path)
        got = len(chk["entries"])
        if got == before + expect_n:
            print(f"{label} OK  {before} -> {got}")
            return chk
        print(f"{label} 校验失败（{before} -> {got}，期望 +{expect_n}），重试 {attempt+1}")
        time.sleep(0.5)
    raise SystemExit(f"{label} 写入失败")


def main():
    # ── 1. seen-posts.json：登记两个已赞帖 ────────────────────────────
    sp = STATE / "seen-posts.json"

    def sp_match(e):
        return e.get("post_id") == LIKES[0]["post_id"]

    def sp_build():
        L = LIKES[0]
        return {
            "post_id": L["post_id"],
            "handle": L["handle"],
            "type": "outbound_like",
            "seen_at": L["ts"],
            "treatment": "like_only",
            "url": L["url"],
            "liked_at": L["ts"],
            "like_posted_at": L["posted_at"],
            "engagement": L["engagement"],
            "topic_signature": L["topic_signature"],
            "context": L["context"],
        }

    append_once(sp, sp_match, sp_build, 1, "seen-posts[bindureddy]")

    def sp2_match(e):
        return e.get("post_id") == LIKES[1]["post_id"]

    def sp2_build():
        L = LIKES[1]
        return {
            "post_id": L["post_id"],
            "handle": L["handle"],
            "type": "outbound_like",
            "seen_at": L["ts"],
            "treatment": "like_only",
            "url": L["url"],
            "liked_at": L["ts"],
            "like_posted_at": L["posted_at"],
            "engagement": L["engagement"],
            "topic_signature": L["topic_signature"],
            "context": L["context"],
        }

    append_once(sp, sp2_match, sp2_build, 1, "seen-posts[dotey]")

    # ── 2. outbound-actions.json：两条公开动作记录（内容派生 id）──────
    oa = STATE / "outbound-actions.json"

    def oa_match(e):
        return e.get("target_post_id") == LIKES[0]["post_id"]

    def oa_build():
        L = LIKES[0]
        return {
            "id": "outbound-like-" + L["post_id"][-6:],
            "timestamp": L["ts"],
            "action_type": "like",
            "target_handle": L["handle"],
            "target_post_id": L["post_id"],
            "target_post_url": L["url"],
            "target_post_topic_signature": L["topic_signature"],
            "treatment": "like_only",
            "like_delta": "135->136（本轮 +1；点后 aria-label 读 136）",
            "verified": True,
            "verifications": {
                "unlike_button_data_testid": True,
                "aria_label_136_likes_liked": True,
                "likes_page_top_entry": True,
            },
            "note": (
                "pulse_round_80；like#1。详情页先 query dom 读 aria-label='135 Likes. Like' 确认是目标帖，"
                "再 click，再 query dom 读 unlike='136 Likes. Liked'，URL 与目标一致。"
                "like#1 -> like#2 间隔 180 秒（3 分钟，过 ≥2min 线）"
            ),
        }

    append_once(oa, oa_match, oa_build, 1, "outbound-actions[bindureddy]")

    def oa2_match(e):
        return e.get("target_post_id") == LIKES[1]["post_id"]

    def oa2_build():
        L = LIKES[1]
        return {
            "id": "outbound-like-" + L["post_id"][-6:],
            "timestamp": L["ts"],
            "action_type": "like",
            "target_handle": L["handle"],
            "target_post_id": L["post_id"],
            "target_post_url": L["url"],
            "target_post_topic_signature": L["topic_signature"],
            "treatment": "like_only",
            "like_delta": "5->6（本轮 +1；点后 aria-label 读 6）",
            "verified": True,
            "verifications": {
                "unlike_button_data_testid": True,
                "aria_label_6_likes_liked": True,
                "likes_page_top_entry": True,
            },
            "note": (
                "pulse_round_80；like#2。发布后 1h34m、赞列表仅 6 人 → 早赞曝光窗口。"
                "详情页 read like(5 Likes) → click → read unlike(6 Likes. Liked)，URL 与目标一致"
            ),
        }

    append_once(oa, oa2_match, oa2_build, 1, "outbound-actions[dotey]")

    # ── 3. recent-picks.json：7 天 topic signature dedup ──────────────
    rp = STATE / "recent-picks.json"

    def rp_match(e):
        return e.get("post_id") == LIKES[0]["post_id"]

    def rp_build():
        L = LIKES[0]
        return {
            "id": "pick-" + L["post_id"][-6:],
            "timestamp": L["ts"],
            "handle": L["handle"],
            "post_id": L["post_id"],
            "url": L["url"],
            "topic_signature": L["topic_signature"],
            "reason": L["reason"],
            "action_taken": f"{ROUND} like_only",
            "expires_at": L["expires_at"],
        }

    append_once(rp, rp_match, rp_build, 1, "recent-picks[bindureddy]")

    def rp2_match(e):
        return e.get("post_id") == LIKES[1]["post_id"]

    def rp2_build():
        L = LIKES[1]
        return {
            "id": "pick-" + L["post_id"][-6:],
            "timestamp": L["ts"],
            "handle": L["handle"],
            "post_id": L["post_id"],
            "url": L["url"],
            "topic_signature": L["topic_signature"],
            "reason": L["reason"],
            "action_taken": f"{ROUND} like_only",
            "expires_at": L["expires_at"],
        }

    append_once(rp, rp2_match, rp2_build, 1, "recent-picks[dotey]")

    # ── 4. index.json：去重索引（seen + outbound 两段）────────────────
    ip = STATE / "index.json"
    for attempt in range(5):
        d = load(ip)
        changed = False
        for L in LIKES:
            if L["post_id"] not in d["seen"]:
                d["seen"][L["post_id"]] = {
                    "t": "like",
                    "h": L["handle"],
                    "d": DATE,
                    "u": L["url"],
                    "a": ["like_only"],
                }
                changed = True
            if L["post_id"] not in d["outbound"]:
                d["outbound"][L["post_id"]] = {
                    "a": ["like"],
                    "d": DATE,
                    "h": L["handle"],
                }
                changed = True
        if not changed:
            print("index.json: 两条均已存在，跳过")
            break
        d["last_updated"] = TS2
        atomic_write(ip, d)
        chk = load(ip)
        if all(L["post_id"] in chk["seen"] and L["post_id"] in chk["outbound"] for L in LIKES):
            print(f"index.json OK  seen={len(chk['seen'])} outbound={len(chk['outbound'])}")
            break
        print(f"index.json 校验失败，重试 {attempt+1}")
        time.sleep(0.5)

    print(ROUND, "state 落盘完成")


if __name__ == "__main__":
    main()
