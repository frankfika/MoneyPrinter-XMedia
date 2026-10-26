# 短文助手 · 移交手册

> **给接手方（新 AI / 新机器）读的第一份文件。**
> 读完这一份，你应该能独立跑起整条流水线，且不会把 Frank 的账号资产玩坏。
>
> 版本：2026-10-26 · 源项目：`frankfika/MoneyPrinter-XMedia` · 源机器：Frank 的 MacBook（Asia/Shanghai）

---

## 0. 一分钟摘要

短文助手是一条 **X（Twitter）内容流水线**，三件事三条独立的 cron：

| cron | 调度 | 干什么 | 权限 |
|------|------|--------|------|
| **chuangzuo**（创作） | `30 3,15 * * *`（12h） | 扫 X → 选热帖 → 写文案 → 浏览器真发 | 可发原创帖 |
| **pulse**（互动） | `0 4,10,16,22 * * *`（4h） | **只 like+reply，不发新帖** | 可 like / reply |
| **super-bot**（汇报） | `0 9 * * *`（每日 09:00） | 读前两者日志 → 结构化日报 | **只读**，绝不碰 X |

**Frank 只跟 super-bot 对话**，不直接看 worker bot。

**本次移交的三个变化点**（决定了下面所有步骤）：

1. **换机器** —— 代码走 git，登录态和 `private/` 走手工拷贝
2. **换 X 账号** —— 老的 `@FrankFika` 不再由这条流水线操作；新账号从 0 开始
3. **全权自动发** —— 新 AI 拥有完整公开面权限，**没有人工在公开动作前逐条把关**

> ⚠️ 第 3 点加上第 2 点 = **风险最高的一种配置**。理由和防线见第 1 节，请务必读完再动手。

---

## 1. 【必读】新账号 + 全权自动发 = 为什么必须先过闸门

Frank 的老账号 `@FrankFika`（3,620 followers）已经被 **@op7418** 和 **@oran_ge** 拉黑。
Frank 事后确认的原因是：**「你很多拉黑是因为被看出来是 AI 评价了」**。

这不是流量问题，是**账号资产损失** —— 老账号的资产是「AI 独角兽董秘 / 评测出身 / 前工程师」这个**可信度**。

**换新账号并没有让这个问题消失，反而更棘手：**

- 老账号至少有 3,620 个人订阅，AI 味内容被看到，最坏结果是掉几个粉
- **新账号 0 粉丝、0 信任背书。AI 味内容 = 直接被标记为批量 spam 账号，前 30 天基本没有翻身的可能**
- 新账号的每一条内容都在「建立人味」——第一条 AI 味的内容发出去，后面 100 条都要先还这笔债

所以这次移交的**第一原则**：

> **AI 味闸门（`scripts/prepublish.py`）必须是发布的唯一路径，且 `exit 1` 时不许手工绕过。**

2026-10-26 那条被撤掉的 reply **句式全部合规**（没踩任何 `banned_phrases`），但整体结构一眼就是 AI。
**只禁词不禁结构 = 挡不住人。** 规则写在文档里挡不住 AI，必须做成代码里的 `exit code`。

### 三道闸（`skills/x-engagement-pulse/SKILL.md` 里有完整版）

| 闸 | 查什么 | 不通过怎么办 |
|----|--------|-------------|
| **第 0 道 · 机器闸门** | 结构 + 词 + 红线，34 条规则 | `python3 scripts/prepublish.py --text "正文"` → **exit 1 不许发** |
| 第 1 道 · 身份质疑 | 「你是 AI / bot 吗」类内容 | **默认不回**，记一笔留痕 |
| 第 2 道 · 内核撞车 | 你的最强反驳是不是自己近 24h 讲过两遍 | 是 → 不发，记 `SKIPPED_NO_REPLY` |

---

## 2. 第 0 步 · 新机器准备

### 2.1 硬依赖

