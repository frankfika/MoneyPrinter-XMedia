---
name: x-engagement-pulse
description: X 转评赞 pulse — 给 @FrankFika 主账号提活跃度。**只 LIKE + REPLY 别人的帖子，不发新帖**。每轮 inbound（回别人给我的 reply，社区建设核心）优先，outbound（主动 like+reply 高优热帖）其次。触发：cron 每 4 小时一轮（4,10,16,22），或手动跑一轮。
---

# X 转评赞 Pulse

双向 engagement bot。**不发新原创长帖 / Quote RT / 新 Post**。

> 本 skill 是**自包含规程**。cron prompt 只保留本轮硬约束并指向这里；所有铁律都在本文档，不需要复制进 prompt。

## 触发

- cron：`0 4,10,16,22 * * *`（Asia/Shanghai），4 轮/天
- 手动：在对话里说「跑一轮 pulse」

## 硬约束（红线）

来自 `state/forbidden.yaml`，绝不踩：

- ❌ 不发新原创长帖 / Quote RT / 新 Post（只 LIKE + REPLY）
- ❌ 不出现 OpenCSG / 公司业务
- ❌ 不出现 Chinese AI 公司名（避开 dotey 那条 5-7% 蒸馏营收帖里点名的 DeepSeek / Moonshot / MiniMax 等）
- ❌ 不写 AI 托管 / 自动互动 措辞在公开文案
- ❌ 不写 AI 生成图、不堆 hashtag（≤ 1 个或不用）
- ❌ 不写「配图如下 / 见下图 / 快去看」

XHS 默认停手（`private/account-safety.yaml#xhs.ban_status.is_banned = true`）。

## 配额（Frank 2026-10-21 降频，最高优先级，压过下面所有节奏建议）

| 类型 | 每轮上限 |
|------|---------|
| **单轮总动作** | **≤ 3**（原来 8） |
| inbound reply | ≤ 1 |
| outbound reply | ≤ 1 |
| outbound like | ≤ 2 |
| 原创 post | 0（chuangzuo cron 独占，pulse 不碰） |
| quote RT | 0（Frank 没要求过，不主动开） |

- 候选不足就少做，**不要凑数**
- 如果 Frank 自己在 2 小时内发过帖（查 `/FrankFika/with_replies` 顶部）→ **本轮主动降载到 1 个动作或零动作**
- like 间隔 ≥ 2 min、reply 间隔（inbound + outbound 合并）≥ 8 min

## 工作流

### Phase A：Inbound 扫描（必做第一步）

1. 打开 `https://x.com/notifications/mentions`
2. 筛 type = reply 的通知（「X replied to your post」），抓 handle / source_post_id / reply 时间
3. 已在 `state/inbound-replies.json` 的 drop（防重复回）—— **先查 `state/index.json` 的 `inbound` 段**
4. 排序：**24h 内 > 8h 内 > 旧**
5. 优先回：
   - **我原帖 ≥ 5K views 的 reply**（高曝光 thread）
   - **中文 KOL 的 reply**（社区活跃度）
6. 写法（`state/style-x.yaml` 口语爆款风）：
   - **80-180 字**（比 outbound 短，接话延伸不是自说自话）
   - 含 1 个具体延伸点 / 反问 / 数字
   - 不堆 hashtag；可附自己 prior 帖（`state/published-posts.json` 选最相关的）
7. 完成后：
   - `state/inbound-replies.json` 末加 `{handle, source_post_id, reply_id, reply_url, at, topic}`
   - `state/seen-posts.json` 末加 `source_post_id`，`treatment=inbound_replied`
   - `state/index.json` 同步更新（见「状态文件」节）

