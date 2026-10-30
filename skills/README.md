# 短文助手 · Skills 索引（入口协议）

整个流程拆成 **6 个创作 pipeline skill + 1 个 engagement skill + 1 个 super-bot = 8 个**。每个 skill 一份 `SKILL.md`，描述职责、输入、输出、禁动作。
所有 skill **共享** `../state/` 下的事实源（账号名单 / 规则 / 账号安全状态 / 禁忌）。

```
┌────────────────────┐
│  hot-topic-tracker │  扫 X → 出素材包
└──────────┬─────────┘
           │ material.yaml
           ▼
┌────────────────────┐
│   post-writer-x    │  写 X 文案（口语爆款风）
└──────────┬─────────┘
           │ x.txt + screenshots
           ▼
┌────────────────────┐
│   publisher-x      │  xb.py 真发 X
└──────────┬─────────┘
           │ posted_url
           ▼
┌────────────────────┐
│  post-writer-xhs → │  ★ 小红书独立发布线（2026-10-30 拆出，chuangzuo 不碰）
│  publisher-xhs     │  ✅ 代点发布：内置浏览器填稿 → 点发布（17:11 起授权）
└────────────────────┘

# ─── 小红书发布 pipeline（独立线，2026-10-30 从创作线拆出；不碰 X）───

┌─────────────────────────┐
│  post-writer-xhs →        │  独立选题/写稿（X 线不代笔）
│  publisher-xhs          │  内置浏览器真窗口代点发布
│  ★ automation 分散档口    │  每天 ≤1 条 / 间隔 ≥12h / ~50% 跳档
│    （9:37/12:37/16:37/   │  automation_enabled=false 期间只跑登录态探测
│     20:37 候选）          │
└─────────────────────────┘

# ─── Engagement pipeline（并列，不创作，只互动）───

┌─────────────────────────┐
│  x-engagement-pulse     │  inbound(回别人的 reply)+ outbound(主动 like+reply)
│  ★ 每轮 ≤3 动作          │  不发新帖。cron 每 6 小时（4 轮/天）
└─────────────────────────┘

# ─── Manager layer（Fang 只跟这个对话）───

┌─────────────────────────┐
│  super-bot              │  首席汇报官 — 只读 + 报告 + 决策建议，不动 X
│  ★ 每日 09:00            │  必查「轮次真空期」
└─────────────────────────┘
```

## Skill 职责速览

| Skill | 职责 | 触发 |
|-------|------|------|
| hot-topic-tracker | 扫 X 高优 handle，出素材包 | chuangzuo pipeline |
| post-writer-x | 按素材包写 X 文案 | chuangzuo pipeline |
| publisher-x | `xb.py` 真发 X | chuangzuo pipeline |
| post-writer-xhs | 按素材包写小红书文案 | chuangzuo pipeline（已复通） |
| publisher-xhs | 内置浏览器填稿 + 点发布（**已授权**） | Frank 说要小红书时 |
| browser-use-utils | 浏览器执行层 CLI（`scripts/browser/xb.py`）用法手册 | 全链路共享 |
| **post-writer-xhs → publisher-xhs** | **小红书独立发布线：写稿 + 代点发布（不碰 X）** | **cron 分散档口 4 候选/天 + 手动喊** |
| **x-engagement-pulse** | **inbound reply + outbound like+reply（不发新帖）** | **cron 每 6 小时（4 轮/天）** |
| **super-bot** | **只读 + 报告 + 决策建议，不动 X** | **cron 每日 09:00 + 手动查询** |

## 运行模式

三条线全部跑在 **Codex Automations**（独立 cron session = 每轮全新上下文）里。浏览器动作**唯一通道 = Codex 内置浏览器**（`mcp__cua_repl__js`，Fang 2026-10-30 拍板）；没有 cua_repl 或浏览器控制被禁 → 本轮如实报零动作，不走 xb.py。前置：Work settings 启用 Local browser use + Fang 在内置浏览器一次性登录。

