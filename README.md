# 短文助手 · X 内容流水线

> Fang 的 X（Twitter）内容流水线 + **双向 engagement pulse bot**。
> 沉淀在这里是为了**整体迁移**和**同步给团队成员 / 自己的另一台机器**。

---

## TL;DR — 一分钟了解

三件事，三条独立的 cron：

| cron | 调度 | 干什么 |
|------|------|--------|
| **chuangzuo**（创作） | `30 3,15 * * *`（12h） | 扫 X → 选热帖 → 写文案 → browser use 真发 X |
| **pulse**（互动） | `0 4,10,16,22 * * *`（4h） | **只 like+reply，不发新帖**。inbound（回别人的 reply）+ outbound（主动 like+reply 高优热帖） |
| **super-bot**（汇报） | `0 9 * * *`（每日 09:00） | **只读 + 报告**，不动 X。读前两者日志 → 结构化日报 → 给 Fang |

**Frank 只跟 super-bot 对话**，不直接看 worker。

跑起来最低依赖：**MiniMax Code session + `mcp_browser`**。
X 账号 `@FrankFika` 已登录在 in-app browser 里。

> ⚠️ **2026-10-25 架构变更**：三个 cron 从「共用一个 session」改成**各自独立 session**（`session.mode=new`）。
> 原因：共用 session 会让上下文无限膨胀（实测涨到 305K/512K tokens），触发 compaction 后大概率中断，
> 且投递成功（`delivered`）≠ 轮次执行 —— 曾经出现过 **51.5 小时零落盘**。
> **状态本来就全在 `state/` 文件里，session 不需要承载历史。**

---

## 架构总览

```
                      state/*.yaml + state/*.json（事实源）
                                 │
                ┌────────────────┼────────────────┐
                ▼                                 ▼
       创作 pipeline skill                  Engagement skill
                │                                 │
   hot-topic-tracker ─→ post-writer-x ─→        x-engagement-pulse
   hot-topic-tracker ─→ post-writer-xhs         （inbound + outbound）
                                 │                │
                          publisher-x             │
                          publisher-xhs           │
                                 │                │
                          outputs/<date>/         │
                          （完成版落盘）           │
                                                  ▼
                                    state/inbound-replies.json
                                    state/seen-posts.json
                                    state/index.json（去重索引）
                                    state/memory/*.md（轮次日志）
```

**三条线共享 `state/` 下的事实源**（账号名单 / 规则 / 账号安全 / 禁忌）。
**三条线各有独立 session，互不污染。**

---

## 目录结构

```
短文助手/
├── README.md                  # 本文件
├── skills/                    # 8 个 skill，每个一份 SKILL.md
│   ├── README.md              # ★ 入口协议：整个流程怎么跑
│   ├── browser-use-utils/     #   mcp_browser 工具封装
│   ├── hot-topic-tracker/     #   扫 X → 出素材包
│   ├── post-writer-x/         #   写 X 文案
│   ├── post-writer-xhs/       #   写小红书文案
│   ├── publisher-x/           #   真发 X
│   ├── publisher-xhs/         #   小红书（当前停手，账号 banned）
│   ├── super-bot/             #   ★ 首席汇报官（只读）
│   └── x-engagement-pulse/    #   ★ 转评赞（只 like+reply）
│
├── state/                     # ★ 事实源
│   ├── forbidden.yaml         #   红线（改前必读，团队不可改）
│   ├── filter-rules.yaml      #   筛选规则
│   ├── watchlist.yaml         #   X 账号名单
│   ├── style-x.yaml           #   X 文风
│   ├── style-xhs.yaml         #   小红书文风
│   ├── schedule.yaml          #   调度参数
│   ├── index.json             #   ★ 去重索引（每轮只读这个，别全量 seen-posts.json）
│   ├── seen-posts.json        #   outbound 已处理帖全量记录
│   ├── published-posts.json   #   已发原创帖记录
│   ├── inbound-replies.json   #   已回 inbound 记录
│   ├── outbound-actions.json  #   outbound like/reply 全量
│   ├── recent-picks.json      #   7 天 topic signature dedup
│   └── memory/                #   ★ 轮次日志（主文件留末 30 段）
│       ├── pulse.md
│       ├── chuangzuo.md
│       ├── super-bot.md
│       └── archive/           #     轮转出去的历史（本地留，不进 git）
│
├── private/                   # 本机私有（不进 git）
│   └── account-safety.yaml    #   登录态 + XHS ban 状态 + 限流历史
│
├── scripts/
│   ├── tail-rounds.py         #   ★ 只读 memory 最后 N 段（别全量 cat）
│   ├── qa-draft.py            #   草稿自检
│   ├── health-check.sh        #   环境体检
│   └── publisher-xhs-dryrun.sh
│
├── outputs/                   # 完成版落盘（不进 git）
│   └── <YYYY-MM-DD>-<slot>/<topic>/{material.yaml, x.txt, screenshots/}
│
└── logs/                      # 运行日志（不进 git）
```