> ⚠️ **通知页文本抽取行序错位**：notifications 的 text 抽取会把「时间 / 上下文预览 / actor / 动词」拆成不对应的行序。中文短句尤其容易被误读成一条「发言」。
> **看到像敌意回复 / 质疑 / 找茬的中文短句，决定回不回之前，必须去 `https://x.com/notifications/mentions` 确认它到底是不是发给 @FrankFika 的。** 唯一可信判据是 Mentions 页出现该 handle + `Replying to @FrankFika`。
> 看到「liked / followed」类动词却配着一段攻击性文字 → 大概率是上下文预览串位，不是回复。

### Phase B：Outbound 扫描（其次）

1. 优先级 handle timeline（每轮至少扫 3 个）：
   - **高优**：karpathy / sama / OpenAI / AnthropicAI / GoogleDeepMind / NVIDIA / dotey / oran_ge / op7418 / vista8 / akhaliq / karminski3 / FinanceYF5 / jiqizhixin
   - **兜底**：For-you / Following timeline（找「high view + low reply」）
2. 筛条件：**≥ 5K views** 或 **≥ 50 likes** 或 AI 关键词命中 + < 8h
3. 已发过的直接 drop —— **查 `state/index.json` 的 `seen` 段**，不要全量加载 `seen-posts.json`
4. 跳过的：
   - dotey 5-7% 蒸馏营收帖引用 simonw 主帖（带 DeepSeek/Moonshot/MiniMax）
   - Tesla 喷气式 / Roadster / SpaceX 类非 AI 帖
   - 7 天 dedup topic（`state/recent-picks.json` 查 `expires_at`）

### Phase C：Outbound reply 写法

80-320 字，口语爆款风（`state/style-x.yaml`）：

- 冲击钩子开头（数字 / 反差 / 意外结果）
- 具体步骤 / 坑点 / 对比
- 一句轻收尾（不写「快去看」式安利腔）
- **含 1 个具体数字 / 链接 / 事实**
- 可附自己 prior 帖（`state/published-posts.json` 选最相关的，放末尾让 X 自动 quote embed）
- 不堆 emoji（0~2 个）、不堆 hashtag（0~1 个）

## 判定不回复（三道闸，第 0 道最先过）

### 🔴 第 0 道闸：AI 味自检（发出去之前，比下面两道都早）

**来源**：2026-10-26 Frank 直接反馈 ——「@op7418 / @oran_ge 拉黑你，是因为被看出来是 AI 评价了。」

`state/forbidden.yaml` 和 `state/style-x.yaml` 禁的是**句式**。
但 2026-10-26 那条被撤掉的 reply 草稿**句式全部合规**，结构一眼就是 AI。
**所以必须查结构，不能只查词。**

#### 撤掉的那条长什么样（反面教材）

> 「"没有 lab 值得信任"这个结论听着对，但没法执行——你总得选一个。
> 我选的标准不看榜单，看我手上有没有它的一手失败样本。……
> 评测真正的产出不是排名，是"我该在哪几处盯它"。」

结构 = **引述对方原话 → 宣布「同意一半 / 没法执行」→ 转折展开 → 对仗升华收尾**。四步全中。

#### 自检五条（任一条不过就不发）

1. **引述型开场** —— 开头在复述对方说了什么？→ 换成从自己的动作 / 场景 / 结论起手
2. **同意一半** —— 「这个结论听着对，但」「没法执行」「一半同意」→ 删掉，直接说自己的判断
3. **转折展开** —— 「但真正的产出是」「问题来了」「其实关键是」→ **AI 味最重的一步**
4. **对仗升华收尾** —— 结尾是两句对称短句？→ 改成陈述句 / 自嘲 / 留个口子不答
5. **内核撞车** —— 这个观点 Frank 自己近 7 天说过？→ 说过就不发

#### 允许的结构（人味的样子）

- 从一个具体动作 / 场景 / 时间起手
- 平铺直叙，允许不完整、不圆满、不总结
- 有具体数字、具体案例、具体人名（**不编**）

#### 判定

**过不了第 0 道闸 → 一律不发。** 把 post_id 记进 `state/seen-posts.json` + `context: SKIPPED_AI_TONE` + 理由。

