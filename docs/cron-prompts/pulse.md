# cron · engagement pulse（每 4 小时）

- cronId（老机器）: `0dbbcbb9-ac42-456a-bd35-73f9ed960a07`
- cron_name: `短文助手 · engagement pulse · 每 4 小时（Frank 2026-10-25 降频）`
- schedule: `0 4,10,16,22 * * *`
- timezone: `Asia/Shanghai`
- session: `{ "mode": "new" }`
- model: `minimax/MiniMax-M3`
- project: `/Users/fangchen/Documents/短文助手` ← **改成新机器路径**

## prompt 原文（逐字复制）

```
按 `/Users/fangchen/Documents/短文助手/skills/x-engagement-pulse/SKILL.md` 跑一轮 pulse。

【硬约束】单轮总动作 ≤3（inbound reply ≤1 / outbound reply ≤1 / outbound like ≤2）；原创 post 0；quote RT 0。不出现 OpenCSG / DeepSeek / Moonshot / MiniMax 等公司名；不写 AI 托管 / 自动互动 / bot 措辞；不堆 hashtag。XHS 停手。公开动作直接执行，不 ask_user 确认文案。

【模式】有 mcp_browser → 完整链路；没有 → 老实写「浏览器不可用，本轮零动作」，不装忙。

【频率】候选不足就少做，不要凑数。Frank 自己在 2 小时内发过帖 → 本轮降载到 1 个动作或零动作。

【失败兜底】限流 / 2FA / 验证码 → 立即停手并写明。candidate=0 → 老实写「0 候选，本轮零动作」。

【状态】写完 state/*.json 后必须同步 state/index.json。轮次记录追加到 state/memory/pulse.md。

【输出】status 段（模式 / 三个计数 + 是否触达上限 / 已发 X URL / 跳过项 / 异常）。

完整 workflow / 文案模板 / 测量方法铁律 / 发送路径铁律全部在 SKILL.md，不要复制到 prompt 里。
```
