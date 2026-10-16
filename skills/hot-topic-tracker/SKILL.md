---
name: hot-topic-tracker
description: 热点追踪 — 在 9/12/15/18/21（上海时间）扫 `state/watchlist.yaml` 的 46 个 X 账号，过滤 AI 关键词 + 浏览量 ≥1.5 万，输出符合 `schemas/material-pack.schema.md` 的素材包。本 skill **只抓不写**；写稿交给 post-writer-x。
---

# 热点追踪

## 触发
- cron 9/12/15/18/21（上海）见 `state/schedule.yaml`
- Fang 单链「扫一下 @xxx」/「改这个」也走这里（直接查该账号时间线，跳过名单）

## 输入
- 触发时刻（slot）
- 名单：`state/watchlist.yaml`（只扫 `status: active`）
- 规则：`state/filter-rules.yaml`

## 工作流
1. 对每个 active 账号，调 `mmx search query --q "from:<handle> ..."` 或用 `mcp__cua_repl__js` 打开 x.com/<handle> 抓时间线
2. 取最近 ~30 分钟内的原创帖（非转推、非回复）
3. 套 `filter-rules.yaml`：
   - AI 关键词命中（zh/en 关键词任一）
   - 浏览量 ≥ `min_view_count`
   - 不在 `drop_when` 列表
4. 比对 `state/seen-posts.json`（post_id 已发过则丢）
5. 命中后写一份 `material-pack.yaml` 到 `outputs/<MMDD>-<slot>/<topic>/material.yaml`

## 输出
- `outputs/<MMDD>-<slot>/<topic>/material.yaml`
- 选填 `screenshots/raw-<handle>-<post_id>.png`（截图原帖原文用）

## 不做
- 不写完整文案
- 不发任何平台
- 不叫醒公众号 / 长文 bot

## 失败兜底
- X 登录墙 / 限流：停手，log 到 `logs/hot-topic-tracker.log`，告诉 Fang
- 没有命中：本轮空跑，log 写 `no_hit`