**宁可这轮 0 动作，也不要为了「有产出」发一条一看就是 AI 的东西。**
账号资产是「AI 独角兽董秘 / 评测出身 / 前工程师」这个**可信度**；
3,620 followers 里已经有 2 个大 V 拉黑。为一点互动量去发结构化点评 = 拿可信度换曝光。

#### 🛡️ 机器闸门（2026-10-26 加，代码级强制）

上面 5 条是**人读的自检**，容易漏。**reply 发出前必须跑机器闸门**：

```bash
python3 scripts/prepublish.py --text "<reply 正文>"
```

- **exit 0** → 可以发
- **exit 1** → 不许发。脚本会自动尝试 LLM 清理再检测；仍不过就**换一条或不发**

检测内容（`state/ai-taste-rules.json`）：
- AI 味：Wikipedia「Signs of AI writing」24 类模式 + Frank 中文 AI 味词表
  （闭环 / 护城河 / 底层逻辑 / 所以问题来了 / 反过来说 …）
- 结构：引述型开场 / 同意一半 / 转折展开 / 对仗升华 / 三段式 / 反问结尾
- 红线：OpenCSG / Chinese AI 公司名 / hashtag 风暴 / 安利腔

> ⚠️ **闸门 exit 1 时不许手工绕过。** 规则写在文档里挡不住人 —— 2026-10-26 那条被撤掉的
> reply **句式全部合规、结构一眼就是 AI**，只有机器闸门能拦住。
> 自动清理会保留所有事实（数字/链接/人名），只改结构。

#### 已验证的检测效果（2026-10-26）

用 13 条**真实发过的**帖做回归：

| 样本 | 结果 |
|---|---|
| 12 条正常帖 | 全部 PASS（无误伤） |
| `pulse_round_83`（含「闭环/护城河/所以问题来了/反过来说」） | **FAIL** —— 抓到了 |
| 被撤掉的那条 AI 味 reply | **FAIL** —— 抓到了 |
| 含 OpenCSG + DeepSeek | **FAIL** —— 红线拦下 |
| 含 4 个 hashtag | **FAIL** —— 红线拦下 |

清理器实测：score 12 → 3，**事实全保留**（半年 / 两周 / 两年 都在），句式从四段式变成口语。

### 闸 1：这是不是身份质疑？

出现「你是 AI / bot / 机器人 / 自动回复吗」「这语感怪」「这文案是人写的吗」类内容 → **默认不回**。

1. 回「是」直接违反红线（文案不得出现 AI 托管 / bot / 自动互动措辞）
2. 回「不是」等于主动把「这是不是自动化账号」拉到台面，风险远大于收益
3. 记一笔留痕即可

**唯一例外**：Frank 明确要正面表态，或该质疑正在扩散（views 明显上涨 / 有人跟着讨论 / 影响合作方观感）。那时交 Frank 定口径，不要自己发挥。

> 注意区分：「技术观点上值得反驳的分歧」该回；「你是不是 AI」是身份质疑，不是分歧。分不清时问自己：回完这句，我是显得更有洞察，还是在给围观群众提供谈资？后者就别回。

### 闸 2：我的最强反驳，是不是自己近 24h 已经讲过两遍以上的同一内核？

对方有内容、但我的回应没有增量 —— 在公开面把刚讲过的话换个包装再讲一遍，读起来不是交锋，是刷存在感。

- **是** → 不发。把 post_id 记进 `state/seen-posts.json`，`context: SKIPPED_NO_REPLY` + `note` 写明理由，避免每轮从零重估
- **不是** → 该回就回。**不要拿「线程收尾」「频率控制」当不思考的借口**

**何时重新考虑**：对方把点展开成具体案例、反问、或给出反例 —— 那才是能产生新交锋的输入。

## 技术要点（mcp_browser）

### 发送路径（唯一稳定方式）

