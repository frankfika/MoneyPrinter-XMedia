#!/usr/bin/env python3
"""
pulse_round_82 state 落盘（并发安全）

沿用 _round81_state_write.py 的约定：
  1) 写前重新读盘
  2) 追加型记录（seen / outbound-actions / recent-picks）→ 追加，不覆盖
  3) 自增 id 一律内容派生（pick-<post_id 后 6 位> / outbound-like-<post_id 后 6 位>）
  4) 原子写（tmp + os.replace）
  5) 写后校验：条目数 + **值 ↔ 位置映射**（round_81 的教训：只校验「值出现过」会漏掉写反）

本轮公开动作（2 个 like，均已验证）：
  like#1 @vista8     2115818384881508545  23:54:15  (post posted 22:49:47, 赞时 64m, 11->12 likes)
  like#2 @_akhaliq   2115826286652248275  23:57:12  (post posted 23:21:11, 赞时 36m,  9->10 likes)
  间隔 176.853 秒 = 2.95 分钟（≥2min 线）

本轮补账（非 agent 动作）：
  Frank 手动 reply @IncomprisSage  own_post_id 2115791244064690547 @ 2026-10-29T21:01:56+08:00
  → 写 outbound reply 字段，**不动 last_published_at**（12h 闸门只数根帖，reply 不计入）

本轮留痕（闸 1 身份质疑，默认不回）：
  @mumblinglewis 2114581731747717523 (Oct 26) 「鉴定训练失败，100%AI味」→ skipped_no_reply
"""
import json, os, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
YAML = ROOT / "private" / "account-safety.yaml"

ROUND = "pulse_round_82"
TS1 = "2026-10-29T23:54:15+08:00"
TS2 = "2026-10-29T23:57:12+08:00"
DATE = "2026-10-29"
EXP1 = "2026-11-05T23:54:15+08:00"
EXP2 = "2026-11-05T23:57:12+08:00"

LIKES = [
    {
        "handle": "vista8",
        "post_id": "2115818384881508545",
        "url": "https://x.com/vista8/status/2115818384881508545",
        "ts": TS1,
        "expires_at": EXP1,
        "posted_at": "2026-10-29T22:49:47+08:00",
        "topic_signature": "personal-site-ai-posting-feature-one-prompt-vibe-programming-x-xhs-sync",
        "engagement": "11->12 likes（本轮 +1）/ 12 replies / 2 reposts / 1.7K views",
        "reason": (
            "「给个人网站加了一个『随想』栏目…提示词就一句话…简单调试优化几轮就行了，"
            "AI 变强后，真的是『许愿式编程』」—— 一手 builder 实践 + 自己动手发 X/小红书，"
            "与 Frank「前工程师 + 自建发布流水线」几乎同一条线；"
            "发布 64 分钟、赞列表仅 11 人 → 早赞窗口内 Frank handle 靠前"
        ),
        "context": (
            "pulse_round_82 outbound-like-508545 like_only — @vista8：个人网站加 X 式「随想」栏目，"
            "一句话提示词 + 许愿式编程；11→12 likes（赞列表 11 人），aria-label 双向核对 + unlike 按钮 + "
            "Likes 历史页顶部三证"
        ),
        "like_delta": "11->12（本轮 +1；点后 aria-label 读 12 Likes. Liked）",
        "aria": "12 Likes. Liked",
    },
    {
        "handle": "_akhaliq",
        "post_id": "2115826286652248275",
        "url": "https://x.com/_akhaliq/status/2115826286652248275",
        "ts": TS2,
        "expires_at": EXP2,
        "posted_at": "2026-10-29T23:21:11+08:00",
        "topic_signature": "omnidirectional-subject-consistent-video-generation-multi-view-images-paper",
        "engagement": "9->10 likes（本轮 +1）/ 2 replies / 3 reposts / 2.6K views（Likes 页卡片此刻显示 11，是他人后续点赞）",
        "reason": (
            "「OmniShowcase：多视角图像 → 主体一致的全向视频生成」—— 主体一致性跨视角是典型的"
            "质量评测维度，与 Frank「评测出身」合得来；发布 36 分钟、赞列表仅 9 人 → 曝光效率最高的一条"
        ),
        "context": (
            "pulse_round_82 outbound-like-248275 like_only — @_akhaliq：多视角图 → 主体一致全向视频生成论文；"
            "9→10 likes（赞列表 9 人），aria-label 双向核对 + unlike 按钮 + Likes 历史页顶部三证"
        ),
        "like_delta": "9->10（本轮 +1；点后 aria-label 读 10 Likes. Liked）",
        "aria": "10 Likes. Liked",
    },
]

