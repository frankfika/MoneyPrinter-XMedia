---
name: x-engagement-pulse
description: X 转评赞 pulse — 给 @FrankFika 主账号提活跃度。**只 LIKE + REPLY 别人的帖子，不发新帖**。每轮 inbound（回别人给我的 reply，社区建设核心）优先，outbound（主动 like+reply 高优热帖）其次。触发：cron 每 **6** 小时一轮（4,10,16,22，共 4 轮/天），或手动跑一轮。
---

# X 转评赞 Pulse

双向 engagement bot。**不发新原创长帖 / Quote RT / 新 Post**。

> 本 skill 是**自包含规程**。cron prompt 只保留本轮硬约束并指向这里；所有铁律都在本文档，不需要复制进 prompt。

## 触发

- cron：`0 4,10,16,22 * * *`（Asia/Shanghai），**4 轮/天，每 6 小时一轮**（⚠️ 不是 4 小时一轮 —— 判真空期阈值按这个算）
- 手动：在对话里说「跑一轮 pulse」

## 🔴 开工自检 · 排定档口台账（必做，不是可选项）

**本轮第一件事不是刷 X，是查上一档口有没有丢。**

本地 cron 依赖 runtime 进程存活 + 机器醒着；**合盖/休眠期间触发器不触发，唤醒后也不补跑**。

1. 读末轮时间戳（`python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 1`）+ 本线排定时刻（**每 6 小时**）。
2. **上一档口距今 > 2 × 6h = 12h → 判定「上一档口丢失」。**
   ⚠️ **末轮新 ≠ 中间没丢** —— 只看末轮时间戳会漏掉窗口中间丢掉的档口。
   ⚠️ 阈值按 **cron 表达式**算，不要按 `state/schedule.yaml` 或任何文档标签算。
3. 三种根因**别混写**：
   - `cron_read view=runs` 里**没有这一格** → 触发器压根没触发（机器睡着）
   - 有投递记录但**没轮次段** → 跑了但崩了/中断了 → **查那一轮自己的 session**：
     ```bash
     mavis session get --session-id <run 的 sessionId>
     ```
     - `status.type == "error"` + `errorCode 50113` + message 含 `firstEventTimeoutMs`
       → **provider 首包超时**（模型 300 秒没吐第一个 token）—— 触发器触发了、prompt 投递了，但整轮零输出
       （更轻的症状：`mavis session messages` 里**只有 user 消息、零 assistant 消息**）
     - 其他 error / aborted → 按那一轮自己的日志继续查
   - ⚠️ **provider 首包超时最阴**：cron 台账里那一格显示 `delivered`，看起来像「跑过了」，
     不主动 `session get` 就完全静默（2026-10-29 16:00 + 22:00 两格连续中招，末轮间隔 13h22m）
     → **可操作动作：调大 `MCODE_LLM_FIRST_EVENT_TIMEOUT_MS`（或 host 的 `firstEventTimeoutMs`）**
4. 确认丢失后：① 轮次段开头写明「上一档口 <时刻> 丢失，根因：…」；② **本轮必须做一次全量 Mentions 回溯补扫**，把空窗期积压的 inbound 接住；③ **不许把「没扫到」写成「没漏接」** —— 要么补扫证实，要么老实写「该区间数据不可用」。
5. **每轮开工做平台侧对账**（见下方「🧾 补账：Frank 自己手动发的帖」）：`from:FrankFika` 搜索首条 + snowflake 反解 → 与 `account-safety.yaml#x.last_published_at` 比对。**不一致 = Frank 自己手动发了帖**（轮次日志覆盖不到）→ 按 4 处补账。

## 硬约束（红线）

来自 `state/forbidden.yaml`，绝不踩：

- ❌ 不发新原创长帖 / Quote RT / 新 Post（只 LIKE + REPLY）
- ❌ 不出现 OpenCSG / 公司业务
- ❌ 不出现 Chinese AI 公司名（避开 dotey 那条 5-7% 蒸馏营收帖里点名的 DeepSeek / Moonshot / MiniMax 等）
- ❌ 不写 AI 托管 / 自动互动 措辞在公开文案
- ❌ 不写 AI 生成图、不堆 hashtag（≤ 1 个或不用）
- ❌ 不写「配图如下 / 见下图 / 快去看」

