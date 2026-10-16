# 短文助手 · Codex 工作流目录

> Fang 的 X（Twitter）+ 小红书短文内容流水线 + **双向 engagement pulse bot**。
> 沉淀在这里是为了**整体迁移**和**同步给其他人**(Codex / 团队成员 / 自己的另一台机器)。

---

## TL;DR — 一分钟了解这个项目

这是一个 Codex 驱动的个人内容流水线，分两件事:

1. **创作 pipeline**(每小时 cron 触发):从 watchlist 高优 handle 扫 X → 选热帖 → 抓真图 → 写 X 文案 + 小红书文案 → browser use 真发 X(XHS 只出草稿)
2. **Engagement pulse**(每 30 分钟 cron 触发):**只 like+reply,不发新帖**。包括 **inbound**(回别人给我的 reply)+ **outbound**(主动 like+reply 高优热帖)
3. **Super-bot**(每日 09:00 +08:00 cron 触发):**只读 + 报告**,不动 X。读前两者的工作日志 → 出结构化日报 → 报告给 Fang。**Fang 只跟 super-bot 对话**,不直接看 worker bots

跑起来最低依赖:**Codex session + `mcp__cua_repl__js` 浏览器工具**。
X 账号 `@FrankFika` 已登录在 Codex in-app browser 里。

---

## 架构总览

```
                      state/*.yaml + state/*.json(事实源)
                                 │
                ┌────────────────┼────────────────┐
                ▼                                 ▼
       创作 pipeline skill                  Engagement skill
       (6 个)                                (1 个)
                │                                 │
   hot-topic-tracker ─→ post-writer-x ─→        x-engagement-pulse
   hot-topic-tracker ─→ post-writer-xhs         (inbound + outbound)
                                 │                │
                          publisher-x             │
                          publisher-xhs           │
                                 │                │
                          outputs/<slot>/          │
                          (完成版落盘)             │
                                                  ▼
                                    state/inbound-replies.json
                                    state/seen-posts.json
                                    $CODEX_HOME/automations/.../memory.md
```

**两条线共享 `state/` 下的事实源**(账号名单 / 规则 / 账号安全 / 禁忌)。

---

## 目录结构(迁移时整个文件夹直接搬)

```
短文助手/
├── README.md                          # 你现在看的(项目入口,给其他人看的)
│
├── state/                             # 持久事实源 — 改这里之前先想清楚
│   ├── watchlist.yaml                 # 46 个 X 账号名单 + 跟单理由
│   ├── filter-rules.yaml              # 筛选规则(AI 关键词 + 浏览量下限)
│   ├── schedule.yaml                  # cron 节奏配置
│   ├── style-x.yaml                   # X 写作规范(口语爆款风 + quote embed)
│   ├── style-xhs.yaml                 # 小红书写作规范(普通版)
│   ├── forbidden.yaml                 # 红线清单(发前必读)
│   ├── account-safety.yaml.sample     # account-safety.yaml 的模板(可分享)
│   ├── seen-posts.json                # 去重:已发的 post_id
│   ├── recent-picks.json              # 去重:近期选题记忆(7 天 expire)
│   ├── published-posts.json           # 所有成功发出的帖(发布历史唯一事实源)
│   └── inbound-replies.json           # 🆕 inbound 已回 reply 记录(2026-10-16 起)
│
├── private/                           # 本机私有(.gitignore)— 真人账号凭据,真人写真数据
│   └── account-safety.yaml            # X / 小红书账号安全状态 + login_state(从 state/ 移过来,模板见 state/account-safety.yaml.sample)
│
├── skills/                            # 7 个 skill(每个一份 SKILL.md)
│   ├── README.md                      # skill 索引 + 流程图 + 共同约束
│   ├── hot-topic-tracker/SKILL.md     # 扫 X → 素材包
│   ├── post-writer-x/SKILL.md         # 写 X 文案
│   ├── post-writer-xhs/SKILL.md       # 写小红书文案
│   ├── publisher-x/SKILL.md           # browser use 真实发 X
│   ├── publisher-xhs/SKILL.md         # 草稿模式发小红书
│   ├── browser-use-utils/SKILL.md     # 浏览器操作通用动作
│   └── x-engagement-pulse/SKILL.md    # 🆕 inbound + outbound engagement(2026-10-16 加)
│
├── schemas/                           # 字段规范(人读)
│   ├── material-pack.schema.md
│   ├── x-post.schema.md
│   └── xhs-post.schema.md
│
├── templates/                         # 空白模板(可复制填)
│   ├── material-pack.yaml
│   ├── x-post.txt
│   └── xhs-post.txt
│
├── scripts/                           # 工具脚本(可手动跑)
│   ├── health-check.sh                # 一键体检(state 解析 + outputs + Codex 注册)
│   ├── qa-draft.py                    # 单条草稿质检(套全部 style / forbidden)
│   ├── run-all-slots.sh               # Cron 模式:串跑 5 slot
│   ├── scan-slot.sh                   # Lite 版 X 扫描(mmx web search)
│   ├── publisher-xhs-dryrun.sh        # XHS 解封前干跑判断(退出码 0/1)
│   ├── cua-full-flow.md               # Codex session 模式复盘菜谱(必读)
│   ├── codex-automation-prompt.md     # Codex UI automation 配置模板
│   └── launchd/com.codex.short-posts.scheduler.plist
│
├── outputs/                           # 完成版落盘(按 日期 / slot / 选题)
│   └── <MMDD>-<slot>/<topic>/
│       ├── material.yaml
│       ├── x.txt
│       ├── xhs.txt
│       └── screenshots/*.png(真图)
│
├── screenshots/                       # 公共截图缓存
└── logs/                              # cron / 浏览器错日志
```

