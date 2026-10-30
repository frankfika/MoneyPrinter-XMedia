---
name: post-writer-x
description: X 文案 — 接 hot-topic-tracker 出的素材包，按 `state/style-x.yaml` 写 X 口语爆款风文案（80-180 字、含 1 个具体延伸点/反问/数字/案例、无 OpenCSG / AI 托管字眼）。本 skill **只写不发**；发 X 交给 publisher-x。
---

# X 文案

## 输入
- `outputs/<YYYY-MM-DD>-<slot>/<topic>/material.yaml`
- `state/style-x.yaml`（写作规范）
- `state/forbidden.yaml`（红线）

## 工作流
1. 读素材包 + 规则
2. 打开 `material.yaml#original.url`，截原帖正文+配图区 → `screenshots/x-1.png`
   （X 源走 `scripts/browser/xb.py`；web 源走**内置浏览器**（见 publisher-x 的「浏览器通道」）。
   截图路径相对仓库根）
3. 打开 `evidence_links[*].url`，截标题+关键段或关键图 → `screenshots/x-2.png`（可多张）
   - **web 源**：`evidence_links[0].url` = 第三方原文 → 截它的标题 + 关键段落/关键数字
   - **事实核对（web 源必做）**：正文里要用的每个数字 / 原话，回 `original.url` 核对。
     aihot 的摘要**只是线索**，不许直接抄 —— 抄错了就是发出去的事实错误。
     截不到原文（要登录 / 404）→ 换选题，别靠摘要硬写。
4. 决定 `treatment_hint`：
   - `first_person_original`：用 Frank 自己的口吻自撰
   - `quote_retweet`：X 应用「引用转发 + 你的短评」
5. 按 `style-x.yaml#structure` 生成正文
6. 落盘到 `outputs/<YYYY-MM-DD>-<slot>/<topic>/x.txt`
7. 自检 `style-x.yaml#self_check`
8. **过闸门**（不可跳过）：
   ```bash
   python3 scripts/prepublish.py outputs/<YYYY-MM-DD>-<slot>/<topic>/
   ```
   exit 0 才能交给 publisher-x。exit 1 = 改到过为止，或不发。
   规则见 `state/ai-taste-rules.json`，检测器 `scripts/humanize.py`。

## 长度与结构

- **80-180 字**（pulse 的 inbound reply）；outbound reply 80-320 字
- 含 **1 个具体延伸点 / 反问 / 数字 / 案例**
- 不堆 hashtag（0~1 个）、不堆 emoji（0~2 个）
- 不写「配图如下 / 见下图 / 快去看」
- 风格随轮次变化：有时短句连发、有时一长段论证、有时反问结尾

## 输出
- `outputs/<YYYY-MM-DD>-<slot>/<topic>/x.txt`
- `outputs/<YYYY-MM-DD>-<slot>/<topic>/screenshots/*.png`

## 引用规则（web 源）

- 正文末尾贴 **`evidence_links[0].url`（第三方原文）**，不要贴站内阅读页（aihot 站内页等）。
  X 会自动把文末链接渲染成引用卡片 —— 正好当出处，不用手动点 Quote RT。
- 贴链接会触发 X 的 auto_quote_embed（见 `state/style-x.yaml#x_auto_behavior`），
  所以**这类帖天然是「引用 + 短评」形态**，正文别写成自说自话的长论证。
- 原文是英文/机器翻译站（aihot 收录的多是英文信源）→ 数字与专有名词照抄原文，不要自己翻译转述。

## 不做
- 不发 X（交给 publisher-x）
- 不生成 AI 配图
- 不写 OpenCSG / 公司内容
- 不编造 Frank 没做过的经历
- 不出现 Chinese AI 公司名（DeepSeek / Moonshot / MiniMax 等）

## 与 publisher-x 交接
- 出稿后立刻把 post_id 加进 `seen-posts.json#entries`
- 把 `material_id` / `screenshots[]` 写进 `x.txt` meta 行
- **写完 state 记得同步 `state/index.json`**
