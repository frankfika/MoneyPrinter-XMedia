---
name: browser-use-utils
description: 浏览器操作执行层 — 给 hot-topic-tracker / post-writer-x / publisher-x / x-engagement-pulse 共享使用。所有浏览器动作统一走仓库内 CLI `scripts/browser/xb.py`（Playwright）：抓 X 时间线、截图落盘、登录态检测、真实计数读取。**只走这个 CLI，不要混用其他浏览器栈。**
---

# Browser Use 执行层（`scripts/browser/xb.py`）

所有浏览器动作统一走仓库里的 CLI，**没有其他入口**：

```bash
python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/foo"}}'
```

- 单次调用 = 单次 action；参数是**一个 JSON 字符串**，形状 `{"action":"...","input":{...}}`
- stdout 单行 JSON：成功 `{"ok":true,"action":"...","data":{...}}`；失败 `{"ok":false,"error":{"code":"...","message":"..."}}`
- 传输：优先 CDP attach（`XB_CDP` 环境变量 → `private/browser.yaml#cdp` → 默认 `http://127.0.0.1:9222`）；attach 不到就用本机 Chrome + 持久化 profile 启动。登录态在 Chrome profile 里，**不在任何可拷贝的文件里**
- 依赖：Playwright + 本机 Chrome；用 `uv run --with playwright python3 scripts/browser/xb.py ...` 调用（本机没装 playwright 时）

> **开工第一步**：先跑一次
> `python3 scripts/browser/xb.py --action '{"action":"login_state"}'`
> 确认 CLI 能跑、浏览器可用。**exit 2 = 浏览器不可用 → 本轮零动作**，不要拿 exit 2 去判断「今天没热点」。

## 退出码（兜底判定的唯一依据）

| 退出码 | 含义 | 怎么办 |
|--------|------|--------|
| **0** | 成功 | 读 `data` |
| **1** | action 执行失败（选择器没命中 / 导航超时 / 页面异常） | 看 `error.message`：能 `wait` 后重查就重查，判死了就停手 |
| **2** | 浏览器不可用（`error.code=BROWSER_UNAVAILABLE`） | **本轮零动作**，memory 老实写「浏览器不可用，本轮零动作」，不装忙 |

- **浏览器不可用的唯一判据是 exit 2**（或返回 JSON 里 `ok:false` + `error.code=BROWSER_UNAVAILABLE`）。exit 1 只是「这一下没成功」，不等于浏览器不可用。
- **exit 2 也覆盖「`xb.py` 本身不存在 / 跑不起来」**（`python3` 打不开脚本文件同样是 exit 2）—— 两种都按「本轮零动作」兜底；日报里要分开报「浏览器不可用」和「CLI 缺失」。
- 机器休眠后浏览器层会整体失效（`exit 2`）；**机器一醒即自愈**，下一轮首条 navigate 通常就成功，重试当前轮修不好。

## action 对照表（旧 JSON 形态 → 新 CLI 调用）

| 动作 | 用途 | CLI 调用 |
|------|------|----------|
| `navigate` | 打开 URL（替换当前 tab） | `python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/<handle>"}}'` |
| `open_tab` | 新开 tab，保留当前页 | `python3 scripts/browser/xb.py --action '{"action":"open_tab","input":{"url":"https://x.com/<handle>"}}'` |
| `wait` | 等页面稳定（毫秒） | `python3 scripts/browser/xb.py --action '{"action":"wait","input":{"kind":"timeout","timeout":3000}}'` |
| `query`（text） | 读可见文本 | `python3 scripts/browser/xb.py --action '{"action":"query","input":{"kind":"text","selector":"[data-testid=\"tweet\"]","maxChars":6000}}'` |
| `query`（dom） | 读 markup / aria-label（**读计数必用**） | 见「读真实计数」一节 |
| `inspect` | 拿元素 selector / ref | `python3 scripts/browser/xb.py --action '{"action":"inspect","input":{"selector":"[data-testid=\"tweetTextarea_0\"]"}}'` |
| `click` | 点元素 | `python3 scripts/browser/xb.py --action '{"action":"click","input":{"selector":"..."}}'`（`ref` 也可） |
| `fill` | 填文本（**吃 `selector`，不吃 `ref`**） | `python3 scripts/browser/xb.py --action '{"action":"fill","input":{"selector":"[data-testid=\"tweetTextarea_0\"]","text":"<正文>"}}'` |
| `press` | 按键 | `python3 scripts/browser/xb.py --action '{"action":"press","input":{"key":"Meta+Enter"}}'` |
| `screenshot` | 截图落盘（路径相对仓库根） | `python3 scripts/browser/xb.py --action '{"action":"screenshot","input":{"path":"outputs/<date>-<slot>/<topic>/screenshots/x-1.png"}}'` |
| `login_state` | 登录态检测 | `python3 scripts/browser/xb.py --action '{"action":"login_state"}'` |

