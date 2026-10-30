---
name: hot-topic-tracker
description: 热点追踪 — 扫 `state/watchlist.yaml` 的 X 账号，按 filter-rules 过滤（AI 关键词 + 浏览量门槛），输出符合 `schemas/material-pack.schema.md` 的素材包。本 skill **只抓不写**；写稿交给 post-writer-x。
---

# 热点追踪

## 触发
- chuangzuo cron（`30 3,15 * * *`，12h 一轮）
- Fang 单链「扫一下 @xxx」/「改这个」也走这里（直接查该账号时间线，跳过名单）

## 输入
- 触发时刻（slot）
- 名单：`state/watchlist.yaml`（只扫 `status: active`）
- 规则：`state/filter-rules.yaml`

## Fallback chain

启动时先判断可用通道，按优先级尝试：

1. **Plan A · `xb.py` 真扫**（`scripts/browser/xb.py` 可执行）
   - `navigate` 到 `x.com/<handle>` → `query kind=text` 抓 timeline → 解析 post_id + view count
     ```bash
     python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/<handle>"}}'
     python3 scripts/browser/xb.py --action '{"action":"query","input":{"kind":"text","selector":"[data-testid=\"tweet\"]","maxChars":6000}}'
     ```
   - 优点：完整 timeline + 实时 view count + 可触发图片附件（publisher-x 同链路）
   - 缺点：休眠后可能整体失效（`exit 2`，**机器一醒即自愈**）
   - 详见 `skills/browser-use-utils/SKILL.md`
2. **Plan B · r.jina.ai 反代**（curl 能到 jina.ai）

   ⚠️ **jina.ai Reader 是付费 SaaS**（free tier 极小）。anonymous 调用被反 abuse 系统标记时整 x.com 域被封（403 AbuseAlleviationError），需 `JINA_API_KEY` 持续可用。
   - `curl r.jina.ai/https://x.com/<handle>` → Markdown 含 `[时间h](x.com/<handle>/status/<pid>)` + view count
   - 缺点：creator 号 (dotey / testingcatalog 等 `tier: creator`) 会缺 time+URL 块 → 优先扫 `tier: official / executive`
   - 媒体直链：pbs.twimg.com 可 curl 下载，做 screenshots/ 真图
3. **Plan C · mmx search lite**
   - `mmx search query --q "OpenAI Anthropic..." --output json`
   - **不支持 from: / site:x.com 操作符**，X 反爬不索引 → organic 里 x.com 命中稀少，多数轮次 `found 0 candidate(s)`
   - **只适合做素材补充，不替代 X 真扫。** 不要把它当主路径。
4. **Plan D · 手贴队列**（全部 Plan 都 down 时）
   - 不发 X，落盘完成版到 `outputs/<date>-<slot>/drafts/` + `seen-posts.json#entries[].drafted_only=true`
   - inbox item 通知 Frank 手贴
   - 不装忙：候选池真 0 时 status 写 `candidate_count=0, drafted=0, published=0, infra={...}`
5. **Plan E · 非 X 内容源**（`scripts/sources.py`，**不用浏览器，最稳**）
   - Frank 2026-10-27 补充的 8 个源，见下面「内容源清单」
   - 纯 HTTP + 正则，**不依赖登录态、不依赖浏览器** → xb.py 挂了也还能用
   - 详见本文件「内容源清单」小节

## 工作流

1. 判断可用 Plan（Plan A 是默认路径）
2. 扫 watchlist.yaml `status: active` 的 handle（**≥ 2 个就够**，不用 ≥ 3）
3. **扫非 X 源**（`scripts/sources.py`）：**≥ 2 个源就够**，aihot + tophub 是默认两个
4. 套 filter-rules.yaml：
   - AI 关键词命中（zh/en 关键词任一）
   - 浏览量 ≥ `min_view_count`
   - 不在 `drop_when` 列表
   - **优先 practitioner 源而不是官方账号**（官方号受众未必最优，这是待验证假设）
5. 比对 `state/index.json` 的 `seen` 段（post_id 已发过则丢）—— **不要全量读 seen-posts.json**
6. 命中后写 `material.yaml` 到 `outputs/<YYYY-MM-DD>-<slot>/<topic>/`
7. 给 post-writer-x 接力写 `x.txt`

## Plan B (r.jina.ai) 实测菜谱

机构号 (`tier: official / executive`) — Markdown 含 `[<relative_time>](https://x.com/<handle>/status/<post_id>)` + 末位 `[<num>[KM]?]` view count + pbs.twimg.com 媒体直链。

**正则提取**：
```python
TIME_RE = re.compile(r'\[(?P<rel>[^\]]+)\]\(https://x\.com/[^/]+/status/(?P<pid>\d+)\)')
VIEW_RE = re.compile(r'\b(\d+(?:\.\d+)?)\s*([KM]?)\b')
MEDIA_RE = re.compile(r'https://pbs\.twimg\.com/(?:amplify_video_thumb|media|tweet_video_thumb)/[^\s\)]+\.(?:webp|png|jpg|mp4)')
```

**已知限制**：
- creator 号 md 会丢时间戳 → 优先 official 列表
- 长时间请求（15s 内）偶尔返 0 byte → 重试 1-2 次
- pbs.twimg.com 直链 `?format=webp&name=large` 默认能用；先验证文件大小 > 1000 再交付

