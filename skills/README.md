# 短文助手 · Skills 索引

整个流程拆成 **6 个创作 pipeline skill + 1 个 engagement skill + 1 个 super-bot = 8 个**。每个 skill 一份 `SKILL.md`，描述职责、输入、输出、禁动作。
所有 skill **共享** `../state/` 下的事实源（账号名单 / 规则 / 账号安全状态 / 禁忌）。

```
┌────────────────────┐
│  hot-topic-tracker │  扫 X → 出素材包（cua_repl 真扫 OR scan-slot.sh lite）
└──────────┬─────────┘
           │ material-pack.json / material.yaml
           ▼
┌────────────────────┐
│   post-writer-x    │  写 X 文案（口语爆款风）
└──────────┬─────────┘
           │ x.txt + screenshots
           ▼
┌────────────────────┐
│   publisher-x      │  cua_repl 真实发 X
└──────────┬─────────┘
           │ posted_url
           ▼
┌────────────────────┐
│  post-writer-xhs   │  写小红书普通版
└──────────┬─────────┘
           │ xhs.txt + screenshots
           ▼
┌────────────────────┐
│  publisher-xhs     │  解封后：浏览器只存草稿；否则：Fang 手贴
└────────────────────┘

# ─── Engagement pipeline (并列,不创作,只互动) ───

┌─────────────────────────┐
│  x-engagement-pulse     │  inbound(回别人的 reply)+ outbound(主动 like+reply 高优热帖)
│  (替代之前的内联 workflow) │  不发新帖,只 like+reply。每 30 min cron。
└─────────────────────────┘

# ─── Manager layer (Fang 只跟这个对话) ───

┌─────────────────────────┐
│  super-bot              │  首席汇报官 — 只读 + 报告 + 决策建议,不动 X
│  (Fang 的唯一对接入口)   │  每日 09:00 +08:00 自动日报 / 随时手动查询
└─────────────────────────┘
                  ▲
                  │ 读
       ┌──────────┴──────────┐
   worker #1 memory     worker #2 memory
   (创作 pipeline)       (engagement pulse)
```

## Skill 职责速览

| Skill | 职责 | 触发 |
|-------|------|------|
| hot-topic-tracker | 扫 X 高优 handle,出素材包 | cron 触发的完整链路 |
| post-writer-x | 按素材包写 X 文案 | pipeline |
| publisher-x | 用 cua_repl 真发 X | pipeline |
| post-writer-xhs | 按素材包写小红书文案 | pipeline |
| publisher-xhs | 解封后:浏览器只存草稿;否则:Fang 手贴 | pipeline |
| browser-use-utils | cua_repl 浏览器工具封装 | pipeline 共享 |
| **x-engagement-pulse** | **inbound reply + outbound like+reply(不发新帖)** | **每 30 min cron** |
| **super-bot** | **只读 + 报告 + 决策建议,不动 X;Fang 的唯一对接入口** | **每日 09:00 +08:00 cron + 手动查询** |

## 模式检测(2026-10-15 起必做)

启动 automation 时第一步先判断：

| 模式 | 触发条件 | 链路 |
|------|---------|------|
| **Codex session 模式** | automation thread 有 `mcp__cua_repl__js` 工具（cron 触发的 automation thread **默认就在 Codex session 里**，有 cua_repl） | 走 cua_repl 真扫 + 真发完整链路 → 目标每轮 3 条完成版 |
| **Cron 模式** | 真的没有 cua_repl 的纯后台环境（罕见） | 只跑 `scripts/run-all-slots.sh` lite → 大概率 0 候选 → status 老实写"未发，原因：cron 无 cua_repl" |

> ⚠️ 历史教训：之前 automation thread 都跑 lite 版是 prompt 设计误导——automation thread **永远在 Codex session 里**，能用 cua_repl。lite 只能作 cron 兜底，不能作默认。

## Codex session 模式工作流（默认）

详细 cua_repl 复盘见 `scripts/cua-full-flow.md`。完整流程：

1. 读 `state/*.yaml` + `state/seen-posts.json` + `state/recent-picks.json`
2. 读 `$CODEX_HOME/automations/users-fangchen-documents-skills-readme-md-1-state-watc/memory.md`（避免重复）
3. **优先 cua_repl 真扫 watchlist 高优 ≥ 3 个 handle 的 timeline**
   - 候选 handle：OpenAI / AnthropicAI / GoogleDeepMind / karpathy / sama / JensenHuang / NVIDIA / dotey / oran_ge / op7418 / deepseek_ai / Alibaba_Qwen
   - 过滤：≥ 15K views + AI 关键词命中 + 未在 seen-posts.json + 不是 dropped handle
4. 候选 ≥ 3 → 取前 3；不足 3 全跑；候选 = 0 才走 `scripts/run-all-slots.sh` lite 兜底
5. 每个候选：抓 4-6 张真图（cua_repl）→ 写 `material.yaml` → 写 `x.txt`（按 `state/style-x.yaml`）
6. cua_repl 在 `x.com/compose/post` 真发：
   - textarea AX click (idx 26)
   - paste 正文
   - filechooser event 附图
   - click Post (idx 13)
   - 抓 `x.com/FrankFika/status/<id>` 路径
7. 更新 `published-posts.json` / `seen-posts.json` / `account-safety.yaml#x.last_published`
8. memory.md 追加本次记录

## 共同约束

- 读 `state/forbidden.yaml` 当红线
- 读 `private/account-safety.yaml` 决定 publish_mode
- 读 `seen-posts.json` + `recent-picks.json` 去重
- XHS 默认停手（`account-safety.yaml#xhs.ban_status.is_banned = true`）

## 每轮产出约定（2026-10-15 起生效）

- **目标：每轮返回 3 条完成版候选**
  - 每个完成版 = `material.yaml` + `x.txt` + `screenshots/`（真图，非占位）+ `posted_url`
  - 候选 ≥ 3 → 取前 3 个跑，不要凑数
  - 候选 < 3 → 全跑，状态报告老实写"实际 X 条"
  - 候选 = 0 → memory + status 写明"0 候选，未发"，不要硬塞
- **screenshots/ 必抓真图**（cua_repl browser use）
  - 一条候选 4-6 张，按内容相关性，命名按 skill 协议
  - 存好后 `ls` 确认非空，写进 status
- **XHS 默认停手**（`private/account-safety.yaml#xhs.ban_status.is_banned = true`）
- **诚实原则**：任何环节拿不到真实结果就写"未发"并给原因，不许装忙
- **cooldown**：`schedule.yaml#cooldown_between_posts_min = 30` 分钟（同一 slot 内）

## 配套脚本

- `scripts/run-all-slots.sh` — Cron 模式入口，串跑 5 slot 的 scan-slot.sh
- `scripts/scan-slot.sh` — Lite 版 X 扫描（mmx web search），Cron 模式必走路径
- `scripts/cua-full-flow.md` — **Codex session 模式复盘菜谱**（必读）
- `scripts/qa-draft.py` — 草稿自检（字长度 / has 数字 / has 链接）
- `scripts/health-check.sh` — 跑前环境体检
- `scripts/publisher-xhs-dryrun.sh` — XHS 草稿 dryrun（账号 banned 时退出码 1）