XHS **不在 pulse 的职责范围** —— 本 skill 只做 X 的 like + reply，任何时候都不碰小红书。
> ⚠️ 2026-10-29 修正一处**会读错人的旧引用**：这里原来写「`xhs.ban_status.is_banned = true`」，
> 但 `private/account-safety.yaml` 里**根本没有 `xhs.ban_status` 这个路径**，而且 10-29 17:07 起
> 真正的字段是 `xhs.is_banned`，**值已改为 `false`**（XHS 线自己复通、17:12 首篇已发布）。
> → **别拿这个 flag 决定 pulse 要不要动 XHS**：XHS 有自己的线（`state/memory/xhs.md`）、自己的授权口径
> （`xhs.agent_publish_allowed`）、自己的节奏（`xhs.publish_rhythm`）。
> → **pulse 对 XHS 的口径是恒定的「不碰」**，与那个 flag 无关。

## 配额（Frank 2026-10-21 降频，最高优先级，压过下面所有节奏建议）

| 类型 | 每轮上限 |
|------|---------|
| **单轮总动作** | **≤ 3**（原来 8） |
| inbound reply | ≤ 1 |
| **outbound reply** | **0** ← Frank 2026-10-27「少评论，多干发原创」 |
| outbound like | ≤ 2 |
| 原创 post | 0（chuangzuo cron 独占，pulse 不碰） |
| quote RT | 0（Frank 没要求过，不主动开） |

> **为什么 outbound reply 归零**（Frank 2026-10-27）：
> 1. 账号已经被 2 个大 V 以「AI 评价」为由拉黑 —— **公开面每多一条结构化点评，就多一次被看穿的机会**；
> 2. inbound reply（别人先找我）是社区建设核心，风险低、对方本来就在等我回 → 保留；
> 3. like 是零文字风险的动作，能维持曝光 → 保留 2 个。
>
> → **评论量从 8 条/天（4 inbound + 4 outbound）降到 4 条/天（全是 inbound），腾出来的注意力给原创。**
>
> outbound reply 能力**保留但默认不用**：只有这三种情况才做，且必须在轮次记录写明理由：
> - Frank 手动点名要回某条；
> - 该帖**直接问 @FrankFika**（不是泛问，是点名）；
> - inbound 的对话继续（对方追问 Frank 自己刚写的回复）—— 这种算 inbound reply，不算 outbound。

- 候选不足就少做，**不要凑数**
- 如果 Frank 自己在 2 小时内发过帖（查 `/FrankFika/with_replies` 顶部）→ **本轮主动降载到 1 个动作或零动作**
- like 间隔 ≥ 2 min、reply 间隔（inbound + outbound 合并）≥ 8 min

> ⚠️ **这两条间隔必须有显式的等待动作，不能靠「中间顺手做别的事」**（2026-10-27 round_77 实测踩到）。
> 浏览器调用**很快**：一次 search / query / dom 只有 1–8 秒，插 7 次也凑不出 2 分钟
> —— round_77 两次 like 的真实间隔只有 **1m41s**，低于 2 min 线。
> → **做法：两次 like 之间显式 `wait` ≥120 秒**（browser `wait` 单次上限 60s → 连续两次 60s）；
> reply 间隔 ≥8min 同理需要连续 `wait`（60×8）或直接跳过本轮该动作。
> → **别的调用只消耗 token，不消耗时间预算。** 间隔是墙上时钟，不是调用次数。

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

> ⚠️ **决定不回的也要留痕**（2026-10-29 pulse_round_82 实测）：@mumblinglewis Oct 26 那条
> 「鉴定训练失败，100%AI味」（闸 1 身份质疑）**扫到过但从没进过台账** → 每轮都要重新评估同一批旧帖，
> 而其中恰恰是最该回绝的那条。
> → **不回的写 `seen-posts`（`treatment=skipped_no_reply`）+ `index.json#seen`（`t=skip`）**，
> 让「0 候选」这个结论有台账支撑，而不是只活在轮次日志里。
>
> ⚠️ **`index.json` 两段语义不同**：`#seen` = 「这条帖我们处理过（回过/赞过/跳过）」；
> **`#outbound` = 「账号对这条帖出过手」**。→ **skip 类记录只进 `#seen`，不进 `#outbound`**（没出手就不该进动作账）。
> 写后校验时别一刀切要求「`seen` 和 `outbound` 同时存在」，否则 skip 条目会被误判成「写入失败」。

> ⚠️ **通知页文本抽取行序错位**：notifications 的 text 抽取会把「时间 / 上下文预览 / actor / 动词」拆成不对应的行序。中文短句尤其容易被误读成一条「发言」。
> **看到像敌意回复 / 质疑 / 找茬的中文短句，决定回不回之前，必须去 `https://x.com/notifications/mentions` 确认它到底是不是发给 @FrankFika 的。** 唯一可信判据是 Mentions 页出现该 handle + `Replying to @FrankFika`。
> 看到「liked / followed」类动词却配着一段攻击性文字 → 大概率是上下文预览串位，不是回复。

