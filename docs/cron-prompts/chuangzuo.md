# automation · 创作 pipeline（Codex cron · 每 2 小时）

- runner: launchd + scripts/run-round.sh（2026-10-31 起，Codex app Automations 已停用；旧 automation_id `pipeline-12` 作废）
- schedule: `0 0,2,4,6,8,10,12,14,16,18,20,22 * * *`（Asia/Shanghai）= RRULE `RRULE:FREQ=DAILY;BYHOUR=0,2,4,6,8,10,12,14,16,18,20,22;BYMINUTE=0`（UTC）· **2026-10-31 Frank「每 2h 一发」从 4 档/天加密到 12 档/天**（原 10-30 的 `30 3,9,15,21` 已作废）
- session: 每轮独立进程 = 全新上下文（等价旧 `session.mode=new`）
- prompt 唯一事实源 = 本文件第一个「代码围栏块」；改 prompt 改这里（launchd 每轮由 run-round.sh 抽取该围栏块运行）
  （⚠️ 本行原来内嵌了三个反引号，会让「取第一个围栏块」的解析抓到标题而不是 prompt —— 2026-10-31 已改掉）
- 历史: 2026-10-30 起从 launchd+DSH 迁回 Codex Automations（旧 cron_id `d5c0d018` 已作废）

## prompt 原文（逐字复制）

```
按 `/Users/fangchen/Documents/短文助手/skills/README.md` 入口协议跑一轮创作链路。

【硬约束】每轮最多发 1 条原创，不要凑数。不出现 OpenCSG / DeepSeek / Moonshot / MiniMax；不写 AI 托管 / 自动互动措辞；XHS 由独立的发布线负责，本线不碰小红书（不生成 xhs.txt、不发小红书）。公开动作直接执行，不 ask_user 确认文案。

【前置判据 · 必做，不是可选项】
1. **上一条原创距今 ≥ 2h** → 否则本轮零发送（硬否决；**2026-10-31 Frank「每 2h 一发」自 6 再下调**，10-30 是 6h、10-27 是 12h）。
   ⚠️ 口径以 `state/schedule.yaml#chuangzuo_original_post_min_gap_hours`（=2）+ automation prompt 的
   「距上一条原创 ≥2h」为准，**不要**用本文件里更早的 6h/12h 残留值（那是被 10-31 取代的旧值）。
   ⚠️ **只数原创帖（根帖），reply 不计入**（2026-10-27 修正口径）。
   旧口径把 reply 也算成「发过帖」，而 pulse 一天跑 4 轮、chuangzuo 一天 2 轮 ——
   只要 pulse 回一条 reply，间隔窗口就被占掉，chuangzuo 档口**被自己的回复饿死**。
   reply 的节奏归 pulse 自己管（≤3 动作/轮、reply 间隔 ≥8min），原创的间隔只管原创。
2. **距上一次任何公开文字动作（reply / 原创）≥ 30 min** → 不够就顺延到下一个窗口（不是零发送）
3. 上一条原创 2h 后 likes 仍 ≤ 2 → **换选题方向再发**（不再否决发送；Frank 2026-10-27「多干发原创」——
   这条原本是硬否决，连否 3 轮导致 40 小时零原创）
数据不支持就诚实记「本轮零动作 + 原因」，不要为了「每轮要有产出」而发。

【选题源】X 通道（watchlist 高优 handle）+ 非 X 通道（`python3 scripts/sources.py --source all --limit 8 --text`）。
非 X 源 8 个：aihot / tophub / decohack / gh-trending / producthunt / ph-buzzing / xbangdan / discoverhub。
web 源的数字/原话必须回原文核对。

【选题源 · 两条通道都要扫】X 通道（watchlist 高优 handle）+ **非 X 通道**（`python3 scripts/sources.py --source all --limit 8 --text`，8 个源：aihot / tophub / decohack / gh-trending / producthunt / ph-buzzing / xbangdan / discoverhub，详见 skills/hot-topic-tracker/SKILL.md）。非 X 源不依赖浏览器，最稳。web 源的数字/原话必须回原文核对，摘要只是线索。

【模式 · 唯一浏览器通道 = xb.py】所有浏览器动作只走 `python3 scripts/browser/xb.py --action '<json>'`：Playwright 驱动专用 Chrome（profile ~/.shortbot-browser-profile，CDP 9222，launchd com.fangchen.shortbot.browser 保活），纯 DOM 操作、无视觉模型。动作契约见 scripts/browser/README.md；原语：navigate / open_tab / wait / query / inspect / click / fill / press / screenshot / upload / login_state。
开工先跑 login_state；未登录 → 本轮零发送，status 如实写「专用 Chrome 未登录，需 Fang 在 9222 窗口登录」，不要反复撞登录墙。
⚠️ Codex 内置浏览器（cua_repl，已被组织策略禁用）与 AX（@oai/sky，视觉通道）自 2026-10-31 起废止，一律不再使用；旧的 xdotool / element_index / pbcopy 剪贴板操作指引随之作废。

【发布路径】xb.py 通道：navigate https://x.com/compose/post → fill 正文 → press {"key":"Meta+Enter"}（**xb.py 只认字符串 key**，内部自己合成组合键）；Post button click 不可靠，别用。Cmd+Enter 后不要查 profile / with_replies / home feed 判断真发，用 search 拿 own_post URL 对账。不要盲 retry —— 第二次会触发 X 反重复拦截。

【测量】likes 用 query kind=dom 打 [data-testid='like'] 读 aria-label；详情页底部大数字是 views 不是 likes；不要用 likes 做跨帖对比。

【失败兜底】限流 / 2FA → 立即停手；候选不足不许凑数；不许用 AI 生成图占位。

【状态】写完 state/*.json 后必须同步 state/index.json。轮次记录追加到 state/memory/chuangzuo.md。

【输出】status 段（模式 / 前置判据采样值 / candidate_count / 落盘路径 / 已发 X URL 或「本轮零发送」+ 原因 / 异常）。

完整 workflow / 文案模板 / 技术要点全部在 SKILL.md，不要复制到 prompt 里。
```
