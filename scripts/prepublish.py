#!/usr/bin/env python3
"""
短文助手 · 发帖前闸门（唯一入口）

**任何要发到 X 的文案都必须先过这个脚本。** 它做三件事：

1. AI 味检测（state/ai-taste-rules.json，Wikipedia Signs-of-AI + Frank 中文清单）
2. 硬红线检测（OpenCSG / Chinese AI 公司名 / hashtag 风暴 / 安利腔）
3. 不过 → 自动调用 LLM 清理器改写 → 再检测；仍然不过 → **exit 1，拦住**

用法：
    python3 scripts/prepublish.py <outputs/.../topic-dir>     # 原创帖：自动取 x.txt
    python3 scripts/prepublish.py --text "要发的正文"         # reply / 短评
    python3 scripts/prepublish.py <dir> --no-rewrite          # 只检测不自动改
    python3 scripts/prepublish.py --text "..." --json         # 机器可读

exit code:
    0 = 通过（可以发）
    1 = 不过（不许发）
    2 = 用法错误
    3 = 清理器故障（原文保留，需要人工改）

配套：state/gate-receipts.json 记录每次闸门结果（含最终文本的 sha256），
用于事后核对「这条到底过没过闸」。
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util

_spec = importlib.util.spec_from_file_location("humanize", ROOT / "scripts" / "humanize.py")
hz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hz)

RECEIPTS = ROOT / "state" / "gate-receipts.json"
META_LINE = re.compile(r"^\s*#")


def read_body(src):
    p = pathlib.Path(src)
    if not p.exists():
        hz.die(f"文件不存在: {p}")
    raw = p.read_text(encoding="utf-8")
    return "\n".join(l for l in raw.splitlines() if not META_LINE.match(l)).strip()


def find_text_file(d):
    """在素材目录里找正文文件。"""
    for name in ("x.txt", "xhs.txt"):
        p = pathlib.Path(d) / name
        if p.exists():
            return p
    return None


def run_qa_draft(d):
    """跑既有质检脚本（需要 yaml）。跑不了不算失败，但要如实报告。"""
    py = ROOT / ".venv" / "bin" / "python"
    cmd = [str(py), str(ROOT / "scripts" / "qa-draft.py"), str(d)] if py.exists() else None
    if cmd is None:
        # 退路：uv 临时环境
        cmd = ["uv", "run", "--quiet", "--with", "pyyaml", "python",
               str(ROOT / "scripts" / "qa-draft.py"), str(d)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                              cwd=str(ROOT))
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"qa-draft 无法运行: {e}"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def append_receipt(rec):
    data = {"schema_version": 1, "receipts": []}
    if RECEIPTS.exists():
        try:
            data = json.loads(RECEIPTS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    data.setdefault("receipts", [])
    data["receipts"].append(rec)
    data["receipts"] = data["receipts"][-500:]
    RECEIPTS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize(hits, score, passed, reasons):
    hard = [h for h in hits if h["severity"] == "hard"]
    return {
        "soft_score": score,
        "hard_hits": [h["rule_id"] for h in hard],
        "all_hits": [h["rule_id"] for h in hits],
        "passed": passed,
        "reasons": reasons,
    }


def main():
    ap = argparse.ArgumentParser(description="发帖前闸门")
    ap.add_argument("src", nargs="?", help="素材目录")
    ap.add_argument("--text", help="直接传正文（reply / 短评）")
    ap.add_argument("--no-rewrite", action="store_true", help="只检测，不自动改写")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip-qa", action="store_true", help="跳过 qa-draft")
    args = ap.parse_args()

    if not args.src and not args.text:
        hz.die("用法: prepublish.py <dir> | --text \"正文\"")

    rules = hz.load_rules()

    if args.text:
        text = args.text.strip()
        origin = "inline"
        d = None
    else:
        d = pathlib.Path(args.src)
        if not d.is_dir():
            hz.die(f"不是目录: {d}")
        f = find_text_file(d)
        if not f:
            hz.die(f"目录里没有 x.txt / xhs.txt: {d}")
        text = read_body(f)
        origin = str(f.relative_to(ROOT)) if str(f).startswith(str(ROOT)) else str(f)

    if not text:
        hz.die("正文为空")

    qa_out = None
    qa_rc = None
    if d is not None and not args.skip_qa:
        qa_rc, qa_out = run_qa_draft(d)

    hits, score = hz.scan(text, rules)
    passed, reasons = hz.gate_verdict(hits, score, rules)
    before = summarize(hits, score, passed, reasons)
    rewritten = False

    # qa-draft 不过也算不过（字数/链接/词表等它管的项）
    if qa_rc is not None and qa_rc != 0 and not args.skip_qa:
        passed = False
        reasons = reasons + ["qa-draft 未通过（见下方 qa 输出）"]

    # 不过 → 尝试自动清理
    if not passed and not args.no_rewrite:
        orig_len = len(text)
        new_text, err = hz.llm_rewrite(text, hits, rules)
        if err:
            reasons.append(f"自动清理失败: {err}")
        else:
            new_text = hz.clean_output(new_text)
            n_hits, n_score = hz.scan(new_text, rules)
            n_passed, n_reasons = hz.gate_verdict(n_hits, n_score, rules)
            ratio = len(new_text) / max(orig_len, 1)
            lo = rules.get("rewrite", {}).get("min_length_ratio", 0.65)
            hi = rules.get("rewrite", {}).get("max_length_ratio", 1.45)
            if n_score > score:
                reasons.append("清理后 AI 味分反而变高，保留原文")
            elif ratio < lo or ratio > hi:
                reasons.append(f"清理后长度比 {ratio:.2f} 越界（{lo}~{hi}），"
                               f"内容可能被砍掉或注水，保留原文")
            else:
                text = new_text
                hits, score = n_hits, n_score
                passed, reasons = n_passed, n_reasons
                rewritten = True
                # 清理后重跑 qa
                if d is not None and not args.skip_qa:
                    tmp = d / "x.txt.gate.tmp"
                    try:
                        tmp.write_text(text + "\n", encoding="utf-8")
                        qa_rc2, qa_out2 = run_qa_draft(d)
                        tmp.unlink(missing_ok=True)
                        if qa_rc2 is not None and qa_rc2 != 0:
                            passed = False
                            reasons.append("清理后 qa-draft 仍未通过")
                            qa_out = qa_out2
                    except OSError:
                        pass

    after = summarize(hits, score, passed, reasons)

    # 清理后的正文要落回源文件（备份原文件），否则清理结果丢失、白干一场
    if rewritten and d is not None and not args.text:
        target = find_text_file(d)
        if target:
            bak = target.with_suffix(target.suffix + ".pre-gate.bak")
            try:
                original_raw = target.read_text(encoding="utf-8")
                # 只替换正文部分，保留 # meta 行
                lines = original_raw.splitlines()
                meta = [l for l in lines if META_LINE.match(l)]
                body_lines = [l for l in lines if not META_LINE.match(l)]
                new_raw = text + ("\n\n" + "\n".join(meta) if meta else "") + "\n"
                target.write_text(new_raw, encoding="utf-8")
                bak.write_text(original_raw, encoding="utf-8")
                rec_extra = {"rewritten_to": str(target.relative_to(ROOT)),
                             "backup": str(bak.relative_to(ROOT))}
            except OSError as e:
                rec_extra = {"rewrite_write_error": str(e)}
        else:
            rec_extra = {}
    else:
        rec_extra = {}

    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "origin": origin,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        "chars": len(text),
        "rewritten": rewritten,
        "before": before,
        "after": after,
        "qa_exit": qa_rc,
    }
    rec.update(rec_extra)
    append_receipt(rec)

    if args.json:
        print(json.dumps({"passed": passed, "text": text, "reasons": reasons,
                          "before": before, "after": after, "qa": qa_out},
                         ensure_ascii=False, indent=2))
    else:
        if rewritten:
            print(f"━━━ 自动清理后 ━━━\n{text}\n", file=sys.stderr)
        if qa_out:
            print(qa_out, file=sys.stderr)
        if passed:
            print("━━━ 闸门通过，可以发 ━━━")
        else:
            print("━━━ 闸门未过，不许发 ━━━")
            for r in reasons:
                print(f"  - {r}")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
