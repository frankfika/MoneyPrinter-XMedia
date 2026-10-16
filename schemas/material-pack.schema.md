# 素材包 Schema（热点汇总 → 短文助手）

每个素材包一个 JSON / YAML 文件，落盘到 `outputs/<MMDD>-<slot>/<topic>/material.json`，
或运行时直接 push 给短文助手。

```yaml
material_id: "MMDD-<slot>-<NN>"        # 全局唯一
slot: am | pm | noon | eve | night     # 与 schedule.yaml#cron_slots 对齐
scanned_at: "2026-10-15T12:00:00+08:00"  # 上海时间 ISO

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

## 字段约束
- `original.url` 必填，缺则素材包不可用
- `author.handle` 必须在 `state/watchlist.yaml` 内
- `metrics.views >= state/filter-rules.yaml#min_view_count`
- `ai_match == true` 才进选

