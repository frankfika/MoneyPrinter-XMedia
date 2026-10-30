# pulse_round_56 — 20:00 降频后第二个有动作的轮次

时间：2026-10-21 20:00 → 20:09 (+0800)
频率基线：pulse cron `0 */2 * * *`，单轮上限 3 动作（reply ≤1 / like ≤2 / 原创 0 / quote RT 0）
本轮实际动作：**2**（1 reply + 1 like），未超上限。

---

## 1. 补账：outbound-129（上一轮真发但未落盘）

- 动作：回复 `@divyasan0`
- 目标帖：`2112650190536798243`
- 自己帖：`2112786747784565019` → https://x.com/FrankFika/status/2112786747784565019
- 时间：13:58 真发，20:00 核实并回填
- 核实方式：X live search `from:FrankFika 腐烂`，确认在 X 上（当时 5h 前）
- 源帖：8h / 1.7K views，*The Most Common Questions About Agent Evals, Answered*
- 角度（166 字）：同意「从真实 trace 建小数据集」，但真正花时间的是数据集建完之后开始腐烂 —— 几十张客户模板一季度改 80 多处，没人回去标哪些 case 已过期。「eval 跑得再准，测的是三个月前的系统。」

## 2. 新动作：outbound-130 like @dyiapanis

- 目标帖：`2112744768791048417`（https://x.com/dyiapanis/status/2112744768791048417）
- 帖文：11:16 AM · Oct 21 · 21 views · 2 likes
- 内容：memory 不是 document store —— 记忆会淡出，没有「永久记住」的显式机制；想留永久记录就拍照/录音，那属于 RAG（obsidian / meeting notes 那一类），是互补的另一套机制。预告会发一个本地多模态 RAG store 来配 Limbic。
- 选中理由：直接接在 FrankFika 9h 那条追问（"你那些文件最后是谁判断它过期了"）后面，是同一条 agent memory 主线的延续，不是随机撒 like。
- 动作：`press_key 'l'`（detail page，无修饰键）
- 验证：视觉证据 = 红心实心 + 计数 2；state 内无此 post_id 历史记录 → 判定 1→2 真发

---

## 3. 本轮踩到的判定坑（重要，写进规则）

**`query kind=dom` 只返回文档中的第一个匹配，不是目标元素。**

本次 detail 页上有多条帖：
1. @dyiapanis 13h 根帖 — 5 likes（页面 DOM 里排第一）
2. @softpoo 11h — 3 likes（已赞，历史轮次点的）
3. @FrankFika 11h / 9h
4. @dyiapanis 11:16AM — **本轮目标帖**

我用 `query [data-testid='like'],[data-testid='unlike']` 查状态，**读到的永远是 #1 根帖的 "5 Likes. Like"**，跟目标帖无关。于是按了 `l` 之后我又查一次，同样读到 "5 Likes. Like"，一度误判成"没生效"。

真相：`l` 生效了，目标是 #4。DOM 查询在这里根本没有判据能力。

**新规则：detail 页点赞验证必须落到目标帖本身的元素/视觉证据，不能用页面级 selector。**
可用做法：
- 滚到底让目标帖进视口，看它自己的 action bar（红心实心 + 计数）；
- 或用能唯一定位的 selector / scoped ref；
- 不要用整页 `[data-testid='like']` 的首个匹配当判据。

顺带发现一处**历史账目不一致**（未处理，留待 Frank 决定）：
- outbound-122 记录赞过 dyiap 线程根帖 0→1
- outbound-128 note 写的是"本轮是 thread 内 47 likes 那条"，赞的是 `2112680392763301913`
- 但现在页面显示 13h 根帖是 "5 Likes. Like"（未赞）

根帖到底赞没赞过，账上说不清。不建议为了对齐账目去补赞/取消赞。

---

## 4. 落盘

| 文件 | 变化 |
|---|---|
| `state/outbound-actions.json` | 122 → **123**（新增 outbound-130；outbound-129 于本轮补齐） |
| `state/seen-posts.json` | 281 → **282** |
| `state/inbound-replies.json` | 37（无变化） |
| `state/published-posts.json` | 118（无变化，原创线未动） |
| `private/account-safety.yaml` | `last_outbound_like_at` 12:43 → **20:07**；旧 like 字段降级为 `*_v2_*` 保留 |

冷却时间戳（本轮后）：
- `last_outbound_reply_at` 13:58
- `last_outbound_like_at` 20:07
- `last_inbound_reply_at` 10:20
- `last_published_at` 09:47（chuangzuo_round_78）

## 5. 频率自律

Frank 明确要求「互动频率不要那么高」。本轮 20:00 触发，上一轮有动作是 13:58，间隔 6h。
下一次 pulse 排定 22:00。**除非 inbound 里有真实的@ 或直接反驳，否则 22:00 轮大概率仍是零动作。**