> 旧字段对应关系：`press_key {key,modifiers}` → `press {key:"Meta+Enter"}`（合成一个字符串）；`fill {ref,text}` → `fill {selector,text}`；`kind:"semantic"` 与 `reload` 没有对应 action，改用 `inspect` / 重新 `navigate`。
> `navigate` 支持 `replaceCurrentTab`（默认替换当前 tab）；要保留当前页就用 `open_tab`。

## 通用动作

### 打开 URL

```bash
python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/<handle>"}}'
```

- 当前 tab 已有内容且要保留 → 用 `open_tab`，不要 `navigate`
- 明确要替换当前 tab → `navigate`（默认行为），或显式 `"replaceCurrentTab": true`

### 等页面稳定

```bash
python3 scripts/browser/xb.py --action '{"action":"wait","input":{"kind":"timeout","timeout":3000}}'
```

`navigate` 之后建议 `wait` 一下再 `query`，否则拿到的是 spinner 页面。

### 读页面文本

```bash
python3 scripts/browser/xb.py --action '{"action":"query","input":{"kind":"text","selector":"[data-testid=\"tweet\"]","maxChars":6000}}'
```

- `kind:"text"` → 可见文本
- `kind:"dom"` → 需要 markup / aria-label 时用（**读计数必用 dom**）
- 元素定位用 `inspect` 拿 selector / ref

**shell 引号**：selector 里含单引号（如 `[data-testid='like']`）时，外层单引号会截断 JSON。
两种安全写法（任选）：

```bash
# 写法 A：外层双引号 + 内层转义
python3 scripts/browser/xb.py --action "{\"action\":\"query\",\"input\":{\"kind\":\"dom\",\"selector\":\"[data-testid='like']\"}}"

# 写法 B：heredoc 传 JSON（长调用更稳）
python3 scripts/browser/xb.py --action "$(cat <<'JSON'
{"action":"query","input":{"kind":"dom","selector":"[data-testid='like']"}}
JSON
)"
```

### 截图（落盘）

```bash
python3 scripts/browser/xb.py --action '{"action":"screenshot","input":{"path":"outputs/<YYYY-MM-DD>-<slot>/<topic>/screenshots/x-1.png"}}'
```

- `path` **相对仓库根**；落盘后返回 `{"path":...,"bytes":...}`
- 截图必须落到 `outputs/<date>-<slot>/<topic>/screenshots/`（既有约定），**不要写 /tmp**，否则下一轮/日报找不到证据
- 截图是**你自己的检查证据**，默认不发给 Frank；Frank 明确要看时才单独发一次

### 检测登录态

```bash
python3 scripts/browser/xb.py --action '{"action":"login_state"}'
```

返回 `{"logged_in": bool, "handle": "@xxx"|null, "url": "..."}`：

- X：`logged_in=true` 且 `handle` 是目标账号 → logged_in
- XHS 创作者中心：`url` 含 `creator.xiaohongshu.com` 且无登录弹窗 → logged_in
- `logged_in=false` → 停手，把 URL 给 Frank（**不要**自己走登录流程 / 读验证码）

