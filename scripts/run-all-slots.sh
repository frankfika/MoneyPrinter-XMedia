#!/usr/bin/env bash
# 短文助手 · 手动跑一轮全部 slot（等价于 9/12/15/18/21 cron 触发一次）
# 用法：bash scripts/run-all-slots.sh
#
# ⚠️ 2026-10-15 重要：
#   - 本脚本 + scan-slot.sh 是 **Cron 模式兜底** 路径（lite: mmx web search）
#   - mmx 不支持 from:X → 几乎永远 0 候选
#   - **默认模式是 Codex session 模式**（cua_repl 真扫），agent 应该先检测 cua_repl 可用性
#   - 只有 agent 在纯后台 / 无 cua_repl 的环境才走这条脚本
#   - 详细 Codex session 流程看 scripts/cua-full-flow.md

set -euo pipefail
cd "$(dirname "$0")/.."

echo "[$(date -Iseconds)] === CRON-MODE run-all-slots.sh ==="
echo "[$(date -Iseconds)] 注意：本模式 lite 路径，期望 0 候选或极少命中"
echo "[$(date -Iseconds)] Codex session 应该直接用 mcp__cua_repl__js 真扫，绕过本脚本"
echo ""

for SLOT in am noon pm eve night; do
  echo "=== slot=${SLOT} ==="
  bash scripts/scan-slot.sh "${SLOT}"
  sleep 2
done
echo "=== all slots done ==="
echo "[$(date -Iseconds)] === CRON-MODE done; agent 请根据实际 candidates 决定是否切到 cua_repl 真扫 ==="
