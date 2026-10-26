# cron · super-bot（每日 09:00）

- cronId（老机器）: `6560e820-db95-4b83-91ad-4a0f7d4d3fd3`
- cron_name: `短文助手 · super-bot 日报 · 每日 09:00`
- schedule: `0 9 * * *`
- timezone: `Asia/Shanghai`
- session: `{ "mode": "new" }`
- model: `minimax/MiniMax-M3`
- project: `/Users/fangchen/Documents/短文助手` ← **改成新机器路径**

## prompt 原文（逐字复制）

```
按 `/Users/fangchen/Documents/短文助手/skills/super-bot/SKILL.md` 跑日报（每日 09:00 +08:00 自动模式）。

【硬约束】不动 X 浏览器（不调 mcp_browser，不发 like / reply / post）；不改 state/*.yaml；不改 worker cron 配置。只读 + 写自己的 state/memory/super-bot.md。

【必读源】state/memory/chuangzuo.md（末 2 段）、state/memory/pulse.md（末 3 段，用 scripts/tail-rounds.py 读，不要全量 cat）、state/index.json、state/published-posts.json、state/inbound-replies.json、private/account-safety.yaml、outputs/ 当日目录。

【🔴 第一件事 · 查轮次真空期】对比 state/memory/*.md 末轮时间戳 vs 现在的真实时间。距末轮 > 2 × 调度间隔 = 真空期，必须写进日报：丢失轮次数 / 时间窗口 / 根因 / 对 inbound 覆盖的影响。cron 投递状态 delivered ≠ 轮次执行，本地 cron 依赖 runtime 存活、机器休眠不补跑。

【输出】完整日报结构（今日概览 / 创作摘要 / 互动摘要 / 轮次真空期 / 异常 / 明日建议）+ inbox-item 给 Frank。

【失败兜底】memory.md 不存在 → 老实写「worker bot #X 暂无历史」；state/*.json 损坏 → 老实写「state 损坏，请人工检查」+ 紧急 inbox-item；缺数据就写「数据不可用，跳过」。不许装忙。

【诚实边界】likes 只有单个真实采样点时不得据此下任何结论；通知页 query kind=text 读到的是 views 不是 likes，口径必须标注。

详细 workflow / 日报模板 / 决策树全部在 SKILL.md，不要复制到 prompt 里。
```
