#!/bin/bash
# install-launchd.sh — 安装/重装四条线的 launchd 定时任务（2026-10-31 起替代 Codex app Automations）
# 幂等：重复跑会先 bootout 再 bootstrap。卸载: bash scripts/install-launchd.sh --uninstall
set -euo pipefail

ROOT="/Users/fangchen/shortbot"
AGENTS="${DESTDIR:-$HOME/Library/LaunchAgents}"   # DESTDIR=/tmp/xxx 可干跑（只生成不加载）
mkdir -p "$AGENTS" "$ROOT/logs/launchd"

# line|时段（分钟 小时，逗号分隔的小时列表）
# chuangzuo 定在 :30 是为了错开 pulse(:00) 和 super-bot(09:00)，避免抢同一个浏览器
LINES=(
  "chuangzuo|30|0,2,4,6,8,10,12,14,16,18,20,22"
  "pulse|0|4,10,16,22"
  "xhs|37|9,12,16,20"
  "super-bot|0|9"
)

write_plist() {
  local label="$1" line="$2" minute="$3" hours="$4" file="$AGENTS/$label.plist"
  {
    cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT/scripts/run-round.sh</string>
    <string>$line</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key>
  <array>
EOF
    IFS=',' read -ra H <<< "$hours"
    for h in "${H[@]}"; do
      cat <<EOF
    <dict><key>Hour</key><integer>$h</integer><key>Minute</key><integer>$minute</integer></dict>
EOF
    done
    cat <<EOF
  </array>
  <key>StandardOutPath</key><string>$ROOT/logs/launchd/$line.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/launchd/$line.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key><string>$HOME</string>
    <key>LANG</key><string>zh_CN.UTF-8</string>
  </dict>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
EOF
  } > "$file"
  echo "written $file"
}

UID_NUM=$(id -u)
for entry in "${LINES[@]}"; do
  IFS='|' read -r line minute hours <<< "$entry"
  label="com.fangchen.shortbot.$line"
  if [ "${1:-}" = "--uninstall" ]; then
    launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
    rm -f "$AGENTS/$label.plist"
    echo "uninstalled $label"
  else
    write_plist "$label" "$line" "$minute" "$hours"
    if [ -n "${DESTDIR:-}" ]; then
      echo "dry-run: skip launchctl for $label"
    else
      launchctl bootout "gui/$UID_NUM/$label" 2>/dev/null || true
      launchctl bootstrap "gui/$UID_NUM" "$AGENTS/$label.plist"
      echo "installed $label  ($minute 点 $hours 时)"
    fi
  fi
done