### Phase B：Outbound 扫描（其次）

1. 优先级 handle timeline（每轮至少扫 3 个）：
   - **高优**：karpathy / sama / OpenAI / AnthropicAI / GoogleDeepMind / NVIDIA / dotey / oran_ge / op7418 / vista8 / akhaliq / karminski3 / FinanceYF5 / jiqizhixin
   - **兜底**：For-you / Following timeline（找「high view + low reply」）
2. 筛条件：**≥ 5K views** 或 **≥ 50 likes** 或 AI 关键词命中 + < 8h
   > ⭐ **「发了多久」和「起来了没有」是两个独立维度，早赞优先（round_78 首提，round_80 再验）**
   >
   > 同一个赞名额，赞**发得晚但赞数还小**的帖，Frank 的 handle 出现在赞列表最前段（几十人的列表里排第 5–6）；
   > 赞**发得久、赞数已经很大**的帖，Frank 就是几百人列表里的第 501 位，等于没赞。
   >
   > → **筛选时优先「< 2h 且赞数 < 20」这类刚起来还没起来的帖**，而不是「5K views / 50+ likes」的大盘帖。
   > → 「≥50 likes」这道质量线**对刚发的帖子不适用**（它刚发 1 小时当然只有 5 个赞）——
   > 刚发内容的正确入口是第三条「AI 关键词命中 + < 8h」，再用「赞列表现在多小」二次排序。
   > → 实测对照（round_80 同轮两个赞）：@dotey 发 1h34m / 5 赞 → 列表 6 人，Frank 排最前；
   >   @bindureddy 发 1h44m / 135 赞 → 列表中盘。同样一个名额，曝光效率差一个量级。
   >
   > ⭐⭐ **最强信号是「赞前 likes = 0」—— 可直接 DOM 实测**（round_86 实测）
   >   两条候选赞前 `aria-label="0 Likes. Like"` → 赞完 Frank 就是 **liked-by 第 1 位**。
   >   → 筛选时**优先「赞前 0 赞」的根帖**，比「<2h 且 <20 赞」的目测准，且判据现成可自动化：
   >   详情页 `query kind=dom` 打 `button[data-testid='like']` 读 aria-label 就能拿到。
   >   → 反例：赞前 55/66/67 赞的帖（@bindureddy / @swyx / @dotey Tibo），Frank 排第 56–68 位 → 一律不赞。
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

**角度选择的安全做法：拿对方自己给的数字做算术**

对方给了几个数、唯独没给某个比值 / 占比 / 分母 —— 那就把他的数摆出来对一次。
（2026-10-27 实例：对方「每周抽 10 条、一个月攒了 60 多条规则」，没给「打架占几条」和「总样本多少」；
回应 = 60 多条规则 vs 每月四十多条样本 → 规则跑在样本前面 + 追问那个没给的读数。）

三个好处：① 天然不撞 Frank 已讲过的内核（闸 0 第 5 条）② 写不出 AI 那套四段式结构
（引述 → 转折 → 升华）③ 真人接话本来就这样 —— 抓对方话里的数。

⚠️ **写之前仍要跟 `state/published-posts.json` 近 7 天逐条对表**，不能凭感觉：
2026-10-27 实测，Frank 10-21 那条「数据集建完之后它就开始腐烂 / eval 跑得再准，测的是三个月前的系统」
跟「尺子只认得它见过的那批输出」几乎是同一个内核 → 那版直接弃掉，改走算术方向才过闸。

## 技术要点（`scripts/browser/xb.py`）

> 本 skill 里所有浏览器动作都通过仓库内 CLI 执行，**唯一形态**：
> `python3 scripts/browser/xb.py --action '{"action":"...","input":{...}}'`
> action 集合、退出码（0 成功 / 1 action 失败 / 2 浏览器不可用）、selector 写法见 `skills/browser-use-utils/SKILL.md`。

