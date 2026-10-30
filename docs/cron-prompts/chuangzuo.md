# automation · 创作 pipeline（Codex cron · 每 12 小时）

- automation_id: `pipeline-12`（Codex app → Automations · cron 类型）
- schedule: `30 3,15 * * *`（Asia/Shanghai）= RRULE `RRULE:FREQ=DAILY;BYHOUR=19,7;BYMINUTE=30`（UTC）
- target: Codex 项目「短文助手」(`71faead3-cd8e-49ec-be13-c9747d4927ac`) · local
- session: 每轮独立进程 = 全新上下文（等价旧 `session.mode=new`）
- prompt 唯一事实源 = 本文件第一个 ``` 围栏块；改 prompt 改这里，再去 automation_update 同步
- 历史: 2026-10-30 起从 launchd+DSH 迁回 Codex Automations（旧 cron_id `d5c0d018` 已作废）

## prompt 原文（逐字复制）

```
按 `/Users/fangchen/Documents/短文助手/skills/README.md` 入口协议跑一轮创作链路。

【硬约束】每轮最多发 1 条原创，不要凑数。不出现 OpenCSG / DeepSeek / Moonshot / MiniMax；不写 AI 托管 / 自动互动措辞；XHS 由独立的发布线负责，本线不碰小红书（不生成 xhs.txt、不发小红书）。公开动作直接执行，不 ask_user 确认文案。

【前置判据 · 必做，不是可选项】
1. **上一条原创距今 ≥ 12h** → 否则本轮零发送（硬否决）。
   ⚠️ **只数原创帖（根帖），reply 不计入**（2026-10-27 修正口径）。
   旧口径把 reply 也算成「发过帖」，而 pulse 一天跑 4 轮、chuangzuo 一天 2 轮 ——
   只要 pulse 回一条 reply，12h 窗口就被占掉，chuangzuo 两个档口**双双 100% 被自己的回复饿死**。
   reply 的节奏归 pulse 自己管（≤3 动作/轮、reply 间隔 ≥8min），原创的 12h 间隔只管原创。
2. **距上一次任何公开文字动作（reply / 原创）≥ 30 min** → 不够就顺延到下一个窗口（不是零发送）
3. 上一条原创 12h 后 likes 仍 ≤ 2 → **换选题方向再发**（不再否决发送；Frank 2026-10-27「多干发原创」——
   这条原本是硬否决，连否 3 轮导致 40 小时零原创）
数据不支持就诚实记「本轮零动作 + 原因」，不要为了「每轮要有产出」而发。

【选题源】X 通道（watchlist 高优 handle）+ 非 X 通道（`python3 scripts/sources.py --source all --limit 8 --text`）。
非 X 源 8 个：aihot / tophub / decohack / gh-trending / producthunt / ph-buzzing / xbangdan / discoverhub。
web 源的数字/原话必须回原文核对。

【选题源 · 两条通道都要扫】X 通道（watchlist 高优 handle）+ **非 X 通道**（`python3 scripts/sources.py --source all --limit 8 --text`，8 个源：aihot / tophub / decohack / gh-trending / producthunt / ph-buzzing / xbangdan / discoverhub，详见 skills/hot-topic-tracker/SKILL.md）。非 X 源不依赖浏览器，最稳。web 源的数字/原话必须回原文核对，摘要只是线索。

【模式 · 双浏览器通道（2026-10-30 起）】开工先做模式检测：
① 有 mcp__cua_repl__js 工具 → **Codex 内置浏览器通道**：开 x.com 查登录态（能进 home timeline / 有头像 = 已登录）；未登录 → 本轮零发送，status 写「内置浏览器未登录 X，需 Fang 一次性登录」。
② 无 cua_repl → **xb.py 通道**：跑 `python3 scripts/browser/xb.py --action '{"action":"login_state"}'`；exit 2（BROWSER_UNAVAILABLE）→ 「浏览器不可用，本轮零动作」；logged_in=false → 「专用 Chrome（~/.shortbot-browser-profile）未登录 X，本轮零发送」。
⚠️ 两通道登录态互相独立，各需一次性人工登录（含 2FA，只有人能做）。发文组合键写法**相反**：内置浏览器 `press_key {"key":"Enter","modifiers":["Meta"]}`；xb.py `press {"key":"Meta+Enter"}`（xb.py 只认字符串 key）。抄错 = 看起来成功但没发出去。

【发布路径】xb.py 通道用 `fill` + `press {"key":"Meta+Enter"}`（**xb.py 只认字符串 key**，内部自己合成组合键）；Post button click 不可靠。Cmd+Enter 后不要查 profile / with_replies / home feed 判断真发，用 search 拿 own_post URL。不要盲 retry —— 第二次会触发 X 反重复拦截。
⚠️ 另一条通道（内置浏览器 `press_key`）的写法**相反**：必须 `{"key":"Enter","modifiers":["Meta"]}`，传字符串会被静默丢掉。

【测量】likes 用 query kind=dom 打 [data-testid='like'] 读 aria-label；详情页底部大数字是 views 不是 likes；不要用 likes 做跨帖对比。

【失败兜底】限流 / 2FA → 立即停手；候选不足不许凑数；不许用 AI 生成图占位。

【状态】写完 state/*.json 后必须同步 state/index.json。轮次记录追加到 state/memory/chuangzuo.md。

【输出】status 段（模式 / 前置判据采样值 / candidate_count / 落盘路径 / 已发 X URL 或「本轮零发送」+ 原因 / 异常）。

完整 workflow / 文案模板 / 技术要点全部在 SKILL.md，不要复制到 prompt 里。
```
