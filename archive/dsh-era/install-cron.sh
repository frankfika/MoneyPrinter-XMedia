#!/bin/bash
# 短文助手 · 三条 cron 的安装/卸载/状态（launchd 版）
#
# 为什么是 launchd 不是 DSH schedule：
#   DSH 的 schedule 语义是「投递回原 Session」（dsh-schedule 包描述：
#   "durable reminders ... original-Session delivery"），上下文会无限膨胀，
#   正是 HANDOVER.md §6 记的 305K/512K compaction 事故根因。
#   launchd + `dsh --profile shortbot` 每轮都是全新进程 / 全新 session，
#   与老机器 Mavis cron 的 `session.mode = new` 语义等价，且不依赖 GUI 是否开着。
#
# 用法：
#   scripts/install-cron.sh --install     装三条（幂等，重复执行会覆盖 plist 后重载）
#   scripts/install-cron.sh --uninstall   卸载三条
#   scripts/install-cron.sh --status      看三条是否在跑 / 下次触发
#   scripts/install-cron.sh --install --dry-run   只打印将要写出的 plist，不落盘
set -uo pipefail

REPO="/Users/fangchen/shortbot"
RUNNER="$REPO/scripts/run-round.sh"
AGENTS="$HOME/Library/LaunchAgents"
PREFIX="com.fangchen.shortbot"

declare -a LINES=(chuangzuo pulse super-bot)
declare -a LABELS=("短文助手-创作" "短文助手-互动" "短文助手-汇报")

plist_body() {
  local line="$1" hours="$2" minute="$3"
  cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PREFIX.$line</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$RUNNER</string>
    <string>$line</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$REPO</string>

  <!-- 服务器时区：本机已是 Asia/Shanghai，launchd 用本地时间触发 -->
  <key>StartCalendarInterval</key>
  <array>
$(for h in $hours; do cat <<ITEM
    <dict>
      <key>Hour</key><integer>$h</integer>
      <key>Minute</key><integer>$minute</integer>
    </dict>
ITEM
done)
  </array>

  <key>StandardOutPath</key>
  <string>$REPO/logs/launchd/$line.out.log</string>
  <key>StandardErrorPath</key>
  <string>$REPO/logs/launchd/$line.err.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key>
    <string>$HOME</string>
    <key>LANG</key>
    <string>zh_CN.UTF-8</string>
  </dict>

  <key>RunAtLoad</key>
  <false/>
  <key>ProcessType</key>
  <string>Interactive</string>
</dict>
</plist>
PLIST
}

# 与 state/schedule.yaml 保持一致（HANDOVER §6）
hours_for() {
  case "$1" in
    chuangzuo) echo "3 15" ;;
    pulse)     echo "4 10 16 22" ;;
    super-bot) echo "9" ;;
  esac
}
minute_for() {
  case "$1" in
    chuangzuo) echo 30 ;;
    *)         echo 0 ;;
  esac
}

ACTION="${1:-}"; DRY="${2:-}"
mkdir -p "$AGENTS" "$REPO/logs/launchd" "$REPO/logs/rounds"

case "$ACTION" in
  --install)
    for i in "${!LINES[@]}"; do
      line="${LINES[$i]}"
      plist="$AGENTS/$PREFIX.$line.plist"
      if [ "$DRY" = "--dry-run" ]; then
        echo "=== would write $plist ==="
        plist_body "$line" "$(hours_for "$line")" "$(minute_for "$line")"
        continue
      fi
      plist_body "$line" "$(hours_for "$line")" "$(minute_for "$line")" > "$plist"
      launchctl bootout "gui/$(id -u)/$PREFIX.$line" 2>/dev/null
      if launchctl bootstrap "gui/$(id -u)" "$plist" 2>/dev/null; then
        echo "OK   $line → ${plist}（已加载）"
      else
        echo "FAIL $line → bootstrap 失败，请手动: launchctl bootstrap gui/$(id -u) $plist" >&2
      fi
    done
    ;;
  --uninstall)
    for line in "${LINES[@]}"; do
      launchctl bootout "gui/$(id -u)/$PREFIX.$line" 2>/dev/null && echo "unloaded $line" || echo "not loaded $line"
      rm -f "$AGENTS/$PREFIX.$line.plist" && echo "removed  $line plist"
    done
    ;;
  --status)
    for line in "${LINES[@]}"; do
      printf "%-10s " "$line"
      if launchctl print "gui/$(id -u)/$PREFIX.$line" >/dev/null 2>&1; then
        echo "LOADED  ($(launchctl print "gui/$(id -u)/$PREFIX.$line" 2>/dev/null | grep -m1 'state =' | tr -s ' '))"
      else
        echo "not loaded"
      fi
    done
    echo; echo "最近日志："
    ls -lt "$REPO/logs/rounds" 2>/dev/null | head -5
    ;;
  *)
    echo "usage: $0 {--install|--uninstall|--status} [--dry-run]"; exit 1 ;;
esac
