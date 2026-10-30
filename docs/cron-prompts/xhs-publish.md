# cron · 小红书发布线（分散发布）

- cron_name: `短文助手 · 小红书发布线 · 分散档口`
- schedule: `37 9,12,16,20 * * *`（4 个候选档口，prompt 内随机挑 1~2 个实际执行）
- timezone: `Asia/Shanghai`
- session: `{ "mode": "new" }`
- model: `minimax/MiniMax-M3`
- project: `/Users/fangchen/Documents/短文助手`

## 为什么是分散而不是固定单一时段

账号被封原因为「利用 AI 托管进行发文/互动」。**固定时段的连发是机器特征最重的形态** —— 每天同一分钟、每天同样条数，正是机器人指纹。分散 + 每天条数浮动 = 更接近真人节奏。这是操作层面降风险的核心手段（文案侧只需 AI 味清零）。

## prompt 原文（逐字复制）

```
【小红书发布轮次 · 分散档口】

读 /Users/fangchen/Documents/短文助手/skills/publisher-xhs/SKILL.md 按它执行。

【本轮发不发 · 随机决定】
1. 读 state/xhs-publish-state.json + private/account-safety.yaml#xhs
2. 若 automation_enabled=false → 只读不动，写「自动化未启用」后结束
3. 读 state/schedule.yaml#xhs 的 posts_per_day_max / min_gap_hours
4. 本轮用随机数决定发几条（1~2 条，需满足 min_gap_hours 与当日条数上限）
5. 随机决定发不发（概率约 50%），不发就老实写「本轮零发布」

【硬约束 · 违反即事故】
- 只走内置浏览器 mcp_browser，不碰平台 AI 功能（智能标题/创作助手/原创声明/内容类型声明）
- 不改任何设置：可见性保持公开可见，不开定时发布，原创声明保持 unchecked
- 每次发布前出确认卡，讲清站点/账号/标题/正文/图片文件名/可见性
- 登录墙/验证码一律停手交给 Frank，不碰验证码
- 素材必须是真截图，禁止 AI 生成图

【发布后】
写 state/xhs-publish-state.json + state/published-posts.json + state/index.json + state/recent-picks.json
轮次记录追加到 state/memory/xhs.md（新段前加一行 <!-- round -->）

【失败兜底】
浏览器不可用/登录墙/验证码 → 立即停手并写明原因，不许装忙
候选不足 → 老实写「0 候选，本轮零发布」
```

## 探测结论（决定 automation_enabled）

cron session 里内置浏览器的小红书登录态是否保持 —— 见 `state/memory/xhs-probe.md`。
未通过前 `automation_enabled=false`，只做人工触发。
