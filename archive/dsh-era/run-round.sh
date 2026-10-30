#!/bin/bash
# 短文助手 · 单轮执行器
#
# 用途：给 launchd / 手工补跑 调用的唯一入口。
#   每轮 = 一个全新的 `dsh --profile shortbot` 进程 = 全新 session
#   （对应 HANDOVER.md §6 的 session.mode = new，避免上下文膨胀到 305K 后被 compaction 打断）
#
# 用法：
#   scripts/run-round.sh chuangzuo        # 真跑一轮创作链路
#   scripts/run-round.sh pulse            # 真跑一轮互动
#   scripts/run-round.sh super-bot        # 真跑一轮日报
#   scripts/run-round.sh chuangzuo --dry-run   # 只打印抽取到的 prompt，不执行
#
# 退出码：
#   0   本轮正常结束（dsh 退出 0）
#   1   参数错误 / 前置检查失败
#   2   上一轮还没结束（锁被占用）
#   3   dsh 本身失败（网络 / 模型 / 崩溃）
set -uo pipefail

REPO="/Users/fangchen/shortbot"
DSH="${DSH_BIN:-/Users/fangchen/.dsh/app/node_modules/.bin/dsh}"
PROFILE="shortbot"
LOG_DIR="$REPO/logs/rounds"
LOCK_DIR="$REPO/logs/.locks"

LINE="${1:-}"
DRY_RUN="${2:-}"
PROMPT_MD="$REPO/docs/cron-prompts/$LINE.md"

case "$LINE" in
  chuangzuo|pulse|super-bot) ;;
  *) echo "usage: $0 {chuangzuo|pulse|super-bot} [--dry-run]" >&2; exit 1 ;;
esac

[ -f "$PROMPT_MD" ] || { echo "FATAL: prompt 文件不存在: $PROMPT_MD" >&2; exit 1; }

# prompt 唯一事实源 = docs/cron-prompts/<line>.md 里第一个 ``` 围栏块
PROMPT="$(awk '/^```/{f=!f; next} f' "$PROMPT_MD")"
[ -n "$PROMPT" ] || { echo "FATAL: 从 $PROMPT_MD 里抽不到 prompt 围栏块" >&2; exit 1; }

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "=== $LINE · 抽取到的 prompt（$(printf %s "$PROMPT" | wc -c | tr -d ' ') bytes）==="
  printf '%s\n' "$PROMPT"
  exit 0
fi

# ── 单飞锁：同一条线不允许并发（跨线可以并行）──
mkdir -p "$LOCK_DIR" "$LOG_DIR"
LOCK="$LOCK_DIR/$LINE.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  HOLDER="$(cat "$LOCK/pid" 2>/dev/null || echo '?')"
  if [ "$HOLDER" != "?" ] && kill -0 "$HOLDER" 2>/dev/null; then
    echo "SKIP: $LINE 上一轮还在跑（pid ${HOLDER}）" >&2
    exit 2
  fi
  echo "WARN: 清理陈旧锁（pid $HOLDER 已不存在）" >&2
  rm -rf "$LOCK"
  mkdir "$LOCK" 2>/dev/null || { echo "FATAL: 拿不到锁 $LOCK" >&2; exit 2; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT INT TERM

TS="$(date +%Y%m%d-%H%M%S)"
LOG="$LOG_DIR/$LINE-$TS.log"

# ── 前置检查（失败也要留下证据，不许安静什么都不做）──
{
  echo "=== round start $LINE $TS (+08:00) ==="
  echo "repo=$REPO"
  echo "dsh=$DSH"
  if [ ! -x "$DSH" ]; then echo "PRECHECK_FAIL: dsh 不可执行: $DSH"; exit 1; fi
  # 直连优先；launchd 上下文里直连可能 000（实测 2026-10-26），失败再试代理 7897
  echo -n "x.com 可达性: 直连="
  code="$(curl -s -o /dev/null -m 15 -w '%{http_code}' https://x.com/ 2>/dev/null)"
  echo -n "${code:-000}"
  if [ "${code:-000}" != "200" ]; then
    echo -n " 代理="
    code2="$(curl -s -o /dev/null -m 15 -w '%{http_code}' -x 127.0.0.1:7897 https://x.com/ 2>/dev/null)"
    echo -n "${code2:-000}"
    echo " （注意：curl 000 只影响这条预检；浏览器走 Chrome 自己的网络栈，2026-10-26 实测 launchd 下 navigate 仍 status=200）"
  else
    echo " （直连可用）"
  fi
  echo "--- prompt begin ---"
  printf '%s\n' "$PROMPT"
  echo "--- prompt end ---"
} > "$LOG" 2>&1

cd "$REPO" || { echo "FATAL: cd $REPO 失败" >&2; exit 1; }

# ── 登录前置守卫 ──
# 未登录时直接跳过，不烧模型额度、不产生「看起来跑了」的空轮次。
# super-bot 是只读线，不需要登录，所以豁免。
if [ "$LINE" != "super-bot" ]; then
  LOGIN_JSON="$(python3 "$REPO/scripts/browser/xb.py" --action '{"action":"login_state"}' 2>/dev/null)"
  LOGIN_RC=$?
  if [ "$LOGIN_RC" -eq 2 ]; then
    {
      echo "=== round skipped $LINE $TS reason=BROWSER_UNAVAILABLE (xb.py exit 2) ==="
      printf '%s\n' "$LOGIN_JSON"
    } >> "$LOG"
    echo "$LINE SKIPPED browser-unavailable log=$LOG"
    exit 0
  fi
  LOGGED_IN="$(printf '%s' "$LOGIN_JSON" | python3 -c 'import json,sys
try: print("true" if json.load(sys.stdin)["data"]["logged_in"] else "false")
except Exception: print("unknown")' 2>/dev/null)"
  if [ "$LOGGED_IN" != "true" ]; then
    {
      echo "=== round skipped $LINE $TS reason=NOT_LOGGED_IN (logged_in=$LOGGED_IN) ==="
      echo "先按 HANDOVER.md §5.2 在 ~/.shortbot-browser-profile 里登录 X，登录后本条线自动生效。"
      printf '%s\n' "$LOGIN_JSON"
    } >> "$LOG"
    echo "$LINE SKIPPED not-logged-in log=$LOG"
    exit 0
  fi
fi

# 注意：注释里不能出现反引号（会启动命令替换），这是这份脚本唯一的花活
"$DSH" --profile "$PROFILE" "$PROMPT" >> "$LOG" 2>&1
RC=$?

{
  echo "=== round end $LINE $(date +%Y%m%d-%H%M%S) rc=$RC ==="
} >> "$LOG"

echo "$LINE rc=$RC log=$LOG"
exit "$RC"