**没有模式分支了** —— 以前有「Codex session 模式 / Cron lite 模式」的二选一，
现在 lite 那条路（`scripts/run-all-slots.sh` / `scan-slot.sh`）已删除：
`state/schedule.yaml` 自己写明 mmx 是通用 web 搜索、不支持 `from:` / `site:x.com`，
**多数 slot 必然 0 候选**，留着只会误导。

开工第一步仍然要检测：**`python3 scripts/browser/xb.py --action '{"action":"login_state"}'` 能跑（exit 0）→ 走完整链路；exit 2（浏览器不可用）→ 老实写「浏览器不可用，本轮零动作」，不装忙。**

## chuangzuo 完整链路

0. **🔴 开工自检 · 排定档口台账（必做，不是可选项）** —— 本轮第一件事不是找选题，是查上一档口有没有丢。
   本地 cron 依赖 runtime 进程存活 + 机器醒着；**合盖/休眠期间触发器不触发，唤醒后也不补跑**。
   - 读末轮时间戳（`python3 scripts/tail-rounds.py state/memory/chuangzuo.md --rounds 1`）+ 本线排定时刻（`30 3,15` = 每 12 小时）。
   - **上一档口距今 > 2 × 12h = 24h → 判定「上一档口丢失」。**
     ⚠️ **末轮新 ≠ 中间没丢** —— 只看末轮时间戳会漏掉窗口中间丢掉的档口。
     ⚠️ 阈值按 **cron 表达式**算，不要按 `state/schedule.yaml` 或任何文档标签算。
   - 两种根因**别混写**：`cron_read view=runs` 里**没有这一格** → 触发器压根没触发（机器睡着）；有投递记录但**没轮次段** → 跑了但崩了/中断了。
   - 确认丢失后：① 轮次段开头写明「上一档口 <时刻> 丢失，根因：…」；② 说明**本窗口少了几次选题机会**（选题是攒出来的，丢一档口 = 少一个备选池）；③ 若因此本轮零发送，必须写明是「闸门否决」还是「备选不足」——两者不是一回事。
   - **每轮开工做平台侧对账**：`search?q=from:FrankFika` 取首条 post_id → snowflake 反解发帖时刻 → 与 `private/account-safety.yaml#x.last_published_at` 比对。
     **不一致 = Frank 自己手动发了帖**（agent 轮次日志覆盖不到）→ 按 4 处补账（`published-posts.json` / `index.json#published` / `account-safety.yaml#x.last_published_*` / 本轮轮次段写明原因）。
     Quote 帖 = 根帖，**计入 12h 窗口**（只有 reply 不计入）。
1. 读 `state/*.yaml` + `state/index.json`（**不要全量读 seen-posts.json**）
2. 读 `state/memory/chuangzuo.md` 末 2 段（`python3 scripts/tail-rounds.py state/memory/chuangzuo.md --rounds 2`）
3. **发不发的前置判据**（必做，不是可选项）：
   - **上一条原创距今 ≥ 12h** → 否则本轮零发送（硬否决）。
     ⚠️ **只数原创帖（根帖），reply 不计入**（2026-10-27 修正）。
     旧口径把 reply 也算成「发过帖」，而 pulse 一天跑 4 轮、chuangzuo 一天 2 轮 ——
     只要 pulse 回一条 reply，12h 窗口就被占掉，chuangzuo 两个档口**双双 100% 被自己的回复饿死**。
     reply 的节奏归 pulse 自己管（配额表 ≤3 动作/轮、reply 间隔 ≥8min），原创的 12h 间隔只管原创。
   - **距上一次任何公开文字动作（reply / 原创）≥ 30 min** → 不够就顺延到下一个窗口（不是零发送）
   - 上一条原创 12h 后 likes 仍 ≤ 2 → **换选题方向再发**（**不再否决发送**；Frank 2026-10-27「多干发原创」：
     这条原本是硬否决，连否 3 轮 → 40 小时零原创。互动差是**选题**问题，不是**发不发**问题）
   - 数据不支持就诚实记「本轮零动作 + 原因」，**不要为了「每轮要有产出」而发**
