# 短文助手 · 本轮 status（2026-10-20 19:50 触发）

## 模式判定
**Cron 模式（降级）** — 本 automation thread 跑在 WorkBuddy 沙箱，工具清单里没有 `mcp__cua_repl__js`（已用工具检索确认，非猜测）。

项目自带探测一致：`scripts/health-gate.sh` 输出
`plan=C cua_repl=down r_jina=down mmx=up(94/100) x_prime=down`

Plan C 的语义 = 只有 mmx 全网搜索可用，**没有 X 时间线、没有浏览量、没有发布通道**。

## 结论
- **candidate_count = 0**
- **完成版 0 条**（material.yaml + x.txt + 真图 + posted_url 四件套：0 套）
- **已发 X：未发**，原因：本 host 无 cua_repl 且网络层直接封 x.com
  - `curl https://x.com/OpenAI` → `000`（连接失败，非 403）
  - `curl https://r.jina.ai/...` → `000`（Plan B 也断）
  - Chrome 未运行，且 `~/Library/Application Support/Google/Chrome` 被 macOS TCC 拒绝访问（无法复用已登录 profile）
- **XHS：停手**（`account-safety.yaml` 无 `xhs` 段，按 README「XHS 默认停手」；`publisher-xhs-dryrun.sh` 按预期退出）
- **未凑数、未用 AI 图占位**

## 本轮顺手修掉的 3 个真实缺陷（这是历次「永远 0 候选」的根因）

| # | 缺陷 | 影响 | 处理 |
|---|------|------|------|
| 1 | `scan-slot.sh` 读 `mmx quota show` 的 `available_amount` 字段，但当前 mmx CLI 返回的是 `model_remains[]`，该字段不存在 → 解析恒为 `-1` | 5 个 slot **每次都被 SKIPPED**，日志只写一行 skip，等于装忙 | 改为读 `model_remains[].current_interval_remaining_percent`；解析失败不再 skip（宁可真跑一次） |
| 2 | 本机 `python3` 全部（3.11/3.12/3.13/系统）都没有 PyYAML | `scan-slot.sh` 的解析段直接 Traceback，`run-all-slots.sh` 因 `set -e` 在 slot=am 就中断 | `pip install --user pyyaml`（6.0.3），已可用 |
| 3 | `state/style-x.yaml`、`private/account-safety.yaml` 无法被 `yaml.safe_load` 解析 | 写稿侧拿不到文风规则（含今天新加的 `anti_ai_slop`）；安全侧读不到 `x.last_published` | 仅做语法层修复，语义一字未改；account-safety 原文备份 `private/account-safety.yaml.bak-20261020` |

修完后 5 个 slot 是**真跑**过的，日志落 `logs/scan/1020-{am,noon,pm,eve,night}.log`，每个都是 `found 0 candidate(s)` —— 这是真实结果，不再是 skip 假象。

## 为什么 lite 版结构上不可能出候选
实测同一条查询：mmx 返回 10 条 organic，其中仅 **1 条** 是 x.com 链接，且不符合 `x.com/<handle>/status/<id>` + watchlist 46 人 + 未 seen 的联合条件。
`scan-slot.sh` 要求「URL 是 X 帖 + handle 在 watchlist + AI 关键词命中 + 未发过」，而 mmx 是通用全网搜索、不支持 `from:` 且 X 反爬不索引 → 命中率接近 0。这是设计层面的，不是运气问题。

## 可选线索（仅记录，未验证、未采用、未成稿）
mmx 结果里反复出现三个 AI 话题，但来源全是聚合站/SEO 页，无法核实真伪与热度，不满足「≥15K views + 可截图验证」：
- Karpathy 加入 Anthropic（多站转载，无一手来源）
- Claude Opus 6 泄露 / Gemini 4 Carbon 泄露（爆料类，无官方）
- OpenAI 同日发布新模型（金融新闻转述）

## 需要 Fang 决策的一件事
要让这套 automation 在本 host 真正「真扫 + 真发」，三者至少通一条：
1. 给本 thread 注入 `mcp__cua_repl__js`（原设计路径）；
2. 放开沙箱对 `x.com` / `r.jina.ai` 的出网（Plan B/X 即可用）；
3. 或把发布动作留在 Codex session 那个 host 跑，本 host 只做选题与草稿。

现状：本 host 只能到 Plan C，硬跑到顶就是 0 候选。

## 附带发现（未改）
`scripts/health-check.sh` 第 32 行遍历 `published-posts.json` 时假设元素是 dict，实际遇到 str → `AttributeError: 'str' object has no attribute 'get'`，体检在「1. state 解析」后中断（不影响上面的结论，数据本身可读）。
