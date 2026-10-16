# X 文案 Schema（短文助手 → publisher-x）

落盘到 `outputs/<MMDD>-<slot>/<topic>/x.txt`，纯文本 UTF-8。

```yaml
# meta（用 # 写在文件首，方便人读；脚本会忽略 # 行）
# material_id: "MMDD-pm-03"
# author_handle: "OpenAI"
# source_url: "https://x.com/OpenAI/status/..."
# draft_at: "2026-10-15T15:08:00+08:00"
# screenshots: [x-1.png, x-2.png]

# 正文（# 之后）
<正文从这里开始，单行 80 字内，短句换行>
```

## 字段约束（脚本校验）
- `material_id` 必填且与 material.json 一致
- `author_handle` 必填且与素材一致
- `source_url` 必填
- 正文：
  - ≥80 字、≤500 字
  - ≥1 个具体数字 / 链接
  - 无 OpenCSG / AI 托管 / AI 生成图相关字眼
  - hashtag ≤1 个
  - 无「配图如下 / 见上图」类元说明
- 截图：`screenshots/` 目录下 ≥2 张真实截图
