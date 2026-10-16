---
name: publisher-x
description: X 发布 — 接 post-writer-x 出的 x.txt，**用 browser use 在已登录的 X 里粘贴 + 传图 + 真实发出**，回传帖 URL 给 Fang。本 skill **不写文案**；遇限流立即停，不假装已发。
---

# X 发布

## 前置
- 读 `state/account-safety.yaml#x`
  - `publish_mode == agent` 才能自动发；`draft_only` / `manual` 退化为只出草稿
  - `login_state == logged_in` 才走浏览器路径；否则把链接给 Fang
- 读 `state/forbidden.yaml#login_rules.x_login`
  - 遇 `We've temporarily limited your login` 立即停手

## 工作流（实测有效 · 2026-10-15 post_id=2110416897112248372）

1. 打开 `https://x.com/compose/post`（SPA，URL 不变，DOM 是 compose modal）
2. **AX index click textarea**（Draft.js contenteditable，playwright locator.click 会被 strict mode 卡）：
   - 在 AX 树里找 `text entry area (settable) Description: Post text`
   - `await tab.click(axIndex)` 触发 click
3. **注入正文**（Draft.js 需要 paste 触发 Draft state sync）：
   ```js
   await tab.paste(null, bodyText, { format: "text" });
   ```
   - `null` 表示聚焦到上次 active element
   - format: "text" 强制纯文本
4. **上传图片**（隐藏 file input + X 自定义 chooser）：
   ```js
   // 1) 注册 filechooser 监听
   let fc = tab.playwright.waitForEvent("filechooser", { timeoutMs: 8000 });
   // 2) AX index click "Choose Files" 按钮
   await tab.click(chooseFilesAxIndex);
   // 3) 设文件
   let fcObj = await fc;
   await fcObj.setFiles([absPath1, absPath2]);
   ```
   - 注意：playwright locator.click 在 Choose Files 上会超时；AX index click 才能稳定触发 chooser 事件
   - `setInputFiles` 在 in-app browser locator wrapper 上**不可用**，必须用 filechooser event
5. **等上传完成**：waitForTimeout 8000ms 起，验证 `data-testid="attachments"` ≥ 1 或 DOM 里出现 2+ blob: URL
6. **点 Post**：AX index click "Post" 按钮（label "Post"、不是 disabled 状态）
7. **抓新帖 URL**：
   - 通常 X 跳转到 `/home`，访问 `https://x.com/FrankFika` 找时间线第一条
   - 或直接轮询 profile 时间线的 `link[href*="/status/"]` 拿新 post_id
8. 落盘：
   - `x.txt` 末尾追加 `# posted_url: <url>` + `# posted_at: <iso>`
   - `seen-posts.json#entries[i].posted_to_x` 加子对象
   - `published-posts.json` 加新条目（这是「真发历史」的唯一事实源）
   - 截图：pre-post / after-post / live-post 三张

## 关于 X 自动 quote embed
参见 `state/style-x.yaml#x_auto_behavior.auto_quote_embed`。
简短版：正文里出现 x.com 链接会被 X 自动识别成 Quote Repost，不必手动点 Quote。

## 失败兜底（必须诚实报告，不假装已发）
| 现象 | 动作 |
|------|------|
| 登录墙 / 验证码 | 停手，把 URL 给 Fang |
| `We've temporarily limited your login` | 停手，告诉 Fang，不硬刷 |
| textarea / Choose Files / Post click 超时 | AX index 重试；不要盲目换 locator click |
| filechooser 等不到 | 改用 setInputFiles via evaluate（fallback） |
| 上传图失败 / 网络错 | 重试 1 次，仍失败则告诉 Fang |
| Post 后拿不到 URL | 截图当前页给 Fang，标 `posted_status: uncertain` |

## 不做
- 不绕过二次验证
- 不擅自重试 >1 次
- 不把失败当成功

## 实测注意事项
- **AX index 是稳定坐标**：每次 getAXState 拿到的 index 会变，操作前必须重新看 AX 树
- **Playwright locator click 在 X 上不稳**：Choose Files、textarea click 都曾超时；优先 AX index
- **tab.paste 走 macOS 系统剪贴板**：会自动恢复剪贴板原内容，所以多行 / 中文都不会乱
- **in-app browser 的 locator wrapper 不暴露 setInputFiles**：用 waitForEvent("filechooser") 模式
