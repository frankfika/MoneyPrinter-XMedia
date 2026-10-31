---
name: publisher-x
description: X 发布 — 接 post-writer-x 出的 x.txt，**在已登录的 X 里真实发出**（唯一通道 = xb.py，见「浏览器通道」），回传帖 URL。本 skill **不写文案**；遇限流立即停，不假装已发。
---

# X 发布

## 浏览器通道（2026-10-31 起唯一通道 = xb.py）

**唯一浏览器通道** = 仓库内 CLI：

```bash
python3 scripts/browser/xb.py --action '<json>'
```

Playwright 驱动专用 Chrome（profile `~/.shortbot-browser-profile`，CDP 9222，launchd `com.fangchen.shortbot.browser` 保活），**纯 DOM 操作、无视觉模型**。

- 动作契约见 `scripts/browser/README.md`；原语：navigate / open_tab / wait / query / inspect / click / fill / press / screenshot / upload / login_state。
- **`upload` 为 2026-10-31 新增**（小红书传图用）：
  `{"action":"upload","input":{"selector":"input[type=file]","files":["/abs/a.png"]}}`
- 前置：launchd 保活的专用 Chrome + Fang 在该浏览器（9222 窗口）**一次性登录 X**（含 2FA，只有人能做）。

> 📌 历史决策：2026-10-30 曾短暂切到「Codex 内置浏览器（cua_repl）/ Computer Use AX」双通道；
> **2026-10-31 起迁回 xb.py**，原因：本地化 + 无视觉（内置浏览器被组织策略禁用，AX 是视觉通道）。

## 前置

- 读 `private/account-safety.yaml#x`
  - `publish_mode == agent` 才能自动发；`draft_only` / `manual` 退化为只出草稿
  - `login_state` 是全局判据：专用 Chrome 登录后由 agent 复核并改为 `logged_in`
  - `publish_channel` = 发布通道标识，当前值 `xb_py`（唯一通道；历史值 `cua_repl` 已废止）
- 通道检查（每轮开工必做）：
  ```bash
  python3 scripts/browser/xb.py --action '{"action":"login_state"}'
  ```
  - 已登录 → 走完整链路
  - 未登录 → **本轮零动作**，如实记录「专用 Chrome 未登录，需 Fang 在 9222 窗口登录」，**不撞登录墙**（撞 10 次也不会让它登录）
  - exit 2（`BROWSER_UNAVAILABLE`）→ 浏览器不可用，本轮零发送，如实写原因
- 读 `state/forbidden.yaml#login_rules.x_login`
  - 遇 `We've temporarily limited your login` 立即停手
- 读 `state/schedule.yaml#publish_gates` —— **闸门不通过就不发**
  - Frank 自己在原创间隔窗口（**当前 2h** —— 2026-10-31「每 2h 一发」自 6 再下调；口径源 `schedule.yaml#chuangzuo_original_post_min_gap_hours`）内发过**根帖** → 零发送
  - 上一条原创 2h 后 likes 仍 ≤ 2 → **换选题方向**（不否决发送，Frank 2026-10-27/10-30 口径）
  - **不要为了「每轮要有产出」而发**（候选差就老实零发送）

## 工作流

### 0. **闸门（不可跳过，代码级强制）**

```bash
python3 scripts/prepublish.py outputs/<YYYY-MM-DD>-<slot>/<topic>/
```

**exit 0 才能往下走。exit 1 = 不许发。**

这个脚本做三件事：
1. AI 味检测（`state/ai-taste-rules.json` —— Wikipedia「Signs of AI writing」24 类模式 + Frank 中文清单）
2. 硬红线检测（OpenCSG / Chinese AI 公司名 / hashtag 风暴 / 安利腔）
3. 不过 → 自动调 LLM 清理器改写 → 再检测；仍不过 → exit 1

**为什么有这层**：2026-10-26 Frank 直接反馈「@op7418 / @oran_ge 拉黑你，是因为被看出来是 AI 评价了」。
之前只靠本文档的文字规则拦，而那条被撤掉的 reply **句式全部合规、结构一眼就是 AI**。
规则写在文档里挡不住人，所以做成了代码。

- 清理成功会把新正文写回 `x.txt`（原文件备份为 `x.txt.pre-gate.bak`）
- 每次闸门结果落盘 `state/gate-receipts.json`（含最终文本 sha256），事后可核对
- **闸门 exit 1 时不要手工绕过**。要么改到过，要么不发 —— 宁可这轮零动作。

### 1. 打开 compose

