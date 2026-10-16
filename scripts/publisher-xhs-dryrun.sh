#!/usr/bin/env bash
# 短文助手 · 小红书发布 dry-run
# 用途：解封 + Fang 授权后，验证 publisher-xhs 决策逻辑，不实际探后台
# 用法：bash scripts/publisher-xhs-dryrun.sh [outputs/<dir>]
# 退出码：0 = 可以走，1 = 应当停手

set -uo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="${1:-outputs/1015-pm/karpathy-frontier-5000}"

echo "━━━ publisher-xhs dry-run ━━━"
echo "out dir: ${OUT_DIR}"

# 把决策结果写到一个临时文件，退出码另传
TMP=$(mktemp)
trap "rm -f ${TMP}" EXIT

python3 - "${OUT_DIR}" > "${TMP}" <<'PY'
import yaml, json, sys, pathlib

out_dir = sys.argv[1]
safety = yaml.safe_load(pathlib.Path("private/account-safety.yaml").read_text())
xhs = safety["xhs"]

is_banned = xhs["ban_status"]["is_banned"]
publish_mode = xhs.get("publish_mode_default", "draft_only")
login_state = xhs.get("login_state", "unknown")

out = pathlib.Path(out_dir)
xhs_txt = out / "xhs.txt"
shots_dir = out / "screenshots"

print(f"\n[1] 账号安全状态")
print(f"    is_banned = {is_banned}")
print(f"    ban_reason = {xhs['ban_status'].get('ban_reason', 'n/a')}")
print(f"    publish_mode_default = {publish_mode}")
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
    print(f"    ❌ 账号仍在封禁（ban_reason: {xhs['ban_status'].get('ban_reason')}）")
    print(f"    → publisher-xhs 必须停手")
    print(f"    → 动作：把 xhs.txt + screenshots 路径给 Fang，由 Fang 在 App 内手贴")
    sys.exit(1)

if publish_mode != "draft_only":
    print(f"    ❌ publish_mode = {publish_mode}（应该 draft_only）")
    sys.exit(1)

if login_state not in ("logged_in", "unknown"):
    print(f"    ❌ login_state = {login_state}（不可登录）")
    sys.exit(1)

print(f"    ✅ 账号已解封、publish_mode=draft_only、login_state 可用")
print(f"    → publisher-xhs 现在可以走：登录创作者中心 → 填 → 只点存草稿，绝不点发布")
print(f"    → 当前动作会真实探后台，请确认你已经看到 Fang 说「可以存草稿了」再执行")
sys.exit(0)
PY
RC=$?

cat "${TMP}"
echo
echo "━━━ 退出码：${RC} (0=可以走 / 1=停手) ━━━"
exit ${RC}
