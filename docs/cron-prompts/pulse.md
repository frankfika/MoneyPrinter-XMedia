# automation · engagement pulse（Codex cron · 每 6 小时 ×4）

- runner: launchd + scripts/run-round.sh（2026-10-31 起，Codex app Automations 已停用；旧 automation_id `x-pulse-6` 作废）
- schedule: `0 4,10,16,22 * * *`（Asia/Shanghai）= RRULE `RRULE:FREQ=DAILY;BYHOUR=20,2,8,14;BYMINUTE=0`（UTC）
- session: 每轮独立进程 = 全新上下文（等价旧 `session.mode=new`）
- prompt 唯一事实源 = 本文件第一个 ``` 围栏块；改 prompt 改这里（launchd 每轮抽取该围栏块运行）
- 历史: 2026-10-30 起从 launchd+DSH 迁回 Codex Automations（旧 cron_id `0dbbcbb9` 已作废）

## prompt 原文（逐字复制）

```
按 `/Users/fangchen/Documents/短文助手/skills/x-engagement-pulse/SKILL.md` 跑一轮 pulse。

【硬约束】单轮总动作 ≤3（inbound reply ≤1 / **outbound reply 0** / outbound like ≤2）← Frank 2026-10-27「少评论，多干发原创」；原创 post 0；quote RT 0。不出现 OpenCSG / DeepSeek / Moonshot / MiniMax 等公司名；不写 AI 托管 / 自动互动 / bot 措辞；不堆 hashtag。XHS 由独立的发布线负责，本线不碰小红书。公开动作直接执行，不 ask_user 确认文案。

【模式 · 唯一浏览器通道 = xb.py】所有浏览器动作只走 `python3 scripts/browser/xb.py --action '<json>'`：Playwright 驱动专用 Chrome（profile ~/.shortbot-browser-profile，CDP 9222，launchd com.fangchen.shortbot.browser 保活），纯 DOM 操作、无视觉模型。动作契约见 scripts/browser/README.md；原语：navigate / open_tab / wait / query / inspect / click / fill / press / screenshot / upload / login_state。
开工先跑 login_state；未登录 → 本轮零动作，status 如实写「专用 Chrome 未登录，需 Fang 在 9222 窗口登录」，不要反复撞登录墙。
⚠️ Codex 内置浏览器（cua_repl，已被组织策略禁用）与 AX（@oai/sky，视觉通道）自 2026-10-31 起废止，一律不再使用。
⚠️ 发送按键用 `press {"key":"Meta+Enter"}`（xb.py 只认字符串 key，内部自己合成组合键）；like/reply 细节见 skills/x-engagement-pulse/SKILL.md 发送路径铁律。

【频率】候选不足就少做，不要凑数。Frank 自己在 2 小时内发过帖 → 本轮降载到 1 个动作或零动作。

【失败兜底】限流 / 2FA / 验证码 → 立即停手并写明。candidate=0 → 老实写「0 候选，本轮零动作」。

【状态】写完 state/*.json 后必须同步 state/index.json。轮次记录追加到 state/memory/pulse.md。

【输出】status 段（模式 / 三个计数 + 是否触达上限 / 已发 X URL / 跳过项 / 异常）。

完整 workflow / 文案模板 / 测量方法铁律 / 发送路径铁律全部在 SKILL.md，不要复制到 prompt 里。
```
