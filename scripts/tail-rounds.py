#!/usr/bin/env python3
"""只读轮次 memory 的最后 N 段 —— 避免每轮把整份 memory 塞进上下文。

用法:
    python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 3
    python3 scripts/tail-rounds.py state/memory/chuangzuo.md --rounds 2 --grep chuangzuo

段起始 = 行首 `##`/`###` 且标题含 pulse / chuangzuo / 日报（不区分大小写）。
没有段标记时退化为输出文件末尾 N 行。
"""
import argparse
import re
import sys

SEG = re.compile(r"^#{2,3}\s+.*(?:pulse|chuangzuo|日报)", re.I)


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

    starts = [i for i, ln in enumerate(lines) if SEG.match(ln)]
    if not starts:
        out = "\n".join(lines[-args.rounds * 40 :])
    else:
        segs = []
        for k, st in enumerate(starts):
            en = starts[k + 1] if k + 1 < len(starts) else len(lines)
            segs.append("\n".join(lines[st:en]).rstrip())
        if args.grep:
            segs = [s for s in segs if args.grep.lower() in s.split("\n", 1)[0].lower()]
        out = "\n\n".join(segs[-args.rounds :])

    if args.max_bytes and len(out.encode()) > args.max_bytes:
        out = out.encode()[: args.max_bytes].decode("utf-8", "ignore") + "\n...[已截断]"
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
