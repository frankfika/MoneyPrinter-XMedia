#!/usr/bin/env python3
"""AI 味闸门回归测试 —— 换机器 / 换 AI 之后的上线验收。

语料：`state/published-posts.json` 里带 `draft_text` 的 13 条**真实发过的**帖。
      这批就是 2026-10-26 建闸门时用的回归集 —— 天然随仓库走，不需要额外文件。

anchors：`state/gate-regression-anchors.json` 存每条样本的**预期判定**。
      判定方向必须完全一致，两种偏差都是回归：
        - known-good 变 FAIL → 假阳性回归（闸门变严，把人话也拦了）
        - known-bad  变 PASS  → 假阴性回归（闸门变松，AI 味漏过去了）
      后者比前者危险 —— 那正是 @op7418 / @oran_ge 拉黑 Frank 的原因。

用法：
  python3 scripts/gate-regression.py                  # 比对 anchors，有出入 exit 1
  python3 scripts/gate-regression.py --report         # 只出报告，不判定
  python3 scripts/gate-regression.py --write-anchors  # 重新生成基线（需人工确认后）

退出码：0 = 全部符合预期；1 = 有回归或出错。
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import humanize  # noqa: E402  （同目录模块，故意在 sys.path 调整之后 import）

POSTS = ROOT / "state" / "published-posts.json"
ANCHORS = ROOT / "state" / "gate-regression-anchors.json"


def load_samples():
    if not POSTS.exists():
        raise SystemExit(f"✗ 找不到 {POSTS} —— 先把仓库完整拉下来")
    data = json.loads(POSTS.read_text(encoding="utf-8"))
    entries = data.get("entries", data if isinstance(data, list) else [])
    samples = []
    for e in entries:
        text = (e.get("draft_text") or "").strip()
        if not text:
            continue
        samples.append(
            {
                "id": e.get("id") or e.get("post_id") or "?",
                "post_id": e.get("post_id"),
                "text": text,
            }
        )
    return samples


def run_one(text, rules):
    hits, soft = humanize.scan(text, rules, channel="x", with_redlines=True)
    passed, reasons = humanize.gate_verdict(hits, soft, rules)
    return {
        "verdict": "PASS" if passed else "FAIL",
        "soft": soft,
        "reasons": reasons,
        "rule_ids": sorted({h["rule_id"] for h in hits}),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="只出报告，不跟 anchors 比对")
    ap.add_argument("--write-anchors", action="store_true", help="重新生成基线")
    args = ap.parse_args()

    try:
        rules = humanize.load_rules()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"✗ 规则集加载失败：{exc}")
    if not rules:
        raise SystemExit("✗ 规则集为空 —— state/ai-taste-rules.json 是不是没拉下来？")

    samples = load_samples()
    if not samples:
        raise SystemExit("✗ 一条语料都没取到 —— published-posts.json 里没有带 draft_text 的条目")

    results = {}
    for s in samples:
        results[s["id"]] = run_one(s["text"], rules)

    # ── 出报告 ──
    print(f"AI 味闸门回归 · {len(samples)} 条真实发过的帖")
    print("=" * 78)
    for s in samples:
        r = results[s["id"]]
        mark = "✅" if r["verdict"] == "PASS" else "🚫"
        print(f"{mark} {s['id']:<24} {r['verdict']:<5} soft={r['soft']:<3} {','.join(r['rule_ids']) or '-'}")
        for reason in r["reasons"][:2]:
            print(f"      └ {reason[:150]}")
    n_pass = sum(1 for r in results.values() if r["verdict"] == "PASS")
    print("-" * 78)
    print(f"合计：PASS {n_pass} / FAIL {len(results) - n_pass} / 共 {len(results)}")

    # ── 写基线 ──
    if args.write_anchors:
        payload = {
            "created_at": humanize.__name__ and __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "note": "2026-10-26 闸门建成时的基线。FAIL 的样本是**已知的 AI 味样本**（含 Frank 被拉黑的真实反例）——它们必须一直 FAIL。",
            "samples": {
                sid: {"expect": r["verdict"], "soft": r["soft"], "rule_ids": r["rule_ids"]}
                for sid, r in results.items()
            },
        }
        ANCHORS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n✅ 基线已写入 {ANCHORS.relative_to(ROOT)}（{len(results)} 条）")
        print("   ⚠️ 请人工核对：FAIL 的那几条确实应该是 AI 味样本，再提交。")
        return 0

    if args.report:
        print("\n（--report 模式：只报告，不判定）")
        return 0

    # ── 比对基线 ──
    if not ANCHORS.exists():
        print(f"\n⚠️  没有基线文件 {ANCHORS.relative_to(ROOT)} —— 只出报告不判定。")
        print("   生成基线：python3 scripts/gate-regression.py --write-anchors")
        return 0

    anchors = json.loads(ANCHORS.read_text(encoding="utf-8")).get("samples", {})
    diffs = []
    for sid, r in results.items():
        exp = anchors.get(sid)
        if exp is None:
            diffs.append((sid, "新增样本（基线里没有）", "-", r["verdict"]))
            continue
        if exp["expect"] != r["verdict"]:
            diffs.append((sid, "判定变了", exp["expect"], r["verdict"]))
    for sid in anchors:
        if sid not in results:
            diffs.append((sid, "样本消失了", anchors[sid]["expect"], "缺失"))

    if not diffs:
        print(f"\n✅ 与基线完全一致（{len(results)} 条）—— 闸门行为没有漂移。")
        return 0

    print(f"\n🚫 与基线不一致 —— {len(diffs)} 条偏差：")
    for sid, why, exp, got in diffs:
        print(f"   {sid}: {why}  期望 {exp} → 实际 {got}")
    print("\n   假阴性（FAIL→PASS）＝ 闸门被改松了，AI 味会漏到公开面 —— 最危险。")
    print("   假阳性（PASS→FAIL）＝ 闸门被改严了，人话也会被拦。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
