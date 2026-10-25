# 短文助手 · Skills 索引（入口协议）

整个流程拆成 **6 个创作 pipeline skill + 1 个 engagement skill + 1 个 super-bot = 8 个**。每个 skill 一份 `SKILL.md`，描述职责、输入、输出、禁动作。
所有 skill **共享** `../state/` 下的事实源（账号名单 / 规则 / 账号安全状态 / 禁忌）。

```
┌────────────────────┐
│  hot-topic-tracker │  扫 X → 出素材包
└──────────┬─────────┘
           │ material.yaml
           ▼
┌────────────────────┐
│   post-writer-x    │  写 X 文案（口语爆款风）
└──────────┬─────────┘
           │ x.txt + screenshots
           ▼
┌────────────────────┐
│   publisher-x      │  browser use 真发 X
└──────────┬─────────┘
           │ posted_url
           ▼
┌────────────────────┐
│  post-writer-xhs   │  写小红书普通版
└──────────┬─────────┘
           │ xhs.txt
           ▼
┌────────────────────┐
│  publisher-xhs     │  ⏸️ 当前停手：账号 banned，Fang 手贴
└────────────────────┘

# ─── Engagement pipeline（并列，不创作，只互动）───

┌─────────────────────────┐
│  x-engagement-pulse     │  inbound(回别人的 reply)+ outbound(主动 like+reply)
│  ★ 每轮 ≤3 动作          │  不发新帖。cron 每 4 小时
└─────────────────────────┘

# ─── Manager layer（Fang 只跟这个对话）───

┌─────────────────────────┐
│  super-bot              │  首席汇报官 — 只读 + 报告 + 决策建议，不动 X
│  ★ 每日 09:00            │  必查「轮次真空期」
└─────────────────────────┘
```

## Skill 职责速览

| Skill | 职责 | 触发 |
|-------|------|------|
| hot-topic-tracker | 扫 X 高优 handle，出素材包 | chuangzuo pipeline |
| post-writer-x | 按素材包写 X 文案 | chuangzuo pipeline |
| publisher-x | browser use 真发 X | chuangzuo pipeline |
| post-writer-xhs | 按素材包写小红书文案 | chuangzuo pipeline（当前停手） |
| publisher-xhs | ⏸️ 停手（账号 banned） | 不可用 |
| browser-use-utils | mcp_browser 工具封装 | 全链路共享 |
| **x-engagement-pulse** | **inbound reply + outbound like+reply（不发新帖）** | **cron 每 4 小时** |
| **super-bot** | **只读 + 报告 + 决策建议，不动 X** | **cron 每日 09:00 + 手动查询** |

## 运行模式

三个 cron 全部跑在 **MiniMax Code session** 里，浏览器工具是 `mcp_browser`。

**没有模式分支了** —— 以前有「Codex session 模式 / Cron lite 模式」的二选一，
现在 lite 那条路（`scripts/run-all-slots.sh` / `scan-slot.sh`）已删除：
`state/schedule.yaml` 自己写明 mmx 是通用 web 搜索、不支持 `from:` / `site:x.com`，
**多数 slot 必然 0 候选**，留着只会误导。

开工第一步仍然要检测：**有 `mcp_browser` 工具 → 走完整链路；没有 → 老实写「浏览器不可用，本轮零动作」，不装忙。**

## chuangzuo 完整链路

1. 读 `state/*.yaml` + `state/index.json`（**不要全量读 seen-posts.json**）
2. 读 `state/memory/chuangzuo.md` 末 2 段（`python3 scripts/tail-rounds.py state/memory/chuangzuo.md --rounds 2`）
3. **发不发的前置判据**（必做，不是可选项）：
   - 上一条原创 12h 后 likes 仍 ≤ 2 → **本轮零发送**
   - Frank 自己在 12h 内发过帖（查 `/FrankFika/with_replies` 顶部）→ **本轮零发送**
   - 数据不支持就诚实记「本轮零动作 + 原因」，**不要为了「每轮要有产出」而发**
4. mcp_browser 真扫 watchlist 高优 handle（≥ 2 个就够）
5. 筛候选：AI 关键词命中 + 未在 `state/index.json` + 优先 practitioner 源而不是官方账号
6. 写 `material.yaml` + `x.txt`（按 `state/style-x.yaml`）
7. mcp_browser 真发：`fill` + `Cmd+Enter`（Meta+Enter）
8. **验证**：Cmd+Enter 后**不要**查 profile / with_replies / home feed，用 search 拿 own_post URL
9. 更新 `published-posts.json` / `seen-posts.json` / **`state/index.json`** / `account-safety.yaml`
10. 轮次记录追加到 `state/memory/chuangzuo.md`（**新段前加一行 `<!-- round -->`**）

## 每轮产出约定

- **每轮最多 1 条原创**（Frank 2026-10-21 降频；README 早期写的「3 条完成版」已作废）
- 候选不足就少做，**不要凑数**
- **screenshots/ 必抓真图**，绝不用 AI 生成图占位
- **XHS 默认停手**（`private/account-safety.yaml#xhs.ban_status.is_banned = true`）
- **诚实原则**：任何环节拿不到真实结果就写「未发」+ 原因，不许装忙
- 原创间隔 ≥ 12 小时（`schedule.yaml#cooldown_between_posts_min` 是下限，不是目标）

## 共同约束

- 读 `state/forbidden.yaml` 当红线
- 读 `private/account-safety.yaml` 决定 publish_mode
- 读 `state/index.json` 去重（**不是**全量 seen-posts.json）
- 读轮次日志只读末 N 段，用 `scripts/tail-rounds.py`
- XHS 默认停手

## 配套脚本

- `scripts/tail-rounds.py` — **只读 memory 最后 N 段**（每轮必用，别全量 cat）
- `scripts/qa-draft.py` — 草稿自检（字数 / has 数字 / has 链接）
- `scripts/health-check.sh` — 跑前环境体检
- `scripts/publisher-xhs-dryrun.sh` — XHS 草稿 dryrun（账号 banned 时退出码 1）