## 内容源清单（非 X，Frank 2026-10-27 补充）

> **一条铁律：HTML 不进上下文。** 这些站单页 70KB–1MB（tophub 首页实测 333K token），
> 直接抓进 agent 上下文 = 一轮吃掉十几万 token。
> **抓取和解析都在 `scripts/sources.py` 里做，agent 只看它吐的 JSON。**

```bash
python3 scripts/sources.py --list                      # 看所有源 + 分层
python3 scripts/sources.py --source aihot --ep latest --limit 10   # 24h 精选
python3 scripts/sources.py --source aihot --ep hot                  # 当前热点（多信源同时讨论）
python3 scripts/sources.py --source aihot --ep search --q "agent"   # 关键词（最近 7 天）
python3 scripts/sources.py --source aihot --ep daily               # AI 日报
python3 scripts/sources.py --source tophub --limit 20
python3 scripts/sources.py --source all --limit 8 --text            # 全源汇总（紧凑文本）
python3 scripts/sources.py --source aihot --ep latest --material    # 第 1 条 → 素材包骨架（YAML）
python3 scripts/sources.py --selftest                              # 验收：逐源断言还能抽出条目（exit 0 = 全过）
```

**`--material` 直接吐素材包骨架**（`source_kind: web` 形状，见 `schemas/material-pack.schema.md`），
省掉手抄标题/链接/时间戳。骨架里 `_agent_must_fill` 那几项 agent 自己补：
`ai_match` 复核、`evidence_links` 补产品页/论文页、`treatment_hint` 按内容改。

**`--selftest` 是源站改版的哨兵**：源站一改 markup 就红，别等选题轮次静默少了源才发现。

| 源 | 层 | 抓法 | 信号 | 适合 |
|---|---|---|---|---|
| **aihot.news** | T1 | `curl` 匿名，无需 key，返回中文 Markdown | 分类 + 信源数 + **原文 canonical URL** | **中文 AI 选题首选**：Anthropic/OpenAI/论文/教程 |
| **tophub.today/c/ai** | T1 | SSR + 正则 | 热度值 | 全网热榜（掘金/知乎/36氪/安全客…），挖中文角度 |
| **decohack.com** | T1 | SSR + 正则 | 票数 | Product Hunt 热榜中文版 + AI 早报 + HN 热榜 |
| **github.com/trending** | T2 | SSR + 正则 | stars today + 语言 | 开源项目趋势（Frank 200+ 开源项目人设，天然对口） |
| **producthunt.com** | T2 | SSR（条目少） | — | **官方核对源**，不是主选题源 |
| **ph.buzzing.cc** | T2 | SSR + 正则 | PH 票数 | PH + HN 的中文翻译聚合，补 decohack 没覆盖的 |
| **xbangdan.com/intel** | T2 | SSR + 正则 | 热度值 | 基于 X 的情报（海外/中文区/话题/长文） |
| **discoverhub.cn** | T2 | **JS 渲染，curl 拿不到** | — | GitHub 趋势中文版，**必须用内置浏览器**；等价源是 github.com/trending |

### 选题优先级

1. **aihot** `latest` / `hot` —— 唯一带**原文 URL** 的源，直接能进 `evidence_links`
2. **tophub /c/ai** —— 找中文语境的爆点（一条 4095 热度的掘金帖可能比英文新闻更适合 Frank 的读者）
3. **decohack** —— 新产品/新工具（Frank 的「前工程师 + 评测出身」人设对工具天然敏感）
4. **github.com/trending** —— 开源项目（对 Frank 的 200+ 开源项目人设最对口）
5. ph-buzzing / producthunt / xbangdan —— 补充

### 非 X 源的铁律

- **aihot 是「线索源」，不是「事实源」**：它自己都写明「重要事实请回原文核对」。
  写稿用的**数字、原话、结论必须回 `原文` 链接核对**；`摘要` 只能当线索。
- **aihot 使用条款**：匿名只读 ≠ 随便用。个人非商业/组织内部免费；**对外商业产品、客户交付、
  数据转售、批量再分发需书面授权**（https://aihot.news/terms）。当前用法（读 → 自己写稿）属前者；
  一旦要对外交付/做成产品，先找 Frank 确认。
- **去重**：web 源用 `canonical url`（aihot 用 `原文` URL，decohack 用 `/product/<slug>/`）
  生成 `topic_signature` 写进 `state/index.json#seen`；`index.json` 的 `post_id` 位置放
  `url:<sha1 前 12 位>`，避免和 X 的 post_id 混。
- **单源失败不拖垮整轮**：`--source all` 已容错（单源异常只写 `note`，不影响其他源）。
- **限流**：aihot 同一 IP 超 ~60 次/分钟会 429（按 `Retry-After` 等）。别在一轮里反复重试。
- `--limit` 必给：每源默认只取需要的条数，别把整榜灌进来。

## 不做
- 不写完整文案
- 不发任何平台
- 不叫醒公众号 / 长文 bot

## 失败兜底
- Plan A `xb.py` 不可用（exit 2）→ 退 Plan B
- Plan B jina.ai 不可达 → 退 Plan C
- Plan C mmx 不可用 → 退 Plan D
- 全部 Plan 都 down → inbox item 给 Frank，**不要每轮都跑一遍然后静默**