1. **`fill` + `Cmd+Enter`（Meta+Enter）是唯一稳定真发路径**。Post button click 不可靠
2. `fill` 一次性填入完整正文（比逐字 type 可靠）
3. 填完后 **wait 8-10 秒**，不需要更久
4. **真发验证的唯一判据**：search 拿到 own_post 的 post_id 和 URL

> ⚠️ **不要盲 retry**。Cmd+Enter 第一次实际真发的概率很高；第二次会触发 X 的反重复拦截（「Whoops! You already said that.」），那就是真实的 spam 信号。
> ⚠️ **Cmd+Enter 后不要查 profile / with_replies / home feed 判断真发** —— 这几个地方有各自的缓存与个性化排序延迟（实测 8-30s 内不会刷新到顶部），读了会误判成失败。

### 真发验证路径（一条 walkway）

1. Cmd+Enter + wait 5s
2. **不要检查** profile / with_replies / home feed top 几条
3. 直接 navigate：
   `https://x.com/search?q=from:<handle>+<unique-keyword>&src=typed_query&f=live`
   - unique keyword = 自己帖里最 distinctive 的词（不要用源帖已占用的词）
4. 检查 search 结果第一篇是不是 own_post，取 `a[href*='/<handle>/status/']` 拿 post_id

> X live search **只能用 1 个引号短语或最多 2 词**，三词以上一律 0 结果。

### 测量方法（踩坑两次，必须遵守）

- **likes 必须用 `query kind=dom` 打 `[data-testid='like']` 或 `[data-testid='unlike']` 读 aria-label**
  （格式 `aria-label="N Likes. Like"` / `"N Likes. Liked"`）
- **X 详情页底部的大数字是 VIEWS 不是 likes**，两者差一个数量级
- `query kind=text` 读到的是 views，不要当 likes 用
- **不要用 likes 做跨帖对比**（样本量不够）。要用就用 views 并按时长归一化
- replies 数用 `[data-testid='reply']` 的 aria-label 读（`"0 Replies. Reply"`），不要靠文本抽取里那个孤立的数字猜

> ⚠️ **页面级 selector 只返回首个匹配**。detail 页一个会话里有多条帖（root / 别人 / 自己 / 目标）时，每条都有自己的 like 按钮，首个匹配可能跟目标完全无关。
> **正确做法**：先把目标帖滚进视口，看**它自己那条 action bar** 的视觉证据（红心实心 + 计数），或用能唯一定位的 scoped selector。
> **绝不用整页 `[data-testid='like']` 首个匹配当判据。**
> 例外：线程页 `[data-testid='unlike']` 只返回根帖 —— 赞一条 reply 必须走干净的详情页 URL。

### 浏览器故障判据

- `navigate` 后若 `query` 返回的 URL **不是目标 URL** → 页面还没加载完，`wait` 再查
- `navigate` 超时（`BROWSER_OPERATION_TIMEOUT`）后 `query` 看 URL：
  - URL = 目标 → 页面在加载，再 wait
  - **URL = 原样没变 → 导航层已死**，页面根本没跳转。**别再对同一 URL 重试** —— 一次 `query` 看 URL，没变就立刻按「浏览器不可用」兜底写零动作收工，别把十几次调用烧在一条死掉的 tab 上
- `reload` 报 `browser_action_failed` / `SKILL_REQUIRED` → 机器休眠后 mcp_browser 整体失效，**重载 skill 修不好**，直接兜底
- 机器一醒即自愈（下一轮首条 navigate 通常就成功）

## 状态文件

| 动作 | 落盘 |
|------|------|
| outbound reply / like | `state/seen-posts.json`（`treatment=reply_riding_traffic` / `like_only`）+ `state/index.json` |
| inbound reply | `state/inbound-replies.json` + `state/seen-posts.json`（`treatment=inbound_replied`）+ `state/index.json` |
| 原创 post | `state/published-posts.json`（**pulse 不发**） |

