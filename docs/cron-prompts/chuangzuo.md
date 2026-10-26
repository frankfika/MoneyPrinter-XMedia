# cron · 创作 pipeline（每 12 小时）

- cronId（老机器）: `d5c0d018-fcb4-4205-8f5e-35d41c0d1fb9`
- cron_name: `短文助手 · 创作 pipeline · 每 12 小时（Frank 2026-10-25 降频）`
- schedule: `30 3,15 * * *`
- timezone: `Asia/Shanghai`
- session: `{ "mode": "new" }`
- model: `minimax/MiniMax-M3`
- project: `/Users/fangchen/Documents/短文助手` ← **改成新机器路径**

## prompt 原文（逐字复制）

```
按 `/Users/fangchen/Documents/短文助手/skills/README.md` 入口协议跑一轮创作链路。

【硬约束】每轮最多发 1 条原创，不要凑数。不出现 OpenCSG / DeepSeek / Moonshot / MiniMax；不写 AI 托管 / 自动互动措辞；XHS 停手（is_banned=true，不生成 xhs.txt）。公开动作直接执行，不 ask_user 确认文案。

【前置判据 · 必做，不是可选项】
1. 上一条原创 12h 后 likes 仍 ≤ 2 → 本轮零发送
2. Frank 自己在 12h 内发过帖 → 本轮零发送
数据不支持就诚实记「本轮零动作 + 原因」，不要为了「每轮要有产出」而发。

【模式】有 mcp_browser → 完整链路；没有 → 老实写「浏览器不可用，本轮零动作」，不装忙。

【发布路径】fill + Cmd+Enter（Meta+Enter）是唯一稳定真发路径，Post button click 不可靠。Cmd+Enter 后不要查 profile / with_replies / home feed 判断真发，用 search 拿 own_post URL。不要盲 retry —— 第二次会触发 X 反重复拦截。

【测量】likes 用 query kind=dom 打 [data-testid='like'] 读 aria-label；详情页底部大数字是 views 不是 likes；不要用 likes 做跨帖对比。

【失败兜底】限流 / 2FA → 立即停手；候选不足不许凑数；不许用 AI 生成图占位。

【状态】写完 state/*.json 后必须同步 state/index.json。轮次记录追加到 state/memory/chuangzuo.md。

【输出】status 段（模式 / 前置判据采样值 / candidate_count / 落盘路径 / 已发 X URL 或「本轮零发送」+ 原因 / 异常）。

完整 workflow / 文案模板 / 技术要点全部在 SKILL.md，不要复制到 prompt 里。
```
