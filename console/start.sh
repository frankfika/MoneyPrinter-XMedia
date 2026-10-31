#!/bin/bash
# 短文助手控制台 · 启动
# 用法： ./console/start.sh          后台起，浏览器打开
#        ./console/start.sh --fg     前台跑（Ctrl+C 停）
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${SHORTBOT_CONSOLE_PORT:-8848}"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

if curl -s -o /dev/null "http://127.0.0.1:$PORT/api/overview"; then
  echo "控制台已经在跑 → http://127.0.0.1:$PORT"
  open "http://127.0.0.1:$PORT" 2>/dev/null || true
  exit 0
fi

if [ "$1" = "--fg" ]; then
  exec "$PY" "$ROOT/console/serve.py"
fi

mkdir -p "$ROOT/logs"
nohup "$PY" "$ROOT/console/serve.py" > "$ROOT/logs/console.log" 2>&1 &
sleep 1.2
if curl -s -o /dev/null "http://127.0.0.1:$PORT/api/overview"; then
  echo "控制台已启动 → http://127.0.0.1:$PORT"
  open "http://127.0.0.1:$PORT" 2>/dev/null || true
else
  echo "启动失败，看 logs/console.log"; tail -20 "$ROOT/logs/console.log"; exit 1
fi
