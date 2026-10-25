#!/usr/bin/env python3
"""
短文助手 · AI 味检测 / 清理 / 发送门禁

**这是底层强制层，不是文档约定。** 任何要发到 X 的文案，先过 `gate`。

用法：
    python3 scripts/humanize.py scan   <file>            # 只检测，输出命中清单
    python3 scripts/humanize.py scan   -                 # 从 stdin 读
    python3 scripts/humanize.py rewrite <file> [-o out]   # 检测 + LLM 改写（保留原意）
    python3 scripts/humanize.py gate   <file>            # 发送门禁：过则 exit 0，不过 exit 1
    python3 scripts/humanize.py gate   <file> --json     # 机器可读

依赖：检测+门禁 零依赖（纯 stdlib）；rewrite 需要本机 `mmx` CLI（MiniMax）。

为什么存在：
    2026-10-26 Frank 直接反馈 ——「@op7418 / @oran_ge 拉黑你，
    是因为被看出来是 AI 评价了」。之前只靠 SKILL.md 里的文字规则拦，
    而 2026-10-26 那条被撤掉的 reply 草稿**句式全部合规、结构一眼就是 AI**。
    规则写在文档里挡不住人，所以做成代码。

规则集：state/ai-taste-rules.json
    来源 = Wikipedia "Signs of AI writing"（24 类模式）+ Frank 自有中文 AI 味清单
    + state/style-x.yaml#voice.anti_ai_slop
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "state" / "ai-taste-rules.json"

# —— 文本里要排除的元信息行（x.txt 的 # meta 行不参与判断）——
META_LINE = re.compile(r"^\s*#")


# ────────────────────────── 规则加载 ──────────────────────────

def load_rules(path=None):
    p = pathlib.Path(path) if path else RULES_PATH
    if not p.exists():
        die(f"规则文件不存在: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"规则文件 JSON 解析失败: {p}\n  {e}")


# ────────────────────────── 红线检查 ──────────────────────────

# state/forbidden.yaml 是 YAML，但 PyYAML 不在系统 python 里。
# 这里用最小解析器读需要的字段，避免给检测器引入依赖。
FORBIDDEN_PATH = ROOT / "state" / "forbidden.yaml"

# Chinese AI 公司名 —— forbidden.yaml#forbidden_content 里没有单列，
# 但 SKILL.md 明确要求避开。写死在这里，gate 时强检。
CHINESE_AI_NAMES = [
    "DeepSeek", "深度求索", "Moonshot", "月之暗面", "Kimi", "MiniMax",
    "通义", "千问", "Qwen", "文心", "文心一言", "Ernie", "智谱", "GLM",
    "ChatGLM", "百川", "Baichuan", "商汤", "日日新", "阶跃", "Step",
    "星火", "讯飞", "Llama", "Grok",
]


def load_forbidden(path=None):
    """极简 YAML 读取：只取 forbidden_content 段的 id/desc/scope。

    不引 PyYAML —— 系统的 python3 没有 yaml，而 gate 必须在任何环境下都能跑。
    """
    p = pathlib.Path(path) if path else FORBIDDEN_PATH
    if not p.exists():
        return []
    out = []
    cur = None
    in_block = False
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if re.match(r"^\S", line):
            in_block = line.strip().startswith("forbidden_content:")
            cur = None
            continue
        if not in_block:
            continue
        m = re.match(r"^\s*-\s*id:\s*(\S+)", line)
        if m:
            cur = {"id": m.group(1).strip(), "desc": "", "scope": [], "severity": "hard"}
            out.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^\s*desc:\s*(.+)", line)
        if m:
            cur["desc"] = m.group(1).strip().strip("\"'")
            continue
        m = re.match(r"^\s*severity:\s*(\S+)", line)
        if m:
            cur["severity"] = m.group(1).strip()
            continue
        m = re.match(r"^\s*scope:\s*\[(.*)\]", line)
        if m:
            cur["scope"] = [s.strip() for s in m.group(1).split(",") if s.strip()]
            continue
    return out


def check_redlines(text, channel="x"):
    """检查硬红线。返回命中列表。

    红线比 AI 味更严重 —— AI 味只是难看，红线是事故。
    """
    hits = []
    low = text.lower()

    for name in CHINESE_AI_NAMES:
        if name.lower() in low:
            hits.append({
                "rule_id": "redline.chinese_ai_company",
                "severity": "hard", "category": "redline",
                "matched": [name], "count": 1,
                "note": "不出现 Chinese AI 公司名（SKILL.md 硬红线）",
            })

    for c in load_forbidden():
        scope = c.get("scope") or []
        if scope and channel not in scope:
            continue
        # 从 id 推导关键词：no_opencsg → opencsg / openCSG
        kw = c["id"].replace("no_", "").replace("_", " ")
        if c["id"] == "no_opencsg":
            needles = ["opencsg", "open csg", "开放传神"]
        elif c["id"] == "no_ai_images":
            needles = []  # 图片类，正文查不出，交给 qa-draft
        elif c["id"] == "no_fabricated_experience":
            needles = []  # 语义类，交给模型/人工
        elif c["id"] == "no_ai_hosting_wording":
            needles = ["ai 托管", "自动互动", "自动发文", "ai 自动发"]
        elif c["id"] == "no_pure_hype":
            needles = []  # 软线，靠 qa-draft 的数字检查
        elif c["id"] == "no_hashtag_storm":
            tags = re.findall(r"#[^#\s]+", text)
            if len(tags) > 1:
                hits.append({
                    "rule_id": f"redline.{c['id']}", "severity": "hard",
                    "category": "redline", "matched": tags[:4], "count": len(tags),
                    "note": c.get("desc", ""),
                })
            continue
        elif c["id"] == "no_placeholder_captions":
            needles = ["配图如下", "见上图", "见下图", "快去看"]
        else:
            needles = [kw]
        for n in needles:
            if n.lower() in low:
                hits.append({
                    "rule_id": f"redline.{c['id']}", "severity": "hard",
                    "category": "redline", "matched": [n], "count": 1,
                    "note": c.get("desc", ""),
                })
                break
    return hits


def die(msg, code=2):
    print(f"ERR: {msg}", file=sys.stderr)
    sys.exit(code)


# ────────────────────────── 文本读取 ──────────────────────────

def read_text(src):
    """src 为 '-' 走 stdin；否则读文件并剥掉 # meta 行。"""
    if src == "-":
        raw = sys.stdin.read()
    else:
        p = pathlib.Path(src)
        if not p.exists():
            die(f"文件不存在: {p}")
        raw = p.read_text(encoding="utf-8")
    body = "\n".join(l for l in raw.splitlines() if not META_LINE.match(l))
    return body.strip()