| 依赖 | 为什么 | 怎么装 | 缺了会怎样 |
|------|--------|--------|-----------|
| **MiniMax Code / Mavis** | 提供 `mcp_browser` 工具 + cron 调度 + session | 装桌面版 | 🔴 整个 pipeline 跑不了（`mcp_browser` 是它的工具名，不是通用协议） |
| **本地代理 7897** | **x.com 直连返回 000，必须走代理** | Clash / Surge 等，端口设 `127.0.0.1:7897` | 🔴 扫不了时间线（2026-10-26 实测：直连 000，代理 200） |
| **`mmx` CLI** | 闸门自动清理要用它调 LLM 改写 | MiniMax 官方 CLI + 配 API key | 🟡 闸门只检测不清理，AI 味文案得全靠手改 |
| **Python 3** | 所有脚本 | 系统自带即可 | 🔴 |
| **`uv`** | `qa-draft.py` 要 `pyyaml`（系统 python3 没有） | `brew install uv` | 🟡 qa-draft 跑不了，闸门的 qa 子检查会挂 |
| **macOS** | `caffeinate` / `pmset` 用来防休眠、查睡眠记录 | —— | 🟡 机器一睡，cron 全停（见第 8 节） |

> ⚠️ **如果接手方不是 MiniMax Code**（比如 Claude Code / Codex），
> `mcp_browser` 这个工具名不存在，5 个 skill 里的浏览器动作都要改写成 Playwright / CDP 脚本 —— **这是整个移交里最大的工作量**，先确认再动。

### 2.2 验证环境

```bash
command -v mmx && mmx quota show          # mmx 可用 + 额度
command -v uv && uv --version             # uv 可用
curl -s -o /dev/null -w "%{http_code}\n" -x 127.0.0.1:7897 https://x.com/   # 代理能通 x.com
python3 -c "import yaml" 2>/dev/null || echo "需要 uv run --with pyyaml"
```

> `qa-draft.py` 是**内容校验器**（占位图 / 格式 / 字数 / 标签），跑得通 ≠ 每篇草稿都过。
> 它会对具体草稿报「N 项失败」—— 那是内容问题，不是脚本问题，别混淆。

---

## 3. 第 1 步 · 拉代码

```bash
git clone https://github.com/frankfika/MoneyPrinter-XMedia.git
cd MoneyPrinter-XMedia
```

目录里**没有**的东西（.gitignore 挡掉了，克隆后没有是正常的）：

| 被忽略的 | 怎么办 |
|---|---|
| `private/` | 手工拷贝（第 2 步） |
| `outputs/**/screenshots/` | 历史截图，本地保留就行 |
| `state/memory/archive/` | 轮转出去的旧轮次归档 |
| `logs/` | 噪音 |
| `.venv/` | 重建：`uv venv && uv pip install pyyaml` |

---

## 4. 第 2 步 · `private/` 拷贝 + **新账号 state 手术**

### 4.1 拷 `private/`

```bash
mkdir -p private
scp <老机器用户>@<老机器>:"/Users/fangchen/Documents/短文助手/private/account-safety.yaml" private/
```

### 4.2 新账号必改（**改错了会永久零发送**）

`private/account-safety.yaml` 里的 `x:` 段是从老账号 `@FrankFika` 继承的。
**新账号一条都没发过，但这些字段还留着老账号的值。**

| 字段 | 新账号该怎么改 | 改错的后果 |
|------|----------------|-----------|
| `account_label` | 新账号的显示名 | 无 |
| `logged_in_as` | 新账号的 handle | 无 |
| `login_state` | 登录后改成 `logged_in` | 闸门/流程会以为没登录 |
| `last_published_at` | **清空** | ⚠️ 留着 = 闸门永远认为「12h 内发过帖」→ **永久零发送** |
| `last_published_post_id` / `_url` / `_round` / `_topic_signature` | **清空** | 同上 |
| `last_outbound_reply_at` / `last_outbound_like_at` / `last_inbound_reply_at` | **清空** | 冷却计算错乱 |
| `publish_mode` | 保持 `agent`（全权自动） | 改成别的就不自动发了 |
| `xhs` 段 | 小红书整体停手，保持 `is_banned: true` | 🔴 解封需要 Frank 显式点头 |

> `last_published_*` 是**冷却闸门的输入**（`chuangzuo_original_post_min_gap_hours: 12`）。
> 这是最容易翻车的一处：抄过去不改，流水线会安静地一条都不发，而且**看起来一切正常**。

### 4.3 `state/` 手术清单

