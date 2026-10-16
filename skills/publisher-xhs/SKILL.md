---
name: publisher-xhs
description: 小红书发布（草稿模式）— 默认**只把 xhs.txt + screenshots 路径交给 Fang 手贴**。只有当 `private/account-safety.yaml#xhs.ban_status.is_banned == false` **且** Fang 明确说「可以存草稿了」时，才用 browser use 登录创作者中心，**只存草稿、绝不点发布**。
---

# 小红书发布

## 决策（每次执行前先查 `private/account-safety.yaml#xhs.ban_status`）

| is_banned | Fang 授权「可以存草稿」 | 动作 |
|-----------|----------------------|------|
| true | — | **不要进后台**；把 xhs.txt + screenshots 路径给 Fang |
| false | false | 把 xhs.txt + screenshots 路径给 Fang |
| false | true | 用 browser use 登录创作者中心，**只存草稿，绝不点发布** |

## 工作流（仅授权后执行）
1. 读 `state/forbidden.yaml#login_rules.xhs_creator_center`
2. `mcp__cua_repl__js` 打开小红书创作者中心，确认登录态
3. 切到「图文笔记 → 写笔记」
4. 填标题、正文、上传 screenshots
5. **点「存草稿」按钮**，**绝对不要点「发布」**
6. 截图存草稿结果页 → `screenshots/xhs-draft-saved.png`
8. 失败兜底：见下表

## 失败兜底
| 现象 | 动作 |
|------|------|
| 登录墙 / 验证码 | 停手，把 URL 给 Fang |
| 找不到「存草稿」按钮 | 截图当前页给 Fang，**不要点任何看起来像发布的按钮** |
| 误点「发布」风险 | 立刻关闭，Fang 申诉 |

## 不做
- 不点发布（不管发生什么）
- 不在 App 外申诉（App 内由 Fang 操作）
- 不在未授权时登录创作者中心
