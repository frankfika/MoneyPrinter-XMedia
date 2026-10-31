# 短文助手 · X + 小红书内容流水线

> 📦 **换机器 / 换 AI 接手 → 读 [`HANDOVER.md`](HANDOVER.md)**（历史决策、闸门原理、移交清单）
> 项目真实路径 `/Users/fangchen/shortbot`；老路径 `/Users/fangchen/Documents/短文助手` 是 symlink。

**这是什么**：Fang 的 X（Twitter）+ 小红书短文流水线 —— 自动选题 → 写稿 → AI 味闸门 → 真发 → 互动 → 日报。
调度在本机 **launchd**（`com.fangchen.shortbot.*` + `scripts/run-round.sh`），浏览器动作走 **xb.py**（专用 Chrome，CDP 9222，纯 DOM 无视觉）。Codex app Automations 已停用（2026-10-31）。

---

## TL;DR — launchd 四条线

| launchd 线 | 调度（Asia/Shanghai） | 干什么 | 权限 |
|---|---|---|---|
| `com.fangchen.shortbot.chuangzuo` X 创作 | `30 3,9,15,21 * * *`（6h×4） | 扫 X + 非 X 源 → 选热帖 → 写文案 → 过闸门 → 真发 X。**不碰小红书** | 每轮最多 1 条，原创间隔 ≥6h |
| `com.fangchen.shortbot.xhs` 小红书发布 | `37 9,12,16,20`（4 候选档口，轮内随机跳档 ~50%） | 独立线：选素材/写稿 → humanize 闸门 → 代点发布。**不碰 X** | 每天 ≤2 条、间隔 ≥10h |
| `com.fangchen.shortbot.pulse` X 互动 | `0 4,10,16,22 * * *`（6h×4） | **只 like + reply，不发新帖**（inbound 回别人的 reply + outbound like 高优帖） | 单轮 ≤3 动作 |
| `com.fangchen.shortbot.super-bot` 日报 | `0 9 * * *`（每日） | **只读 + 结构化日报**（三线全覆盖），轮次真空期必查 | 只读，绝不碰账号 |

四个职责一条线一个，互不越界（Fang 2026-10-30 拍板拆分）。
**Fang 的日常只有一个动作：看 super-bot 日报。** 想手动操作时直接说人话（见下）。
prompt 唯一事实源在 `docs/cron-prompts/<线>.md`；每轮开轮先读它，改规则改文件即生效。

## Fang 怎么说，它就怎么做

| 你说 | 它做 |
|---|---|
| 「写条 X，就说 xxx」「按这条新闻写」 | 走创作链路出稿，发前给你确认卡 |
| 「跑一轮 pulse」 | 按 `skills/x-engagement-pulse/SKILL.md` 手动跑一轮互动 |
| 「发小红书」「这个也发小红书」 | `publisher-xhs` 代点发布（已授权，节奏分散） |
| 「今天 X 怎么样」「本周 summary」 | super-bot 即时只读摘要 |
| 「以后 inbound 优先回中文 KOL」 | 先回话确认，你点头才改 state |

---

## 架构

```
        state/*.yaml + state/*.json（★ 唯一事实源）
                    │
   ┌──────────┬─────┴─────┬─────────────┬──────────────┐
   ▼          ▼           ▼             ▼              ▼
 X 创作线   小红书发布线  X 互动线    日报线
 chuangzuo  xhs         pulse       super-bot
            （独立线）
 skills/    skills/     skills/     skills/
 hot- →    post-writer- x-engagement- super-bot
 topic →   xhs →       pulse
 writer-x  publisher-  （只 like+reply）
   │       xhs
 publisher-x │
   ▼          ▼           ▼              ▼
outputs/<档期>/    state/index.json    state/memory/*.md
（落盘 + 真截图）  （去重索引）        （轮次日志）
                    │
                    ▼
        xb.py（专用 Chrome，CDP 9222，DOM 无视觉）
```

四条线共享 `state/` 事实源，各自独立 session（每轮全新上下文，不膨胀）。

## 浏览器通道（唯一：xb.py）

2026-10-31 起唯一浏览器通道 = **xb.py**（`python3 scripts/browser/xb.py --action '<json>'`）：
Playwright 驱动专用 Chrome（profile `~/.shortbot-browser-profile`，CDP 9222，
launchd `com.fangchen.shortbot.browser` 保活），**纯 DOM 操作、无视觉模型**。
历史决策：曾切「Codex 内置浏览器（cua_repl）/ Computer Use AX」，因内置浏览器被组织策略禁用、
AX 是视觉通道，2026-10-31 起迁回 xb.py（本地化 + 无视觉）。

前置（缺一不可，agent 每轮自检）：
1. launchd `com.fangchen.shortbot.browser` 保活的专用 Chrome 在跑（CDP 9222）
2. Fang 在该浏览器（9222 窗口）**一次性登录 X 和小红书**（含 2FA，只有人能做）
3. agent 复核登录态后更新 `private/account-safety.yaml`

