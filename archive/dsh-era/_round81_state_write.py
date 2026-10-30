#!/usr/bin/env python3
"""
pulse_round_81 state 落盘（并发安全）

沿用 _round80_state_write.py / _round92_state_write.py 的约定：
  1) 写前重新读盘（不用内存旧快照）
  2) 追加型记录（seen / outbound-actions / recent-picks）→ 追加，不覆盖
  3) 自增 id 一律内容派生（pick-<post_id 后 6 位> / outbound-like-<post_id 后 6 位>），
     不读「最后一个 id +1」—— 那是 read-modify-write 竞态
  4) 原子写（tmp + os.replace）
  5) 写后校验：条目数 = 写前 + 预期新增

本轮公开动作（2 个 like，均已验证）：
  like#1 @dotey      2115618084044349828  10:14:14  (post posted 09:33:52, 赞时 40m)
  like#2 @jiqizhixin 2115494806004613515  10:18:10  (post posted 01:24:00, 赞时 8.9h)
  间隔 236 秒 = 3.94 分钟（≥2min 线）
"""
import json, os, pathlib, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
YAML = ROOT / "private" / "account-safety.yaml"

ROUND = "pulse_round_81"
TS1 = "2026-10-29T10:14:14+08:00"
TS2 = "2026-10-29T10:18:10+08:00"
DATE = "2026-10-29"
EXP1 = "2026-11-05T10:14:14+08:00"
EXP2 = "2026-11-05T10:18:10+08:00"

