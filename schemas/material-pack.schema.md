# 素材包 Schema（热点汇总 → 短文助手）

每个素材包一个 JSON / YAML 文件，落盘到 `outputs/<MMDD>-<slot>/<topic>/material.json`，
或运行时直接 push 给短文助手。

```yaml
material_id: "MMDD-<slot>-<NN>"        # 全局唯一
slot: am | pm | noon | eve | night     # 与 schedule.yaml#cron_slots 对齐
scanned_at: "2026-10-15T12:00:00+08:00"  # 上海时间 ISO
source_kind: x | web                  # ★ x = X 原帖；web = 非 X 源（aihot/tophub/decohack/gh…）

author:
  name: "作者显示名"
  handle: "x_handle"                   # 不含 @
  lang: zh | en

original:
  url: "https://x.com/<handle>/status/<post_id>"  # 必填
  post_id: "1234567890123456789"       # 用于去重
  posted_at: "2026-10-15T11:42:00+08:00"

metrics:
  views: 230000
  likes: 1820
  retweets: 410
  replies: 220

ai_match: true                         # 是否通过 AI 关键词命中

summary: "一句话讲清为什么值得发（数字 / 反差 / 新产品）"

evidence_links:                        # 选填；命中的官网/论文/GitHub
  - label: "官方博客"
    url: "https://..."
  - label: "arXiv 论文"
    url: "https://arxiv.org/abs/..."

screenshots_needed:                    # 给浏览器操作员列清单
  - "原帖正文+配图区"
  - "官方博客标题+关键段落"
  - "产品页 dashboard"

treatment_hint: first_person_original | quote_retweet
  # first_person_original: 公共新闻 / 产品发布
  # quote_retweet: 他人个人经历 / 故事

dedup_hits: []                         # 与 seen-posts.json 比对的结果
```

## 非 X 源（source_kind: web）· Frank 2026-10-27

非 X 源来自 `scripts/sources.py`（aihot / tophub / decohack / gh-trending / ph-buzzing /
producthunt / xbangdan / discoverhub）。字段语义跟 X 源不同，**别硬套**：

```yaml
source_kind: web
source_name: aihot            # 来自哪个源
original:
  url: "https://latent.space/p/ainews-anthropic-s1/"   # = 原文 canonical URL（不是站内阅读页）
  post_id: "url:3f2a91c4b8de"                            # web 源没有 post_id → 用 url 的 sha1 前 12 位
  posted_at: "2026-10-27T15:24:00+08:00"
author:
  name: "Latent Space"
  handle: "latent-space"      # web 源填信源名 slug，不要求在 watchlist.yaml 里
  lang: zh
signal: "行业"                # ★ web 源的热度信号：分类 / 热度值 / stars today / 票数 / 信源数
metrics: null                 # web 源没有 views/likes → 留 null，不要编
read_url: "https://aihot.news/items/nbvleghbxraalsahhggnc6qov"   # 站内阅读页（可选）
evidence_links:               # ★ 引用必须指向第三方原文，不是站内阅读页
  - label: "原文"
    url: "https://latent.space/p/ainews-anthropic-s1/"
```

### web 源的字段约束
- `original.url` = **第三方原文 URL**；`evidence_links[0].url` 同样指向原文（写稿时贴文末）
- `ai_match == true` 才进选（关键词仍按 `state/filter-rules.yaml` 判）
- `metrics` 留 `null`；热度用 `signal` 表达，**不要拿 views 当 likes 用**
- `post_id` 用 `url:<sha1 前 12 位>`，保证 `state/index.json#seen` 的去重键唯一
- **aihot 源：摘要只是线索**，正文里的数字/原话必须回 `original.url` 核对

## 字段约束（X 源）
- `original.url` 必填，缺则素材包不可用
- `author.handle` 必须在 `state/watchlist.yaml` 内
- `metrics.views >= state/filter-rules.yaml#min_view_count`
- `ai_match == true` 才进选

