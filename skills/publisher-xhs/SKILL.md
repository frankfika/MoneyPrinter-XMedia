---
name: publisher-xhs
description: 小红书发布 — 用 xb.py（专用 Chrome，CDP 9222，DOM 无视觉）登录创作服务平台，把 xhs.txt + screenshots 填成图文笔记并**点「发布」提交**。2026-10-29 17:11 起 Frank 授权 agent 代点发布。风险在操作层面：走 xb.py 单通道、不碰平台 AI 功能、不改任何设置。
---

# 小红书发布

> ✅ **2026-10-29 17:12 首篇已发布**（note_id `6ae30e1b0000000033012638`，状态「审核中」）
>
> 口径演变：**只存草稿**（17:07 Frank 当次选择）→ **17:11 Frank 改口**「你集中一个时间去点吧。。或者分散去帮我点哈」→ agent 代点发布。
> 封禁原因是「利用 AI 托管进行发文/互动」—— **风险在操作层面，不在文案**。文案只需把 AI 味清零（soft_score 0），操作才决定账号安危。

## 决策（每次执行前先查 `private/account-safety.yaml#xhs`）

| `agent_publish_allowed` | 动作 |
|---|---|
| false | 写稿 → 存草稿 → 停手，把草稿位置告诉 Frank |
| true | 走完整流程，**点「发布」**，点完回读笔记管理页确证 |

> `agent_publish_allowed` 的值由 `private/account-safety.yaml#xhs` 说了算，**不要自己改**。
> 当前 = **true**（2026-10-29 17:11 Frank 明确授权）。

## 🛡️ 操作层面 4 条硬约束（违反即回到被封风险）

1. **只走 xb.py 单通道**（2026-10-31 起唯一浏览器通道）：
   ```bash
   python3 scripts/browser/xb.py --action '<json>'
   ```
   Playwright 驱动专用 Chrome（profile `~/.shortbot-browser-profile`，CDP 9222，launchd
   `com.fangchen.shortbot.browser` 保活），纯 DOM 操作、无视觉模型。
   前置：Fang 已在该浏览器（9222 窗口）**一次性登录小红书创作服务平台**；每轮开工先
   `{"action":"login_state"}` 自检，未登录 → 本轮零动作，如实记录「专用 Chrome 未登录，需 Fang 在 9222 窗口登录」。
   - 动作契约见 `scripts/browser/README.md`；原语 navigate / open_tab / wait / query / inspect / click / fill / press / screenshot / upload / login_state。
   - 历史决策：2026-10-30 曾切「Codex 内置浏览器」，**2026-10-31 起迁回 xb.py**，原因：本地化 + 无视觉（内置浏览器被组织策略禁用）。
2. **平台 AI 功能一个不碰**：智能标题、创作助手（`.chat-fab` 客服气泡）、原创声明（保持 unchecked）、内容类型声明 —— 全部保持默认。
3. **一个设置都不改**：可见性保持「公开可见」、不开定时发布、原创声明不动 → 表单状态与手工发一条完全一致。
4. **不做「定时自动发文」式的连发** —— 节奏分散（见 `state/schedule.yaml#xhs`），且每次发布前仍出确认卡。

## 工作流（首次填稿）

1. 读 `state/forbidden.yaml#login_rules.xhs_creator_center` + `private/account-safety.yaml#xhs`
2. 导航到 `https://www.xiaohongshu.com/explore`（**别直连 `/creator/publish/publish`，那个路由已 404**）
3. 点左侧/底部「**发布**」→ 落到 `creator.xiaohongshu.com/publish/publish`（query 变 `?source=official&from=tab_switch`，正常，**不是**导航失败）
4. 顶部切「**上传图文**」标签（切标签会改 URL）
5. 图片走 **`upload` 动作**（2026-10-31 新增，不再用剪贴板粘贴 PNG）：
   ```bash
   python3 scripts/browser/xb.py --action '{"action":"upload","input":{"selector":"input[type=file]","files":["/abs/outputs/.../screenshots/a.png","/abs/.../b.png"]}}'
   ```
   传 `screenshots/*.png`（≥2 张真图，绝对路径）→ 关掉「图片可以编辑啦」引导弹窗
6. **标题**：`xhs.txt` 第 1 行。**XHS 上限是 20 个字符**（不是仓库的"单位"算法）——「美国政府买Claude打4折，不用先交钱」正好 20 字符
7. **正文**：一次 `fill` 灌完整正文 + 标签行
   - 填完**点一下标题框让编辑器失焦**，话题联想面板才会关
   - 编辑器会把 `#Claude` 拆成 `<span class="suggestion">#Claud</span>e` —— XHS 自己的话题联想插件，**平台预览显示完整**，不用修
8. **点「暂存离开」**（底栏白按钮，class `ce-btn white`）= 存草稿并退出
   - ⚠️ 底栏没有叫「存草稿」的按钮，**别找错**
9. 验证：`草稿箱(N)` 计数 + 列表里的标题与保存时间

## 发布（二次发布：从草稿箱发布，最稳）

**优先走这条路** —— 比重新填一遍更稳，标题/正文原样带过去，不会被编辑器改写。

1. 进「笔记管理」`https://creator.xiaohongshu.com/new/note-manager?source=official`
2. 点草稿条目的「**编辑**」→ 打开草稿
3. **回读标题 input 的 value + 正文，与 `xhs.txt` 逐字核对** —— 防草稿被截断/改写
4. `query` 找到红色「发布」按钮（class `ce-btn bg-red`）
5. 点它 → URL 变 `…/publish/publish?source=official&published=true`，编辑器重置为空白
6. 回笔记管理页确证

> 若发布按钮定位/点击失败 → **停手告诉 Frank**，不要瞎点（可能误触别的按钮）。

## 验证（发布后必做）

在笔记管理页回读并确认这 4 项：
1. **note_id** —— 从 DOM 的 `data-impression` 属性里读 `"noteId":"..."`（**别自己编**）
2. 标题逐字一致
3. 状态（审核中 / 已通过 / 未通过）+ 时间
4. 草稿箱归零

## 发布后落盘（别忘）

- `private/account-safety.yaml#xhs`：`last_published_at` / `last_published_note_id` / `last_published_title` / `last_published_url` / `last_published_status`
- `state/published-posts.json`：加条目（`platform: xiaohongshu`）
- `state/index.json`：`seen[note_id]` + `published[note_id]`（写完必须同步）
- `state/recent-picks.json`：加 pick 条目
- `state/memory/xhs.md`：追加轮次段（前面加一行 `<!-- round -->`）

## 失败兜底

| 现象 | 动作 |
|------|------|
| 登录墙 / 验证码 | 停手，把 URL 给 Frank（**不碰验证码、不自动过二次验证**） |
| 弹「电脑设备登录超限，请重新登录」 | 让 Frank 扫码/手机号登录，别反复刷 |
| 找不到「上传图文」/「暂存离开」 | 截图当前页给 Frank，**不要点任何看起来像「发布」的按钮** |
| 发布键点不动 | **停手**告诉 Frank，不要瞎点（可能误触别的按钮） |
| 误点「发布」 | 立刻停手告诉 Frank，由他删稿/处理 |

## 不做

- 不碰平台 AI 功能：智能标题、创作助手（chat-fab）、原创声明、内容类型声明 —— 全部保持默认
- 不改可见性 / 不开定时发布 —— 表单状态必须与手工发一条完全一致
- 不在 App 外申诉（App 内由 Frank 操作）
- 不把 X 的文案直接复制到小红书