---

## ★ 三个 cron

### 调度配置

通过 `cron_read` / `cron_update` 管理（不在文件里，配置存在 runtime）。

| cron | cron_id | 调度 | session |
|------|---------|------|---------|
| super-bot | `6560e820-db95-4b83-91ad-4a0f7d4d3fd3` | `0 9 * * *` | `mode=new`（独立） |
| pulse | `0dbbcbb9-ac42-456a-bd35-73f9ed960a07` | `0 4,10,16,22 * * *` | `mode=new`（独立） |
| chuangzuo | `d5c0d018-fcb4-4205-8f5e-35d41c0d1fb9` | `30 3,15 * * *` | `mode=new`（独立） |

```bash
# 看配置和最近投递
# → mcp_invoke tool_name=cron_read arguments={"view":"list"}
# → mcp_invoke tool_name=cron_read arguments={"view":"runs","cron_id":"..."}
```

### cron prompt 的规矩

**prompt 只写「本轮硬约束 + 指向 SKILL.md」，不复制规程。**

所有铁律（测量方法、发送路径、失败判据）都在 `skills/*/SKILL.md` 里，
因为 `session.mode=new` 的新 session **没有任何历史上下文**，规程必须自包含。

一个合格 prompt 约 12 行：模式检测 + 硬约束 + 频率上限 + 失败兜底 + 输出格式 + 指向 SKILL.md。

---

## 上下文管理（省 token 的关键）

**别全量 cat。** 每轮该读什么：

```bash
# 规程（读一次就够）
skills/x-engagement-pulse/SKILL.md          # 12.8 KB

# 去重 —— 只读索引，不读 147KB 的 seen-posts.json
state/index.json                              # 47.6 KB

# 规则
state/forbidden.yaml  state/style-x.yaml  state/watchlist.yaml   # 合计 13 KB
private/account-safety.yaml                                         # 5.7 KB

# 轮次日志 —— 只读末 N 段
python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 3      # 3.9 KB
python3 scripts/tail-rounds.py state/memory/chuangzuo.md --rounds 2  # 5.9 KB
```

**每轮上下文源合计 ≈ 89 KB**（旧方案 8 个文件全量 cat ≈ 1276 KB，**省 93%**）。

写完 `state/seen-posts.json` / `inbound-replies.json` / `published-posts.json` 后，
**必须同步 `state/index.json`**，否则下一轮去重会漏。

---

## State 文件（关键事实源）

| 文件 | 谁写 | 谁读 | 改动权限 |
|------|------|------|----------|
| `forbidden.yaml` | Fang | 全部 skill | **改前必读；团队不可改** |
| `watchlist.yaml` | Fang | hot-topic-tracker, pulse | Fang 口头 |
| `filter-rules.yaml` | Fang | hot-topic-tracker | Fang 口头 |
| `schedule.yaml` | Fang | cron | Fang 口头 |
| `style-x.yaml` | Fang | post-writer-x, pulse | Fang 口头 |
| `style-xhs.yaml` | Fang | post-writer-xhs | Fang 口头 |
| `account-safety.yaml`（private/） | Fang / agent | 全部 skill | **XHS 解封要 Fang 显式说** |
| `index.json` | agent | pulse, hot-topic-tracker | agent 自动（**每次写 state 必须同步**） |
| `seen-posts.json` | agent | hot-topic-tracker, pulse | agent 自动 |
| `published-posts.json` | agent | post-writer-x, pulse | agent 自动 |
| `inbound-replies.json` | agent | pulse | agent 自动 |
| `outbound-actions.json` | agent | pulse, super-bot | agent 自动 |
| `recent-picks.json` | agent | hot-topic-tracker | agent 自动 |

---

## Outputs 落盘结构

每条完成版落在 `outputs/<YYYY-MM-DD>-<slot>/<topic>/`：

```
outputs/
└── 2026-10-25-am-c1/
    └── anthropic-protein-wet-lab/
        ├── material.yaml          # 源帖 ID / handle / 选题理由 / 真图路径
        ├── x.txt                  # X 文案（已发布后附 posted_url）
        ├── xhs.txt                # 小红书文案（等 Fang 手贴）
        └── screenshots/
            ├── x-source-post.png
            ├── x-compose-empty.png
            ├── x-before-post.png
            ├── x-after-post.png
            └── x-live-post.png
```

**真图强制**：`screenshots/*.png` 必须由 browser use 真抓，绝不用 AI 生成图占位。

---

## 怎么用

### 单条（最常见 —— Fang 在对话里说「按这个写」）
1. 走 `skills/hot-topic-tracker` → 素材包 → `post-writer-x` → 文案 → `publisher-x` 真发
2. 同选题出 `xhs.txt` 交给 Fang 手贴（账号封禁中）
3. `python3 scripts/qa-draft.py outputs/<dir>/` 全 PASS 才算完成版

