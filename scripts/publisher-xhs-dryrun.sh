#!/usr/bin/env bash
# 短文助手 · 小红书发布 dry-run
# 用途：验证 publisher-xhs 决策逻辑，不实际探后台
# 用法：bash scripts/publisher-xhs-dryrun.sh [outputs/<dir>]
# 退出码：0 = 可以走（agent 代点发布，仍需当次确认卡）/ 1 = 应当停手
# 口径（2026-10-29 17:11 Frank 授权）：agent_publish_allowed=true + publish_mode=agent → 代点发布；
#   节奏分散、发布前确认卡、4 条操作硬约束（真窗口/不碰平台 AI 功能/不改设置/不连发）

set -uo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="${1:-outputs/1029-pm-gsa-procurement}"

echo "━━━ publisher-xhs dry-run ━━━"
echo "out dir: ${OUT_DIR}"

PYBIN=".venv/bin/python"
[ -x "$PYBIN" ] || PYBIN="python3"

"$PYBIN" - "$OUT_DIR" <<'PY'
import sys, pathlib
try:
    import yaml
except ModuleNotFoundError:
    sys.exit("FATAL: 需要 pyyaml —— 用仓库 .venv 或 uv run --with pyyaml")

out_dir = sys.argv[1]
safety = yaml.safe_load(pathlib.Path("private/account-safety.yaml").read_text())
xhs = safety["xhs"]

# 兼容新旧两种 schema：2026-10-29 后 is_banned 在 xhs 顶层；更早是 ban_status.is_banned
if "is_banned" in xhs:
    is_banned = bool(xhs["is_banned"])
    ban_reason = xhs.get("ban_reason", "n/a")
else:
    is_banned = bool(xhs.get("ban_status", {}).get("is_banned", True))
    ban_reason = xhs.get("ban_status", {}).get("ban_reason", "n/a")

publish_mode = xhs.get("publish_mode", xhs.get("publish_mode_default", "draft_only"))
agent_allowed = bool(xhs.get("agent_publish_allowed", False))
login_state = xhs.get("login_state", "unknown")

out = pathlib.Path(out_dir)
xhs_txt = out / "xhs.txt"
shots_dir = out / "screenshots"

print(f"\n[1] 账号安全状态")
print(f"    is_banned = {is_banned}")
print(f"    ban_reason = {ban_reason}")
print(f"    publish_mode = {publish_mode}")
print(f"    agent_publish_allowed = {agent_allowed}")
print(f"    login_state = {login_state}")

print(f"\n[2] 输出产物检查")
if xhs_txt.exists():
    title_line = xhs_txt.read_text().splitlines()[0]
    print(f"    xhs.txt 存在，标题: {title_line!r}")
else:
    print(f"    ⚠️  xhs.txt 不存在")
if shots_dir.exists():
    n = len(list(shots_dir.glob("*.png")))
    print(f"    screenshots/ 有 {n} 张图")
else:
    print(f"    ⚠️  screenshots/ 不存在")

print(f"\n[3] 决策")
if is_banned:
    print("    ❌ 账号在封禁中 → publisher-xhs 必须停手")
    print("    → 动作：把 xhs.txt + screenshots 路径给 Fang，由 Fang 手发")
    sys.exit(1)
if not (agent_allowed and publish_mode == "agent"):
    print(f"    ❌ 未授权 agent 代点发布（agent_publish_allowed={agent_allowed}, publish_mode={publish_mode}）→ 停手")
    sys.exit(1)
if login_state != "logged_in":
    print(f"    ❌ login_state={login_state} → 停手，先把 URL 给 Fang 登录")
    sys.exit(1)

print("    ✅ 已解封 + agent 代点发布已授权 + 已登录")
print("    → 可以走 publisher-xhs：内置浏览器真窗口填稿 → 确认卡（站点/账号/标题/正文/图/可见性）→ 点发布")
print("    → 4 条操作硬约束：不碰平台 AI 功能 / 不改任何设置 / 真窗口 / 节奏分散不连发")
sys.exit(0)
PY