# ────────────────────────── 检测器 ──────────────────────────

def compile_rule(rule):
    """把一条规则编译成 (regex_list, max_count)。max_count 为 None 表示纯 regex 命中。"""
    pats = []
    for raw in rule.get("patterns", []):
        try:
            pats.append(re.compile(raw, re.IGNORECASE))
        except re.error as e:
            die(f"规则 {rule['id']} 的正则非法: {raw!r} ({e})")
    return pats, rule.get("max_count")


def scan(text, rules, channel="x", with_redlines=True):
    """返回 (hits, soft_score)。hit 含 rule_id / severity / matched 片段。"""
    hits = []
    soft_score = 0

    if with_redlines:
        hits.extend(check_redlines(text, channel))

    for rule in rules["rules"]:
        pats, max_count = compile_rule(rule)
        matched = []
        for rx in pats:
            for m in rx.finditer(text):
                matched.append(m.group(0).strip())
                if max_count is not None and len(matched) >= max_count:
                    break
            if max_count is not None and len(matched) >= max_count:
                break

        if max_count is not None:
            # 计数型（破折号 / emoji）：超过阈值才命中
            if len(matched) > max_count:
                hits.append({
                    "rule_id": rule["id"], "category": rule["category"],
                    "severity": rule["severity"], "weight": rule.get("weight", 1),
                    "matched": matched[:5], "count": len(matched),
                    "note": rule.get("note", ""),
                })
            continue

        if matched:
            hits.append({
                "rule_id": rule["id"], "category": rule["category"],
                "severity": rule["severity"], "weight": rule.get("weight", 1),
                "matched": list(dict.fromkeys(matched))[:5],
                "count": len(matched),
                "note": rule.get("note", ""),
            })

    for h in hits:
        h.setdefault("weight", 5 if h["severity"] == "hard" else 1)
        if h["severity"] == "soft":
            soft_score += h["weight"] * min(h["count"], 3)

    return hits, soft_score

