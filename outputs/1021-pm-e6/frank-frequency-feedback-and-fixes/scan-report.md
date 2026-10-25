# Frank 2026-10-21 12:51 反馈：X 互动频率过高

> 直接原话：「另外啊，你和大家互动的频率不要那么高！！！」

## 这是第一次由 Frank 本人对频率下指令

此前所有关于发布频率的设定（reply 5–15min / like 1.5–4min / post 12–25min、
cron 30min + 1h、单轮 ≤8 动作）**全部是我自己推断的**，写进 SKILL.md 和 cron prompt。
Frank 从没确认过这些数字。

## 已执行的改动

| cron | 原频率 | 新频率 | 单轮动作上限 |
|---|---|---|---|
| engagement pulse `0dbbcbb9-ac42-456a-bd35-73f9ed960a07` | 30 min | **2h** | 8 → **3** |
| 创作 pipeline `d5c0d018-fcb4-4205-8f5e-35d41c0d1fb9` | 1h | **6h** | 3 条原创 → **1 条** |
| super-bot 日报 `6560e820-db95-4b83-91ad-4a0f7d4d3fd3` | 24h | 不变 | 只读，不发 X |

新硬上限（已写入两个 cron 的 prompt）：
- inbound reply ≤ 1
- outbound reply ≤ 1
- outbound like ≤ 2
- 原创 post 0（pulse 侧）
- quote RT 0
- 候选不足就少做，不凑数
- Frank 自己在窗口内发过帖 → 主动降载到 1 个动作或零动作

## 新增前置闸门（chuangzuo）

> 发之前先读上一条原创的实时 likes（`[data-testid='like']` 的 aria-label）。
> **如果上一条原创 12h 后 likes 仍然 ≤ 2 → 本轮零发送。**
> 不要为了「每轮要有产出」而发。

round 79 / round 80 连续两轮零发送是**正确执行**，不是偷懒。

## 这次降频和数据一致，不是空降

Frank 说「不要那么高」时，我刚好测完唯一可信的基线：

| cluster | 时长 | views | likes | replies |
|---|---|---|---|---|
| 20 | 12.5h | 79 | 1 | 3 |
| 23 | 5.5h | 37 | 0 | 0 |
| 24 | 4.5h | 29 | 0 | 0 |
| 25 | 3h | 29 | 0 | 0 |

合计 **79 views / 1 like / 3 replies**。同期互动线换来了 @dyiapianis followed you。

所以降频是双重正确的：
1. Frank 明确要求
2. 数据也指向同一处——原创线边际收益接近零，高频发只是刷屏

## 对我判断方式的修正

我之前把「原创 vs 互动」当成**流量分配的效率题**：
- 该发多少条
- 该选什么主题
- 该发在什么时段

Frank 的反馈说明我漏了一层：**频率本身对他有成本**，不只是收益高低的问题。
这个维度之前完全不在我的判据里。

以后判据必须包含「这个动作对 Frank 的打扰成本」，
不只是「这个动作能拿到多少 likes」。

## 顺带修的两个 bug

Frank 同一句话里还有一条：「你要持续修复 bug，持续优化代码哈」

本轮修的实际 bug：
- **likes / views 测量错误**（踩坑两次，已写进两个 cron 的 prompt 作为铁律）
- **round 52 账目漏记**（动作真发但 state 没落盘，12:35 已回填）

代码项目（OpenDesk / OpenCSG）那边需要 Frank 明确指一下才切得过去，
本 session 跑的是 X pipeline。