### `state/index.json`（去重索引）

去重查询**只读索引**，不要全量加载 `state/seen-posts.json`（148KB / 284 条，每轮全量读全是纯浪费）：

```json
{
  "seen":       { "<post_id>": { "treatment": "...", "ts": "..." } },
  "inbound":    { "<post_id>": { "reply_id": "...", "ts": "..." } },
  "published":  { "<post_id>": { "url": "...", "ts": "..." } }
}
```

每次写 `state/seen-posts.json` / `inbound-replies.json` / `published-posts.json` 后，**同步更新索引**。

## 失败 / 限流

- **「We've temporarily limited your login」** → 立即停手，memory 写「本轮停手，触发 login 限流」
- **2FA / 验证码** → 立即停手，memory 写「触发 2FA，Fang 处理」
- **单轮 candidate = 0** → memory 老实写「0 候选，本轮零动作」，**不装忙**
- **mcp_browser 不可用** → memory 老实写「浏览器不可用，本轮零动作」，等下次

## memory + status 输出

轮次记录追加到 `state/memory/pulse.md`：

```
<!-- round -->
### pulse_round_N (YYYY-MM-DD HH:MM–HH:MM +08:00) — 一句话结论

- 模式：MiniMax Code session / 浏览器不可用
- inbound_replied_count / outbound reply_count / like_count（写明是否触达 ≤3 上限）
- 已发 X URL 列表
- 跳过的（公司名 / ban / cooldown / 线程已收尾 / 重复已赞 / SKIPPED_NO_REPLY）
- 异常（限流 / 浏览器卡顿 / mcp_browser 不可用）
- 新经验（可选）
```

> ⚠️ **每个新轮次段前面必须有一行 `<!-- round -->`**（这是段边界标记）。
> 不要靠标题猜边界 —— 轮次段内部的小节标题经常含 "pulse round" 这类关键词，
> 按标题切会把一轮切成碎片，agent 读到的是半截记录。
>
> 读历史轮次用：`python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 3`

## 相关文件

- `state/index.json` — **去重索引，每轮先查这个**
- `state/seen-posts.json` — outbound 已处理帖 ID 全量记录
- `state/recent-picks.json` — 7 天 topic signature dedup
- `state/inbound-replies.json` — inbound 已回 reply 记录
- `state/style-x.yaml` — 口语爆款风 style
- `state/watchlist.yaml` — X 账号名单
- `state/forbidden.yaml` — 硬红线
- `private/account-safety.yaml` — 登录态 + XHS ban 状态
- `state/memory/pulse.md` — 轮次进度（本 skill 的日志）
- `state/memory/chuangzuo.md` — 创作 pipeline 轮次进度（只读，用于对账）
- `state/memory/super-bot.md` — 日报记录（只读）

## 开工前对账

开工先查 **state 末条 vs memory 末条是否对得上**，对不上先补账再跑新动作。

> ⚠️ **「建议下一轮零动作」不能当成跳过扫描的理由。**
> 间隔 **< 10 分钟** → 可以连扫都不扫（纯烧配额）。
> 间隔 **> 10 分钟** → **真扫一次再下结论**。成本 3 次调用，换一个有证据的结论。
> 「扫过、确认 0 候选」vs「没扫、假定 0 候选」——报告里长得一模一样，但只有一个能拿去做决策依据。

## 决策记录

- **2026-10-16（Frank）**：启用 inbound reply 模式（「别人的和我们的互动也需要去回复和回应，这样才有人」）；inbound 文案 80-180 字；inbound 优先于 outbound
- **2026-10-21（Frank）**：「你和大家互动的频率不要那么高！！！」→ 30min 降到 2h，动作上限 8 砍到 3
- **2026-10-25**：cron 降到 4 轮/天（4,10,16,22）；去重改走 `state/index.json`；铁律从 cron prompt 下沉到本 skill