| 文件 | 动作 | 理由 |
|------|------|------|
| `state/ai-taste-rules.json` | **原样带走** | 闸门规则集，34 条，核心资产 |
| `state/gate-regression-anchors.json` | **原样带走** | 验收基线，13 条 |
| `state/style-x.yaml` / `forbidden.yaml` / `watchlist.yaml` / `filter-rules.yaml` | **原样带走** | 规则层，Frank 拍过板的 |
| `state/seen-posts.json` / `index.json` | **带走** | 去重连续性 —— 防止新 AI 重复骚扰同一个人 |
| `state/inbound-replies.json` | **带走** | 同上 |
| `state/published-posts.json` | **带走，别删** | ① 历史记录 ② **`draft_text` 是闸门回归语料**，删了验收就没语料了 |
| `state/index.json` 的 `published` 段 | **清空** | 新账号 published = 0，否则统计口径错 |
| `state/recent-picks.json` | **建议重新生成** | 已失真：115 条里 63 条没有任何日期字段，7 天 dedup 不可用 |
| `state/skip-handles.json` | 带走，**但加注** | @op7418 / @oran_ge 拉黑的是老账号；新账号没被拉黑。不过**根因（AI 味）对新账号一样成立**，保守起见先跳过 |
| `state/gate-receipts.json` | 带走（历史留痕） | —— |

---

## 5. 第 3 步 · 登录新 X 账号

登录态**不存在任何可拷贝的文件**里，它在 Mavis 内置浏览器的 profile 里。必须在新机器上手动登一次：

1. 在新机器打开 MiniMax Code，打开 in-app browser（右侧 FilePanel）
2. 登录新 X 账号
3. 确认能打开 `https://x.com/notifications/mentions`
4. 把 `private/account-safety.yaml#x.login_state` 确认成 `logged_in`

---

## 6. 第 4 步 · 重建三条 cron

**关键参数：`session.mode = new`**（每轮独立 session）。

共享 session 会让上下文无限膨胀（实测涨到 305K/512K tokens），触发 compaction 后大概率中断，
且 **投递成功（`delivered`）≠ 轮次执行** —— 曾经出现过 **51.5 小时零落盘**。
**状态本来就全在 `state/` 文件里，session 不需要承载历史。**

| cron | cron_name | schedule | session |
|------|-----------|----------|---------|
| 创作 | `短文助手 · 创作 pipeline · 每 12 小时` | `30 3,15 * * *` | `{mode: new}` |
| 互动 | `短文助手 · engagement pulse · 每 4 小时` | `0 4,10,16,22 * * *` | `{mode: new}` |
| 汇报 | `短文助手 · super-bot 日报 · 每日 09:00` | `0 9 * * *` | `{mode: new}` |

三条的 `prompt` 原文**已经导出进仓库**了 —— `docs/cron-prompts/{super-bot,pulse,chuangzuo}.md`，逐字复制，别改写。

> 🔴 **prompt 里有绝对路径**：`/Users/fangchen/Documents/短文助手/...`
> 新机器路径不一样的话，**三处都要改**（各 prompt 里的 skill 路径 + `project` 字段）。
> 漏改的后果很阴：agent 去读一个不存在的目录，然后**安静地什么都不做**，看起来像「今天没热点」。

`project` 要指向**新机器**的项目绝对路径，`model` 填接手方要用的模型，`timezone` 是 `Asia/Shanghai`。

> ⚠️ 老机器上的三条 cron **记得停掉**，否则两个机器同时对同一个 X 账号操作。

---

## 7. 第 5 步 · 上线验收（**过不了就别开 cron**）

### 7.1 闸门回归（必须 exit 0）

```bash
python3 scripts/gate-regression.py
```

预期输出：`PASS 12 / FAIL 1 / 共 13`，最后一行 `✅ 与基线完全一致`。

- 那 1 条 FAIL 是 `pulse_round_83` —— **已知的 AI 味真实反例**（被 `frank.pivot_expand`「问题来了」抓到，soft 分 15）。它必须一直 FAIL
- 如果变成 13 条全 PASS → 闸门被改松了，**AI 味会漏到公开面**，最危险
- 如果多了几条 FAIL → 闸门被改严了，人话也会被拦

### 7.2 首帖闸门（必须 exit 0）

新 AI 先自己写 3 条候选文案，逐条过：

```bash
python3 scripts/prepublish.py --text "候选正文"
```

`exit 0` 才能进发布流程。`exit 1` 就换一条 —— **不许手工绕过**。

### 7.3 冷启动节奏建议（新账号）

新账号 0 粉丝，**建议**（不是硬规则）：

- 前 2 周：每天原创 ≤ 1 条、每天互动动作 ≤ 1 个
- 每一条都必须过闸门 + 走 `fill` + `Cmd+Enter` 唯一真发路径
- 不要在 24h 内重复同一内核（闸 2）

---

## 8. 故障模式速查

### 8.1 🔴 机器睡了 → cron 全停（Frank 已经踩过）

