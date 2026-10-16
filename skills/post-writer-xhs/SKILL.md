---
name: post-writer-xhs
description: 小红书文案（普通版）— 接 post-writer-x 的同一份素材包，按 `state/style-xhs.yaml` 写自然口语小红书文案（标题 ≤20 单位、300~700 字、3~8 个标签、≥2 张真图、无 AI 托管 / 自动发文相关字眼）。本 skill **默认只出草稿**；是否存草稿看 publisher-xhs。
---

# 小红书文案（普通版）

## 输入
- 同 post-writer-x 的素材包 + 同一批 `screenshots/*.png`

## 工作流
1. 读 `state/style-xhs.yaml` + `state/forbidden.yaml`
2. 写标题（≤20 单位）+ 正文（300~700 字，分段）+ 标签（3~8 个）
3. 落盘到 `outputs/<MMDD>-<slot>/<topic>/xhs.txt`
4. 自检 `style-xhs.yaml#self_check`

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
