#!/usr/bin/env bash
# 只读冒烟：验证 xb.py 的三条核心链路（导航 / 读文本 / 读 likes·截图）。
# 只读，不点赞、不回复、不发帖、不登录。
#
#   bash scripts/browser/smoke.sh
#
# 退出码：0 = 全部关键链路通过；1 = 有关键链路失败（自动打印 error.code）
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
XB=(python3 "$ROOT/scripts/browser/xb.py")
PROFILE="${1:-https://x.com/frankfika}"
FAILED=0

hr() { printf '%s\n' "------------------------------------------------------------"; }

call() {  # call <说明> <action-json>
  local desc="$1" action="$2" out code
  printf '### %s\n' "$desc"
  printf '$ python3 scripts/browser/xb.py --action %s\n' "'$action'"
  out="$("${XB[@]}" --action "$action" 2>/dev/null)"
  code=$?
  printf '%s\n' "$out"
  printf 'exit=%s\n\n' "$code"
  LAST_OUT="$out"
  LAST_CODE="$code"
  if [ "$code" -ne 0 ]; then
    FAILED=$((FAILED + 1))
  fi
}

hr
printf 'xb.py 只读冒烟 · profile=%s\n' "$PROFILE"
printf 'browser.yaml: %s\n' "$ROOT/private/browser.yaml"
hr

call "0. login_state（未登录 logged_in=false 也算正常）" '{"action":"login_state"}'

call "1. navigate" "{\"action\":\"navigate\",\"input\":{\"url\":\"$PROFILE\"}}"

call "2. query kind=text（页面可见文本，截断 800 字符）" \
     '{"action":"query","input":{"kind":"text","maxChars":800}}'

# 3. §8.5 规定的唯一合法 likes 读法：query kind=dom 打 [data-testid='like'] 读 aria-label
printf '### 3. query kind=dom → [data-testid=%s] aria-label（手册 §8.5）\n' "'like'"
printf '$ python3 scripts/browser/xb.py --action '"'"'{"action":"query","input":{"kind":"dom","selector":"[data-testid='"'"'"'"'"'"'"'like'"'"'"'"'"'"'"']"}}'"'"'\n'
out="$("${XB[@]}" --action '{"action":"query","input":{"kind":"dom","selector":"[data-testid='"'"'like'"'"']"}}' 2>/dev/null)"
code=$?
printf '%s\n' "$out"
printf 'exit=%s\n' "$code"
if [ "$code" -eq 0 ]; then
  printf '✅ likes 可读（登录态有效）\n\n'
else
  # 未登录时 X 会剥离 data-testid，这是环境事实，不是工具坏；只警告不算失败
  printf '⚠️  读不到 [data-testid=%s]：通常是「X 未登录，页面被剥离 data-testid」。\n' "'like'"
  printf '    需要 Frank 在 %s 这个 profile 里人工登录一次，之后同一命令即可读到 aria-label="N Likes. Like"。\n\n' \
         "${XB_PROFILE:-~/.shortbot-browser-profile}"
fi

call "4. screenshot（落盘证明截图链路通）" \
     '{"action":"screenshot","input":{"path":"scripts/browser/_smoke.png"}}'

hr
if [ "$FAILED" -eq 0 ]; then
  printf '✅ 冒烟通过：navigate / query text / screenshot 全部 exit 0\n'
  exit 0
fi
printf '❌ 有 %d 条关键链路失败，看上面对应的 error.code\n' "$FAILED"
exit 1