# ── 非 agent 动作：Frank 手动发的 reply（平台侧对账发现）──────────────
MANUAL_REPLY = {
    "own_post_id": "2115791244064690547",
    "own_url": "https://x.com/FrankFika/status/2115791244064690547",
    "target_handle": "IncomprisSage",
    "target_post_id": "2115385755266601207",
    "target_post_url": "https://x.com/IncomprisSage/status/2115385755266601207",
    "ts": "2026-10-29T21:01:56+08:00",
    "target_posted_at": "2026-10-28T18:10:40+08:00",
    "topic_signature": "france-indigenous-population-race-remark-reply-incompris-sage",
    "text": "@IncomprisSage 。。法国原住民都快成黑人了。。",
}

# ── 本轮补记的 skip 留痕（闸 1 身份质疑）────────────────────────────
SKIP_INBOUND = {
    "handle": "mumblinglewis",
    "post_id": "2114581731747717523",
    "url": "https://x.com/mumblinglewis/status/2114581731747717523",
    "date": "2026-10-26",
    "topic_signature": "auth-training-failed-100pct-ai-flavor-identity-challenge",
}


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def atomic_write(p, data):
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def append_once(path, match_fn, build_fn, expect_n, label):
    for attempt in range(5):
        d = load(path)
        entries = d["entries"]
        if any(match_fn(e) for e in entries):
            print(f"{label}: 已存在，跳过")
            return
        before = len(entries)
        entries.append(build_fn())
        d["last_updated"] = TS2
        atomic_write(path, d)
        chk = load(path)
        got = len(chk["entries"])
        if got == before + expect_n:
            print(f"{label} OK  {before} -> {got}")
            return
        print(f"{label} 校验失败（{before} -> {got}，期望 +{expect_n}），重试 {attempt+1}")
        time.sleep(0.5)
    raise SystemExit(f"{label} 写入失败")


