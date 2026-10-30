#!/bin/bash
# 优雅重启 DSH，并在「新进程起不来」时自动回滚浏览器插件配置再重试一次。
#
# 为什么要它：desktop profile 的组合（cordis.patch.yml + package.json 的 bundles）只在
# host 启动时加载，改完必须重启 app 才生效。而重启期间如果配置有问题，app 会起不来，
# 人在 GUI 里就没法自救 —— 所以把「回滚 + 再拉起」做进脚本里。
#
# 用法：
#   scripts/restart-dsh.sh [--delay 秒]
#   scripts/restart-dsh.sh --check     只检查当前进程/composition 状态，不重启
set -euo pipefail

APP_NAME="DeepSeek Harness"
HOST_PAT="dsh-desktop-host/lib/index.js"
REVERT="$HOME/shortbot/scripts/revert-dsh-browser.sh"
LOG="$HOME/Library/Logs/shortbot/restart-dsh.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

# 注意：macOS 的 pgrep -f 匹配不到这个长 argv 的进程（实测，ps 能看到但 pgrep 返回 1），只能用 ps
host_pid() { ps ax -o pid=,command= | grep -F "$HOST_PAT" | grep -v grep | awk '{print $1}' | head -1; }

wait_host() {  # $1=期望秒数
  local n=0
  while [ "$n" -lt "${1:-45}" ]; do
    if [ -n "$(host_pid)" ]; then return 0; fi
    sleep 1; n=$((n+1))
  done
  return 1
}

if [ "${1:-}" = "--check" ]; then
  pid="$(host_pid)"
  if [ -n "$pid" ]; then
    log "host 在跑 pid=$pid  启动于 $(ps -o lstart= -p "$pid" | tr -s ' ')"
    grep -q "dsh-experimental-browser-use-playwright-mcp" "$HOME/.dsh/profiles/desktop/cordis.patch.yml" \
      && log "配置里有内置浏览器条目（若进程启动早于该文件修改时间，则尚未生效）" \
      || log "配置里没有内置浏览器条目"
  else
    log "host 没在跑"
  fi
  exit 0
fi

DELAY=0
[ "${1:-}" = "--delay" ] && DELAY="${2:-0}"
[ "$DELAY" -gt 0 ] && { log "delay ${DELAY}s before restart"; sleep "$DELAY"; }

OLD_PID="$(host_pid || true)"
log "旧 host pid=${OLD_PID:-none}"

log "quit app"
osascript -e "quit app \"$APP_NAME\"" 2>/dev/null || true
for i in $(seq 1 15); do [ -z "$(host_pid)" ] && break; sleep 1; done
if [ -n "$(host_pid)" ]; then
  log "quit 超时，TERM 旧进程"
  pkill -TERM -f "$HOST_PAT" 2>/dev/null || true
  sleep 3
  pkill -KILL -f "$HOST_PAT" 2>/dev/null || true
  sleep 2
fi

log "reopen"
open -a "$APP_NAME" 2>/dev/null || true

if wait_host 60; then
  log "OK 新 host pid=$(host_pid) 启动于 $(ps -o lstart= -p "$(host_pid)" | tr -s ' ')"
  exit 0
fi

log "FAIL 新 host 没起来 → 自动回滚浏览器插件配置，然后再拉起一次"
[ -x "$REVERT" ] && bash "$REVERT" >> "$LOG" 2>&1 || log "回滚脚本不存在，手动还原 $HOME/.dsh/profiles/desktop/{package.json,cordis.patch.yml}.bak-20261026-before-browser2"
open -a "$APP_NAME" 2>/dev/null || true
if wait_host 60; then
  log "OK 回滚后 host 起来了 pid=$(host_pid)"
else
  log "STILL FAIL —— 需要人工：看 $HOME/Library/Logs/DeepSeek*/，或终端跑 $REVERT"
fi