> ### ⚠️ 2026-10-31 起：唯一链路 = xb.py（专用 Chrome，CDP 9222，DOM 无视觉）
>
> | 链路 | 状态 |
> |---|---|
> | `scripts/browser/xb.py`（专用 Chrome，profile `~/.shortbot-browser-profile`，launchd `com.fangchen.shortbot.browser` 保活） | ✅ 唯一通道。登录态 = Fang 在 9222 窗口一次性登录 X |
> | Codex 内置浏览器（cua_repl）/ Computer Use AX | ⛔ 已废止（组织策略禁用 / 视觉通道） |
>
> 前置自检：`python3 scripts/browser/xb.py --action '{"action":"login_state"}'`。
> 未登录 → **本轮零动作**，如实记录「专用 Chrome 未登录，需 Fang 在 9222 窗口登录」，不撞登录墙。
>
> xb.py 侧的坑：
> - 组合 OR 搜索一次扫多个高优 handle：`search?q=(from:a OR from:b OR from:c)`（省一半调用）；
>   但 live search 的引号短语 `from:x "短语"` 实测 **0 结果**，别指望。
> - 发送组合键 `press {"key":"Meta+Enter"}`（**字符串 key**，`modifiers` 字段不读）。
> - 真发验证仍用 `conversation_id:` 算子（`from:` 索引会漏自己刚发的新帖）。
> - likes 用 `query kind=dom` 打 `[data-testid='like']` / `[data-testid='unlike']` 读 aria-label，
>   必须走**干净详情页**（线程页首个匹配可能跟目标无关）。
> - 配额节奏别看钟表估：**post_id 是 snowflake，反解时间戳能拿到精确到秒的发帖时刻**
>   （`ts = ((id >> 22) + 1288834974657) / 1000`），用它核「reply 间隔 ≥ 8min」。
>
> ### 🧭 操作补充（pulse_round_74 实测）
>
> - **换页面**：`navigate` 到目标 URL 即可；需要保留当前页时用 `open_tab`（会切换活动页，注意别在旧页上动作）。
>   开完 tab 就别再回读（每开一个都是一次上下文消耗）。
> - **要拿到「根帖」的 post_id（它在搜索页排第 3/4 位，DOM 首匹配拿不到）**：
>   打开该 thread 里任意一条回复的**详情页** → `query kind=dom` 打 `a[href*='<handle>/status/']`，
>   **首匹配就是祖先链最上层的根帖**（比翻页滚动便宜得多，2026-10-27 实测省掉一整轮滚动）。
> - **要精确锁定某一条帖：用「handle + 关键词」缩窄搜索**：`from:vista8 Hallmark` ——
>   关键词只命中一条时，DOM 首匹配就是它，省掉分辨「哪张卡片是哪条帖」的 token。
> - **🔴 缩窄搜索的关键词必须用 ASCII**：中文词会整页报 `Something went wrong. Try reloading.`
>   （**不是 0 结果，是错误页**）—— 2026-10-28 实测 `q=from:AI_Jasonyu 小鱼` 直接报错，
>   换成 `q=from:AI_Jasonyu PPT` 秒出。中文帖的 distinctive token 通常是**产品名 / 英文词**（PPT / Claude / MCP / Sora），
>   不是中文短语。
> - **`query kind=dom` 的 selector 列表也只回首个匹配**（2026-10-28 实测：
>   `a[href*='/X/status/'], button[aria-label*='Likes']` 仍只回 1 个元素）
>   → **一条 selector 拿不到多个元素**，取 post_id 只能靠「窄化搜索 + DOM 首匹配」这一招。
> - **同一条 thread 里选 like 目标时优先挑「根帖」**：根帖详情页只有一条 `[data-testid='like']`，
>   回复帖详情页的首个 like 按钮会落到祖先帖上（下面「页面级 selector 只返回首个匹配」那条坑）。

### 发送路径（唯一稳定方式）

1. **`fill` + `Cmd+Enter`（Meta+Enter）是唯一稳定真发路径**（CLI：`fill` 填正文 → `press {"key":"Meta+Enter"}`）。Post button click 不可靠
   > 🐛 **xb.py 的 `press` 只认字符串 key**。传 `{"key":"Enter","modifiers":["Meta"]}` 时 `modifiers` 字段根本不读，变成普通 Enter，发不出去且没有报错。
2. `fill` 一次性填入完整正文（比逐字 type 可靠）
3. 填完后 **wait 8-10 秒**，不需要更久
4. **真发验证的唯一判据**：search 拿到 own_post 的 post_id 和 URL

> ⚠️ **不要盲 retry**。Cmd+Enter 第一次实际真发的概率很高；第二次会触发 X 的反重复拦截（「Whoops! You already said that.」），那就是真实的 spam 信号。
> ⚠️ **Cmd+Enter 后不要查 profile / with_replies / home feed 判断真发** —— 这几个地方有各自的缓存与个性化排序延迟（实测 8-30s 内不会刷新到顶部），读了会误判成失败。
> ⚠️ **确认「确实没发出去」之后可以重发一次**，但必须：① 用**逐字相同**的正文（sha256 对齐闸门 receipt），让 X 的重复防护兜底 —— 真发过就会被「Whoops! You already said that.」拦下，不会产生重复帖；② 重发后必须再验一次「只有 1 条」，确认没造出重复。

