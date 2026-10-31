# 端到端测试报告 · 2026-10-15 15:00 上海

测试题目：Karpathy 10/12 「5000 人见前沿 AI」帖  
post_id：`2109361546505966046` · 浏览 6,421,387 · 赞 43,071 · 转 7,884

## 1. 事实源加载
| 文件 | 状态 |
|------|------|
| state/watchlist.yaml | ✅ 解析通过，46 账号（25 EN + 21 ZH），@karpathy 在 active |
| state/filter-rules.yaml | ✅ 命中 AI 关键词 + 浏览量 6.4M 远超 1.5 万阈值 |
| state/style-x.yaml | ✅ 写入 X 文案遵循 |
| state/style-xhs.yaml | ✅ 写入 XHS 文案遵循 |
| state/forbidden.yaml | ✅ 无红线命中 |
| state/account-safety.yaml | ✅ X publish_mode=agent，XHS is_banned=true（草稿模式） |

## 2. 浏览器路径（mcp__cua_repl__js + Codex in-app browser）
| 步骤 | 结果 |
|------|------|
| 打开 x.com/karpathy | ✅ 登录态 = 陈放Frank🕊️ / x.com/FrankFika |
| 截图时间线 → screenshots/x-karpathy-timeline.png | ✅ 115 KB |
| 导航到 status/2109361546505966046 | ✅ 标题更新为原帖文本 |
| 截图原帖详情 → screenshots/x-post-detail.png | ✅ 147 KB，含 4-tier 表格 + 6.4M 浏览 |
| 打开 x.com/compose/post | ✅ 标题 "Compose new post / X"，路径通 |
| 实际发 X | ⏸️ **未发** — 需 Fang 单独授权本条 |

## 3. X 文案产出（outputs/1015-pm/karpathy-frontier-5000/x.txt）
- 字数 242（style-x.yaml target 180~320）✅
- 含具体数字（5000 / 60亿 / 2000万 / 6.4M）✅
- 含原帖链接 ✅
- hashtag 0 个（≤1）✅
- 无 forbidden_phrases ✅
- 无 OpenCSG / AI 托管 ✅

## 4. XHS 文案产出（outputs/1015-pm/karpathy-frontier-5000/xhs.txt）
- 标题 "全球只有 5000 人见过真前沿 AI" — 13 单位（≤20）✅
- 正文 569 字符（300~700）✅
- 标签 5 个（3~8）✅
- 无 AI 托管 / 自动发文 ✅
- 无 OpenCSG ✅

## 5. 截图
- screenshots/x-karpathy-timeline.png 115 KB ✓
- screenshots/x-post-detail.png 147 KB ✓
- screenshots/x-compose-ui.png 12 KB ✓
> 三张都是 X.com 真实截图，无 AI 生成图。

## 6. 去重状态
- seen-posts.json：加入 post_id 2109361546505966046 ✅
- recent-picks.json：加入 topic_signature `karpathy-frontier-5000-tiers`，7 天内不再重选题 ✅

## 7. XHS 路径
- **未测试登录/创作者中心** — 账号仍处封禁，未授权不探后台
- xhs.txt 已落盘，按策略交给 Fang App 内手贴

## 8. 验证结果
- 全流程数据流通：watchlist → 选材 → material.yaml → x.txt + xhs.txt → screenshots
- 浏览器 use：可开 X、可截真图、可到 compose（未发）
- 自检脚本：对 style-x.yaml + style-xhs.yaml 的所有硬约束跑过，全部 PASS

## 9. 等指令
- 「发 X」→ publisher-x 走真实发帖
- 「改文案」→ 在 x.txt / xhs.txt 上调整
- 「换题」→ 重跑 hot-topic-tracker

---

## 10. 真实发帖（2026-10-15 17:06 北京）

收到 Fang 「跑一下真的去发啊」明确授权后走完整 publisher-x 流程。

| 步骤 | 结果 |
|------|------|
| 打开 compose | ✅ https://x.com/compose/post |
| AX index click textarea (25) | ✅ Draft.js 编辑器 focus |
| tab.paste 注入 242 字正文 | ✅ textarea 245 字 |
| AX click Choose Files (44) | ✅ filechooser 事件触发 |
| setFiles 2 张截图 | ✅ 2 个 Media 容器出现 |
| AX click Post (13) | ✅ 跳转回 /home |
| 访问 /FrankFika | ✅ 时间线顶部出现新帖 1 second ago |
| 访问新帖 URL | ✅ https://x.com/FrankFika/status/2110416897112248372 渲染正常 |

### 真实帖状态
- **post_id**: 2110416897112248372
- **URL**: https://x.com/FrankFika/status/2110416897112248372
- **时间**: 2026-10-14T17:06:12.000Z (UTC)
- **正文**: 与 x.txt 一致
- **图片**: 2 张真图（原帖截图 + 时间线截图）
- **附加**: X 自动把文末 Karpathy 链接识别成 Quote Repost，原帖作为引用卡嵌入
- **0 互动**: 0 reply / 0 repost / 0 like / 1 view（刚发，正常）

### 落盘更新
- `outputs/.../x.txt` 末尾追加 posted_url + posted_at
- `state/seen-posts.json` 该条 entry 加 `posted_to_x` 子对象（含 own_post_id / url / time / media_count）
- `outputs/.../screenshots/` 加 x-before-post.png / x-after-post.png / x-live-post.png 三张真截图
