#!/bin/bash
# run-round.sh <line> — 本地无头跑一轮流水线（2026-10-31 起替代 Codex app Automations）
# line: chuangzuo | pulse | xhs | super-bot
# prompt 唯一事实源 = docs/cron-prompts/<line>.md 第一个围栏块；本脚本只抽取，不维护副本。
set -uo pipefail

LINE="${1:?usage: run-round.sh <chuangzuo|pulse|xhs|super-bot>}"
ROOT="/Users/fangchen/shortbot"
cd "$ROOT" || exit 1

case "$LINE" in
  xhs) PROMPT_FILE="docs/cron-prompts/xhs-publish.md" ;;
  *)   PROMPT_FILE="docs/cron-prompts/${LINE}.md" ;;
esac
[ -f "$PROMPT_FILE" ] || { echo "missing $PROMPT_FILE" >&2; exit 1; }

mkdir -p logs/local
TS=$(date +%Y%m%d-%H%M%S)
LOG="logs/local/${LINE}-${TS}.log"

# 同一条线不并发（跨线可并行）；mkdir 原子锁（macOS 没有 flock）
# ponytail: 锁目录 >120min 视为上轮僵死直接抢占，够用于最长几十分钟的轮次
LOCKDIR="logs/local/.${LINE}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -n "$(find "$LOCKDIR" -maxdepth 0 -mmin +120 2>/dev/null)" ] && rmdir "$LOCKDIR" 2>/dev/null && mkdir "$LOCKDIR" 2>/dev/null; then
    echo "[$TS] stole stale lock" >> "$LOG"
  else
    echo "[$TS] previous $LINE round still running, skip" >> "$LOG"
    exit 0
  fi
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

# 抽取第一个 ``` 围栏块
PROMPT_TEXT=$(awk '/^```/{n++; if(n==1){inside=1; next} if(n==2){exit}} inside' "$PROMPT_FILE")
if [ -z "$PROMPT_TEXT" ]; then
  echo "[$TS] no fenced prompt block in $PROMPT_FILE" >> "$LOG"
  exit 1
fi

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export LANG="zh_CN.UTF-8"

echo "[$TS] round start (codex exec)" >> "$LOG"
codex exec -s danger-full-access -C "$ROOT" "$PROMPT_TEXT" >> "$LOG" 2>&1
RC=$?
echo "[$(date +%Y%m%d-%H%M%S)] round end, exit=$RC" >> "$LOG"
exit 0