---

## Skill 拆分(8 个,详见各 SKILL.md)

| # | Skill | 职责 | 触发 |
|---|-------|------|------|
| 1 | **hot-topic-tracker** | 扫 X 高优 handle,出素材包 | cron 触发的完整链路 |
| 2 | **post-writer-x** | 按素材包写 X 文案(口语爆款风) | pipeline |
| 3 | **publisher-x** | 用 cua_repl 真发 X | pipeline |
| 4 | **post-writer-xhs** | 按素材包写小红书文案 | pipeline |
| 5 | **publisher-xhs** | 解封后:浏览器只存草稿;否则:Fang 手贴 | pipeline |
| 6 | **browser-use-utils** | cua_repl 浏览器工具封装 | pipeline 共享 |
| 7 | **x-engagement-pulse** 🆕 | **inbound reply + outbound like+reply(不发新帖)** | **每 30 min cron** |
| 8 | **super-bot** 🆕 | **只读 + 报告 + 决策建议,不动 X;Fang 的唯一对接入口** | **每日 09:00 +08:00 cron + 手动** |

`skills/README.md` 是 skill 索引 + 共同约束 + Codex session 模式复盘入口。

---

## Automation / Cron 配置(3 个)— 必读

> **重要**:这 2 个 automation 都在 Codex app 里注册,**不是** system crontab / launchd。
> 它们由 Codex app 自己定时触发(根据 `automation.toml#rrule`),每次触发会启动一个 Codex session thread,把 prompt 喂进去,然后 agent 跑。

### Automation 在文件系统里的位置

```
$CODEX_HOME/automations/                          # = ~/.codex/automations/
├── users-fangchen-documents-skills-readme-md-1-state-watc/   # 1. 创作 pipeline(每小时)
│   ├── automation.toml                            # prompt + rrule + target thread
│   └── memory.md                                  # 轮次进度 + 历史经验 + 决策记录
│
├── x-engagement-pulse-30min/                      # 2. Engagement pulse(每 30 min)
│   ├── automation.toml                            # prompt 精简,引用 SKILL.md
│   └── memory.md                                  # pulse 轮次进度
│
└── .run-jitter-salt                               # Codex app 内部文件,不要碰
```

### Automation 是什么 — 写给其他 Codex 的简介

一个 automation = 一段**反复跑的 Codex session 任务**:
- **`automation.toml`** = 这任务叫什么 / 多久跑一次 / 用什么模型 / 跑哪个 thread / 跑的时候喂什么 prompt
- **`memory.md`** = 这个任务自己的"笔记本",每次跑完追加轮次记录,agent 启动时先读这里避免重复

