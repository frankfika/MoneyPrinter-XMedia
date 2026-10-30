#!/usr/bin/env bash
# 可选：给 xb.py 建一个本地 venv（playwright + pyyaml）。
# 好处：启动更快（免去每次 uv 解析）、uv 不在线时也能跑。
# xb.py 会优先使用 scripts/browser/.venv；没建就自动走 `uv run --with playwright`。
#
#   bash scripts/browser/setup.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"

command -v uv >/dev/null 2>&1 || {
  echo "需要 uv（brew install uv），或用 pip install playwright 后直接跑 xb.py" >&2
  exit 1
}

echo "==> 建 venv: $VENV"
uv venv "$VENV"

echo "==> 安装 playwright + pyyaml（不下载浏览器，用 channel=chrome 复用系统 Chrome）"
uv pip install --python "$VENV/bin/python" playwright pyyaml

echo "==> 自检"
"$VENV/bin/python" -c "import playwright.sync_api, yaml; print('playwright + pyyaml OK')"

echo "==> 试跑 xb.py"
python3 "$HERE/xb.py" --list-actions >/dev/null 2>&1 || true
echo "完成。之后 python3 scripts/browser/xb.py ... 会自动用这个 venv。"