### 🛑 点击动作前必看：活动 tab 会漂移（2026-10-28 pulse_round_79 实测，踩过并撤销）

**规则**：`open_tab` **会切换活动 tab**。读完 A 帖详情页后再开一个 B 搜索页，A 就不再是活动 tab 了 —— 而 `click` 用的是**活动 tab** 上的首个匹配元素。

**pulse_round_79 的实测事故**：
1. 在 @emollick 详情页读到了 like 按钮（122 Likes）；
2. 又开了 3 个搜索 tab 找第二个候选（活动 tab 最后停在搜索结果页）；
3. 直接 `click button[data-testid='like']` → **点到了搜索页第一张卡片**（@xiaohu 那条，97→98），不是 @emollick；
4. 点完查 `button[data-testid='unlike']` → **返回的 URL 是搜索页、不是目标详情页** → 立刻判定打错；
5. 点 `unlike` 撤销 → 回查 `97 Likes. Like`（未赞态）→ 净零；
6. 复核 `https://x.com/FrankFika/likes`（跳 `/i/history/likes`）顶部只有本轮该赞的 2 条、**没有误赞那条** → 确认干净。

**正确做法（三步连做，中间不许插任何调用）**：
```
open_tab(目标帖详情页 URL)  →  click(selector)  →  query(kind=dom) 验
```
- **验证必须同时看 URL**，不能只看按钮状态 —— `unlike` 存在只说明「某个帖被赞了」，**URL 对不上就是赞错对象**。
- 「干净详情页 + 首个匹配 = 根帖」这条前提**只在页面确实是那条帖的详情页时成立**；在搜索结果页上，首个 `button[data-testid='like']` 属于**第一张卡片**。
- 需要在多个候选之间切换时：每个候选各自「开详情页 → 立刻点 → 立刻验」，或者先把所有 post_id 收集齐，最后再逐个走「开 → 点 → 验」。
- **收尾自查**：一轮 like 做完，用 `https://x.com/FrankFika/likes` 看一眼历史列表顶部 —— 一屏确认「赞了哪些、有没有多余的」。

### 真发验证路径（一条 walkway）

1. Cmd+Enter + wait 5s
2. **不要检查** profile / with_replies / home feed top 几条
3. 直接 navigate：
   `https://x.com/search?q=from:<handle>+<unique-keyword>&src=typed_query&f=live`
   - unique keyword = 自己帖里最 distinctive 的词（不要用源帖已占用的词）
4. 检查 search 结果第一篇是不是 own_post，取 `a[href*='/<handle>/status/']` 拿 post_id

> X live search **只能用 1 个引号短语或最多 2 词**，三词以上一律 0 结果。
>
> ⚠️ **2026-10-27 实测：`conversation_id:` 对「回复帖的 post_id」不一定有索引** ——
> 搜 `conversation_id:<一条回复帖的 id>` 返回「No results」，但那条帖、以及我在它下面的回复都真实存在。
> → **别把「No results」当成没发出去的证据**。改成**两路交叉**才算数：
> ① 目标帖详情页的 thread DOM 出现「@FrankFika · Ns」+ 正文逐字对上；
> ② `from:FrankFika` 搜索页取**首条** post_id（列表按新到旧，首条 = 刚发的那条）。
> 两路都命中 = 真发；两路都空 = 才允许按下面的重发规则重试一次。

### 判定「没发出去」的探针（比 `from:` 索引可靠）

`from:` 索引**会漏**：实测 `from:FrankFika since:2026-10-21 until:2026-10-24` 会漏掉已确认发过的 Oct 21 回复。**`conversation_id:` 算子实测是实时的**（dotey 会话里有 1 分钟前的回复在列）。

`https://x.com/search?q=conversation_id:<目标帖 post_id>&src=typed_query&f=live`

- 按时间倒序列出该会话的回复（`Replying to @xxx` + 相对时间）。**自己的 reply 若真发，会出现在对应的时间档位上**
- 反向用法：线程页回复区按「Relevant」排序 + 懒加载，自己那条 0 点赞的回复常常**不在线程 DOM 里** —— 所以线程里查不到**不等于**没发出去，必须靠 search 判据
- 查不到时的收尾顺序：① `conversation_id:` 算子 ② `from:<handle>` + 独特短语（引号包 1 个词） ③ 线程 DOM `a[href*='/<handle>/status/']` ④ 看 X 侧有无系统失败通知 / 限流横幅
- **四路都查不到 = 确认未投递**，此时才允许按上面的规则重发一次

### 测量方法（踩坑两次，必须遵守）

