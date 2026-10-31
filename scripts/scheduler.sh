#!/bin/bash
# scheduler.sh — 本地常驻调度器（2026-10-31 起，替代 launchd；由 Claude 直接控制）
# 每 30s 醒一次，到点且该档没跑过就 fire 一轮 scripts/run-round.sh。
# 控制：启动 nohup bash scripts/scheduler.sh & ；停止 touch logs/local/.scheduler-stop 或 kill $(cat logs/local/.scheduler.pid)
set -uo pipefail

ROOT="/Users/fangchen/shortbot"
cd "$ROOT" || exit 1
mkdir -p logs/local
STOP="$ROOT/logs/local/.scheduler-stop"
PIDF="$ROOT/logs/local/.scheduler.pid"
rm -f "$STOP"
echo $$ > "$PIDF"
trap 'rm -f "$PIDF"' EXIT

log() { echo "[$(date +%F_%T)] $*" >> logs/local/scheduler.log; }
log "scheduler start (pid $$)"

# line|minute|hours(逗号分隔)
SCHED=(
  "chuangzuo|30|0,2,4,6,8,10,12,14,16,18,20,22"
  "pulse|0|4,10,16,22"
  "xhs|37|9,12,16,20"
  "super-bot|0|9"
)

while [ ! -f "$STOP" ]; do
  H=$(date +%-H); M=$(date +%-M); TODAY=$(date +%Y%m%d)
  for entry in "${SCHED[@]}"; do
    IFS='|' read -r line minute hours <<< "$entry"
    [ "$M" = "$minute" ] || continue
    case ",$hours," in *",$H,"*) ;; *) continue ;; esac
    STAMP="logs/local/.fired-${line}-${TODAY}-${H}${M}"
    [ -e "$STAMP" ] && continue
    touch "$STAMP"
    log "fire $line"
    bash scripts/run-round.sh "$line" &
  done
  sleep 30
done
log "scheduler stop requested"
