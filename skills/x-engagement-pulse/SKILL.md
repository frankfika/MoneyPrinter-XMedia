---
name: x-engagement-pulse
description: X 转评赞 pulse — 给 @FrankFika 主账号提活跃度。**只 LIKE + REPLY 别人的帖子,不发新帖**。每轮 inbound(回别人给我的 reply,社区建设核心)优先,outbound(主动 like+reply 高优热帖)其次。触发:每 30 min cron,或手动跑一轮。
---

# X 转评赞 Pulse

双向 engagement bot。**不发新原创长帖 / Quote RT / 新 Post**。

## 触发

- 每 30 min cron(automation: `x-engagement-pulse-30min`)
- 手动:在 Codex thread 里说「跑一轮 pulse」即可

## 硬约束(红线)

来自 `state/forbidden.yaml`,绝不踩:

- ❌ 不发新原创长帖 / Quote RT / 新 Post(只 LIKE + REPLY)
- ❌ 不出现 OpenCSG / 公司业务
- ❌ 不出现 Chinese AI 公司名(避开 dotey 那条 5-7% 蒸馏营收帖里点名的 DeepSeek / Moonshot / MiniMax 等)
- ❌ 不写 AI 托管 / 自动互动 措辞在公开文案
- ❌ 不写 AI 生成图、不堆 hashtag(≤ 1 个或不用)
- ❌ 不写「配图如下 / 见下图 / 快去看」

XHS 默认停手(`private/account-safety.yaml#xhs.ban_status.is_banned = true`)。

## 配额(每轮)

| 类型 | 上限 | 优先级 |
|------|------|--------|
| **inbound reply** | 2 | 🥇 最高(社区建设) |
| outbound like+reply | 2 | 🥈 |
| outbound like-only | 2 | 🥉 |
| like 间隔 | ≥ 2 min | hard |
| reply 间隔(inbound + outbound 合并) | ≥ 8 min | hard |

## 工作流

### Phase A:Inbound 扫描(必做第一步)

1. 打开 `https://x.com/notifications/mentions`
2. 筛 type = reply 的通知(「X replied to your post」),抓:
   - **handle**(对方)
   - **source_post_id**(他回了我的哪条帖)
   - **at**(reply 时间)
3. 已在 `state/inbound-replies.json` 的 drop(防重复回)
4. 排序:**24h 内 > 8h 内 > 旧**
5. 优先回:
   - **我原帖 ≥ 5K views 的 reply**(高曝光 thread,reply 我会跟着涨曝光)
   - **中文 KOL 的 reply**(社区活跃度)
6. inbound reply 写法(`state/style-x.yaml` 「口语爆款风」):
   - **80-180 字**(比 outbound 短,因为是接话延伸,不是自说自话)
   - 含 1 个具体延伸点 / 反问 / 数字
   - 不堆 hashtag
   - 可附自己 prior 帖(从 `state/published-posts.json` 选最相关的)
7. 完成后:
   - `state/inbound-replies.json` 末加 `{handle, source_post_id, reply_id, reply_url, at, topic}`
   - `state/seen-posts.json` 末加 `source_post_id`,`treatment=inbound_replied`

### Phase B:Outbound 扫描(其次)

1. 优先级 handle timeline(每轮至少扫 3 个):
   - **高优**:karpathy / sama / OpenAI / AnthropicAI / GoogleDeepMind / NVIDIA / dotey / oran_ge / op7418 / vista8 / akhaliq / karminski3 / FinanceYF5 / jiqizhixin
   - **兜底**:For-you / Following timeline(找「high view + low reply」)
2. 筛条件:**≥ 5K views** 或 **≥ 50 likes** 或 AI 关键词命中 + < 8h
3. 已发过的(`state/seen-posts.json`)直接 drop
4. 跳过的:
   - dotey 5-7% 蒸馏营收帖引用 simonw 主帖(带 DeepSeek/Moonshot/MiniMax)
   - Tesla 喷气式 / Roadster / SpaceX 类非 AI 帖
   - 7 天 dedup topic(从 `state/recent-picks.json` 查 `expires_at`)