- **likes 用 `query kind=dom` 打 `button[data-testid='like']` / `button[data-testid='unlike']`**（两个都试，命中哪个用哪个）
  > 2026-10-28 pulse_round_76 实测（**修正 round_75 的结论**）：detail 页上 **两种形态都在**
  > - `button[data-testid='like']` —— **可用**，可直接当 `click` 的 selector 用
  > - `aria-label` —— 形态是 **`"147 Likes. Like"` / `"148 Likes. Liked"`**（**带数字前缀**，不是裸的 `"Like"`）
  > → 写死 `button[aria-label='Like']` 会匹配不到（round_75 就是因为这个写成了「`[data-testid='like']` 不存在」，
  > 其实只是它那次的 aria-label 形态不同）。**稳妥写法：`button[data-testid='like']`，或 `button[aria-label*='Likes']`。**
  - 形态：`data-testid="like"` → 点完变 `data-testid="unlike"`；`aria-label` 从 `N Likes. Like` → `N Likes. Liked`；
    `aria-pressed` false→true；class 变 `text-magenta-500`
  - **点赞数就在这个按钮里面**（`x-animated-count-visual` 内，如 `26` → `27`），不用再数文本抽取里的孤立数字
    > ⚠️ **2026-10-29 pulse_round_80 实测：X 的进出场过渡会让旧值和新值同时留在按钮 DOM 里。**
    > 实测 unlike 按钮 HTML 同时含 `135` 和 `136` 两个数字（前者是过渡中的旧值）。
    > → **判据必须读 aria-label 整串（`136 Likes. Liked`），不要从按钮 HTML 里抠孤立数字** ——
    > 抠数字会把过渡中的旧值当成当前值，赞没赞、赞了几个都判错。
  - `button[data-testid='like']` 可以直接当 `click` 的 selector 用（干净详情页、目标=根帖时首个匹配就是它），
    省掉一整轮 `inspect` 找 ref —— 一条 detail 页 490 个元素，inspect 输出大到会烧上下文
  - 点完必须再查一次 `button[data-testid='unlike']`（+ 计数 +1）才算验证通过
- **X 详情页底部的大数字是 VIEWS 不是 likes**，两者差一个数量级
- `query kind=text` 读到的是 views，不要当 likes 用
- **搜索结果卡片的数字顺序也会骗人**：3 个数时是 `replies / reposts / views`（第 3 个是 views）；
  4 个数时第 3 个才是 likes。**只有详情页 like 按钮（`button[aria-label='Like']`）里的数字是真的点赞数**
  （2026-10-27 实测：搜索页显示「7 9 2.9K」，详情页 aria-label 却是 `9 Likes` —— 差了一个数量级）
- **不要用 likes 做跨帖对比**（样本量不够）。要用就用 views 并按时长归一化
- replies 数用 `[data-testid='reply']` 的 aria-label 读（`"0 Replies. Reply"`），不要靠文本抽取里那个孤立的数字猜

> ⚠️ **页面级 selector 只返回首个匹配**。detail 页一个会话里有多条帖（root / 别人 / 自己 / 目标）时，每条都有自己的 like 按钮，首个匹配可能跟目标完全无关。
> **正确做法**：先把目标帖滚进视口，看**它自己那条 action bar** 的视觉证据（红心实心 + 计数），或用能唯一定位的 scoped selector。
> **绝不用整页 like 按钮的首个匹配当判据。**
> 例外：线程页的首个 unlike 只返回根帖 —— 赞一条 reply 必须走干净的详情页 URL。

### 动作时刻怎么测（两类动作，两类时间源）

**动作有没有自己的 id，决定用哪个时间源**：

| 动作 | 时间源 | 精度 |
|---|---|---|
| 发帖 / reply（**有 post_id**） | `ts = ((id >> 22) + 1288834974657) / 1000`（snowflake 反解） | 精确到秒 |
| **点赞（没有 post_id）** | `mavis session messages` 里那条 assistant 消息的 `timestamp`（epoch ms） | 精确到秒 |

- session message 翻页定位：`mavis session messages --session-id me --before <某条 msg_id> --limit 2`，
  一次能捞到一两条，`timestamp` 字段就是该次动作发出的时刻（不是结果返回的时刻）。
- 没有 session 工具时，退而求其次：用 bash `date` 在动作前后各打一个锚点，夹逼出区间
  （round_77 就是这么把 like#1 夹在 10:06:08–10:06:20 之间）。
- ⚠️ **别把「发帖时刻」当成「点赞时刻」** —— post_id 反解出来的是对方那篇帖什么时候发的，
  跟 Frank 什么时候点的赞毫无关系。round_77 差点用这个数去核 2 分钟间隔，结论会完全错。