**症状**：cron 状态全是 `delivered`，但 `state/memory/*.md` 末轮时间戳停在几小时前。

**根因**（2026-10-26 实测）：03:38 笔记本合盖 → 网络断 → agent-runtime 抛
`net::ERR_CONNECTION_CLOSED`（errorCode 50113）→ turn 被打断。机器 09:01:53 才醒。
**15 次投递只有 2 次落盘，丢 12 轮。**

**诊断三件套**：
```bash
# 1. 末轮时间戳 vs 真实时间
python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 1
# 2. 那一轮 session 的死法
mavis session get <session_id>       # status 字段直接写明死法
# 3. 机器睡眠/唤醒一手证据
pmset -g log | grep -E "Entering Sleep state|Wake from"
```

**防呆**：
```bash
nohup caffeinate -i -m -s >/dev/null 2>&1 & disown   # 挡住空闲休眠
```
⚠️ `caffeinate` **挡不住合盖休眠** —— macOS 合盖必睡（除非外接显示器 + 电源 + 外设走 clamshell 模式）。
**合盖 = 三条 cron 全停，这个只能靠物理上别盖。**

### 8.2 🔴 代理没配 → 扫不到时间线

`curl` 直连 x.com 返回 `000` = 连不上。必须走 `-x 127.0.0.1:7897`。
**注意区分「扫描通道被封」和「没热点」** —— candidate_count = 0 有两种完全不同的原因，别混写。

### 8.3 🟡 免登录核验通道（不发帖也能读数据）

| 通道 | 用途 | 状态 |
|------|------|------|
| `cdn.syndication.twimg.com/tweet-result` | 单帖 likes / replies（免登录） | ✅ 可用，走代理 |
| `r.jina.ai` | 通用抓取 | ❌ 匿名额度作废（401 bad IP reputation） |
| syndication timeline-profile | 时间线扫描 | ❌ 429 出口 IP 被限 |

### 8.4 🟡 发布路径

**唯一稳定的真发路径是 `fill` + `Cmd+Enter`（Meta+Enter）。** Post button click 不可靠。
- 填完等 8–10 秒
- **不要**查 profile / with_replies / home feed 判断真发（各自有缓存延迟，8–30s 不刷新）
- 真发验证：search 拿 own_post 的 post_id 和 URL
- **不要盲 retry** —— 第二次会触发 X 的反重复拦截（真实 spam 信号）

### 8.5 🟡 测量口径（踩过两次）

- **likes 必须** `query kind=dom` 打 `[data-testid='like']` 读 aria-label（`"N Likes. Like"`）
- **详情页底部大数字是 VIEWS 不是 likes**，差一个数量级
- `query kind=text` 读到的也是 views
- replies 用 `[data-testid='reply']` 的 aria-label
- **不要用 likes 做跨帖对比**（样本量不够）
- 页面级 selector 只返回首个匹配 —— detail 页每条帖都有自己的 like 按钮，**首个匹配可能跟目标完全无关**

---

## 9. 目录地图 · 谁能改什么

```
短文助手/
├── skills/            9 个 skill（规程层）—— 改需要 Frank 点头
├── scripts/           闸门 / 检测 / 落盘工具
├── state/             ★ 事实源（唯一真相）
│   ├── *.yaml         规则（forbidden / style / watchlist / filter / schedule）
│   ├── *.json         去重索引 / 已发记录 / 闸门规则 + 收据
│   └── memory/*.md    轮次日志（chuangzuo / pulse / super-bot）
├── private/           account-safety.yaml（**手拷，不进 git**）
├── outputs/           完成版落盘（material.yaml / x.txt / screenshots）
├── schemas/ templates/
└── README.md          架构文档
```

**状态变更授权表**（改 state 前必读）：

| 改什么 | 改哪份 | 谁授权 |
|--------|--------|--------|
| 增减 X 账号 | `watchlist.yaml` | Frank 口头 |
| 改浏览量下限 / AI 关键词 | `filter-rules.yaml` | Frank 口头 |
| X 文风 | `style-x.yaml` | Frank 口头 |
| X 发帖模式 | `account-safety.yaml#x.publish_mode` | Frank 口头 |
| 小红书解封 | `account-safety.yaml#xhs` | Frank **显式说**「可以存草稿了」 |
| pulse / chuangzuo 节奏配额 | cron 配置 + `skills/*/SKILL.md` | Frank 口头 |
| 闸门规则集 | `ai-taste-rules.json` | **任何改动都必须跑 `gate-regression.py` 验证** |