4. **扫两条选题通道**（≥ 2 个 handle + ≥ 2 个源就够）：
   - **X 通道**：`xb.py` / 内置浏览器 真扫 watchlist 高优 handle
   - **非 X 通道**（Frank 2026-10-27 新增，**不依赖浏览器，最稳**）：
     `python3 scripts/sources.py --source all --limit 8 --text`
     源清单见 `skills/hot-topic-tracker/SKILL.md#内容源清单`
     （aihot / tophub / decohack / gh-trending / producthunt / ph-buzzing / xbangdan / discoverhub）
5. 筛候选：AI 关键词命中 + 未在 `state/index.json` + 优先 practitioner 源而不是官方账号
   - web 源去重键用 `url:<sha1 前 12 位>`（见 `schemas/material-pack.schema.md`）
6. 写 `material.yaml`（`source_kind: x | web`）+ `x.txt`（按 `state/style-x.yaml`）
   - web 源：数字/原话**必须回原文核对**（aihot 摘要只是线索）
7. 真发 —— **先选对浏览器通道**（见 `skills/publisher-x/SKILL.md#浏览器通道`）：
   - Codex 内置浏览器（有 `mcp__cua_repl__js`）：`fill` → `press_key {"key":"Enter","modifiers":["Meta"]}`
   - xb.py：`fill` → `press {"key":"Meta+Enter"}`
   ⚠️ 两条通道的组合键写法**相反**，抄错就是「看起来成功但没发出去」
8. **验证**：Cmd+Enter 后**不要**查 profile / with_replies / home feed，用 search 拿 own_post URL
9. 更新 `published-posts.json` / `seen-posts.json` / **`state/index.json`** / `account-safety.yaml`
10. 轮次记录追加到 `state/memory/chuangzuo.md`（**新段前加一行 `<!-- round -->`**）

## 每轮产出约定

- **每轮最多 1 条原创**（Frank 2026-10-21 降频；README 早期写的「3 条完成版」已作废）
- 候选不足就少做，**不要凑数**
- **选题不只来自 X**：非 X 源（`scripts/sources.py`）同样是合法素材来源，
  写的是同一个 Frank 人设，不是「搬运别人的 X 帖」
- **web 源的数字必须回原文核对** —— 摘要/热榜标题里的数字经常是二手的
- **screenshots/ 必抓真图**，绝不用 AI 生成图占位
- **XHS 可代点发布**（`private/account-safety.yaml#xhs.agent_publish_allowed = true`），但操作层面 4 条硬约束必守：不碰平台 AI 功能 / 不改任何设置 / 走真窗口 / 节奏分散不连发
- **诚实原则**：任何环节拿不到真实结果就写「未发」+ 原因，不许装忙
- 原创间隔 ≥ 12 小时（`schedule.yaml#cooldown_between_posts_min` 是下限，不是目标）
- **目标 2 条/天**（3:30 + 15:30 各一条）。互动差（likes ≤ 2）只调**选题方向**，不调**发不发**
- **pulse 的 outbound reply 已归零**（少评论）→ 注意力优先给原创

## 共同约束

- 读 `state/forbidden.yaml` 当红线
- 读 `private/account-safety.yaml` 决定 publish_mode
- 读 `state/index.json` 去重（**不是**全量 seen-posts.json）
- 读轮次日志只读末 N 段，用 `scripts/tail-rounds.py`
- XHS 节奏分散发布（不固定单一时段），发布前出确认卡

## 配套脚本

- `scripts/tail-rounds.py` — **只读 memory 最后 N 段**（每轮必用，别全量 cat）
- `scripts/sources.py` — **非 X 内容源统一抓取器**（8 个源，解析在脚本里做，HTML 不进上下文）
- `scripts/qa-draft.py` — 草稿自检（字数 / has 数字 / has 链接）
- `scripts/health-check.sh` — 跑前环境体检
- `scripts/publisher-xhs-dryrun.sh` — XHS 草稿 dryrun
- `scripts/humanize.py scan <xhs.txt> --json` — 小红书稿 AI 味闸门（软分必须 0）