def gate_verdict(hits, soft_score, rules):
    """返回 (passed, reasons)。"""
    g = rules.get("gate", {})
    reasons = []
    hard = [h for h in hits if h["severity"] == "hard"]
    max_hard = g.get("max_hard_hits", 0)
    if len(hard) > max_hard:
        for h in hard:
            reasons.append(f"HARD [{h['rule_id']}] 命中「{h['matched']}」 — {h['note']}")
    thr = g.get("soft_score_threshold", 10)
    if soft_score >= thr:
        reasons.append(f"SOFT 分 {soft_score} ≥ 阈值 {thr}（AI 味过重）")
    return (not reasons), reasons


# ────────────────────────── LLM 清理器 ──────────────────────────

REWRITE_SYSTEM = """你是一个中文社交媒体编辑，专门把"AI 味"重写掉，让文案读起来像真人随手写的。

判断标准基于 Wikipedia 的 "Signs of AI writing" 模式库。真人文本的特征：句长不齐、有具体细节、允许不完整、不总结、不升华、偶尔口语插入语、承认没做到。

硬性要求：
1. **保留原意和所有事实**（数字、链接、具体人名/工具名）。绝不能编造原文没有的事实或经历。
2. **不要写"总结句"**，不要在结尾升华。
3. **不要用「不是 X，而是 Y」句式** —— 这是 LLM 最强指纹。
4. 句长要不齐：允许一句很短，一句较长。
5. 具体名词优先于抽象名词。
6. 不要用破折号（——）连续出现。
7. 不要用「这是」开头，不要用「值得一提」开头。
8. 输出**只有改写后的正文**，不要任何解释、不要标题、不要 markdown、不要引号包裹。
9. 保持原语言（中文）和原长度区间（不要大幅增减）。

下面是待改写的正文。改写它。

待改写正文：
"""


def build_user_prompt(text, hits):
    """把命中的具体规则塞进 prompt，让模型针对性改而不是泛泛润色。"""
    lines = []
    if hits:
        lines.append("【这条草稿命中了以下 AI 味模式，改写时必须全部消除】：")
        for h in hits:
            lines.append(f"- {h['rule_id']}：命中「{'、'.join(h['matched'])}」— {h['note']}")
        lines.append("")
    lines.append("【正文】")
    lines.append(text)
    return "\n".join(lines)


def llm_rewrite(text, hits, rules_cfg):
    """调用 mmx text chat 改写。失败返回 (None, error)。

    ⚠️ 实测坑（2026-10-26）：MiniMax-M3.1-Flash 会开 thinking，
    思考 token 可能吃掉整个 max_tokens 预算（实测 thinking_tokens=1999/2000），
    结果 stop_reason=max_tokens 且 content 里没有任何 text 块 —— 表现为「返回空内容」。
    修法：max_tokens 给足（默认 8000），且失败时自动加预算重试一次。
    """
    mmx = shutil_which("mmx") or "/opt/homebrew/bin/mmx"
    if not os.path.exists(mmx):
        return None, "找不到 mmx CLI（MiniMax 本地 CLI），无法自动改写"

    model = rules_cfg.get("rewrite", {}).get("model", "MiniMax-M3.1-Flash-Preview")
    max_tokens = rules_cfg.get("rewrite", {}).get("max_tokens", 8000)
    temp = rules_cfg.get("rewrite", {}).get("temperature", 0.9)

    cmd = [
        mmx, "text", "chat",
        "--model", model,
        "--system", REWRITE_SYSTEM,
        "--message", build_user_prompt(text, hits),
        "--max-tokens", str(max_tokens),
        "--temperature", str(temp),
        "--output", "json",
        "--no-color",
        "--timeout", "120",
    ]

    last_err = None
    for attempt in range(2):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            last_err = "mmx 调用超时"
            continue
        except OSError as e:
            return None, f"mmx 调用失败: {e}"

        if proc.returncode != 0:
            last_err = f"mmx 返回码 {proc.returncode}: {(proc.stderr or proc.stdout or '').strip()[:400]}"
            break

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            last_err = f"mmx 输出非 JSON: {proc.stdout.strip()[:400]}"
            break

        stop = data.get("stop_reason")
        chunks = [c.get("text", "") for c in data.get("content", []) if c.get("type") == "text"]
        out = "\n".join(chunks).strip()

        if out:
            return out, None

        # 空内容：多半是 thinking 吃满预算 → 加预算重试
        usage = data.get("usage", {}) or {}
        detail = usage.get("output_tokens_details", {}) or {}
        last_err = (f"mmx 返回空内容（stop_reason={stop}, "
                    f"thinking_tokens={detail.get('thinking_tokens')}）")
        if attempt == 0:
            cmd[cmd.index("--max-tokens") + 1] = str(max_tokens * 3)

    return None, last_err or "mmx 调用失败"


