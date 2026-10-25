# pulse_round_57 — 零动作

时间：2026-10-21 22:00–22:08 (+0800)
模式：MiniMax Code session，mcp_browser 可用，**真扫了 notifications**
动作数：**0**（上限 3，未触达）
距离上一次真实动作（outbound-130 like @20:07）：**2 小时**

---

## 1. 开工对账：通过

| 位置 | 末条 |
|---|---|
| `state/outbound-actions.json` | outbound-130 · 2026-10-21T20:07 · like @dyiapanis |
| pulse `memory.md` | `## 🔴 pulse_round_56` 记录同一条 |
| `account-safety.yaml` | `last_outbound_like_at: 20:07` |

三处一致，**无需补账**。

## 2. Frank 手动发帖检查：不触发降载

`/FrankFika/with_replies` 顶部最新一条是 outbound-129 的回复（7h 前）。
Frank 自己 2 小时内没发过帖 → 不需要额外降载到 1 个动作。

## 3. Notifications 真扫结果（最近 12h）

| 时间 | 内容 | 判定 |
|---|---|---|
| 1h | `Product Hunt 😸` liked your reply | 纯赞，无需回应 |
| 3h | 「没有报备，出了问题你去处理么？幼稚，为了黑而黑」 | **不是回复我们**（Mentions 里没有 Mahdi），是 liked-post 的会话上下文预览 → 无动作义务 |
| 5h | `Mahdi` followed you（上下文是我们那条 eval 回复） | 关系信号，无动作 |
| 5h | `marilys alcantara` / `Lamarcus Milton` followed you | 关系信号，无动作 |
| 8h | `Ryu` added you to their List | 关系信号，无动作 |
| 9h | `Truth Only` liked your reply | 纯赞 |
| 10h | `Neko Legends` liked your reply（memory 那条） | 纯赞 |
| 10h | `Demetri` followed you | 关系信号，无动作 |
| 10h | `Demetri` 回复我们（memory vs document store） | **20:07 已处理** = outbound-130 |
| 11h | `AetrixEmby` 回复我们 | 纯肯定层 → 按规则不接话 |
| 12h | `Demetri` liked your reply | 纯赞 |
| 12h–22h | `AetrixEmby` 连发 5 条回复 | 全是纯肯定 |

## 4. 为什么零动作（逐条对规则）

### inbound reply = 0
- **2 小时内零新 @ / 零新直接回复**。Mentions 标签页最新一条是 10h 前的 Demetri，已在 20:07 处理。
- AetrixEmby 在 11h–22h 之间连发 6 条，内容全是纯肯定：「这点太关键了」「签字这招妙啊」「省的不只是几天」
  「口径生效日期这条戳中了」「这招狠」「这坑太熟了」。
  命中既有铁律：**长线程到「纯肯定」层就收尾，不开新层**。再回一条只会把 20+ 楼的附和链拉得更长。
- Mahdi 那条看着像挑衅，但经 Mentions 核对**不是发给我们的回复**，没有回应义务。

### outbound reply = 0
- 没有值得接的候选：没有新的高优 handle 发言，没有需要反驳的观点。
- Frank 的既定策略是「宁可 1 条尖锐反驳，不要 3 条附和」——没有实质分歧可反驳，就不发。

### outbound like = 0
- 20:07 刚赞过 dyiap 同一条线程（`2112744768791048417`），距今 2 小时。
- 继续在同一条线程加 like 是自我重复，且直接违反 Frank「互动频率不要那么高」的要求。

## 5. 落盘

**state 全部无变化**：
- `state/outbound-actions.json` 123
- `state/seen-posts.json` 282
- `state/inbound-replies.json` 37
- `state/published-posts.json` 118

冷却时间戳全部保持不动：
- `last_outbound_reply_at` 13:58
- `last_outbound_like_at` 20:07
- `last_inbound_reply_at` 10:20
- `last_published_at` 09:47

## 6. 新经验

**Notifications 页的 text 抽取会把「时间 / 上下文预览 / actor / 动词」拆成不对应的行序。**
本轮「3h 没有报备…幼稚，为了黑而黑 / Mahdi liked 2 of your posts」一度被读成
「Mahdi 在 3h 前发了一条敌意回复找茬」。切到 `/notifications/mentions` 核对后确认：
**Mahdi 根本不在 Mentions 里**，那条是他自己发的帖（作为 liked-post 的会话上下文被带出来），
不是回复我们。

**规则**：通知里任何看起来像「敌意回复 / 质疑 / 找茬」的中文短句，
在决定要不要回之前，**必须去 Mentions 标签页确认它到底是不是发给 @FrankFika 的**。
否则会对着一个根本没点名我们的人开火。
