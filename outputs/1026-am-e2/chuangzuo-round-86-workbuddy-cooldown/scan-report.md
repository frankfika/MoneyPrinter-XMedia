# chuangzuo round_86 · WorkBuddy automation 触发 · 2026-10-26 00:37–00:55 +08:00

**结论：本轮零发送（未发），完整原因见 §3。未凑数、未用 AI 图占位。**

---

## 1. 模式检测（第一步）

| 检测项 | 结果 |
|---|---|
| `mcp__cua_repl__js` | ❌ 不存在（ToolSearch 精确检索无此工具） |
| `mcp_browser`（README 现行唯一要求） | ❌ 不存在 |
| Playwright / CDP 本机登录态 | ❌ 无 |
| 结论 | **浏览器链路不可用** → README「没有 → 老实写「浏览器不可用，本轮零动作」」 |

本 host 是 **WorkBuddy automation sandbox**，不是 Codex / MiniMax session。
用户 prompt 里「2026-10-15 纠错：cron thread 必有 cua_repl」这条**在本 host 不成立**；
prompt 里的 cron 降级路径 `scan-slot.sh lite` 也**已在 2026-10-25 被删除**
（`state/schedule.yaml` L81-87 明确写了删除理由），所以那条路连跑都跑不了。

---

## 2. 网络层新发现（本轮唯一硬产出，可复用）

前几轮 memory 记的是「x.com 物理不可达」。**这个结论不准确，已纠正。**

| 通道 | 直连 | 经本地代理 `127.0.0.1:7897` |
|---|---|---|
| `x.com` | 000（超时） | **200** |
| `api.x.com` | 000 | 200 |
| `r.jina.ai` | 000 | 200，但**正文 401**：`blocked ... bad IP reputation`（匿名额度已废） |
| `cdn.syndication.twimg.com/tweet-result` | — | **200，可用**（单帖元数据，无需登录） |
| `syndication.twitter.com/srv/timeline-profile/*` | — | **429 Rate limit exceeded**（出口 IP 被限） |
| `1.1/statuses/user_timeline.json`（guest token） | — | guest token 申请成功，接口 **404 code 34**（v1.1 已下线） |

**净结论**：
- ✅ **单帖核验可做**（不需要登录、不需要浏览器）——这是本轮能验证 00:33 那条帖子的原因。
- ❌ **时间线扫描做不了**：唯一免登录入口 429，官方 API 需授权。
- 所以「0 候选」的**真实原因是扫描通道被封，不是没有热点**。这两件事不能混着写。

---

## 3. 为什么零发送（决定性，与候选数无关）

`state/schedule.yaml` 硬约束：

```yaml
chuangzuo_original_post_max: 1          # 每轮最多 1 条
chuangzuo_original_post_min_gap_hours: 12
```

**事实对账**：`private/account-safety.yaml#x.last_published_at = 2026-10-26T00:34:47+08:00`，
post `2114394951454994675`（chuangzuo_round_85，由另一个 session 真发）。
本轮开跑时间 00:37:50，**距上一条 3 分 03 秒**。

→ **12h 冷却远未满足，下一窗口 = 2026-10-26 12:34 之后。**
即便此刻有 100 个候选，本轮也只能零动作。**这是本轮零发送的第一因，优先级高于候选数。**

> 注：prompt 里写的「cooldown ≥ 30 分钟」「每轮 3 条完成版」均已过时。
> `schedule.yaml` 自己注明 30 min 只是硬地板不是目标；README（2026-10-26 00:01）写明
> 「每轮最多 1 条原创（Frank 2026-10-21 降频；早期『3 条完成版』已作废）」。
> 本轮按 **README + schedule.yaml** 执行，不按 prompt 的旧数字。

---

## 4. 唯一真实验证：round_85 那条帖子确实在线

用 syndication 匿名 API 实读（非猜测）：

```
post_id       2114394951454994675
created_at    2026-10-25T16:33:34Z  = 2026-10-26 00:33:34 +08:00
author        @FrankFika (陈放Frank🕊️, is_blue_verified)
favorite      0
replies       0
lang          zh
```

正文（节选，实读原文）：

> 自己训一个模型，绕不开一个问题：你拿什么判断它训好了。
> 我维护着一套三十多张的客户模板，一个季度改了 80 多次。改到最后我在意的已经不是"哪张模板写得好"，而是"它什么时候会失效"……

**判断**：round_85 的 `posted_url` 是真的，无「假装已发」缺口。

已把**首个 0h18m 基线样本**写入 `state/published-posts.json`（round_85 条目 `metrics_samples`），
`method` 标注为 syndication 匿名 API。这是**新测量通道**——之前所有样本都靠 DOM 视觉 + aria-label，
必须开浏览器；这条不需要。给 12h 后的 likes 闸门留了增量起点（likes 0 → 到 12:34 再看是否 ≤2）。

---

## 5. 本轮 status（prompt 要求格式）

| 项 | 值 |
|---|---|
| **candidate_count** | **0**（扫描通道 429 / 需登录，非「无热点」） |
| **完成版落盘** | **无**（0 条 material.yaml / x.txt / screenshots） |
| **已发 X URL** | **未发** —— 原因：12h 冷却未到（上一条 00:34:47，本轮 00:37:50，差 3 分钟）；叠加扫描通道不可用 |
| **XHS 状态** | ⏸️ 停手。`account-safety.yaml#xhs` 本轮未触碰；README「XHS 默认停手」维持 |
| **真图** | 无（无浏览器 → 抓不到真截图；按红线**不用 AI 图占位**） |
| **AI 生成图** | 0 张 |
| **state 变更** | published-posts.json：仅 round_85 追加 1 个 metrics 样本（加性，未改历史） |

---

## 6. 异常 / 阻塞

1. **🔴 本 automation 与 chuangzuo cron 职责重叠** —— 这是最该处理的事。
   `state/schedule.yaml` 写明 chuangzuo 由 cron `d5c0d018-…`（MiniMax session，`mcp_browser` 已登录）承担，
   12h 一轮。本 automation（`fef98705`）跑在 WorkBuddy sandbox，**没有浏览器**，
   每轮必然只能写「未发」。它每触发一次，就多一份「看起来跑了但没产出」的日志，
   而这恰好是 Frank 最反感的「装忙」。
   → **建议**：要么停掉它，要么把它降级成**只读核验器**（读 syndication 补 metrics_samples + 查轮次真空期），
   明确不承担发布职责。

2. **本轮撞车**：开跑时 chuangzuo_round_85 正在 00:30–00:40 执行并发帖。
   两条线同时写 `state/` 有并发写风险（本轮已用 tmp+`os.replace` 原子写规避）。

3. **jina 匿名额度作废**（bad IP reputation）→ 之前 memory 里记的 r.jina.ai 备用读取路径**已不可用**，别再依赖。

4. **syndication timeline 429** 是本机出口 IP 层面的限制，重试无用（连试 3 次全 429）。

---

## 7. 下次启动先看

1. **下一窗口 12:34+**，先查 `likes` 闸门：round_85 若 12h 后 likes ≤ 2 → 按 README 继续零发送（不要为产出而发）。
2. **要真扫时间线，必须在有登录态浏览器的 session 里跑**（MiniMax / Codex）。本 host 再怎么试也扫不到。
3. **等 Frank 拍板本 automation 的去留**（见 §6.1）。
4. 抽样一律走 `cdn.syndication.twimg.com/tweet-result?id=<id>`，带 `-x http://127.0.0.1:7897`，免登录。
