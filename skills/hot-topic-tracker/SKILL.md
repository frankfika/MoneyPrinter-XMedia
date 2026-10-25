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

1. **Plan A · mcp_browser 真扫**（`mcp_browser` 工具在 inventory 里）
   - `navigate` 到 `x.com/<handle>` → `query kind=text` 抓 timeline → 解析 post_id + view count
   - 优点：完整 timeline + 实时 view count + 可触发图片附件（publisher-x 同链路）
   - 缺点：休眠后可能整体失效（**机器一醒即自愈**）
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

## 工作流

1. 判断可用 Plan（Plan A 是默认路径）
2. 扫 watchlist.yaml `status: active` 的 handle（**≥ 2 个就够**，不用 ≥ 3）
3. 套 filter-rules.yaml：
   - AI 关键词命中（zh/en 关键词任一）
   - 浏览量 ≥ `min_view_count`
   - 不在 `drop_when` 列表
   - **优先 practitioner 源而不是官方账号**（官方号受众未必最优，这是待验证假设）
4. 比对 `state/index.json` 的 `seen` 段（post_id 已发过则丢）—— **不要全量读 seen-posts.json**
5. 命中后写 `material.yaml` 到 `outputs/<YYYY-MM-DD>-<slot>/<topic>/`
6. 给 post-writer-x 接力写 `x.txt`

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

## 不做
- 不写完整文案
- 不发任何平台
- 不叫醒公众号 / 长文 bot

## 失败兜底
- Plan A mcp_browser 不可用 → 退 Plan B
- Plan B jina.ai 不可达 → 退 Plan C
- Plan C mmx 不可用 → 退 Plan D
- 全部 Plan 都 down → inbox item 给 Frank，**不要每轮都跑一遍然后静默**
