# Codex Automation 配置（直接贴进 Codex UI）

## 名称
短文助手·每3小时扫一轮

## 类型
Heartbeat（attach 到当前短文助手 thread，最稳；如要 standalone cron 也行）

## 触发节奏（任选其一）

**Heartbeat（推荐）**：
- Interval: 180 minutes
- 这条 thread 在每次触发时会收到一条自动消息，由 Codex 跑下面的 prompt

**Cron**（如要严格 9/12/15/18/21）：
- RRULE: `FREQ=HOURLY;INTERVAL=3`
- 或者 `0 9,12,15,18,21 * * *`（macOS / Unix cron 语法，Codex automation 用 RRULE）

## Prompt（直接贴）

```
按 `/Users/fangchen/Documents/短文助手/skills/README.md` 入口协议跑一轮完整链路：

1. 读 state/watchlist.yaml + state/filter-rules.yaml + private/account-safety.yaml
2. 跑 bash /Users/fangchen/Documents/短文助手/scripts/run-all-slots.sh
3. 看新生成的 outputs/<MMDD>-<slot>/ 下有没有 material.yaml；若有 →
   跑完整链路（browser use 抓真图 → 写 x.txt/xhs.txt → QA）
4. X 真发前必须明确等 Fang 在本条触发里回复「发」才点 Post；
   否则只产草稿
5. XHS 默认停手（账号封禁），除非 Fang 显式说「可以存草稿了」
   + state 已改

完成后用一段简短的 status 报告（不要复述 README）：
- 本轮扫到几个候选
- 草稿落盘清单
- 是否已发 X（带 URL）
- XHS 状态
- 异常 / 阻塞

不要做任何「假装已发」的事；任何环节拿不到真实结果就老实说「未发」。
```

## 失败兜底
- `state/seen-posts.json` 已发的 post_id 不会再选题
- `bash /Users/fangchen/Documents/短文助手/scripts/health-check.sh` 可一行命令验证系统
- `bash /Users/fangchen/Documents/短文助手/scripts/publisher-xhs-dryrun.sh` 退出码 1 = 正确停手
