---
name: publisher-x
description: X 发布 — 接 post-writer-x 出的 x.txt，**用 mcp_browser 在已登录的 X 里真实发出**，回传帖 URL。本 skill **不写文案**；遇限流立即停，不假装已发。
---

# X 发布

## 前置

- 读 `private/account-safety.yaml#x`
  - `publish_mode == agent` 才能自动发；`draft_only` / `manual` 退化为只出草稿
  - `login_state == logged_in` 才走浏览器路径；否则把链接给 Frank
- 读 `state/forbidden.yaml#login_rules.x_login`
  - 遇 `We've temporarily limited your login` 立即停手
- 读 `state/schedule.yaml#publish_gates` —— **闸门不通过就不发**
  - Frank 自己在间隔窗口内发过帖 → 零发送
  - 上一条原创 12h 后 likes 仍 ≤ 2 → 零发送
  - **不要为了「每轮要有产出」而发**

## 工作流

### 1. 打开 compose
```json
{"action":"navigate","input":{"url":"https://x.com/compose/post"}}
```
X 是 SPA，URL 不变，DOM 里出现 compose modal。

### 2. 填正文（**唯一稳定路径**）
```json
{"action":"inspect","input":{}}
```
拿到 compose 文本框的 ref 后：
```json
{"action":"fill","input":{"ref":"<ref>","text":"<正文>"}}
```
`fill` 一次性填入，比逐字 type 可靠。

### 3. 发送 —— **`fill` + `Cmd+Enter`**
```json
{"action":"press_key","input":{"key":"Enter","modifiers":["Meta"]}}
```
- **Post button click 不可靠** —— `tweetButtonInline` 是 disabled 的，AX 树里最先出现的永远是它
- Cmd+Enter 后 **wait 8-10 秒**（不需要更久）

### 4. 验证真发 —— **用 search，不要靠 profile**
```json
{"action":"navigate","input":{"url":"https://x.com/search?q=from:FrankFika+<unique-keyword>&src=typed_query&f=live"}}
```
- unique keyword = 自己帖里最 distinctive 的词（**不要用源帖已占用的词**）
- 检查结果第一篇是不是 own_post，取 `a[href*='/FrankFika/status/']` 拿 post_id

> ⚠️ **Cmd+Enter 后不要查 profile / with_replies / home feed** —— 这几处有各自的缓存与个性化排序延迟（实测 8-30s 内不会刷新到顶部），读了会误判成失败，然后想「保险再发一次」→ 触发 X 反重复拦截。
> ⚠️ **X live search 只能用 1 个引号短语或最多 2 词**，三词以上一律 0 结果。

### 5. 配图（**当前默认不做**）
`mcp_browser` 的真图 upload 路径（隐藏 `input[type=file]` / filechooser）在 in-app browser 里
长期不可用 —— `data-testid="fileInput"` 的 ref 拿不到，`upload_files` 会报 invalid_input。

**当前默认发纯文字帖。** 配图路径恢复前，不要在这上面反复试。

### 6. 落盘
- `x.txt` 末尾追加 `# posted_url: <url>` + `# posted_at: <iso>`
- `published-posts.json` 加新条目（**「真发历史」的唯一事实源**）
- `seen-posts.json` 加 `posted_to_x`
- **`state/index.json` 同步更新**（漏了下一轮去重会重发）
- `private/account-safety.yaml#x.last_published_at` 更新

## 关于 X 自动 quote embed

`state/style-x.yaml#x_auto_behavior.auto_quote_embed`：正文里出现 x.com 链接会被 X 自动识别成 Quote Repost，不必手动点 Quote。

## 失败兜底（必须诚实报告，不假装已发）

| 现象 | 动作 |
|------|------|
| 登录墙 / 验证码 | 停手，把 URL 给 Frank |
| `We've temporarily limited your login` | 停手，告诉 Frank，不硬刷 |
| Cmd+Enter 后 URL 跳 `/home` + modal 关 | **这是真发信号**，走第 4 步用 search 验证 |
| Cmd+Enter 后 search 也查不到 | 停手，写 `posted_status: uncertain`，**不要盲 retry** |
| `navigate` 超时 | `query` 看 URL：URL=目标 → 再 wait；URL 没变 → 导航层已死，兜底写零动作 |
| `Validation failed: root: must not have additional properties` | 原样重发即可 |

> ⚠️ **不擅自重试 >1 次**。第二次 Cmd+Enter 会触发 X 的反重复拦截（「Whoops! You already said that.」），
> 那是**真实的 spam 信号**，比漏发严重。

## 不做
- 不绕过二次验证
- 不把失败当成功
- 不在没拿到 own_post URL 的情况下声称「已发」
