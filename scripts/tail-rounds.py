#!/usr/bin/env python3
"""只读轮次 memory 的最后 N 段 —— 避免每轮把整份 memory 塞进上下文。

用法:
    python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 3
    python3 scripts/tail-rounds.py state/memory/chuangzuo.md --rounds 2 --grep chuangzuo

段边界：**优先按显式分隔符 `<!-- round -->` 切**（2026-10-26 起约定）。
没有分隔符的旧文件才退回标题正则。

⚠️ 为什么不靠标题正则：轮次段内部的小节标题经常含关键词
（`### 规则扩展（跟 pulse round 55 同源）`、`## Engagement pulse`），
按关键词匹配会把它们误切成独立段，tail 读出来就是碎片而不是完整一轮。
标题正则只作旧文件兼容，且必须人工校验。
"""
import argparse
import re
import sys

SEP = "<!-- round -->"
LEGACY_SEG = re.compile(
    r"^#{2,3}\s+(?:.*\bpulse[_ ]round|.*\bchuangzuo[_ ]round|日报\s*·)",
    re.I,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--rounds", type=int, default=3, help="取最后 N 个轮次段")
    ap.add_argument("--grep", default=None, help="只保留标题含该词的段")
    ap.add_argument("--max-bytes", type=int, default=0, help="输出字节上限（0 = 不限）")
    args = ap.parse_args()

    try:
        with open(args.path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
    except OSError as exc:
        print(f"读不到 {args.path}: {exc}", file=sys.stderr)
        return 1

    starts = []
    if SEP in "\n".join(lines):
        starts = [i for i, ln in enumerate(lines) if ln.strip() == SEP]
        # 分隔符本身不计入段内容
        segs = []
        for k, st in enumerate(starts):
            en = starts[k + 1] if k + 1 < len(starts) else len(lines)
            segs.append("\n".join(lines[st + 1 : en]).strip())
    else:
        starts = [i for i, ln in enumerate(lines) if LEGACY_SEG.match(ln)]
        segs = []
        for k, st in enumerate(starts):
            en = starts[k + 1] if k + 1 < len(starts) else len(lines)
            segs.append("\n".join(lines[st:en]).rstrip())

    if not segs:
        out = "\n".join(lines[-args.rounds * 40 :])
    else:
        if args.grep:
            segs = [s for s in segs if args.grep.lower() in s.split("\n", 1)[0].lower()]
        out = "\n\n".join(segs[-args.rounds :])

    if args.max_bytes and len(out.encode()) > args.max_bytes:
        out = out.encode()[: args.max_bytes].decode("utf-8", "ignore") + "\n...[已截断]"
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
