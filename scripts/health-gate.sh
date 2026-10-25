#!/usr/bin/env bash
# 短文助手 · 启动前 health gate (2026-10-16 review 加)
# 探测 3 个 infra 通道：cua_repl / r.jina.ai / mmx search
# 输出 PLAN 标记：plan-a/b/c/d，下游按 plan 选路径
set -u
cd "$(dirname "$0")/.."

# jina key source: ~/.jina/config.json 或 JINA_API_KEY env（兜底）
if [ -f ~/.jina/config.json ]; then
  JINA_API_KEY=$(python3 -c "import json,sys; d=json.load(open('/Users/fangchen/.jina/config.json')); print(d.get('api_key',''))" 2>/dev/null)
fi
JINA_API_KEY="${JINA_API_KEY:-${JINA_API_KEY_ENV:-}}"

LOG=logs/health-gate.log
mkdir -p "${LOG%/*}"

echo "[$(date -Iseconds)] health-gate START" | tee -a "$LOG"

PLAN=""
CUA_REPL="down"
R_JINA="down"
MMX="down"
MMX_BAL="?"

# 1. cua_repl: 看本 thread 启动时是否标记过 (proxy via env file written by scripts/probe-inventory.sh)
if [ -f .infra_probe/cua_repl_available ]; then
  CUA_REPL="up"
fi

# 2. r.jina.ai (2026-10-16 update: 也可能 403 abuse-ban，需要 body 验证)
RJ_RESP=$(curl -s -m 3 -w "
%{http_code}" "https://r.jina.ai/https://x.com/OpenAI" 2>/dev/null || echo "000")
RJ_CODE=$(echo "$RJ_RESP" | tail -1)
# 真 up 标志：status 200 + body 里有 "Google DeepMind on X" 等时间线特征
if [ "$RJ_CODE" = "200" ] && echo "$RJ_RESP" | grep -q "Google DeepMind on X\|OpenAI on X\|Anthropic on X"; then
  R_JINA="up"
elif [ "$RJ_CODE" = "403" ] && echo "$RJ_RESP" | grep -q "AbuseAlleviationError"; then
  R_JINA="abuse_banned"
elif [ "$RJ_CODE" = "401" ]; then
  R_JINA="needs_key"
else
  R_JINA="down"
fi

# 3. mmx balance - 新版本 mmx CLI 返回 model_remains 数组 (5h interval / weekly)
# 同时兼容老格式 available_amount
MMX_STATUS="unknown"
mmx_quota_out=$(mmx quota show --output json 2>/dev/null)
MMX_DETAIL=$(echo "$mmx_quota_out" | python3 -c "
import json,sys
try:
    d=json.loads(sys.stdin.read())
except Exception:
    print('err')
    sys.exit()
if 'error' in d:
    print('err')
    sys.exit()
# New format: model_remains array
if 'model_remains' in d:
    for m in d['model_remains']:
        if m.get('model_name') == 'general':
            print('up', m.get('current_interval_remaining_percent', 0), m.get('current_weekly_remaining_percent', 0))
            sys.exit()
# Old format: available_amount
aa = float(d.get('available_amount', '-1'))
print('up' if aa > 0 else 'insufficient')
" 2>/dev/null)
case "$MMX_DETAIL" in
  up*) MMX="up"; MMX_BAL="$MMX_DETAIL" ;;
  insufficient|err) MMX="down"; MMX_BAL="insufficient/err" ;;
  *) MMX="down"; MMX_BAL="unknown:$MMX_DETAIL" ;;
esac

# Plan X-prime: 直接 curl x.com/<handle> - 绕过所有 SaaS (2026-10-16 发现)
# 特征：抓到的 HTML 必须含 __INITIAL_DATA__ (hydrate data) + tweet_results 不为空
X_PRIME_STATUS="down"
X_RESP=$(curl -sL -m 5 -A "Mozilla/5.0" "https://x.com/OpenAI" 2>/dev/null)
if echo "$X_RESP" | grep -q "twimg.com" && echo "$X_RESP" | grep -q "OpenAI"; then
  X_PRIME_STATUS="up"
fi
# 选 plan
if [ "$CUA_REPL" = "up" ]; then
  PLAN="A"
elif [ "$R_JINA" = "up" ]; then
  PLAN="B"
elif [ "$MMX" = "up" ]; then
  PLAN="C"
elif [ "$X_PRIME_STATUS" = "up" ]; then
  PLAN="X"  # prime = direct x.com curl
else
  PLAN="D"
fi

echo "[$(date -Iseconds)] health-gate RESULT plan=${PLAN} cua_repl=${CUA_REPL} r_jina=${R_JINA} mmx=${MMX} x_prime=${X_PRIME_STATUS} mmx_bal=${MMX_BAL}" | tee -a "$LOG"
echo "$PLAN"