### 浏览器故障判据

- `navigate` 后若 `query` 返回的 URL **不是目标 URL** → 页面还没加载完，`wait` 再查
- `navigate` 超时（exit 1）后 `query` 看 URL：
  - URL = 目标 → 页面在加载，再 wait
  - **URL = 原样没变 → 导航层已死**，页面根本没跳转。**别再对同一 URL 重试** —— 一次 `query` 看 URL，没变就立刻按「浏览器不可用」兜底写零动作收工，别把十几次调用烧在一条死掉的 tab 上
- 任意 action 返回 **exit 2**（`error.code=BROWSER_UNAVAILABLE`）→ 机器休眠后浏览器层整体失效，**重试 / 重载 skill 都修不好**，直接兜底
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

### 🔒 落盘必须并发安全（2026-10-29 pulse_round_80 实测有并发写者）

**pulse 和 chuangzuo 两条线会同时写这批 state 文件。** round_80 跑的时候 `chuangzuo_round_92`
正在写 `seen-posts.json` / `recent-picks.json` / `index.json`（04:05–04:06）。
**「DSH 那条 pulse 线 NOT_LOGGED_IN 跳过了」只能说明没有并发 pulse，不能说明整轮没有并发写者。**

落盘规则（`scripts/_round92_state_write.py` / `scripts/_round80_state_write.py` 是现成模板）：

1. **写前重新读盘** —— 不能用几轮之前读进内存的快照
2. **追加型记录**（seen / outbound-actions / recent-picks）→ 追加，不覆盖
3. **自增 id 一律内容派生** —— `outbound-like-<post_id 后 6 位>` / `pick-<post_id 后 6 位>`，
   **不要读「最后一个 id 再 +1」**（那是 read-modify-write 竞态，两个 writer 会撞同一个号）
4. **原子写**（tmp + `os.replace`）
5. **写后校验**：条目数 = 写前 + 预期新增；不满足就重试

> 撞号的后果**不报错、不丢数据**，只是去重索引里出现重复主键 → 表现为「某个候选莫名其妙被跳过」，
> 极难归因，且只在并发窗口出现。**追加型记录天然抗并发，只有自增 id 会撞。**

> 🔧 **改 `private/account-safety.yaml` 的校验口径**（round_86 实测）
> - 本机系统 python（`python3` / 3.11 / 3.12 / 3.13 / `/usr/bin/python3`）**都没有 PyYAML**；
>   仓库自带 **`.venv/bin/python`（PyYAML 6.0.3）** 可用 → 优先用它。
> - 没有 venv 时用 **macOS 自带 ruby 的 psych**：`ruby -ryaml -e "..."`（本轮就是这么验的）。
> - ⚠️ **期望值的类型必须跟 YAML 实际解析类型对齐**：`last_published_at` 无引号 → 解析成 `Time`；
>   `last_outbound_like_at` 有引号 → 解析成字符串。拿字符串去比 `Time` 会**假阳性 FAIL**，
>   本轮第一次跑就因这个假阳性触发了回滚（已修：统一转 ISO 字符串再比）。
> - 校验失败**必须从 `.bak` 回滚**，别带着半写状态往下走。

## 失败 / 限流

- **「We've temporarily limited your login」** → 立即停手，memory 写「本轮停手，触发 login 限流」
- **2FA / 验证码** → 立即停手，memory 写「触发 2FA，Fang 处理」
- **单轮 candidate = 0** → memory 老实写「0 候选，本轮零动作」，**不装忙**
- **浏览器不可用（`xb.py` exit 2 / `error.code=BROWSER_UNAVAILABLE`）** → memory 老实写「浏览器不可用，本轮零动作」，等下次

## memory + status 输出

轮次记录追加到 `state/memory/pulse.md`：

```
<!-- round -->
### pulse_round_N (YYYY-MM-DD HH:MM–HH:MM +08:00) — 一句话结论

- 模式：cron session（`scripts/browser/xb.py`）/ 浏览器不可用
- inbound_replied_count / outbound reply_count / like_count（写明是否触达 ≤3 上限）
- 已发 X URL 列表
- 跳过的（公司名 / ban / cooldown / 线程已收尾 / 重复已赞 / SKIPPED_NO_REPLY）
- 异常（限流 / 浏览器卡顿 / 浏览器不可用 exit 2）
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

### 🧾 补账：Frank 自己手动发的帖（2026-10-28 pulse_round_79 实测漏了 1 条）

**每轮开工时都要拿平台侧真实时间线对一遍 `account-safety.yaml#x.last_published_at`**：
`https://x.com/search?q=from:FrankFika&src=typed_query&f=live` → 取首条 post_id → **snowflake 反解**出精确发帖时刻。