---

## 10. 状态契约

| 动作 | 落盘 | 还要同步 |
|------|------|---------|
| outbound reply / like | `seen-posts.json` | `index.json` |
| inbound reply | `inbound-replies.json` + `seen-posts.json` | `index.json` |
| 原创 post | `published-posts.json` | `index.json` |
| 闸门放行/拦下 | `gate-receipts.json`（含最终文本 sha256，事后可核对） | —— |
| 轮次日志 | `memory/<bot>.md`（**每段前必须有 `<!-- round -->`**） | —— |

**`index.json` 是每轮的轻量去重索引 —— 只读它，不要全量加载 `seen-posts.json`（147KB）。**

**轮次日志的段边界必须用显式分隔符 `<!-- round -->`**，不要靠标题正则猜
（轮次段内部的小节标题经常含「pulse round」这类关键词，按标题切会把一轮切成碎片）。
写完跑一次冒烟测试：

```bash
python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 1   # 必须取到最新完整一段
```

---

## 11. 铁律（**接手方第一条就要读 `state/forbidden.yaml` 全文**）

- ❌ 不出现 OpenCSG / 公司业务
- ❌ 不出现 Chinese AI 公司名：DeepSeek / Moonshot / MiniMax 等
- ❌ 不写 AI 托管 / 自动互动 / bot 措辞在公开文案
- ❌ 不写 AI 生成图 / 不堆 hashtag（≤1）/ 不写「配图如下 / 见下图 / 快去看」
- ❌ pulse 模式不发新原创长帖 / Quote RT / 新 Post
- ❌ XHS 自动发布 = 禁止（账号封禁中，只出草稿）
- ❌ **闸门 exit 1 不许手工绕过**
- ❌ **不许装忙** —— 缺数据就写「数据不可用，跳过」，不要凑数字
- ✅ 候选不足就少做，**不要凑数**

---

## 12. 决策记录（Frank 拍过板的，继承）

| 时间 | 决策 |
|------|------|
| 2026-10-16 | 启用 inbound reply 模式；inbound 文案 80–180 字；inbound 优先于 outbound |
| 2026-10-21 | 「你和大家互动的频率不要那么高」→ 30min 降到 2h，单轮动作上限 8 砍到 3；inbound reply ≤1 / outbound reply ≤1 / outbound like ≤2 |
| 2026-10-23 | 原创线 66h likes Δ0 → 建议显式暂停（**待 Frank 答复**） |
| 2026-10-25 | cron 降到 4 轮/天；三条 cron 拆成独立 session（`mode=new`）；铁律从 cron prompt 下沉到 skill；memory 迁到项目内 `state/memory/` |
| 2026-10-26 | 「被拉黑是因为被看出来是 AI 评价了」→ 新增第 0 道 AI 味自检 + **代码级闸门**（`prepublish.py`），规则从 `style-x.yaml` 单向读取 |
| 2026-10-26 | 「拉黑的是……你不要去乱评价」→ outbound reply 默认更保守，**宁可不发，也不发有 AI 腔的结构化点评** |

**完整的决策记录在每个 `skills/*/SKILL.md` 末尾**，接手方必须读完 —— 那里有 Frank 一手反馈的原文。

---

## 13. 移交检查清单

打勾再开 cron：

- [ ] 新机器装了 Mavis（提供 `mcp_browser`）
- [ ] 代理 7897 通 x.com（`curl -x 127.0.0.1:7897 https://x.com/`）
- [ ] `mmx` 可用 + 有额度
- [ ] `uv` 可用，`uv run --with pyyaml python3 scripts/qa-draft.py` 跑得通
- [ ] 仓库已 clone，`state/ai-taste-rules.json` + `state/gate-regression-anchors.json` 在
- [ ] `private/account-safety.yaml` 已拷，**新账号字段已改，`last_published_*` 已清空**
- [ ] 新 X 账号已登录，`login_state: logged_in`
- [ ] `python3 scripts/gate-regression.py` → **exit 0**，12 PASS / 1 FAIL
- [ ] 3 条候选文案 `python3 scripts/prepublish.py --text` → 全 exit 0
- [ ] 三条 cron 建好，`session.mode=new`，prompt 逐字复制
- [ ] **prompt 里的绝对路径已改成新机器路径**（3 处 + `project`）
- [ ] **老机器上的三条 cron 已停掉**
- [ ] `caffeinate` 已挂上（且**别合盖**）
- [ ] `state/recent-picks.json` 已重新生成