每轮开工自检：`python3 scripts/browser/xb.py --action '{"action":"login_state"}'`。
未登录 → 本轮零动作，如实记录「专用 Chrome 未登录，需 Fang 在 9222 窗口登录」，不撞登录墙。

动作契约见 `scripts/browser/README.md`；原语：navigate / open_tab / wait / query / inspect /
click / fill / press / screenshot / upload / login_state
（`upload` 为 2026-10-31 新增，小红书传图用：
`{"action":"upload","input":{"selector":"input[type=file]","files":["/abs/a.png"]}}`）。

---

## 目录结构（2026-10-30 整理后）

```
shortbot/
├── README.md / HANDOVER.md    # 本文 / 历史与深度原理
├── docs/cron-prompts/         # ★ 四条 launchd 线的 prompt 唯一事实源
├── skills/                    # 8 个 skill（README.md 是入口协议）
├── state/                     # ★ 事实源：规则 / 名单 / 去重索引 / 轮次日志 memory/
├── scripts/                   # 闸门 / 体检 / 源抓取 / 浏览器 xb.py / QA
├── outputs/                   # 完成版落盘（>7 天的在 outputs/archive/）
├── private/                   # 账号安全（不进 git）
├── logs/                      # 运行日志（不进 git）
└── archive/                   # dsh-era 脚本、launchd plist、旧产物
```

## 🛡️ 不被当成 AI（三道闸，代码级强制）

背景：Frank 的老号被 @op7418 / @oran_ge 拉黑，原因是「被看出来是 AI 评价了」。所以：

1. **第 0 道 · 机器闸门** `scripts/prepublish.py`（34 条结构+词+红线规则，改前必读 `state/ai-taste-rules.json`）
   - 真发前必须 `python3 scripts/prepublish.py --text "<正文>" --no-rewrite` → **exit 1 不许发、不许绕过**
   - 默认模式会自动改写后放行 = 绕过闸门，所以真发一律 `--no-rewrite`
2. **第 1 道 · 身份质疑**（「你是 AI/bot 吗」）→ 默认不回，记一笔
3. **第 2 道 · 内核撞车**（近 24h 讲过两遍的反驳）→ 不发

小红书稿走 `python3 scripts/humanize.py scan <xhs.txt> --json`，软分必须 0。

回归验证：`uv run --with pyyaml python3 scripts/gate-regression.py` → 12 PASS / 1 FAIL 为正常。

## 红线快速版（完整版 `state/forbidden.yaml`，每轮开工必读）

- ❌ pulse 模式不发新原创长帖 / Quote RT / 新 Post
- ❌ 不出现 OpenCSG / 公司业务；❌ Chinese AI 公司名（DeepSeek / Moonshot / MiniMax…）
- ❌ 不写 AI 托管 / 自动互动措辞；❌ AI 生成图占位；❌ 堆 hashtag（≤1）
- ❌ XHS 固定时段连发；代点发布前必出确认卡（站点/账号/标题/正文/图/可见性）
- ❌ 拿不到真实 URL = 没发；禁止装忙

## 当前账号状态（2026-10-30）

| 账号 | 状态 | 说明 |
|---|---|---|
| X `@FrankFika` | ⚠️ 专用 Chrome 待一次性登录 | 登录前轮次会诚实报「专用 Chrome 未登录，本轮零发送」 |
| 小红书「弗兰克的思维导图」 | ✅ 已授权 agent 代点发布 | 登录态在专用 Chrome（9222 窗口），需在该浏览器里确认一次 |

## ⚠️ 轮次真空期（本机调度的固有性质）

launchd 只在**机器醒着**时触发；睡眠/关机期间不触发、不补跑。
super-bot 日报必查：memory 末轮时间戳 vs 真实时间，距末轮 > 2 × 调度间隔 = 真空期，写进日报。

## 日常运维

```bash
bash scripts/health-check.sh                  # 体检：state 解析 + outputs 完整性
python3 scripts/qa-draft.py outputs/<档期>/<topic>/   # 单条草稿质检
python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 3   # 轮次日志末 N 段
bash scripts/publisher-xhs-dryrun.sh          # XHS 干跑判断
```

## 迁移说明

1. 整个文件夹搬（`private/`、`logs/`、`state/memory/archive/` 不进 git，单独拷）
2. 装好 launchd 四条线（`com.fangchen.shortbot.{chuangzuo,pulse,xhs,super-bot}`，入口 `scripts/run-round.sh`；prompt 从 `docs/cron-prompts/*.md` 第一个围栏块复制）
3. 专用 Chrome 重新登录（X + 小红书）；`launchd` 保留 `com.fangchen.shortbot.browser` 保活