**为什么必须做**：
- agent 轮次日志覆盖不到 **Frank 手动发的帖**（pulse_round_79 就发现 19:49 有一条 Quote @Peer_zh 的帖，任何轮次日志里都没有 —— DSH 那两轮都 `NOT_LOGGED_IN` 跳过了）；
- 而 **`last_published_at` 是 chuangzuo 的 12h 闸门输入** —— 不补的话，下一轮 chuangzuo 会按旧时间算 12h，**可能在 Frank 刚发过之后 7.5 小时就再发一条**，直接破掉「一天 2 条」的节奏；
- 也直接影响 pulse 自己的 **2h 降载判据**（Frank 2 小时内发过帖 → 本轮降载到 1 个动作或零动作）。

> 🔴 **「档口没丢」不能作为跳过平台侧对账的理由**（round_86 实测）
>
> 2026-10-31 16:00 档口：cron 台账**完全干净**（10:00 → 16:00 档口命中、窗口内无中间档口），
> 平台侧照样抓到 **2 条漏账根帖**（10:13:15 / 11:46:13，账号侧直发，不在任何 agent 轮次日志里）。
> → **漏账的来源是「账号侧直发」，与调度器健康度无关** → 平台侧对账是**每轮必做项**，不是「档口出问题时才做」。
> → 后果实测：不补账 → `last_published_at` 停在 04:54 → chuangzuo 15:30 档会在 Frank 11:46 那条之后**仅 3.7h** 就再发一条。
> → **根帖补账时 `media_count` 用详情页 DOM 核对**：`query kind=dom` 打 `[data-testid='tweetPhoto']` →
>   「Element not found」= 无图片（链接卡片不算 media）。比直接填 0 可靠。
> → **补根帖时 `last_published_at` 取「最新那条根帖」**，旧值轮转到 `_v2`（不覆盖只轮转）。

**补账要写 4 处**（缺一处下一轮还是错的）：
1. `state/published-posts.json` → 加条目（id 用 `frank_manual_<日期>-<HHMM>` 区分于轮次 id，`source.note` 写明「手动发布，非任何 agent 轮次产出」）
2. `state/index.json` → `#published` 段
3. `private/account-safety.yaml` → `x.last_published_at` / `_post_id` / `_url` / `_round` / `_treatment` / `_topic_signature`
4. `state/memory/pulse.md` → 本轮记录里写明补账原因

> ⚠️ **手动发的内容分两种，落点相反（2026-10-29 pulse_round_82 实测）**：
>
> | 手动发的形态 | 落点 | 为什么 |
> |---|---|---|
> | **根帖**（含 Quote 帖，10-28 那条就是） | 上表 4 处全写，含 `last_published_at` | Quote 帖 = 根帖，**计入 chuangzuo 的 12h 原创闸门** |
> | **reply**（10-29 21:01 那条就是） | **只写 `last_outbound_reply_*` 系列 + `seen-posts` / `outbound-actions` / `recent-picks` / `index.json#seen`**，**`last_published_at` 一个字都不动** | **reply 不计入 12h 闸门**（`skills/README.md:82`）；误写会让下一轮 chuangzuo 以为「刚发过原创」→ 硬否决，把原创线饿死（2026-10-27 修过一次的老坑） |
>
> → 动手前先看形态：**详情页正文以 `@别人` 开头 / 出现在别人帖的 thread 里 = reply**。
> → 手动 reply 也要写 `outbound-actions.json`，但标 `source: frank_manual` + `agent_generated: false`，
>   否则下一轮会把「账号自己发过的东西」当成「agent 发的」来继承节奏闸门。
> → 同时补 `recent-picks.json`（dedup）：Frank 自己表过态的话题，agent 不必再碰。

**用 snowflake 反解，别用页面上的相对时间**：`with_replies` 页对 quote RT 的排序会把手动帖排到别的帖后面去（pulse_round_79 实测：19:49 的帖在页面上排不到顶部，但 `from:FrankFika` 搜索首条就是它）。

## 决策记录

- **2026-10-16（Frank）**：启用 inbound reply 模式（「别人的和我们的互动也需要去回复和回应，这样才有人」）；inbound 文案 80-180 字；inbound 优先于 outbound
- **2026-10-21（Frank）**：「你和大家互动的频率不要那么高！！！」→ 30min 降到 2h，动作上限 8 砍到 3
- **2026-10-25**：cron 降到 4 轮/天（4,10,16,22）；去重改走 `state/index.json`；铁律从 cron prompt 下沉到本 skill