```bash
python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/compose/post"}}'
```

X 是 SPA，URL 不变，DOM 里出现 compose modal。

### 2. 填正文（**唯一稳定路径**）

```bash
# 先确认 compose 文本框在
python3 scripts/browser/xb.py --action '{"action":"inspect","input":{"selector":"[data-testid=\"tweetTextarea_0\"]"}}'
# fill 吃 selector（不是 ref），一次性填入，比逐字 type 可靠
python3 scripts/browser/xb.py --action '{"action":"fill","input":{"selector":"[data-testid=\"tweetTextarea_0\"]","text":"<正文>"}}'
```

### 3. 发送 —— **`fill` + `Cmd+Enter`**

```bash
python3 scripts/browser/xb.py --action '{"action":"press","input":{"key":"Meta+Enter"}}'
```

> ⚠️ xb.py 的 `press` **只认字符串 key**（`{"key":"Meta+Enter"}`），内部 `normalize_key()` 自己合成组合键；
> 传 `{"key":"Enter","modifiers":["Meta"]}` 时 `modifiers` 字段根本不读，会变成普通 Enter，发不出去且没有报错。

- **Post button click 不可靠** —— `tweetButtonInline` 是 disabled 的，AX 树里最先出现的永远是它
- Cmd+Enter 后 **wait 8-10 秒**（不需要更久）：
  ```bash
  python3 scripts/browser/xb.py --action '{"action":"wait","input":{"kind":"timeout","timeout":9000}}'
  ```

### 4. 验证真发 —— **用 search，不要靠 profile**

```bash
python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/search?q=from:FrankFika+<unique-keyword>&src=typed_query&f=live"}}'
```
- unique keyword = 自己帖里最 distinctive 的词（**不要用源帖已占用的词**）
- 检查结果第一篇是不是 own_post，取 `a[href*='/FrankFika/status/']` 拿 post_id

**原创帖的验证比 reply 麻烦**（reply 有 `conversation_id:` 算子，原创帖是 root post，没有）：

1. Cmd+Enter + wait 8-10s
2. `search?q=from:FrankFika+<unique-keyword>` —— keyword 用**自己帖里最 distinctive 的 1 个词**
   （不要用源帖已占用的词）；live search **只能用 1 个引号短语或最多 2 词**，三词以上一律 0 结果
3. 查不到 → **等 60s** 再查一次 `from:FrankFika`（`from:` 索引会漏刚发的帖，实测漏过）
4. 还查不到 → 查自己 profile `https://x.com/FrankFika`（新帖会在顶部，但有 8-30s 缓存延迟）
5. **四路都查不到 → 写 `posted_status: uncertain`，不要盲 retry**
   （第二次 Cmd+Enter 会触发 X 的反重复拦截「Whoops! You already said that.」，
   那是**真实 spam 信号**，比漏发严重。确认未投递后才允许重发一次，且正文必须逐字相同，
   发完再验「只有 1 条」。）

> ⚠️ **Cmd+Enter 后立刻查 profile / with_replies / home feed 会误判** —— 缓存延迟 8-30s，
> 读了会以为没发出去，然后想「保险再发一次」→ 触发 X 反重复拦截。

### 5. 配图（需要时走 `upload` 动作）

xb.py 2026-10-31 起有 `upload` 动作：

```bash
python3 scripts/browser/xb.py --action '{"action":"upload","input":{"selector":"input[type=file]","files":["/abs/path/a.png"]}}'
```

恢复配图时先确认**截图文件已在 `outputs/<...>/screenshots/` 落盘**（`state/style-x.yaml#must_have` 要求 ≥2 张真截图），`files` 必须是真实文件的绝对路径数组。

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
| `navigate` 超时（exit 1） | `query` 看 URL：URL=目标 → 再 wait；URL 没变 → 导航层已死，兜底写零动作 |
| 任意 action 返回 exit 2（`error.code=BROWSER_UNAVAILABLE`） | 浏览器不可用 → 兜底写「本轮零发送」，不重试 |
| exit 1（选择器没命中 / 参数不对） | 看 `error.message`；参考 `skills/browser-use-utils/SKILL.md` 的 action 对照表 |

> ⚠️ **不擅自重试 >1 次**。第二次 Cmd+Enter 会触发 X 的反重复拦截（「Whoops! You already said that.」），
> 那是**真实的 spam 信号**，比漏发严重。

## 不做
- 不绕过二次验证
- 不把失败当成功
- 不在没拿到 own_post URL 的情况下声称「已发」
