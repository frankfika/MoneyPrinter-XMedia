# pulse_round_58 — 浏览器不可用，零动作

**关键：这不是「无事可做」，是「做不了」。而且顺带发现一个 26.7 小时没有任何 pulse 轮次完成的真空期。**

- 轮次启动时刻：2026-10-22 16:00:44 +0800（`date` 实测）
- 轮次收尾时刻：2026-10-23 00:50 +0800（`date` / `python3` / `date -u` 三方交叉验证一致）
- **单个轮次内部耗时 8h49m** —— 强烈指向机器在此期间休眠/挂起
- 动作数：**0**（上限 3，未触达）
- 上一次真实动作：outbound-130 like @dyiapanis，2026-10-21 20:07 → 距今 **28h43m**

---

## 1. 开工对账：通过，无需补账

| 位置 | 末条 |
|---|---|
| `state/outbound-actions.json` | outbound-130 · 2026-10-21T20:07 · like @dyiapanis `2112744768791048417` |
| `state/inbound-replies.json` | inbound-037 · 2026-10-21T10:20 · AetrixEmby |
| `state/published-posts.json` | chuangzuo_round_78 · 2026-10-21T09:47 · `2112722078583652781` |
| pulse `memory.md` | `pulse_round_57 (2026-10-21 22:00–22:08) — 零动作` |
| `account-safety.yaml` | `last_outbound_like_at: 2026-10-21T20:07:00+08:00` |

五处一致。**没有「真发了但没落盘」的缺口。**

## 2. 浏览器不可用 — 完整失败记录（8 次尝试，不装忙）

| # | 动作 | 结果 |
|---|---|---|
| 1 | `navigate` → `/notifications/mentions` | `SKILL_REQUIRED`（receipt 跨 18h 失效） |
| 2 | 重新 load `browser-use:control-in-app-browser` skill | 成功 |
| 3 | `navigate` → `/notifications/mentions` | `BROWSER_OPERATION_TIMEOUT` |
| 4 | `inspect` | 成功，但页面显示 **"Something went wrong. Try reloading."** + Retry 按钮 |
| 5 | `reload` | `browser_action_failed: Browser action failed in Electron main` |
| 6 | `navigate` → `/notifications` | `BROWSER_OPERATION_TIMEOUT` |
| 7 | `wait 5s` + `query main` | 成功读回，仍是 "Something went wrong. Try reloading." |
| 8 | `navigate` → `/FrankFika/with_replies` | `BROWSER_OPERATION_TIMEOUT` |
| 9 | `wait 6s` + `query main` | **URL 仍是 `/notifications`** → 导航根本没发生，不是「慢」 |
| 10 | `navigate` → `/notifications/mentions`（重载 skill 后） | `SKILL_REQUIRED` 再次失效 → 重载 skill |
| 11 | `navigate` → `/notifications/mentions` | `BROWSER_OPERATION_TIMEOUT`（第 4 次超时） |

**结论：导航能力整体失效，不是通知接口单点故障。**
三个不同 URL 全部超时，且第 9 次证明 URL 没变化、页面根本没跳转。
叠加 `Electron main` 层失败，符合「机器睡了 ~9h 后 Electron browser tab 处于失效状态」。

**因此本轮连 notifications 都没扫成，本轮零动作。** 没有猜测、没有用旧数据编动作。

## 3. ⚠️ 本轮真正的问题：26.7 小时没有任何 pulse 轮次完成

| 项 | 值 |
|---|---|
| 最后一个完成的 pulse 轮次 | `pulse_round_57`，2026-10-21 22:08 |
| 本轮实际完成时刻 | 2026-10-23 00:50 |
| **真空期** | **26h42m** |

期间**未完成**的排定轮次：
- pulse（`0 */2 * * *`）：10-22 的 00:00 / 02:00 / 04:00 / 06:00 / 08:00 / 10:00 / 12:00 / 14:00 —— **9 个**
- chuangzuo（`0 */6 * * *`）：10-22 的 04:00 / 10:00 —— **2 个**
- super-bot（`0 9 * * *`）：10-22 的 09:00 日报 —— **1 个**

**这不是 cron 配置坏了。** 用 `cron_read` 核对，三个任务全部健康：

| cron | schedule | enabled | status | next_run |
|---|---|---|---|---|
| pulse `0dbbcbb9…` | `0 */2 * * *` | ✅ true | ✅ active | 2026-10-23 02:00 |
| chuangzuo `d5c0d018…` | `0 */6 * * *` | ✅ true | ✅ active | 2026-10-23 06:00 |
| super-bot `6560e820…` | `0 9 * * *` | ✅ true | ✅ active | 2026-10-23 09:00 |

**根因判断：local runtime 期间不活跃（机器休眠 / 应用未运行）。**
本地 cron 依赖 runtime 进程存活，机器一睡，触发点无人执行，且不会补跑。
证据链：本轮 cron 在 10-22 16:00 被触发，但轮次内部时钟走了 8h49m —— 机器在 browser 调用期间挂起过。

**这对 Frank 的实际含义：这不是「跑得慢」，是「不在的时候完全不跑」。**
所以「互动频率低」在睡眠时段是自动达成的，但代价是**睡眠期间进来的 inbound 完全没人接**。

## 4. 一个被顺带发现的欠账

`chuangzuo_round_78`（2026-10-21 09:47 发布）至今 **39h**，但它的 **12h likes 闸门采样从来没做过**——
12h 窗口（10-21 21:47）正好落在真空期里，没有 chuangzuo 轮次运行。
该硬闸门（上一条原创 12h 后 likes ≤ 2 → 零发送）至今**从未被真正评估过一次**。

**下一次 chuangzuo（10-23 06:00）必须先补这个采样**，否则原创线的核心判据形同虚设。
本轮（pulse）无权代做 —— 原创线归 chuangzuo cron 独占。

## 5. 落盘

**state 全部无变化**（本轮零动作）：
- `state/outbound-actions.json` 123
- `state/seen-posts.json` 282
- `state/inbound-replies.json` 37
- `state/published-posts.json` 118

冷却时间戳全部保持不动：
- `last_outbound_reply_at` 2026-10-21 13:58
- `last_outbound_like_at` 2026-10-21 20:07
- `last_inbound_reply_at` 2026-10-21 10:20
- `last_published_at` 2026-10-21 09:47

## 6. 需要 Frank 决策的两件事

1. **要「跑得久」还是要「机器不睡时才有」** —— 如果希望 Frank 睡觉期间也能接 inbound，
   得把这条 pipeline 搬到一台常开机器上；本地 cron 在机器睡眠时**不会补跑**，这个性质改不了。
2. **原创线 12h 闸门要不要保留** —— 它至今一次都没被评估过，而最近 4 条原创的真实基线
   是 79/37/29/29 views、1/0/0/0 likes。闸门可能在保护一个已经不需要保护的东西。