> 通用 shell / 页面标题 / 「登录」链接 **都不算** 登录态证据。唯一判据是 `login_state` 的返回。

### 读真实计数（重要，踩过两次）

```bash
python3 scripts/browser/xb.py --action "$(cat <<'JSON'
{"action":"query","input":{"kind":"dom","selector":"[data-testid='like']"}}
JSON
)"
```

- likes → `aria-label="N Likes. Like"` / `"N Likes. Liked"`（`[data-testid='like']` / `[data-testid='unlike']`）
- replies → `aria-label="N Replies. Reply"`（`[data-testid='reply']`）
- views → 页面明文 `N Views`

> ⚠️ **坑 ①：likes 必须用 `query kind=dom` 打 `[data-testid='like']` 读 aria-label。**
> `query kind=text` 读到的数字**不是 likes**（见坑 ②）。
>
> ⚠️ **坑 ②：详情页底部的大数字是 VIEWS 不是 likes。** 两者差一个数量级；`query kind=text` 读到的也是 views。
> 不要把 views 当 likes 写进 memory / 日报。
>
> ⚠️ **坑 ③：页面级 selector 只返回首个匹配。** detail 页每条帖（root / 别人 / 自己 / 目标）都有各自的 like 按钮，**首个匹配可能跟目标帖完全无关**。
> 正确做法：先把目标帖滚进视口，看**它自己那条 action bar** 的视觉证据（红心实心 + 计数），或用能唯一定位的 scoped selector。
> **绝不用整页 `[data-testid='like']` 首个匹配当判据。**
> 例外：线程页 `[data-testid='unlike']` 只返回根帖 —— 赞一条 reply 必须走干净的详情页 URL。

### 填文本 + 发送

```bash
# 1) 填正文（fill 吃 selector）
python3 scripts/browser/xb.py --action '{"action":"fill","input":{"selector":"[data-testid=\"tweetTextarea_0\"]","text":"<正文>"}}'
# 2) 发送（Meta+Enter = Cmd+Enter）
python3 scripts/browser/xb.py --action '{"action":"press","input":{"key":"Meta+Enter"}}'
# 3) 等 8-10 秒
python3 scripts/browser/xb.py --action '{"action":"wait","input":{"kind":"timeout","timeout":9000}}'
```

- **`fill` + `Cmd+Enter`（即 `press {key:"Meta+Enter"}`）是唯一稳定的真发路径**；Post button click 不可靠
- `fill` 一次性填入完整正文（比逐字输入可靠），每次都会清空目标，不需要额外清空
- 填完后 **等 8–10 秒**，不需要更久
- 真发验证：用 search 拿 own_post URL（见 `skills/publisher-x/SKILL.md`）

## 失败兜底

| 现象 | 动作 |
|------|------|
| 退出码 2（`error.code=BROWSER_UNAVAILABLE`） | **本轮零动作**，memory 写「浏览器不可用，本轮零动作」，等下一轮（机器一醒即自愈） |
| 登录墙 / `login_state` 返回 `logged_in=false` | 停手，把 URL 给 Frank |
| 二次验证 / 验证码 | 停手，把页面 URL 给 Frank，**绝不**自己读验证码 |
| 限流 / 临时封 | 停手，写 memory |
| `navigate` 超时（exit 1） | `query` 看 URL：URL=目标 → 页面在加载，再 wait；**URL 没变 → 导航层已死，别重试同一 URL** |
| exit 1 且 selector 没命中 | `wait` 后再 `query` 一次；仍不命中 → 页面结构变了，停手写 memory，不要连环猜 selector |

## 铁律（跨 skill 通用）

- **发任何公开动作前先读 `state/forbidden.yaml`**
- **真发验证用 search 拿 own_post URL**，不要靠 profile / with_replies / home feed
- **不盲 retry**：Cmd+Enter 第二次会触发 X 反重复拦截
- **浏览器不可用 = exit 2**，看到 exit 2 就写零动作收工，**不装忙**
- 任何「拿不到真实结果」→ 老实写「未发」+ 原因