收到触发时,Codex app 会:
1. 按 rrule 算出下次触发时间
2. 在 `target.project_id` 指定的 project 下起一个新 thread(或者 attach 到已有 thread)
3. 把 `prompt` 当 user message 发进去
4. agent 收到 prompt → 读 SKILL.md → 跑活 → 写 memory → 完成

---

### Automation #1:创作 pipeline(每小时)

| 字段 | 值 |
|------|---|
| 目录 | `~/.codex/automations/users-fangchen-documents-skills-readme-md-1-state-watc/` |
| id | `users-fangchen-documents-skills-readme-md-1-state-watc` |
| name | 跑一轮短文助手完整链路 |
| kind | `cron` |
| rrule | `FREQ=HOURLY;INTERVAL=1;BYMINUTE=0` — 每个整点触发 |
| model | `MiniMax-M3` |
| reasoning_effort | `high` |
| target | project `71faead3-cd8e-49ec-be13-c9747d4927ac` |
| cwd | `/Users/fangchen/Documents/短文助手` |
| prompt 引用 | `skills/README.md`(协议入口)+ 6 个 skill |

**这一轮做什么**:扫 X 高优 handle → 筛 ≥ 15K views 热帖 → 抓真图 → 写 X/XHS 文案 → browser use 真发 X → 落盘 outputs/ → memory.md 追加记录。

**目标**:每轮 3 条完成版;候选 < 3 全跑(不凑数);候选 = 0 老实写"未发"。

**memory.md 内容格式**:每轮一段,记录 candidate_count / 落盘路径 / 已发 X URL / 跳过原因 / Draft.js 新经验 / cron vs Codex session 链路差异。

---

### Automation #2:Engagement pulse(每 30 分钟)

