#!/usr/bin/env bash
# 短文助手 · 一键体检
# 用法：bash scripts/health-check.sh

set -uo pipefail
cd "$(dirname "$0")/.."

echo "━━━ 1. state/*.yaml 解析 + 关键计数 ━━━"
# 2026-10-29: 系统 python3 没有 yaml 模块 → 解析整段崩掉（后面所有检查都跟着瞎报）。
# 优先用仓库 .venv，退路 uv 临时环境。
if [ -x ".venv/bin/python" ] && .venv/bin/python -c "import yaml" 2>/dev/null; then
  PY=".venv/bin/python"
elif command -v uv >/dev/null 2>&1; then
  PY="uv run --quiet --with pyyaml python"
else
  PY="python3"
fi
$PY <<'PY'
import yaml, json, pathlib, sys
ok = True
state = pathlib.Path("state")
private = pathlib.Path("private")

def fail(msg):
    global ok
    ok = False
    print(f"  ✗ {msg}")

def good(msg):
    print(f"  ✓ {msg}")

# watchlist
w = yaml.safe_load((state / "watchlist.yaml").read_text())
n = sum(1 for a in w["accounts"] if a["status"] == "active")
if n == 46: good(f"watchlist active = {n}")
else: fail(f"watchlist active 应该是 46，实际 {n}")

# filter
f = yaml.safe_load((state / "filter-rules.yaml").read_text())
good(f"filter min_view_count = {f['min_view_count']}")

# schedule
s = yaml.safe_load((state / "schedule.yaml").read_text())
# 2026-10-29: cron_slots 已于 2026-10-25 移除，实际是 crons 三条线 → 读不到就报 crons
if "cron_slots" in s:
    good(f"schedule slots = {[c['id'] for c in s['cron_slots']]}")
else:
    good(f"schedule crons = {[c for c in s.get('crons', {})]}")

# account-safety
a = yaml.safe_load((private / "account-safety.yaml").read_text())
good(f"x login_state = {a['x'].get('login_state', '?')}  publish_mode = {a['x']['publish_mode']}")
# 2026-10-29: last_published 在 2026-10-20 修复后是**字符串** post_id（旧格式才是 dict）
lp = a['x'].get('last_published')
if isinstance(lp, dict):
    good(f"x last_published: {lp.get('post_id', '?')} @ {lp.get('at', '?')}")
elif lp:
    good(f"x last_published: {lp}")
if a['x'].get('last_published_post_id'):
    good(f"x last_published_post_id: {a['x']['last_published_post_id']} @ {a['x'].get('last_published_at', '?')}")
# 2026-10-29: xhs 段是**扁平**结构（is_banned 直接挂在段下），没有嵌套 ban_status
xhs = a['xhs']
xhs_banned = xhs.get('is_banned')
if xhs_banned is None:
    xhs_banned = (xhs.get('ban_status') or {}).get('is_banned')
if xhs_banned:
    good("xhs 仍处封禁（草稿模式）")
else:
    good("xhs 已解封（按 Fang 授权可走 publisher-xhs）")

# forbidden
fr = yaml.safe_load((state / "forbidden.yaml").read_text())
n_red = sum(1 for r in fr['forbidden_content'] if r['severity'] == 'hard')
good(f"forbidden.yaml 硬红线 {n_red} 条")

# seen / recent / published
sp = json.loads((state / "seen-posts.json").read_text())
rp = json.loads((state / "recent-picks.json").read_text())
good(f"seen-posts = {len(sp['entries'])} 条")
good(f"recent-picks = {len(rp['entries'])} 条")

# published-posts（optional，可能不存在）
pp_path = state / "published-posts.json"
if pp_path.exists():
    pp = json.loads(pp_path.read_text())
    good(f"published-posts = {len(pp['entries'])} 条（已发布历史）")
else:
    good("published-posts.json 未创建（还没真发过）")

# style-x 自动行为记录
sx = yaml.safe_load((state / "style-x.yaml").read_text())
if "x_auto_behavior" in sx:
    good(f"style-x 记录了 X 自动行为：{list(sx['x_auto_behavior'].keys())}")

sys.exit(0 if ok else 1)
PY

echo
echo "━━━ 2. outputs/ 最新产物 ━━━"
# 2026-10-29: 实际布局是 outputs/<MMDD-slot-topic>/（单层），旧写法 outputs/<slot>/*/ 多了一层
# → 上一轮 1028 也被误报「material.yaml 缺失」。两种布局都兼容。
ls -t outputs 2>/dev/null | head -3 | while read slot; do
  for d in "outputs/$slot" "outputs/$slot"/*/; do
    [ -d "$d" ] || continue
    # 只有含素材文件的目录才算一个选题产物目录（避免把 screenshots/ 这种子目录也当产物）
    if [ ! -f "$d/material.yaml" ] && [ ! -f "$d/x.txt" ] && [ ! -f "$d/xhs.txt" ]; then
      continue
    fi
    echo "  $d"
    # 2026-10-29: 老写法靠 "$d"/*/ 自带尾斜杠让 "$d$f" 拼对；单层目录没有尾斜杠 → "$d$f" 少一杠
    for f in material.yaml x.txt xhs.txt; do
      if [ -f "${d%/}/$f" ]; then
        sz=$(wc -c < "${d%/}/$f")
        # x.txt 检查 posted_url
        if [ "$f" = "x.txt" ] && grep -q "posted_url" "${d%/}/$f"; then
          url=$(grep "posted_url" "${d%/}/$f" | head -1 | awk '{print $NF}')
          echo "    ✓ $f ($sz B)  posted: $url"
        else
          echo "    ✓ $f ($sz B)"
        fi
      else
        echo "    ✗ $f 缺失"
      fi
    done
    n_shots=$(ls "${d%/}/screenshots" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$n_shots" -ge 2 ]; then
      echo "    ✓ screenshots/ $n_shots 张（≥2 OK）"
    else
      echo "    ✗ screenshots/ 仅 $n_shots 张（需 ≥2）"
    fi
  done
done

echo
echo "━━━ 3. Codex skill 入口 ━━━"
SK="/Users/fangchen/.codex/skills/short-posts/SKILL.md"
if [ -f "$SK" ]; then
  echo "  ✓ $SK 已注册"
else
  echo "  ✗ $SK 缺失"
fi

echo
echo "━━━ 4. 浏览器可达性（mmx 搜索代理） ━━━"
if command -v mmx >/dev/null 2>&1; then
  echo "  ✓ mmx CLI 可用"
else
  echo "  ✗ mmx CLI 不可用"
fi

echo
echo "━━━ 体检结束 ━━━"
echo
echo "━━━ 5. publisher-xhs dry-run ━━━"
bash scripts/publisher-xhs-dryrun.sh > /dev/null 2>&1
RC=$?
if [ "${RC}" = "0" ]; then
  echo "  ✓ publisher-xhs 当前可走（已解封 + agent 代点发布已授权）"
elif [ "${RC}" = "1" ]; then
  echo "  ✓ publisher-xhs 当前按预期停手（封禁中 / 未授权 / 未登录）"
else
  echo "  ✗ publisher-xhs-dryrun.sh 退出码异常: ${RC}"
fi

