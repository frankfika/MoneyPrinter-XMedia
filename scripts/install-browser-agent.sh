#!/bin/bash
# 自动化 Chrome 常驻器 —— 让 DSH 内置浏览器（playwright-mcp，mode: attach）和
# scripts/browser/xb.py 都永远有一个带登录态、开着 CDP 9222 的 Chrome 可以附着。
#
# 为什么需要它（2026-10-26 实测）：
#   - 内置浏览器 attach 模式的语义是「会话独占 + 附着到已存在的浏览器」，
#     9222 上没浏览器 → 该会话的浏览器工具直接不可用；
#   - 手工 `open -na ... --remote-debugging-port=9222` 起的 Chrome 重启机器就没了；
#   - 所以用 LaunchAgent 在登录时把 Chrome 拉起来，登录态存在 profile 里，跨重启保留。
#
# 用法：
#   scripts/install-browser-agent.sh --install     安装并立即启动
#   scripts/install-browser-agent.sh --status      看状态
#   scripts/install-browser-agent.sh --uninstall   卸载（不杀正在跑的 Chrome）
#
# 注意：profile 目录必须**不是** ~/Library/Application Support/Google/Chrome
#      （Chrome 136+ 拒绝在默认 profile 上开远程调试端口；且 macOS TCC 不让读）。
set -euo pipefail
set -u

LABEL="com.fangchen.shortbot.browser"
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/$LABEL.plist"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="$HOME/.shortbot-browser-profile"
PORT=9222
LOG_DIR="$HOME/Library/Logs/shortbot"

ACTION="${1:---status}"

status() {
  if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
    echo "$LABEL  LOADED  ($(launchctl print "gui/$(id -u)/$LABEL" | awk '/state =/{print $0; exit}' | sed 's/^[[:space:]]*//'))"
  else
    echo "$LABEL  not loaded"
  fi
  if curl -s -m 3 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo "CDP $PORT  活着：$(curl -s -m 3 "http://127.0.0.1:$PORT/json/version" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("Browser","?"))' 2>/dev/null)"
  else
    echo "CDP $PORT  没有响应"
  fi
  echo "profile   $PROFILE"
}

install() {
  mkdir -p "$AGENTS" "$LOG_DIR"
  if [ ! -x "$CHROME" ]; then echo "FATAL: 找不到 Chrome: $CHROME" >&2; exit 1; fi
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$CHROME</string>
    <string>--user-data-dir=$PROFILE</string>
    <string>--remote-debugging-port=$PORT</string>
    <string>--remote-allow-origins=*</string>
    <string>--no-first-run</string>
    <string>--no-default-browser-check</string>
    <string>--no-service-autorun</string>
    <string>--disable-sync</string>
    <string>--lang=zh-CN</string>
    <string>about:blank</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
  <key>StandardOutPath</key><string>$LOG_DIR/chrome.out.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/chrome.err.log</string>
</dict></plist>
PLISTEOF
  plutil -lint "$PLIST" >/dev/null || { echo "FATAL: plist 非法" >&2; exit 1; }
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  launchctl kickstart -p "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  echo "installed $PLIST"
  sleep 3
  status
}

uninstall() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null && echo "unloaded $LABEL" || echo "not loaded $LABEL"
  rm -f "$PLIST" && echo "removed $PLIST"
  echo "（没有杀正在跑的 Chrome —— 要关就自己关窗口）"
}

case "$ACTION" in
  --install) install ;;
  --status) status ;;
  --uninstall) uninstall ;;
  *) echo "用法: $0 --install|--status|--uninstall" >&2; exit 1 ;;
esac
