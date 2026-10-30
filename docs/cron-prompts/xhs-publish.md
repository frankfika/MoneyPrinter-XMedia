# automation · 小红书发布线（Codex cron · 每天 4 个候选档口 · 独立线）

- automation_id: `automation`（Codex app → Automations · cron 类型；显示名「短文助手·小红书发布线·分散档口」）
- schedule: `37 9,12,16,20 * * *`（Asia/Shanghai）= RRULE `RRULE:FREQ=DAILY;BYHOUR=1,4,8,12;BYMINUTE=37`（UTC）
- target: Codex 项目「短文助手」(`71faead3-cd8e-49ec-be13-c9747d4927ac`) · local
- session: 每轮独立进程 = 全新上下文
- prompt 唯一事实源 = 本文件第一个 ``` 围栏块
- 历史: 2026-10-30 从创作线拆出独立线（Fang 拍板：不同平台 = 不同线）；前身为 MiniMax 时代 cron 设计稿

## 为什么是分散而不是固定单一时段

账号被封原因为「利用 AI 托管进行发文/互动」。**固定时段连发是机器特征最重的形态** —— 每天同一分钟、同样条数 = 机器人指纹。
每天 4 个候选档口 + 轮内随机跳档（约 50%）+ 每天条数浮动 = 更接近真人节奏。这是操作层面降风险的核心手段（文案侧只需 AI 味清零）。

## prompt 原文（逐字复制）

```
【小红书发布轮次 · 独立线（2026-10-30 拆分：X 线不碰小红书，本线不碰 X）】

先读 `/Users/fangchen/shortbot/skills/publisher-xhs/SKILL.md` 并按它执行；所有 `state/`、`outputs/`、`scripts/` 相对路径的根都是 `/Users/fangchen/shortbot/`。读不到 SKILL.md → 本轮零动作，如实写原因，不凭记忆跑。

【模式检测（必做第一步）】
- 有 mcp__cua_repl__js → 内置浏览器通道：开 https://www.xiaohongshu.com/explore 查登录态（右上角显示「弗兰克的思维导图」= 已登录）
- 无 cua_repl / 报 Local browser use is disabled → 本轮零动作，如实写原因。**不许走 xb.py**（已停用）

【A · 探测模式 —— state/xhs-publish-state.json#automation_enabled=false 时】
1. 只做登录态探测 + 读草稿箱计数，不点发布
2. 登录态 OK → 写 state/memory/xhs-probe.md（时间戳 / 结论 / 可见身份），连续 3 轮通过后在 status 写「探测已通过 N/3，等 Fang 一句『开』」
3. **不许自己 flip automation_enabled** —— 那是 Frank 显式说出口才动的开关
4. 登录墙 / 验证码 → 零动作，URL 给 Fang

【B · 发布模式 —— automation_enabled=true（Fang 显式开过）后】
1. 节奏闸门（读 state/schedule.yaml#xhs + state/xhs-publish-state.json）：
   - 当天已发 ≥ posts_per_day_max → 本轮零发布
   - 距 last_published_at < min_gap_hours → 本轮零发布
   - 随机跳档：本轮约 50% 概率零发布（老实写「跳档」，不装忙）
2. 选素材：扫 outputs/ 近 7 天目录，找「有 xhs.txt + screenshots/ ≥2 张真图 + 不在 xhs-publish-state published 清单」的候选。
   没有合格草稿 → 走选题：python3 scripts/sources.py --source all --limit 8 --text → 按 state/style-xhs.yaml 写 xhs.txt（标题 ≤20 字符）+ 内置浏览器抓真截图
3. 闸门：python3 scripts/humanize.py scan <xhs.txt> --json → 软分必须 0；红线词（OpenCSG / Chinese AI 公司名 / AI 托管措辞）命中 → 零发布
4. 发布单留痕（= cron 模式的确认卡）：把 站点 / 账号 / 标题 / 正文逐字 / 图片文件名 / 可见性=公开 写进轮次日志，发布前逐项回读核对
5. 按 SKILL.md「二次发布」流程：creator 中心 → 草稿编辑 → 回读核对 → 点「发布」→ 回笔记管理页确证，拿 note_id + URL。拿不到 = 没发
6. 记账：xhs-publish-state.json + published-posts.json + index.json + recent-picks.json；轮次段（段首加一行 <!-- round -->）追加 state/memory/xhs.md

【硬约束 · 违反即事故】
- 只走内置浏览器真窗口；不碰平台 AI 功能（智能标题 / 创作助手 / 原创声明 / 内容类型声明全保持默认）；不改任何设置；可见性=公开可见；不开定时发布
- 素材必须真截图，禁 AI 生成图占位；登录墙 / 验证码一律停手给 Fang
- 任何「假装已发」= 事故；拿不到 note_id / URL 就是没发

【输出】status：模式（探测/发布/跳档/零动作）/ 节奏闸门采样值 / 候选 + 发布单 / note_id + URL 或零发布原因 / 异常
```

## 探测结论（决定 automation_enabled）

cron session 里内置浏览器的小红书登录态是否保持 —— 见 `state/memory/xhs-probe.md`。
未通过前 `automation_enabled=false`，线只跑探测模式；Fang 显式说「开」后才允许 flip（红线纪律）。