| 字段 | 值 |
|------|---|
| 目录 | `~/.codex/automations/x-engagement-pulse-30min/` |
| id | `x-engagement-pulse-30min` |
| name | X 转评赞 pulse · 每 30 分钟 |
| kind | `cron` |
| rrule | `FREQ=WEEKLY;BYHOUR=10;BYMINUTE=45;BYDAY=SU,MO,TU,WE,TH,FR,SA` — Codex app 用 rrule 在 10:45 / 11:15 / 11:45 ... 等整 30 分钟点触发(由 Codex app 解释) |
| model | `MiniMax-M3` |
| reasoning_effort | `high` |
| target | project `71faead3-cd8e-49ec-be13-c9747d4927ac`(同 #1) |
| cwd | `/Users/fangchen/Documents/短文助手` |
| prompt 引用 | `skills/x-engagement-pulse/SKILL.md`(详细 workflow 都在这里) |

**这一轮做什么**:
- **Phase A inbound**(优先):扫 `x.com/notifications/mentions`,回别人给我的 reply(社区建设核心)
- **Phase B outbound**(其次):扫 watchlist 高优 handle,主动 like+reply 热帖

**硬约束**:**不发新原创 / Quote RT / 新 Post**,只 like+reply。

**目标配额**:2 inbound reply + 2 outbound like+reply + 2 outbound like-only / 轮;reply 间隔 ≥ 8 min;like 间隔 ≥ 2 min。

**memory.md 内容格式**:每轮一段,记录 inbound_replied_count / outbound candidate_count / like_count / reply_count / 已发 URL 列表 / 跳过原因 / 异常 / Draft.js 新经验。

---

### automation.toml 字段详解(给其他 Codex 看的 schema)

```toml
version = 1                            # schema 版本,目前都 1
id = "<unique-id>"                     # 唯一标识,跟目录名同名
kind = "cron"                          # 现在只支持 cron / heartbeat
name = "<人类可读名>"                   # Codex UI 显示的名字
prompt = "<触发时喂给 agent 的 prompt>" # 精简版,详细 workflow 引用 SKILL.md
status = "ACTIVE"                      # ACTIVE / PAUSED
rrule = "<iCal RRULE>"                 # cron 节奏,见 https://datatracker.ietf.org/doc/html/rfc5545
model = "MiniMax-M3"                    # 用哪个模型
reasoning_effort = "high"              # none / minimal / medium / high / xhigh / max / ultra
execution_environment = "local"        # local / thread (Codex app 解释)
target = { type = "project", project_id = "<uuid>" }  # 哪个 Codex project
cwds = ["/path/to/workdir"]            # agent 启动的工作目录
created_at = <epoch_ms>                # 创建时间戳
updated_at = <epoch_ms>                # 最后修改时间戳
```

> **写 prompt 的原则**:**精简**,只写硬约束 + 配额 + status 输出格式 + 失败兜底。详细 workflow 引用 SKILL.md(改一处生效所有 cron 触发)。

---

### 怎么查看 / 修改 automation

```bash
# 查看本机所有 automation
ls -la ~/.codex/automations/

# 查看某个 automation 的配置
cat ~/.codex/automations/<id>/automation.toml

# 查看某个 automation 的历史进度
cat ~/.codex/automations/<id>/memory.md

# 修改 automation.toml 后:
# - 改 rrule / prompt / status → 直接保存即可,Codex app 会热加载
# - 改 id / kind / target → 需要在 Codex UI 里重新注册(不推荐改)
```

**注意**:`.run-jitter-salt` 是 Codex app 内部文件(防 cron 抖动),**不要改 / 不要删**。

---

### memory.md 怎么维护

每次 automation 触发跑完,agent 必须 append 一段到 memory.md:
- **轮次编号**(N / N+1 / N+2 ...)
- **本轮做了什么**(candidate_count / inbound_replied / outbound_like / outbound_reply)
- **已发 X URL 列表**(inbound + outbound 合并)
- **跳过的**(公司名 / ban / cooldown / 自己帖已有 reply 链)
- **异常**(限流 / 浏览器卡顿 / 5xx / cua_repl 不可用)
- **新经验**(Draft.js / contenteditable / cua_repl quirks)

下个轮次启动时,agent 先读 memory.md 最后几条,避免重复发同一个帖 / 重复掉同一个经验。

---

### 加第 4 个 automation 的流程

1. 新建目录:`mkdir -p ~/.codex/automations/<new-id>/`
2. 写 `automation.toml`(复制 #1 或 #2 改 id / name / prompt / rrule)
3. 写空的 `memory.md`:`touch ~/.codex/automations/<new-id>/memory.md`
4. 如果新 automation 用新 skill,先去 `skills/` 加 `SKILL.md`,prompt 里引用
5. Codex app 会自动发现新目录(下次启动或 reload 后生效)
6. 第一轮跑完,看 memory.md 是否正确追加 + status 报告格式对不对

---

### Automation 三层关系(manager / worker)

```
                    共享 state/*.yaml + state/*.json
                              │
            ┌─────────────────┼─────────────────┐
            ▼                                   ▼
   automation #1 (每小时)              automation #2 (每 30 min)
   创作 pipeline · worker               engagement pulse · worker
            │                                   │
            └──────────────┬────────────────────┘
                           │ 写
                           ▼
                  outputs/<slot>/<topic>/
                  state/inbound-replies.json
                  state/seen-posts.json
                           │
                           │ 读(只读)
                           ▼
                  automation #3 (每日 09:00 +08:00)
                  super-bot · manager
                           │
                           │ emit inbox-item
                           ▼
                  Fang (你) — 唯一对接入口
```

**worker → manager → Fang** 三层关系,super-bot 是中间层。Fang 不直接看 worker bot 的 memory,只看 super-bot 的日报。

```
                    共享 state/*.yaml + state/*.json
                              │
            ┌─────────────────┼─────────────────┐
            ▼                                   ▼
   automation #1 (每小时)              automation #2 (每 30 min)
   创作 pipeline                        engagement pulse
   ↓                                   ↓
   outputs/<slot>/<topic>/              state/inbound-replies.json
   (完成版落盘)                         state/seen-posts.json
            │                                   │
            └───────────── 共享 memory.md 模式 ─┘
                          (各自写各自的 memory.md,
                           不互相依赖)
```

- **共享**:state/ 下的事实源(watchlist / forbidden / account-safety / seen-posts / recent-picks)
- **互不依赖**:两个 memory.md 完全独立,各跑各的
- **互斥**:不发新帖 vs 不创作 — #2 永远是 like+reply,#1 永远是发新帖
- **共用 cooldown**:发新帖 cooldown ≥ 30 min(`schedule.yaml`),发 reply cooldown ≥ 8 min(`skills/x-engagement-pulse/SKILL.md`)

---

### 关键设计决策(2026-10-15 / 16)

- **两个独立 automation**:不像一个混在一起跑,因为 cadence 不一样(每小时 vs 30 min),且目标不同(创作 vs engagement)。独立让两个 workflow 各自演化
- **prompt 引用 SKILL.md**:不在 prompt 里塞 workflow,改规则只动 SKILL.md 一处
- **memory.md 模式**:每个 automation 自带笔记本,跨 session 续 context。**重要**:memory.md 不应该无限增长,定期 prune 早期轮次(保留关键决策和经验即可)

---

### Automation #3:Super-bot 首席汇报官(每日 09:00 +08:00)🆕

| 字段 | 值 |
|------|---|
| 目录 | `~/.codex/automations/super-bot/` |
| id | `super-bot` |
| name | 短文助手日报 · 每日 09:00 (+08:00) |
| kind | `cron` |
| rrule | `FREQ=DAILY;BYHOUR=1;BYMINUTE=0`(UTC 01:00 = +08:00 09:00) |
| model | `MiniMax-M3` |
| reasoning_effort | `medium`(比 worker 轻,只读不写) |
| target | project `71faead3-cd8e-49ec-be13-c9747d4927ac`(同 #1 / #2) |
| cwd | `/Users/fangchen/Documents/短文助手` |
| prompt 引用 | `skills/super-bot/SKILL.md` |

**这一轮做什么**:
- 读 worker bot #1 + #2 的 `memory.md` 最近 24h
- 读 `state/published-posts.json` + `inbound-replies.json` + `seen-posts.json` 当日新增
- 读 `private/account-safety.yaml`(X login + 限流)
- 扫 `outputs/$(date +%m%d)/` 当日完成版
- 出结构化日报(创作 pipeline / engagement pulse / 异常 / 明日建议)
- emit inbox-item 给 Fang

**硬约束**:**只读 + 报告**,不动 X 浏览器,**不亲自做 engagement / 不发 like+reply+post**。

**触发模式**:
- **Cron 自动**(每日 09:00 +08:00):跑完整日报
- **手动查询**(Fang 问「今天怎么样 / 本周 summary」):跑即时摘要
- **规则确认**(Fang 说「以后 X」):先回话确认,不要立即改 state / SKILL.md

**核心定位**:**Fang 的唯一对接入口**。worker bots 不直接 reply 给 Fang,所有汇总走 super-bot。

---

## State 文件(关键事实源)

| 文件 | 谁写 | 谁读 | 改动权限 |
|------|------|------|----------|
| `watchlist.yaml` | Fang | hot-topic-tracker, x-engagement-pulse | Fang 口头 |
| `filter-rules.yaml` | Fang | hot-topic-tracker | Fang 口头 |
| `schedule.yaml` | Fang | cron launchd | Fang 口头 |
| `style-x.yaml` | Fang | post-writer-x, x-engagement-pulse | Fang 口头 |
| `style-xhs.yaml` | Fang | post-writer-xhs | Fang 口头 |
| `forbidden.yaml` | Fang | 全部 skill | **改前必读;团队不可改** |
| `account-safety.yaml` | Fang / agent | 全部 skill | **XHS 解封要 Fang 显式说** |
| `seen-posts.json` | agent | hot-topic-tracker, x-engagement-pulse | agent 自动 |
| `recent-picks.json` | agent | hot-topic-tracker | agent 自动 |
| `published-posts.json` | agent | post-writer-x, x-engagement-pulse | agent 自动 |
| `inbound-replies.json` 🆕 | agent | x-engagement-pulse | agent 自动 |

---

## Outputs 落盘结构

每条完成版都落在 `outputs/<MMDD>-<slot>/<topic>/`:

```
outputs/
├── 1016-am/openai-rosalind-data-policy/
│   ├── material.yaml          # 源帖 ID / handle / 选题理由 / 真图路径
│   ├── x.txt                  # X 文案(已发布后附 # posted_url)
│   ├── xhs.txt                # 小红书文案(等 Fang 手贴)
│   └── screenshots/
│       ├── x-source-post.png
│       ├── x-compose-empty.png
│       ├── x-before-post.png
│       ├── x-after-post.png
│       └── x-live-post.png
```

**真图强制**:`screenshots/*.png` 必须由 `mcp__cua_repl__js` 真抓,绝不用 AI 生成图占位。

---

## 怎么用

### 单条(最常见 — Fang 在 thread 里说「按这个写」)
1. Codex thread 启动 → 自动读 `README.md`(这份)+ `state/*.yaml`
2. 走 `skills/hot-topic-tracker` → 素材包 → `post-writer-x` → 文案 → `publisher-x` 真发
3. 同选题出 `xhs.txt` 交给 Fang 手贴(账号封禁中)
4. `bash scripts/qa-draft.py outputs/<dir>/` 全 PASS 才算完成版

### Cron 批量(每小时自动)
- Codex 收到 cron 触发消息 → 读 `skills/README.md` 入口协议 → 3 完成版
- 候选 = 0 → memory + status 老实写「未发,原因」
- cooldown ≥ 30 分钟(`schedule.yaml#cooldown_between_posts_min`)

### Pulse(每 30 分钟)
- Codex 收到 pulse cron 触发 → 读 `skills/x-engagement-pulse/SKILL.md`
- Phase A inbound(回别人的 reply)优先 → Phase B outbound(主动 like+reply)其次
- 候选 = 0 → 老实写「0 候选,本轮零动作」

### Super-bot 每日 09:00 +08:00(每日早报)
- Codex 收到 super-bot cron 触发 → 读 `skills/super-bot/SKILL.md`
- 自动跑完整日报(读 worker bots memory + state/*.json + outputs/ 当日)
- emit inbox-item 给 Fang

### Super-bot 手动查询(随时)
- 在 Codex thread 里说「按 `/Users/fangchen/Documents/短文助手/skills/super-bot/SKILL.md` 帮我看下今天 X 互动」
- super-bot 跑即时摘要,不跑完整日报

### 手动跑一轮 pulse
在 Codex thread 里直接说:
> 「按 `/Users/fangchen/Documents/短文助手/skills/x-engagement-pulse/SKILL.md` 跑一轮 pulse」

### 改规则
任何时候 Fang 改规则 → 立刻改 `state/*.yaml` 并保留 changelog:
- 「后面小红书只要普通版」→ 已在 `style-xhs.yaml`
- 「停代发 X」→ 改 `account-safety.yaml#x.publish_mode = draft_only`
- 「加 X 账号」→ 改 `watchlist.yaml`,加 handle / lang / tier / follow_for

---

## 状态变更 checklist(改 state 前必读)

| 改什么 | 改哪份 | 谁授权 |
|--------|--------|--------|
| 增减 X 账号 | `watchlist.yaml` | Fang 口头 |
| 改浏览量下限 / AI 关键词 | `filter-rules.yaml` | Fang 口头 |
| X 文风 | `style-x.yaml` | Fang 口头 |
| 小红书文风 | `style-xhs.yaml` | Fang 口头 |
| X 发帖模式 | `account-safety.yaml#x.publish_mode` | Fang 口头 |
| 小红书解封 / 改草稿权限 | `account-safety.yaml#xhs` | Fang **显式说**「可以存草稿了」 |
| Pulse 节奏 / 配额 | automation.toml + SKILL.md | Fang 口头 |

---

## 红线快速版(完整版见 `forbidden.yaml`)

- ❌ 不发新原创长帖 / Quote RT / 新 Post(pulse 模式硬红线)
- ❌ 不出现 OpenCSG / 公司业务
- ❌ 不出现 Chinese AI 公司名:DeepSeek / Moonshot / MiniMax 等
- ❌ 不写 AI 托管 / 自动互动 措辞在公开文案
- ❌ 不写 AI 生成图 / 不堆 hashtag / 不写「配图如下 / 快去看」
- ❌ XHS 自动发布 = 禁止(账号封禁中,只出草稿)

**发起 campaign 前必读** `state/forbidden.yaml` 全文。

---

## 当前账号安全状态(2026-10-16)

| 账号 | 状态 | publish_mode |
|------|------|--------------|
| X (`@FrankFika`) | ✅ logged_in | agent(自动发) |
| 小红书 | ⏸️ banned(AI 托管发文) | draft_only(只草稿) |

任何「想改 XHS publish_mode → agent」的操作前,**必须**确认:
1. `account-safety.yaml#xhs.ban_status.is_banned` 改为 `false`
2. Fang **显式说**「可以存草稿了」
3. 解封后只走 publisher-xhs 草稿模式,绝不点发布

---

## 失败兜底原则

1. **浏览器登录墙 / 验证码** → 把 URL 给 Fang,不自动过
2. **X 限流**('We've temporarily limited your login')→ 立即停手,memory 写明,不装忙
3. **2FA / 二次验证** → 立即停手,memory 写明
4. **XHS 任何自动发布风险** → 立刻停手,关闭页面
5. **任何「假装已发」行为** → 禁止;拿不到 URL 就是没发
6. **cua_repl 工具不可用** → 老实写「浏览器不可用,本轮零动作」

---

## 日常运维

```bash
# 体检:state 解析 + outputs 完整性 + Codex skill 注册 + mmx 可用性
bash scripts/health-check.sh

# 单条草稿质检
python3 scripts/qa-draft.py outputs/<MMDD-slot>/<topic>/

# 装成 macOS launchd(可选,比 crontab 稳)
cp scripts/launchd/com.codex.short-posts.scheduler.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.codex.short-posts.scheduler.plist

# XHS 干跑判断(账号封禁时退出码 1)
bash scripts/publisher-xhs-dryrun.sh [outputs/<dir>]
```

每次出完稿、准备发布前都先跑 `qa-draft.py`,全部 PASS 再走下一步。
新 session 进来第一件事跑 `health-check.sh`。

---

## 整体迁移指南(给新机器 / 给其他人)

### 最小迁移包(整个 `/Users/fangchen/Documents/短文助手/` 直接拷贝)

```bash
# 1. 复制整个项目文件夹(保持路径不变,避免 automation.toml target 失效)
cp -r /Users/fangchen/Documents/短文助手/ /path/to/new/location/

# 2. 复制 automation 配置(3 个 — 含 super-bot)
mkdir -p ~/.codex/automations/
cp -r /Users/fangchen/.codex/automations/users-fangchen-documents-skills-readme-md-1-state-watc/ ~/.codex/automations/
cp -r /Users/fangchen/.codex/automations/x-engagement-pulse-30min/ ~/.codex/automations/
cp -r /Users/fangchen/.codex/automations/super-bot/ ~/.codex/automations/

# 3. Codex session 启动时,确保 mcp__cua_repl__js 工具可用
# 4. X 账号在新 Codex in-app browser 登录一次(@FrankFika)
# 5. 跑 health-check.sh 验证
bash scripts/health-check.sh
```

### 给其他人同步(去掉私人内容)

最小同步包(去掉 `private/account-safety.yaml` 和所有 `outputs/`,只保留可分享的 workflow / skill / state 模板 + `state/account-safety.yaml.sample` 模板):

```
state/watchlist.yaml      (46 账号名单 = 公开)
state/filter-rules.yaml
state/schedule.yaml
state/style-x.yaml
state/style-xhs.yaml
state/forbidden.yaml      (红线 = 公开)
state/account-safety.yaml.sample  (模板,公开;接收方复制到 private/account-safety.yaml 后填写真实信息)
state/seen-posts.json     (脱敏:删掉 own_post_id,保留 post_id dedup 模式)
state/recent-picks.json   (脱敏:删掉 own_post_id)
state/published-posts.json(脱敏:删掉 own_post_id)
skills/                   (整份公开)
schemas/                  (整份公开)
templates/                (整份公开)
scripts/                  (整份公开,launchd plist 需改路径)
README.md                 (本文件)
```

**不能分享**:`private/account-safety.yaml`(含登录态 + 个人信息)、`inbound-replies.json`、`outputs/`(含真图,可能是 Fang 私人素材)。

### 部署到第二台机器 checklist

- [ ] 整个 `短文助手/` 复制过去(路径保持一致,或改 `automation.toml#cwds`)
- [ ] `~/.codex/automations/users-fangchen-documents-skills-readme-md-1-state-watc/` 复制过去
- [ ] `~/.codex/automations/x-engagement-pulse-30min/` 复制过去
- [ ] `~/.codex/automations/super-bot/` 复制过去
- [ ] 启动 Codex session,确认 `mcp__cua_repl__js` 在工具列表里
- [ ] 在 Codex in-app browser 里登录 X 账号 @FrankFika
- [ ] 从模板创建 `private/account-safety.yaml`:
      `cp state/account-safety.yaml.sample private/account-safety.yaml && vim private/account-safety.yaml`
- [ ] 跑 `bash scripts/health-check.sh` 看 12/12 PASS
- [ ] 手动跑一轮 pulse 确认链路:
      > 「按 `/path/to/短文助手/skills/x-engagement-pulse/SKILL.md` 跑一轮 pulse」
- [ ] 等下一次 cron 自动触发,看 memory.md 是否追加记录

---

## 发布历史查询

```bash
# 看最近 10 条已发 X
python3 -c "import json; pp=json.load(open('state/published-posts.json')); [print(e['own_post_url'], '·', e.get('source_post_id','')) for e in pp['entries'][-10:]]"

# 看最近 10 条已回 inbound reply
python3 -c "import json; ir=json.load(open('state/inbound-replies.json')); [print(e['reply_url'], '·', e.get('handle','')) for e in ir['entries'][-10:]]"

# 看最近 5 个完成版落盘
ls -t outputs/ | head -5
```

**唯一成功事实源**:
- X 已发 = `state/published-posts.json#entries[i].own_post_id`
- XHS 草稿 = `outputs/<dir>/xhs.txt` + Fang 手贴确认
- inbound reply = `state/inbound-replies.json#entries[i].reply_id`

---

## 关键决策日志(最近)

| 日期 | 决策 | 文件 |
|------|------|------|
| 2026-10-15 | 启用 X agent 真发;XHS draft_only | `account-safety.yaml` |
| 2026-10-15 | 6 个创作 pipeline skill 上线 | `skills/` |
| 2026-10-16 02:00 | 启用转评赞 pulse 模式(目标 6 小时) | `account-safety.yaml#x.notes` |
| 2026-10-16 13:45 | 启用 inbound reply 模式(inbound 优先于 outbound) | `skills/x-engagement-pulse/SKILL.md` |
| 2026-10-16 13:46 | 加 `x-engagement-pulse` 第 7 skill + `inbound-replies.json` 状态文件 | `skills/`, `state/` |
| 2026-10-16 13:47 | 整理:automation.toml prompt 精简,引用 SKILL.md | `automation.toml` |
| 2026-10-16 13:50 | 加 super-bot 第 8 skill + 第 3 automation(每日 09:00 自动日报 + 手动查询);Fang 唯一对接入口 | `skills/super-bot/SKILL.md`, `~/.codex/automations/super-bot/` |

---

## 故障排查 quick ref

| 症状 | 排查路径 |
|------|----------|
| Cron 跑 0 候选 | 看 memory.md 是否「0 候选,本轮零动作」老实写;若装了忙是 prompt 设计错误 |
| X 限流 | `account-safety.yaml#x.rate_limit_incidents` 追加 incident |
| XHS 解封 | 等 Fang 显式说「可以存草稿了」+ 改 `account-safety.yaml#xhs.ban_status.is_banned` |
| output 落盘不全 | 看 memory.md 哪一步失败;`scripts/qa-draft.py` 跑一次 |
| Codex session 没 cua_repl | 老实写「浏览器不可用,本轮零动作」,等下次 |
| 两个 automation 的 memory.md 找不到 | 检查 `$CODEX_HOME` 环境变量 + `~/.codex/automations/` 路径 |

---

> **原始交接文档**:`/Users/fangchen/Downloads/HANDOFF-短文助手流程.md`(给历史交接参考,主入口已迁到这里)