def main():
    # ── 0. 写前快照（校验用）────────────────────────────────────────
    sp = STATE / "seen-posts.json"
    oa = STATE / "outbound-actions.json"
    rp = STATE / "recent-picks.json"
    ip = STATE / "index.json"
    pre = {
        "seen": len(load(sp)["entries"]),
        "oa": len(load(oa)["entries"]),
        "rp": len(load(rp)["entries"]),
        "idx_seen": len(load(ip)["seen"]),
        "idx_out": len(load(ip)["outbound"]),
    }
    print("写前快照:", pre)

    # 参考：已有 skip 条目的字段形态（保持一致）
    for e in load(sp)["entries"]:
        if e.get("post_id") == "2115084100054942112":
            print("参考 skip 条目字段:", sorted(e.keys()))
            break

    # ── 1. seen-posts.json ───────────────────────────────────────────
    for L in LIKES:
        def m(e, L=L):
            return e.get("post_id") == L["post_id"]

        def b(L=L):
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

        append_once(sp, m, b, 1, f"seen-posts[{L['handle']}]")

    # Frank 手动 reply 的目标帖 —— 登记为已出手，防止后续轮次再选
    def m_manual(e):
        return e.get("post_id") == MANUAL_REPLY["target_post_id"]

    def b_manual():
        return {
            "post_id": MANUAL_REPLY["target_post_id"],
            "handle": MANUAL_REPLY["target_handle"],
            "type": "outbound_reply_manual",
            "seen_at": MANUAL_REPLY["ts"],
            "treatment": "frank_manual_reply_not_agent",
            "url": MANUAL_REPLY["target_post_url"],
            "own_post_id": MANUAL_REPLY["own_post_id"],
            "own_post_url": MANUAL_REPLY["own_url"],
            "topic_signature": MANUAL_REPLY["topic_signature"],
            "context": (
                "pulse_round_82 平台侧对账补账 —— Frank 本人手动发的 reply（不在任何 agent 轮次日志里）："
                f"own_post_id {MANUAL_REPLY['own_post_id']} @ {MANUAL_REPLY['ts']}，"
                f"目标帖 {MANUAL_REPLY['target_post_id']}（{MANUAL_REPLY['target_posted_at']} 发）。"
                "正文：「@IncomprisSage 。。法国原住民都快成黑人了。。」"
            ),
        }

    append_once(sp, m_manual, b_manual, 1, "seen-posts[IncomprisSage 手动 reply 补账]")

    # 闸 1 留痕
    def m_skip(e):
        return e.get("post_id") == SKIP_INBOUND["post_id"]

    def b_skip():
        return {
            "post_id": SKIP_INBOUND["post_id"],
            "handle": SKIP_INBOUND["handle"],
            "type": "inbound_reply",
            "seen_at": "2026-10-29T23:59:00+08:00",
            "treatment": "skipped_no_reply",
            "url": SKIP_INBOUND["url"],
            "topic_signature": SKIP_INBOUND["topic_signature"],
            "context": (
                "pulse_round_82 补记留痕 —— @mumblinglewis Oct 26 的 reply「鉴定训练失败，100%AI味」"
                "（Replying to @FrankFika and @dotey，已在 Mentions 页确证是发给 @FrankFika 的）："
                "属闸 1 身份质疑（质疑内容是 AI 写的 / 自动化痕迹），按 SKILL 默认不回，只留痕。"
                "此前 round_81 扫到过但没写台账 → 每轮都要重新评估，本轮补上。"
            ),
        }

    append_once(sp, m_skip, b_skip, 1, "seen-posts[mumblinglewis 闸1 留痕]")

    # ── 2. outbound-actions.json ─────────────────────────────────────
    for idx, L in enumerate(LIKES):
        def m(e, L=L):
            return e.get("target_post_id") == L["post_id"]

        def b(L=L, idx=idx):
            return {
                "id": "outbound-like-" + L["post_id"][-6:],
                "timestamp": L["ts"],
                "action_type": "like",
                "target_handle": L["handle"],
                "target_post_id": L["post_id"],
                "target_post_url": L["url"],
                "target_post_topic_signature": L["topic_signature"],
                "treatment": "like_only",
                "like_delta": L["like_delta"],
                "verified": True,
                "verifications": {
                    "unlike_button_data_testid": True,
                    "aria_label_liked": True,
                    "likes_page_top_entry": True,
                    "url_matches_target": True,
                },
                "note": (
                    f"{ROUND}；like#{idx+1}。详情页先 query dom 读 aria-label 确认是目标帖且未赞，"
                    "再 click，再 query dom 读 unlike + aria-label='Liked'，URL 与目标一致。"
                    "like#1 -> like#2 间隔 176.853 秒（2.95 分钟，过 ≥2min 线）；"
                    "两次赞之间用显式 wait 60+60 秒兑现间隔，不靠顺手调用凑时间"
                ),
            }

        append_once(oa, m, b, 1, f"outbound-actions[{L['handle']}]")

    def m_mr(e):
        return e.get("own_post_id") == MANUAL_REPLY["own_post_id"] and e.get("agent_generated") is False

    def b_mr():
        return {
            "id": "outbound-reply-" + MANUAL_REPLY["target_post_id"][-6:],
            "timestamp": MANUAL_REPLY["ts"],
            "action_type": "reply",
            "target_handle": MANUAL_REPLY["target_handle"],
            "target_post_id": MANUAL_REPLY["target_post_id"],
            "target_post_url": MANUAL_REPLY["target_post_url"],
            "target_post_topic_signature": MANUAL_REPLY["topic_signature"],
            "treatment": "frank_manual_reply_not_agent",
            "own_post_id": MANUAL_REPLY["own_post_id"],
            "own_post_url": MANUAL_REPLY["own_url"],
            "source": "frank_manual",
            "agent_generated": False,
            "verified": True,
            "verifications": {
                "from_search_first_result": True,
                "snowflake_timestamp": True,
                "own_post_page_title_matches": True,
            },
            "note": (
                f"{ROUND} 平台侧对账补账 —— 这条 reply 是 **Frank 本人手动发的**，"
                "不是任何 agent 轮次产出（轮次日志覆盖不到）。发现方式："
                "`search?q=from:FrankFika` 首条 = 2115791244064690547，snowflake 反解 = "
                f"{MANUAL_REPLY['ts']}，比 account-safety.yaml#x.last_published_at（10-28 19:49:39 那条 "
                "Quote 根帖）新。⚠️ **它是一条 reply，不是根帖 → 不计入 chuangzuo 的 12h 闸门**，"
                "所以 last_published_at 保持不动；只更新 last_outbound_reply_* 系列。"
            ),
        }

    append_once(oa, m_mr, b_mr, 1, "outbound-actions[Frank 手动 reply 补账]")

    # ── 3. recent-picks.json（7 天 topic signature dedup）────────────
    for L in LIKES:
        def m(e, L=L):
            return e.get("post_id") == L["post_id"]

        def b(L=L):
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

        append_once(rp, m, b, 1, f"recent-picks[{L['handle']}]")

    def m_mrp(e):
        return e.get("post_id") == MANUAL_REPLY["target_post_id"]

    def b_mrp():
        return {
            "id": "pick-" + MANUAL_REPLY["target_post_id"][-6:],
            "timestamp": MANUAL_REPLY["ts"],
            "handle": MANUAL_REPLY["target_handle"],
            "post_id": MANUAL_REPLY["target_post_id"],
            "url": MANUAL_REPLY["target_post_url"],
            "topic_signature": MANUAL_REPLY["topic_signature"],
            "reason": (
                "Frank 本人手动回过这条（France 原住民 / 种族话题）—— 非 agent 产出。"
                "记进 dedup 是为了不让后续轮次把这个话题再当成候选（该话题对外争议大，"
                "Frank 既然已经自己表过态，agent 不必再碰）"
            ),
            "action_taken": f"frank_manual_reply (非 {ROUND} 动作)",
            "expires_at": "2026-11-05T21:01:56+08:00",
        }

    append_once(rp, m_mrp, b_mrp, 1, "recent-picks[IncomprisSage 手动 reply dedup]")

    # ── 4. index.json ────────────────────────────────────────────────
    for attempt in range(5):
        d = load(ip)
        changed = False
        for L in LIKES:
            if L["post_id"] not in d["seen"]:
                d["seen"][L["post_id"]] = {
                    "t": "like", "h": L["handle"], "d": DATE, "u": L["url"], "a": ["like_only"],
                }
                changed = True
            if L["post_id"] not in d["outbound"]:
                d["outbound"][L["post_id"]] = {"a": ["like"], "d": DATE, "h": L["handle"]}
                changed = True
        if SKIP_INBOUND["post_id"] not in d["seen"]:
            d["seen"][SKIP_INBOUND["post_id"]] = {
                "t": "skip", "h": SKIP_INBOUND["handle"], "d": DATE,
                "u": SKIP_INBOUND["url"], "a": ["skipped_no_reply"],
            }
            changed = True
        # Frank 手动 reply：目标帖 + 自己那条 reply id
        if MANUAL_REPLY["target_post_id"] not in d["seen"]:
            d["seen"][MANUAL_REPLY["target_post_id"]] = {
                "t": "reply", "h": MANUAL_REPLY["target_handle"], "d": DATE,
                "u": MANUAL_REPLY["target_post_url"], "a": ["frank_manual_reply"],
            }
            changed = True
        if MANUAL_REPLY["own_post_id"] not in d["seen"]:
            d["seen"][MANUAL_REPLY["own_post_id"]] = {
                "t": "own", "h": "FrankFika", "d": DATE,
                "u": MANUAL_REPLY["own_url"], "a": ["reply"],
            }
            changed = True
        if MANUAL_REPLY["target_post_id"] not in d["outbound"]:
            d["outbound"][MANUAL_REPLY["target_post_id"]] = {
                "a": ["reply"], "d": DATE, "h": MANUAL_REPLY["target_handle"],
            }
            changed = True
        if MANUAL_REPLY["own_post_id"] not in d["outbound"]:
            d["outbound"][MANUAL_REPLY["own_post_id"]] = {
                "a": ["reply"], "d": DATE, "h": "FrankFika",
            }
            changed = True
        if not changed:
            print("index.json: 全部已存在，跳过")
            break
        d["last_updated"] = TS2
        atomic_write(ip, d)
        chk = load(ip)
        # 校验：出手的帖（like + 手动 reply 目标 + 手动 reply 自己那条）要同时在 seen 和 outbound；
        # skip 类记录（@mumblinglewis 闸 1 留痕）**只在 seen** —— 没出手就不该进 outbound。
        must_be_both = [L["post_id"] for L in LIKES] + [
            MANUAL_REPLY["target_post_id"], MANUAL_REPLY["own_post_id"],
        ]
        ok = all(pid in chk["seen"] and pid in chk["outbound"] for pid in must_be_both)
        ok = ok and SKIP_INBOUND["post_id"] in chk["seen"]
        ok = ok and SKIP_INBOUND["post_id"] not in chk["outbound"]
        if ok:
            print(f"index.json OK  seen={len(chk['seen'])} outbound={len(chk['outbound'])}")
            break
        print(f"index.json 校验失败，重试 {attempt+1}")
        time.sleep(0.5)

    # ── 5. account-safety.yaml ───────────────────────────────────────
    # 5a. like 滚动 4 槽位（slot1 = 最近一次赞）
    prev = [
        ("2026-10-29T10:18:10+08:00", "2115494806004613515", "jiqizhixin",
         "embodied-benchmark-simulation-vs-real-robot-gap-zero-plug-insertions"),
        ("2026-10-29T10:14:14+08:00", "2115618084044349828", "dotey",
         "worktree-parallel-agent-tasks-local-vs-cloud-verification-cost"),
        ("2026-10-29T04:09:16+08:00", "2115512767394275550", "dotey",
         "copilot-obsolete-concept-ai-not-copilot-autopilot-era"),
        ("2026-10-29T04:06:16+08:00", "2115509412400070883", "bindureddy",
         "gemini-carbon-livebench-benchmark-launch-expectation"),
    ]
    new = sorted(
        [(L["ts"], L["post_id"], L["handle"], L["topic_signature"]) for L in LIKES],
        key=lambda r: r[0], reverse=True,
    )
    merged = (new + prev)[:4]

    lines = YAML.read_text(encoding="utf-8").split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("last_outbound_like_at:"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("last_outbound_like"):
                j += 1
            for n, (at, pid, h, sig) in enumerate(merged, start=1):
                suffix = "" if n == 1 else f"_{n}"
                out.append(f'  last_outbound_like{suffix}_at: "{at}"')
                out.append(f'  last_outbound_like{suffix}_target_post_id: "{pid}"')
                out.append(f"  last_outbound_like{suffix}_target_handle: {h}")
                out.append(f"  last_outbound_like{suffix}_topic_signature: {sig}")
            i = j
            continue
        out.append(ln)
        i += 1
    text = "\n".join(out)

    # 5b. outbound reply 字段（Frank 手动 reply 补账）
    #     ⚠️ last_published_at **不动** —— 12h 闸门只数根帖，reply 不计入
    repl = [
        ('  last_outbound_reply_at: "2026-10-27T19:31:11+08:00"',
         f'  last_outbound_reply_at: "{MANUAL_REPLY["ts"]}"'),
        ('  last_outbound_reply_own_post_id: "2115043630008369379"',
         f'  last_outbound_reply_own_post_id: "{MANUAL_REPLY["own_post_id"]}"'),
        ('  last_outbound_reply_target_post_id: "2114952872458633296"',
         f'  last_outbound_reply_target_post_id: "{MANUAL_REPLY["target_post_id"]}"'),
        ('  last_outbound_reply_treatment: regular_post_original_mode_no_url_citation',
         '  last_outbound_reply_treatment: frank_manual_reply_not_agent'),
        ('  last_outbound_reply_target_handle: dotey',
         f'  last_outbound_reply_target_handle: {MANUAL_REPLY["target_handle"]}'),
        ('  last_outbound_reply_topic_signature: claude-motion-opendesign-motion-opus55-alternative-tool-vendor-lock',
         f'  last_outbound_reply_topic_signature: {MANUAL_REPLY["topic_signature"]}'),
    ]
    for old, new_line in repl:
        if old not in text:
            raise SystemExit(f"account-safety.yaml 找不到待替换行: {old!r}")
        text = text.replace(old, new_line, 1)

    # 5c. notes 追加本轮补账说明
    anchor = "  notes:\n"
    note = (
        "    - 2026-10-29 23:57 pulse_round_82 平台侧对账：发现 Frank 本人于 21:01:56 手动回了一条 "
        "@IncomprisSage（own_post_id 2115791244064690547，目标帖 2115385755266601207）—— 不在任何 agent 轮次日志里。"
        "已补账到 seen-posts / outbound-actions / recent-picks / index.json，并更新 last_outbound_reply_*。"
        "**last_published_at 保持 2026-10-28T19:49:39 不动**：那条是 reply 不是根帖，12h 原创闸门只数根帖"
        "（skills/README.md:82「Quote 帖 = 根帖，计入 12h 窗口；只有 reply 不计入」）。\n"
    )
    if note not in text:
        if anchor not in text:
            raise SystemExit("account-safety.yaml 找不到 notes 锚点")
        text = text.replace(anchor, anchor + note, 1)

    YAML.write_text(text, encoding="utf-8")

    # ── 6. 写后校验（值 ↔ 位置映射，不只校验「值出现过」）────────────
    import subprocess
    res = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-c", """
import yaml, sys
d = yaml.safe_load(open('private/account-safety.yaml'))
x = d['x']
errs = []
# like 槽位：slot1 = 最近一次赞（_akhaliq 23:57:12），slot2 = vista8 23:54:15
if x['last_outbound_like_at'] != '2026-10-29T23:57:12+08:00': errs.append('slot1 at')
if x['last_outbound_like_target_handle'] != '_akhaliq': errs.append('slot1 handle')
if x['last_outbound_like_target_post_id'] != '2115826286652248275': errs.append('slot1 pid')
if x['last_outbound_like_2_at'] != '2026-10-29T23:54:15+08:00': errs.append('slot2 at')
if x['last_outbound_like_2_target_handle'] != 'vista8': errs.append('slot2 handle')
if x['last_outbound_like_2_target_post_id'] != '2115818384881508545': errs.append('slot2 pid')
if x['last_outbound_like_3_target_handle'] != 'jiqizhixin': errs.append('slot3 handle')
if x['last_outbound_like_4_target_handle'] != 'dotey': errs.append('slot4 handle')
# reply 槽位 = Frank 手动 reply
if x['last_outbound_reply_at'] != '2026-10-29T21:01:56+08:00': errs.append('reply at')
if x['last_outbound_reply_own_post_id'] != '2115791244064690547': errs.append('reply own pid')
if x['last_outbound_reply_target_post_id'] != '2115385755266601207': errs.append('reply target pid')
if x['last_outbound_reply_target_handle'] != 'IncomprisSage': errs.append('reply handle')
if x['last_outbound_reply_treatment'] != 'frank_manual_reply_not_agent': errs.append('reply treatment')
# 12h 闸门输入必须保持不动（reply 不计入）
if str(x['last_published_at']) != '2026-10-28 19:49:39+08:00': errs.append('last_published_at 被动了！')
if x['last_published_post_id'] != '2115410666068815948': errs.append('last_published_post_id 被动了！')
print('ACCOUNT_SAFETY_OK' if not errs else 'ACCOUNT_SAFETY_FAIL ' + ','.join(errs))
sys.exit(0 if not errs else 1)
"""],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    print(res.stdout.strip() or res.stderr.strip())
    if "ACCOUNT_SAFETY_OK" not in res.stdout:
        raise SystemExit("account-safety 校验失败")

    # ── 7. 条目数校验 ────────────────────────────────────────────────
    post = {
        "seen": len(load(sp)["entries"]),
        "oa": len(load(oa)["entries"]),
        "rp": len(load(rp)["entries"]),
        "idx_seen": len(load(ip)["seen"]),
        "idx_out": len(load(ip)["outbound"]),
    }
    print("写后快照:", post)
    assert post["seen"] == pre["seen"] + 4, f"seen 条目数异常 {pre['seen']} -> {post['seen']}"
    assert post["oa"] == pre["oa"] + 3, f"outbound-actions 条目数异常 {pre['oa']} -> {post['oa']}"
    assert post["rp"] == pre["rp"] + 3, f"recent-picks 条目数异常 {pre['rp']} -> {post['rp']}"
    assert post["idx_seen"] == pre["idx_seen"] + 5, f"index.seen 异常 {pre['idx_seen']} -> {post['idx_seen']}"
    assert post["idx_out"] == pre["idx_out"] + 4, f"index.outbound 异常 {pre['idx_out']} -> {post['idx_out']}"

    # ── 8. 值 ↔ 位置映射终检（独立于写入逻辑，手写期望值）────────────
    spd = load(sp)
    for L in LIKES:
        hits = [e for e in spd["entries"] if e.get("post_id") == L["post_id"]]
        assert len(hits) == 1, f"seen-posts {L['post_id']} 条目数 {len(hits)}"
        e = hits[0]
        assert e["liked_at"] == L["ts"], f"{L['handle']} liked_at 错位"
        assert e["like_posted_at"] == L["posted_at"], f"{L['handle']} like_posted_at 错位"
        assert e["handle"] == L["handle"], f"{L['handle']} handle 错位"
        assert e["treatment"] == "like_only", f"{L['handle']} treatment 错位"
        assert e["url"] == L["url"], f"{L['handle']} url 错位"
    mr = [e for e in spd["entries"] if e.get("post_id") == MANUAL_REPLY["target_post_id"]]
    assert len(mr) == 1, "手动 reply 目标帖 seen-posts 条目数异常"
    assert mr[0]["treatment"] == "frank_manual_reply_not_agent", "手动 reply treatment 错位"
    assert mr[0]["own_post_id"] == MANUAL_REPLY["own_post_id"], "手动 reply own_post_id 错位"
    sk = [e for e in spd["entries"] if e.get("post_id") == SKIP_INBOUND["post_id"]]
    assert len(sk) == 1 and sk[0]["treatment"] == "skipped_no_reply", "闸1 留痕错位"

    ipd = load(ip)
    assert ipd["seen"]["2115818384881508545"]["h"] == "vista8", "index.seen vista8 错位"
    assert ipd["seen"]["2115818384881508545"]["t"] == "like", "index.seen vista8 t 错位"
    assert ipd["seen"]["2115826286652248275"]["h"] == "_akhaliq", "index.seen _akhaliq 错位"
    assert ipd["outbound"]["2115826286652248275"]["a"] == ["like"], "index.outbound _akhaliq 错位"
    assert ipd["seen"]["2114581731747717523"]["t"] == "skip", "index.seen mumblinglewis 错位"
    assert ipd["outbound"]["2115791244064690547"]["h"] == "FrankFika", "index.outbound own reply 错位"
    assert ipd["outbound"]["2115385755266601207"]["h"] == "IncomprisSage", "index.outbound target 错位"

    oad = load(oa)
    for L in LIKES:
        hits = [e for e in oad["entries"] if e.get("target_post_id") == L["post_id"]]
        assert len(hits) == 1, f"outbound-actions {L['handle']} 条目数 {len(hits)}"
        assert hits[0]["id"] == "outbound-like-" + L["post_id"][-6:], f"{L['handle']} id 派生错位"
        assert hits[0]["timestamp"] == L["ts"], f"{L['handle']} timestamp 错位"
        assert hits[0]["action_type"] == "like", f"{L['handle']} action_type 错位"
    mra = [e for e in oad["entries"] if e.get("own_post_id") == MANUAL_REPLY["own_post_id"]]
    assert len(mra) == 1, "手动 reply outbound-actions 条目数异常"
    assert mra[0]["agent_generated"] is False, "手动 reply 必须标 agent_generated=false"

    rpd = load(rp)
    for L in LIKES:
        hits = [e for e in rpd["entries"] if e.get("post_id") == L["post_id"]]
        assert len(hits) == 1, f"recent-picks {L['handle']} 条目数 {len(hits)}"
        assert hits[0]["id"] == "pick-" + L["post_id"][-6:], f"{L['handle']} pick id 错位"
        assert hits[0]["expires_at"] == L["expires_at"], f"{L['handle']} expires_at 错位"
        assert hits[0]["topic_signature"] == L["topic_signature"], f"{L['handle']} topic 错位"

    print("✅ 写后校验通过：值↔位置映射 + 条目数 + 12h 闸门未被动，全部正确")
    print(ROUND, "state 落盘完成")


if __name__ == "__main__":
    main()