### Cron 批量
- cron 触发 → 读对应 `skills/*/SKILL.md` → 执行
- 候选 = 0 → memory + status 老实写「未发，原因」，**不装忙**

### 手动跑一轮
> 「按 `/Users/fangchen/Documents/短文助手/skills/x-engagement-pulse/SKILL.md` 跑一轮 pulse」

### Super-bot 手动查询（随时）
> 「按 `/Users/fangchen/Documents/短文助手/skills/super-bot/SKILL.md` 帮我看下今天 X 互动」

### 改规则
任何时候 Fang 改规则 → 立刻改 `state/*.yaml` 并保留 changelog。

---

## 状态变更 checklist（改 state 前必读）

| 改什么 | 改哪份 | 谁授权 |
|--------|--------|--------|
| 增减 X 账号 | `watchlist.yaml` | Fang 口头 |
| 改浏览量下限 / AI 关键词 | `filter-rules.yaml` | Fang 口头 |
| X 文风 | `style-x.yaml` | Fang 口头 |
| 小红书文风 | `style-xhs.yaml` | Fang 口头 |
| X 发帖模式 | `account-safety.yaml#x.publish_mode` | Fang 口头 |
| 小红书解封 / 改草稿权限 | `account-safety.yaml#xhs` | Fang **显式说**「可以存草稿了」 |
| Pulse / chuangzuo 节奏配额 | cron 配置 + `skills/*/SKILL.md` | Fang 口头 |

---

## 红线快速版（完整版见 `forbidden.yaml`）

- ❌ 不发新原创长帖 / Quote RT / 新 Post（pulse 模式硬红线）
- ❌ 不出现 OpenCSG / 公司业务
- ❌ 不出现 Chinese AI 公司名：DeepSeek / Moonshot / MiniMax 等
- ❌ 不写 AI 托管 / 自动互动 措辞在公开文案
- ❌ 不写 AI 生成图 / 不堆 hashtag / 不写「配图如下 / 快去看」
- ❌ XHS 自动发布 = 禁止（账号封禁中，只出草稿）

**每轮开工前必读** `state/forbidden.yaml` 全文。

---

## 当前账号安全状态（2026-10-25）

| 账号 | 状态 | publish_mode |
|------|------|--------------|
| X (`@FrankFika`) | ✅ logged_in | agent（自动发） |
| 小红书 | ⏸️ banned（AI 托管发文） | draft_only（只草稿） |

任何「想改 XHS publish_mode → agent」的操作前，**必须**确认：
1. `account-safety.yaml#xhs.ban_status.is_banned` 改为 `false`
2. Fang **显式说**「可以存草稿了」
3. 解封后只走 publisher-xhs 草稿模式，绝不点发布

---

## 失败兜底原则

1. **浏览器登录墙 / 验证码** → 把 URL 给 Fang，不自动过
2. **X 限流**（"We've temporarily limited your login"）→ 立即停手，memory 写明，不装忙
3. **2FA / 二次验证** → 立即停手，memory 写明
4. **XHS 任何自动发布风险** → 立刻停手，关闭页面
5. **任何「假装已发」行为** → 禁止；拿不到 URL 就是没发
6. **mcp_browser 不可用** → 老实写「浏览器不可用，本轮零动作」
7. **cron 投递成功 ≠ 轮次执行** → 日报必须查「轮次真空期」，见下

---

## ⚠️ 轮次真空期（本地 cron 的固有性质）

**cron 依赖 runtime 进程存活。机器一睡，触发点无人执行，且不补跑。**

后果：
- 睡眠期间进来的 inbound **完全没人接**
- `cron_read` 看到的 `status: delivered` 只代表消息投进 session 了，**不代表那一轮跑完并落盘**

判据（super-bot 日报必查）：`state/memory/*.md` 末轮时间戳 vs 现在的真实时间。
距末轮 > 2 × 调度间隔 = 真空期，要写进日报。

曾出现的实测：10-23 20:12 → 10-25 23:45，**51.5 小时零落盘，丢失 35 个排定轮次**。

**这个性质本地 cron 改不掉。** 想让 Frank 睡觉时也有人接，只能把 pipeline 搬到常开机器上。

---

## 日常运维

```bash
# 体检：state 解析 + outputs 完整性
bash scripts/health-check.sh

# 单条草稿质检
python3 scripts/qa-draft.py outputs/<date-slot>/<topic>/

# 只读轮次日志末 N 段
python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 3

# XHS 干跑判断（账号封禁时退出码 1）
bash scripts/publisher-xhs-dryrun.sh
```

---

## 迁移说明

搬到别的机器时：

1. 整个文件夹直接搬（`private/` 和 `state/memory/archive/` 不进 git，需单独拷）
2. 在目标机器上重建 3 个 cron（`cron_create`），**`session.mode` 一定要选 `new`**
3. 浏览器工具名从 `mcp__cua_repl__js` 换成 `mcp_browser`（见 `skills/browser-use-utils/SKILL.md`）
4. `private/account-safety.yaml` 里的登录态在目标机器上要重新确认