def shutil_which(name):
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def clean_output(raw):
    """剥掉模型偶尔加的 markdown 包裹 / 前后解释。"""
    t = raw.strip()
    # ```...``` 包裹
    t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
    t = re.sub(r"\n```\s*$", "", t)
    # 整段被引号包裹
    if len(t) > 2 and t[0] in "「\"“" and t[-1] in "」\"”":
        t = t[1:-1].strip()
    # 前面带「改写后：」这类前缀
    t = re.sub(r"^(改写后|修改后|润色后|最终版|重写后)\s*[:：]\s*", "", t)
    return t.strip()


# ────────────────────────── 输出 ──────────────────────────

def print_scan(hits, soft_score, rules, passed, reasons, as_json):
    if as_json:
        print(json.dumps({
            "passed": passed, "soft_score": soft_score,
            "hits": hits, "reasons": reasons,
        }, ensure_ascii=False, indent=2))
        return
    if not hits:
        print("✓ 未命中任何 AI 味模式")
        return
    print(f"命中 {len(hits)} 条 AI 味模式（soft 分 {soft_score}）\n")
    for h in sorted(hits, key=lambda x: (x["severity"] != "hard", -x["weight"])):
        tag = "HARD" if h["severity"] == "hard" else "soft"
        print(f"  [{tag}] {h['rule_id']}  ← 命中「{'、'.join(h['matched'])}」")
        print(f"         {h['note']}")
    if reasons:
        print("\n判定：**不过**")
        for r in reasons:
            print(f"  - {r}")
    else:
        print("\n判定：**过**")


# ────────────────────────── main ──────────────────────────

def main():
    ap = argparse.ArgumentParser(description="AI 味检测 / 清理 / 发送门禁")
    ap.add_argument("mode", choices=["scan", "rewrite", "gate"])
    ap.add_argument("src", help="文件路径，或 - 表示 stdin")
    ap.add_argument("-o", "--out", help="rewrite 输出文件（默认打印到 stdout）")
    ap.add_argument("--rules", help="规则文件路径（默认 state/ai-taste-rules.json）")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    ap.add_argument("--force", action="store_true", help="gate 模式：即使不过也返回 0（仅调试用）")
    args = ap.parse_args()

    rules = load_rules(args.rules)
    text = read_text(args.src)

    if not text.strip():
        die("正文为空，无法检测")

    if args.mode == "scan":
        hits, score = scan(text, rules)
        passed, reasons = gate_verdict(hits, score, rules)
        print_scan(hits, score, rules, passed, reasons, args.json)
        sys.exit(0)

    if args.mode == "gate":
        hits, score = scan(text, rules)
        passed, reasons = gate_verdict(hits, score, rules)
        print_scan(hits, score, rules, passed, reasons, args.json)
        sys.exit(0 if (passed or args.force) else 1)

    # rewrite
    hits, score = scan(text, rules)
    print(f"━━━ 改写前 ━━━", file=sys.stderr)
    print_scan(hits, score, rules, *gate_verdict(hits, score, rules), as_json=False)

    if not hits:
        print("\n无需改写（未命中任何模式）。", file=sys.stderr)
        if args.out:
            pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        sys.exit(0)

    new_text, err = llm_rewrite(text, hits, rules)
    if err:
        print(f"\nERR: 自动改写失败 —— {err}", file=sys.stderr)
        print("（原文已保留，请手工改写后重跑 gate）", file=sys.stderr)
        sys.exit(3)

    new_text = clean_output(new_text)
    new_hits, new_score = scan(new_text, rules)
    new_passed, new_reasons = gate_verdict(new_hits, new_score, rules)

    print(f"\n━━━ 改写后 ━━━", file=sys.stderr)
    print_scan(new_hits, new_score, rules, new_passed, new_reasons, as_json=False)
    print(f"\n━━━ soft 分 {score} → {new_score} ━━━", file=sys.stderr)

    if new_score > score:
        print("\nWARN: 改写后分数变高，保留原文更安全。", file=sys.stderr)
        new_text = text

    if args.out:
        pathlib.Path(args.out).write_text(new_text + "\n", encoding="utf-8")
        print(f"\n已写入 {args.out}", file=sys.stderr)
    else:
        print("\n" + new_text)


if __name__ == "__main__":
    main()