### Phase C:Outbound reply 写法

80-320 字,**口语爆款风**(`state/style-x.yaml`):

- 冲击钩子开头(数字 / 反差 / 意外结果)
- 具体步骤 / 坑点 / 对比
- 一句轻收尾(不写「快去看」式安利腔)
- **含 1 个具体数字 / 链接 / 事实**
- **可附自己 prior 帖**(`state/published-posts.json` 选最相关的,放末尾让 X 自动 quote embed)
- 不堆 emoji(0~2 个)、不堆 hashtag(0~1 个)

### Phase D:技术要点(cua_repl Draft.js)

参考 `scripts/cua-full-flow.md`,关键:

1. **dialog textarea vs page composer**:进入 reply dialog 后,用 `[data-testid="tweetTextarea_0"].first()` 锁 dialog textarea,千万别 click `.last()`(会 navigate 到 /compose/post)
2. **fill() 比 paste() 更可靠**:fill(完整正文)一次性填入,1-2 秒内显示完整
3. **tweetButton click**:用 `[data-testid="tweetButton"].first().click()`,`tweetButtonInline` 是 disabled 的(AX 树里最先出现的永远是 disabled)
4. **Post click 后**:toast "Your post was sent" → 1-2 秒内 reply id 出现在 thread 顶部
5. **self-quote embed**:reply text 末尾放自己帖 URL,X 自动渲染 Quote RT card

### Phase E:收尾

回复完后:

- outbound `state/seen-posts.json` 末加 `treatment=reply_riding_traffic` 或 `like_only`
- inbound `state/inbound-replies.json` 末加(同 Phase A 第 7 步)
- `$CODEX_HOME/automations/x-engagement-pulse-30min/memory.md` 追加本轮:
  - inbound_replied_count / outbound candidate_count
  - like_count / reply_count
  - 已发 X URL 列表
  - 跳过的(公司名 / ban / cooldown / 自己帖已有 reply 链)
  - 异常(限流 / 浏览器卡顿 / 5xx)
  - Draft.js / contenteditable 新经验

## 失败 / 限流

- **'We've temporarily limited your login'** → 立即停手,memory 写「本轮停手,触发 login 限流」
- **2FA / 验证码** → 立即停手,memory 写「触发 2FA,Fang 处理」
- **单轮 candidate = 0** → memory 老实写「0 候选,本轮零动作」,**不装忙**
- **cua_repl 工具不可用** → memory 老实写「浏览器不可用,本轮零动作」,等下次

## status 输出格式

每轮结束 emit 一段:

```
[pulse round N]
- inbound_replied_count: X
- outbound_candidate_count: Y
- like_count: Z
- reply_count: W
- 已发 X URL 列表: [url1, url2, ...]
- 跳过: [...] (原因)
- 异常: [...] (限流 / 5xx / 浏览器卡顿)
- 新经验(可选): [...] (Draft.js / contenteditable)
```

## 相关文件

- `state/seen-posts.json` — outbound 已发帖 ID dedup
- `state/recent-picks.json` — 7 天 topic signature dedup
- `state/inbound-replies.json` — inbound 已回 reply 记录(本 skill 引入,首次运行建)
- `state/style-x.yaml` — 口语爆款风 style
- `state/watchlist.yaml` — 46 个 X 账号名单
- `state/forbidden.yaml` — 硬红线
- `private/account-safety.yaml` — 登录态 + XHS ban 状态
- `$CODEX_HOME/automations/x-engagement-pulse-30min/automation.toml` — cron prompt(精简版,引用本 skill)
- `$CODEX_HOME/automations/x-engagement-pulse-30min/memory.md` — 轮次进度

## 2026-10-16 决策记录

- **Fang 决策**:启用 inbound reply 模式(Fang 原话「别人的和我们的互动也需要去回复和回应,这样才有人」)
- inbound reply 文案 80-180 字(比 outbound 短,接话延伸)
- inbound 优先于 outbound(社区建设核心)
