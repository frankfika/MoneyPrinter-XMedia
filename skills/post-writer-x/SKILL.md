---
name: post-writer-x
description: X 文案 — 接 hot-topic-tracker 出的素材包，按 `state/style-x.yaml` 写 X 口语爆款风文案（≥80/≤500 字、≥1 个数字 / 链接、≥2 张真图、无 OpenCSG / AI 生成图相关字眼）。本 skill **只写不发**；发 X 交给 publisher-x。
---

# X 文案

## 输入
- `outputs/<MMDD>-<slot>/<topic>/material.yaml`
- `state/style-x.yaml`（写作规范）
- `state/forbidden.yaml`（红线）

## 工作流
1. 读素材包 + 规则
2. 用 `mcp__cua_repl__js` 打开 `material.yaml#original.url`，截原帖正文+配图区 → `screenshots/x-1.png`
3. 打开 `evidence_links[*].url`，截标题+关键段或关键图 → `screenshots/x-2.png`（可多张）
4. 决定 `treatment_hint`：
   - `first_person_original`：用 Fang 自己的口吻自撰
   - `quote_retweet`：X 应用「引用转发 + 你的短评」
5. 按 `style-x.yaml#structure` 生成正文
7. 落盘到 `outputs/<MMDD>-<slot>/<topic>/x.txt`
8. 自检 `style-x.yaml#self_check`

## 输出
- `outputs/<MMDD>-<slot>/<topic>/x.txt`
- `outputs/<MMDD>-<slot>/<topic>/screenshots/*.png` ≥2 张

## 不做
- 不发 X（交给 publisher-x）
- 不生成 AI 配图
- 不写 OpenCSG / 公司内容
- 不编造 Fang 没做过的经历

## 与 publisher-x 交接
- 出稿后立刻 `add seen-posts.json#entries` 加入 post_id
- 把 `material_id` / `screenshots[]` 写进 `x.txt` meta 行
