#!/usr/bin/env bash
# Probe the current thread's tool inventory and write markers to .infra_probe/
# Used by health-gate.sh to know if cua_repl was available at boot time.
#
# 在 automation thread 的 hot-topic-tracker skill 入口跑一次
set -u
cd "$(dirname "$0")/.."

mkdir -p .infra_probe

# 这个 thread 的 tool inventory 由 Codex runtime 控制；本 shell script 不能直接 list tools,
# 所以发明 indirect probes:
# 1. 如果启动时 environment 有 CODEX_THREAD_HAS_CUA_REPL=1，则 mark available
# 2. 否则 absent
if [ "${CODEX_THREAD_HAS_CUA_REPL:-0}" = "1" ]; then
  echo "up" > .infra_probe/cua_repl_available
  echo "thread boot marked cua_repl=up"
else
  rm -f .infra_probe/cua_repl_available
  echo "thread boot marked cua_repl=down"
fi

# Probe mmx
MMX_BAL=$(mmx quota show 2>/dev/null | python3 -c "import json,sys
try:
    d=json.loads(sys.stdin.read())
    print(d.get('available_amount','-1'))
except Exception:
    print('-1')" 2>/dev/null || echo "-1")
echo "$MMX_BAL" > .infra_probe/mmx_balance_at_boot

# Probe r.jina.ai
RJ=$(curl -s -m 3 -o /dev/null -w "%{http_code}" "https://r.jina.ai/" 2>/dev/null || echo "000")
echo "$RJ" > .infra_probe/r_jina_status_at_boot