LIKES = [
    {
        "handle": "dotey",
        "post_id": "2115618084044349828",
        "url": "https://x.com/dotey/status/2115618084044349828",
        "ts": TS1,
        "expires_at": EXP1,
        "posted_at": "2026-10-29T09:33:52+08:00",
        "topic_signature": "worktree-parallel-agent-tasks-local-vs-cloud-verification-cost",
        "engagement": "19->20 likes（本轮 +1）/ 18 replies / 1 repost / 3.1K views",
        "reason": (
            "「能不用 Worktree 就不用，但并行任务一多、想不相互干扰，还是绕不开 worktree」—— "
            "中文 KOL 里少见的多 agent 并行工程实践判断（云端并行 vs 本机验证 vs 云端成本），"
            "正好落在 Frank「前工程师 / 一手实践」人设上；"
            "发布 40 分钟就赞，赞列表才 19 人 → Frank 的 handle 出现在最前段（早赞曝光窗口）"
        ),
        "context": (
            "pulse_round_81 outbound-like-449828 like_only — @dotey：多 agent 并行任务的 worktree 取舍；"
            "19→20 likes（赞列表 19 人，Frank handle 排最前），aria-label 双向核对 + unlike 按钮 + "
            "Likes 历史页顶部三证"
        ),
        "like_delta": "19->20（本轮 +1；点后 aria-label 读 20 Likes. Liked）",
        "aria": "20 Likes. Liked",
    },
    {
        "handle": "jiqizhixin",
        "post_id": "2115494806004613515",
        "url": "https://x.com/jiqizhixin/status/2115494806004613515",
        "ts": TS2,
        "expires_at": EXP2,
        "posted_at": "2026-10-29T01:24:00+08:00",
        "topic_signature": "embodied-benchmark-simulation-vs-real-robot-gap-zero-plug-insertions",
        "engagement": "11->12 likes（本轮 +1）/ 3 replies / 1 repost / 844 views",
        "reason": (
            "「模拟 benchmark 100% 分，真机 11 次插拔 0 次成功 —— 具身分数取决于测试允许什么」—— "
            "benchmark 分数与真实部署之间的落差，正是 Frank「评测出身」的核心命题"
            "（呼应他 10-26 的「自训模型要自己的验收尺子」）；"
            "赞列表仅 11 人，早赞窗口内 Frank handle 靠前"
        ),
        "context": (
            "pulse_round_81 outbound-like-613515 like_only — @jiqizhixin：具身智能 benchmark 与真机表现的落差；"
            "11→12 likes，aria-label 双向核对 + unlike 按钮 + Likes 历史页顶部三证"
        ),
        "like_delta": "11->12（本轮 +1；点后 aria-label 读 12 Likes. Liked）",
        "aria": "12 Likes. Liked",
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
    for idx, L in enumerate(LIKES):
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

    # ── 2. outbound-actions.json：两条公开动作记录（内容派生 id）──────
    oa = STATE / "outbound-actions.json"
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
                    f"pulse_round_81；like#{idx+1}。详情页先 query dom 读 aria-label 确认是目标帖且未赞，"
                    "再 click，再 query dom 读 unlike + aria-label='Liked'，URL 与目标一致。"
                    "like#1 -> like#2 间隔 236 秒（3.94 分钟，过 ≥2min 线）；"
                    "两次赞之间用显式 wait 60+60 秒兑现间隔，不靠顺手调用凑时间"
                ),
            }

        append_once(oa, m, b, 1, f"outbound-actions[{L['handle']}]")

    # ── 3. recent-picks.json：7 天 topic signature dedup ──────────────
    rp = STATE / "recent-picks.json"
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

    # ── 5. account-safety.yaml：滚动 4 槽位 like 时间线 ─────────────
    # 槽位约定：slot 1 = 最近一次赞，slot 2 = 上上次 ……（滚动保留最近 4 条）
    # 新数据入 slot 1/2，原 slot 1/2 顺延到 3/4，最旧的被挤出。
    prev = [
        # (at, post_id, handle, topic_signature) —— 原有 slot1..slot4，按新到旧
        ("2026-10-29T04:09:16+08:00", "2115512767394275550", "dotey",
         "copilot-obsolete-concept-ai-not-copilot-autopilot-era"),
        ("2026-10-29T04:06:16+08:00", "2115509412400070883", "bindureddy",
         "gemini-carbon-livebench-benchmark-launch-expectation"),
        ("2026-10-28T22:24:19+08:00", "2115444742595260551", "simonw",
         "october-inflection-point-coding-agents-opus-5-5-vibe-game-dev"),
        ("2026-10-28T22:16:52+08:00", "2115419671877062710", "emollick",
         "talkie-1930-neuron-persona-locking-open-model-mechanistic-interpretability"),
    ]
    # 槽位 1 = 最近一次赞 → 新数据必须按时间**倒序**入槽。
    # （本轮 like#1=dotey 10:14:14 早于 like#2=jiqizhixin 10:18:10，
    #   所以 slot1 是 jiqizhixin，slot2 才是 dotey —— 写反了就是「最近一次赞」记录错位。）
    new = sorted(
        [(L["ts"], L["post_id"], L["handle"], L["topic_signature"]) for L in LIKES],
        key=lambda r: r[0],
        reverse=True,
    )
    merged = (new + prev)[:4]      # 新到旧，取前 4 条

    lines = YAML.read_text(encoding="utf-8").split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("last_outbound_like_at:"):
            # 整个 like 槽位块（含 _2_/_3_/_4_）整体替换
            j = i
            while j < len(lines) and (
                lines[j].strip().startswith("last_outbound_like")
                or lines[j].strip().startswith("last_outbound_like_2_")
                or lines[j].strip().startswith("last_outbound_like_3_")
                or lines[j].strip().startswith("last_outbound_like_4_")
            ):
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
    YAML.write_text("\n".join(out), encoding="utf-8")

    # 写后校验（用 venv 的 python3 —— 系统 python3 没装 yaml）
    import subprocess
    res = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-c", """
import yaml, sys
d = yaml.safe_load(open('private/account-safety.yaml'))
x = d['x']
ok = (x['last_outbound_like_at'] == '2026-10-29T10:18:10+08:00'
      and x['last_outbound_like_target_handle'] == 'jiqizhixin'
      and x['last_outbound_like_target_post_id'] == '2115494806004613515'
      and x['last_outbound_like_2_at'] == '2026-10-29T10:14:14+08:00'
      and x['last_outbound_like_2_target_handle'] == 'dotey'
      and x['last_outbound_like_2_target_post_id'] == '2115618084044349828'
      and x['last_outbound_like_3_target_handle'] == 'dotey'
      and x['last_outbound_like_4_target_handle'] == 'bindureddy'
      and str(x['last_published_at']) == '2026-10-28 19:49:39+08:00'
      and d['xhs']['is_banned'] is True)
print('ACCOUNT_SAFETY_OK' if ok else 'ACCOUNT_SAFETY_FAIL')
sys.exit(0 if ok else 1)
"""],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    print(res.stdout.strip() or res.stderr.strip())
    if "ACCOUNT_SAFETY_OK" not in res.stdout:
        raise SystemExit("account-safety 校验失败")

    print(ROUND, "state 落盘完成")


if __name__ == "__main__":
    main()
