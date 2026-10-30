---
name: post-writer-xhs
description: 小红书文案（普通版）— 接 post-writer-x 的同一份素材包，按 `state/style-xhs.yaml` 写自然口语小红书文案（标题 ≤20 单位、300~700 字、3~8 个标签、≥2 张真图、无 AI 托管 / 自动发文相关字眼）。本 skill 只负责出稿；是否发布看 publisher-xhs。
---

# 小红书文案（普通版）

> ✅ **2026-10-29 17:12 首篇已发布**（note_id `6ae30e1b0000000033012638`）
>
> 账号可用，这条线正常跑：文案照常写，产出落到 `outputs/<MMDD>-<slot>/<topic>/xhs.txt`，
> 由 `publisher-xhs` 填进创作服务平台并发布。
> ⚠️ 风险在**操作层面**不在文案：文案只需 AI 味清零，操作约束见 publisher-xhs。

## 输入
- 同 post-writer-x 的素材包 + 同一批 `screenshots/*.png`

## 工作流
1. 读 `state/style-xhs.yaml` + `state/forbidden.yaml`
2. 写标题（≤20 **字符**，小红书按字符数卡）+ 正文（300~700 字，分段）+ 标签（3~8 个）
3. 落盘到 `outputs/<MMDD>-<slot>/<topic>/xhs.txt`
4. 自检 `style-xhs.yaml#self_check`
5. **AI 味闸门必跑**：`python3 scripts/humanize.py scan outputs/<dir>/xhs.txt --json` → soft_score 必须是 0
   - 常见 LLM 指纹：📌/💡 当小标题、「为什么值得看」式收尾、三条并列 bullet、结尾甩问题、四项枚举（州、市、部落、属地）
   - 修法示例见 `outputs/1029-pm-gsa-procurement/xhs.txt`（软分 3 → 0）
6. `python3 scripts/prepublish.py --text "<正文>" --no-rewrite --json` → passed 必须 true
7. 标题里**不要留空格**（小红书按字符数卡，20 字符是硬上限）


## 输出
- `outputs/<MMDD>-<slot>/<topic>/xhs.txt`
- 复用同批 screenshots（无需重复截）

## 不做
- 不写「AI 托管发文 / 自动互动 / Token / 提示词工程」类黑话
- 不发 OpenCSG / 公司内容
- 不写「快去看」「保姆级」「一键」

## 风格边界
- 不要像 X 那么短：XHS 偏多段 / emoji 适量 / 像在讲故事
- 不要把 X 文案直接复制过来
