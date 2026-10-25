---
name: browser-use-utils
description: 浏览器操作工具集 — 给 hot-topic-tracker / post-writer-x / publisher-x / publisher-xhs 共享使用。封装 mcp_browser 抓 X 时间线、截图、登录态检测、真实计数读取等通用动作。
---

# Browser Use 工具集（mcp_browser）

所有浏览器操作都走 `mcp_browser`（MiniMax Code 的 in-app Browser），不要混用其他浏览器栈。

> ⚠️ **第一次用必须先加载 skill**：`skill(name="browser-use:control-in-app-browser")`，
> 而且必须是**那一步唯一的工具调用**，拿到完整 SKILL.md 之后再调 `mcp_browser`。
> 直接调 `mcp_browser` 会返回 `SKILL_REQUIRED`。

## 通用动作

### 打开 URL
```json
{"action":"navigate","input":{"url":"https://x.com/<handle>"}}
```
- 当前 tab 已有内容且用户要保留 → 用 `open_tab`，不要 `navigate`
- 明确要替换当前 tab → `navigate` + `replaceCurrentTab: true`

### 等页面稳定
```json
{"action":"wait","input":{"kind":"timeout","timeout":3000}}
```
navigate 之后建议 wait 一下再 query，否则拿到的是 spinner 页面。

### 读页面文本
```json
{"action":"query","input":{"kind":"text","selector":"[data-testid='tweet']","maxChars":6000}}
```
- `kind:"text"` → 可见文本
- `kind:"dom"` → 需要 markup 时用（读 aria-label 必用 dom）
- `kind:"semantic"` → 按可见文字找可操作元素的 ref
- 元素 ref 用 `inspect` 拿

### 截图
```json
{"action":"screenshot","input":{}}
```
截图结果是**模型可见的检查证据**，默认不发给用户。
用户明确要看时才通过 `userDelivery.mediaMarkup` 发一次。

### 检测登录态
- X：左下角出现 `@FrankFika` 账号标记 / 顶部有「Post」按钮 → logged_in
- XHS 创作者中心：URL 含 `creator.xiaohongshu.com` 且无登录弹窗 → logged_in

> 通用 shell / 页面标题 / 「登录」链接 **都不算** 登录态证据。

### 读真实计数（重要）

```json
{"action":"query","input":{"kind":"dom","selector":"[data-testid='like'], [data-testid='unlike']"}}
```
- likes → `aria-label="N Likes. Like"` / `"N Likes. Liked"`
- replies → `aria-label="N Replies. Reply"`（`[data-testid='reply']`）
- views → 页面明文 `N Views`

> ⚠️ **页面级 selector 只返回首个匹配**。detail 页有多条帖时，首个匹配可能不是目标帖。
> 正确做法：先把目标帖滚进视口，看**它自己那条 action bar** 的视觉证据。
> ⚠️ **底部大数字是 views 不是 likes**，两者差一个数量级。

### 填文本 + 发送
```json
{"action":"fill","input":{"ref":"<ref>","text":"<正文>"}}
```
然后 `press_key` 发 `Meta+Enter`（= Cmd+Enter）。

> `fill` 每次都会清空目标，不需要传 `clear`。

## 失败兜底

| 现象 | 动作 |
|------|------|
| 登录墙 | 停手，把 URL 给 Frank |
| 二次验证 / 验证码 | 停手，把页面 URL 给 Frank，**绝不**自己读验证码 |
| 限流 / 临时封 | 停手，写 memory |
| `navigate` 超时 | `query` 看 URL：URL=目标 → 页面在加载，再 wait；**URL 没变 → 导航层已死，别重试同一 URL** |
| `reload` 报 `browser_action_failed` / `SKILL_REQUIRED` | 机器休眠后 browser 整体失效，重载 skill 修不好 → 兜底写零动作，等下一轮（机器一醒即自愈） |
| `Validation failed: root: must not have additional properties` | 原样重发即可 |

## 铁律（跨 skill 通用）

- **不发起 campaign 前先读 `state/forbidden.yaml`**
- **真发验证用 search 拿 own_post URL**，不要靠 profile / with_replies / home feed
- **不盲 retry**：Cmd+Enter 第二次会触发 X 反重复拦截
- 任何「拿不到真实结果」→ 老实写「未发」+ 原因，**不装忙**
