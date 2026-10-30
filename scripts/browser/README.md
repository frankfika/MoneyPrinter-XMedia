# scripts/browser · xb.py 浏览器执行层

**替代 MiniMax Code 内置工具 `mcp_browser` 的 Playwright 实现。**

旧环境里 5 个 skill 的浏览器动作（扫 X 时间线、截图、读 likes/replies、真发帖 `fill + Cmd+Enter`、登录态检测）
全靠 `mcp_browser` 这个工具名。接手方（DeepSeek Harness / 任何非 MiniMax 环境）没有这个工具，
所以把它的**动作清单原样搬到 CLI** 上，让 skill 文档只需要改「怎么调」，不用改「调什么」。

- 接口契约：`{"action":"...","input":{...}}`，一个进程一次 action，stdout 一行 JSON
- 只读优先：本工具**不提供**发帖 / 点赞 / 回复 / 关注 / 登录的专用封装；
  `fill` + `press` 只是按键与填表原语，是否发送由调用方（skill + 闸门）决定
- 传输：优先 attach 已经带调试端口在跑的 Chrome（能复用登录态），失败再起专属 profile

> 旧动作清单对照表在 `skills/browser-use-utils/SKILL.md`，本 README 第 5 节是它的新版本。

> 📍 **仓库真实路径 `/Users/fangchen/shortbot`**（旧 `/Users/fangchen/Documents/短文助手` 是指过来的 symlink，
> 两个都能用）。原因是 macOS TCC：launchd 拉起的 `/bin/bash` 读 `~/Documents` 会 `Operation not permitted`。
> `xb.py` 内部全部用 `__file__` 推导仓库根，**没有硬编码路径**，所以搬家不受影响。

---

## 1. 快速开始

```bash
cd /Users/fangchen/shortbot      # 真实路径；旧路径 /Users/fangchen/Documents/短文助手 是 symlink，也能用

# 登录态（未登录时 logged_in=false，exit 仍是 0）
python3 scripts/browser/xb.py --action '{"action":"login_state"}'

# 打开页面
python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/frankfika"}}'

# 读页面文本（selector 可省，省了就是整页 body）
python3 scripts/browser/xb.py --action '{"action":"query","input":{"kind":"text","maxChars":4000}}'

# 截图
python3 scripts/browser/xb.py --action '{"action":"screenshot","input":{"path":"screenshots/x.png"}}'

# 三条只读链路一次跑完（含 §8.5 的 likes 读法）
bash scripts/browser/smoke.sh
```

`__pycache__` / `.state/` / `.venv/` / `*.png` 都在 `scripts/browser/.gitignore` 里，不会进 git。

---

## 2. 依赖与引导（重要）

| 依赖 | 用途 | 现状 |
|---|---|---|
| Python 3.9+ | 跑 `xb.py` | 本机 `/opt/homebrew/bin/python3`（3.15） |
| `playwright` (Python 包) | 驱动 Chrome | 系统 python3 **没有**；`xb.py` 自动引导 |
| 本机 Google Chrome | 真正的浏览器 | `/Applications/Google Chrome.app`（155） |
| `uv` | 自动引导 playwright | `/opt/homebrew/bin/uv`（0.11.16） |
| `pyyaml` | 读 `private/browser.yaml` | 有则用，没有就用内置极简解析器兜底 |

**自动引导**：`python3 scripts/browser/xb.py ...` 发现当前解释器没有 playwright 时，
会自动用 `uv run --no-project --with playwright --with pyyaml python3 <自己>` 重新执行（约 0.2s，缓存后），
所以**不需要手动装任何东西**，也不下载浏览器二进制（用 `channel="chrome"` 复用系统 Chrome）。

可选加速 / 离线方案（cron 机器建议做一次）：

```bash
bash scripts/browser/setup.sh   # 建 scripts/browser/.venv（playwright + pyyaml）
```

建好后 `xb.py` 优先用这个 venv，启动更快，且不依赖 uv 的在线解析。

也可以用 npx 那一套（`npx playwright --version` = 1.58.2）做等价验证，
但本工具只实现了 Python 路径（见第 10 节「没做/有风险」）。

---

## 3. 命令行参数

```
python3 scripts/browser/xb.py --action '<JSON>' [选项]
```

| 选项 | 说明 |
|---|---|
| `--action '<JSON>'` | **必填**，形状 `{"action":"...","input":{...}}` |
| `--action-file PATH` | 从文件读 action JSON（cron 里引号难写时用） |
| `--ensure` | 确保浏览器在跑并复用（**默认已开启**，加不加都一样） |
| `--ephemeral` | 一次性模式：CDP 死了就用 persistent context 起一个，跑完关掉 |
| `--headless` / `--headed` | 无头 / 有头（默认取配置 `headless`，即 **有头**） |
| `--timeout-ms N` | 本次调用的硬超时上限（默认 `action_timeout_ms` = 30000） |
| `--proxy URL` / `--no-proxy` | 本次强制走/不走代理（覆盖 `proxy_mode`） |
| `--cdp URL` | 覆盖 CDP endpoint（优先于 `XB_CDP` 环境变量与配置） |
| `--config PATH` | 覆盖配置文件（默认 `private/browser.yaml`） |
| `--lock-wait-ms N` | 并发互斥等待上限（默认 `min(10000, timeout-3000)`） |
| `--list-actions` | 列出支持的 action + 退出码 |
| `--print-config` | 打印解析后的配置（调试用） |

环境变量：`XB_CDP` / `XB_CONFIG` / `XB_TIMEOUT_MS` / `XB_DEBUG=1`（登录态判定细节）/ `XB_CHROME`（Chrome 路径）。

---

## 4. 输出契约

**成功**（stdout 一行，退出码 0）：

```json
{"ok": true, "action": "navigate", "data": {"url": "https://x.com/frankfika", "title": "陈放Frank🕊️ (@FrankFika) / X", "status": 200, "settle_ms": 800}}
```

**失败**（stdout 一行，退出码 1 或 2）：

```json
{"ok": false, "action": "query", "error": {"code": "SELECTOR_NOT_FOUND", "message": "..."}}
```

- **stdout 只有那一行 JSON**，所有日志/进度走 stderr（`[xb] ...`）
- 不依赖 TTY：`</dev/null` 照常工作
- 有硬超时（SIGALRM），超时会中断并输出 `{"ok":false,"error":{"code":"TIMEOUT"}}`，不会挂死 cron
- 同 profile 的并发调用用 `.state/xb.lock` 串行化

### 退出码

| 退出码 | 含义 | skill 侧怎么处理 |
|---|---|---|
| `0` | 成功 | 读 `data` |
| `1` | action 执行失败（选择器没命中、导航失败、超时、并发锁超时…） | 看 `error.code`，一般不重试 |
| `2` | **`BROWSER_UNAVAILABLE`** —— 浏览器/Playwright/Chrome 不可用 | **零动作兜底**：本轮不碰 X，写 memory「浏览器不可用」，等下一轮 |

> 退出码 2 是给 skill 的「**浏览器层死掉 ≠ 今天没热点**」判据。
> 遇到 2 不要盲重试（老手册 §8.2 的东西：扫描通道被封和没热点是两件事）。

### error.code 全表

| code | 退出码 | 触发场景 | 建议动作 |
|---|---|---|---|
| `BROWSER_UNAVAILABLE` | 2 | CDP 连不上 + Chrome 拉不起来 + profile 被占用 | 本轮零动作；检查 Chrome / profile |
| `BAD_INPUT` | 1 | action JSON 不合法、缺必填字段、selector 语法错 | 修调用方 |
| `UNKNOWN_ACTION` | 1 | action 名不在契约里 | 修调用方 |
| `NAVIGATION_FAILED` | 1 | 导航层失败（DNS/代理/超时） | 别重试同一 URL；查代理 |
| `SELECTOR_NOT_FOUND` | 1 | selector 没命中（常见：X 未登录剥离 testid、页面没加载完） | 先 `wait` 再 query；检查登录态 |
| `REF_NOT_FOUND` | 1 | `inspect` 拿的 ref 过期/没存 | 重新 `inspect` |
| `ACTION_FAILED` | 1 | click/fill/press/screenshot 执行失败 | 看 message |
| `TIMEOUT` | 1 | 撞上 `--timeout-ms` 硬上限 | 拆小动作 / 放宽超时 |
| `LOCK_TIMEOUT` | 1 | 另一个 xb.py 正在用浏览器 | 本轮跳过，不要并发重试 |

---

## 5. action 对照表（旧 `mcp_browser` → 新 `xb.py`）

调用形式统一为：

```bash
python3 scripts/browser/xb.py --action '{"action":"<名字>","input":{...}}'
```

| # | 旧 `mcp_browser` 调用 | 新命令（`--action` 里的 JSON） | 返回 `data` 关键字段 |
|---|---|---|---|
| 1 | `{"action":"navigate","input":{"url":U,"replaceCurrentTab":true}}` | **同名同形** | `url, title, status, settle_ms, replaced_current_tab` |
| 2 | `{"action":"open_tab","input":{"url":U}}` | **同名同形** | `url, title, status, tab_count` |
| 3 | `{"action":"wait","input":{"kind":"timeout","timeout":3000}}` | **同名同形** | `kind, waited_ms, requested_ms, url` |
| 4 | `{"action":"query","input":{"kind":"text","selector":"...","maxChars":6000}}` | **同名同形**（selector 可省 = 整页 body） | `text, length, truncated, match_count, url` |
| 5 | `{"action":"query","input":{"kind":"dom","selector":"[data-testid='like']"}}` | **同名同形** | `html, html_length, **aria_label**, match_count, matches[]`（每个 match 带 `aria_label/testid/attributes/text/html`） |
| 6 | `{"action":"query","input":{"kind":"semantic","text":"Post"}}` | **同名同形**（扩展支持） | `matches[{ref,text,aria_label}]` |
| 7 | `{"action":"inspect","input":{"selector":"..."}}` | 同形 | `elements[{ref,tag,text,aria_label,attributes,visible}]` |
| 8 | `{"action":"click","input":{"ref":"<ref>"}}` / `{"selector":"..."}` | 同形，`ref` 跨调用有效（存 `.state/refs.json`） | `url, title, clicked{selector,index,ref?}` |
| 9 | `{"action":"fill","input":{"ref":"<ref>","text":"正文"}}` | 同形，`ref` 或 `selector` 都行；**fill 自动清空**（不需要 `clear`） | `filled_chars, value_len, cleared_before_fill:true` |
| 10 | `{"action":"press_key","input":{"key":"Meta+Enter"}}` | `{"action":"press","input":{"key":"Meta+Enter"}}` | `key`（规范化后）, `requested_key` |
| 11 | `{"action":"screenshot","input":{}}` | 同形，`path` 可选（相对仓库根，默认 `screenshots/xb-<时间戳>.png`） | `path`(绝对), `rel_path`, `bytes` |
| 12 | （登录态检测，旧版靠左下角 `@handle` 判断） | `{"action":"login_state","input":{}}`（`url` 可选，默认探 `/home`） | `logged_in:bool, handle:"@xxx"\|null, url` |

补充说明：

- **`press` 的键名**：`Meta+Enter` = `Cmd+Enter`（`cmd`/`command` 都会归一化成 `Meta`），
  还支持 `Enter` / `Escape` / `Backspace` / `Tab` / `ArrowDown` / `Control+A` 等。
- **可选扩展字段**（契约外的便利项，不用也不影响）：
  `query` 支持 `maxMatches`、`all:true`（返回 `items[]`，扫时间线一次拿多条）；
  `navigate`/`open_tab` 支持 `waitFor`（选择器）与 `settleMs`；
  `press` 支持 `selector`（先点一下目标再按键，用于聚焦输入框）。
- 旧手册里 `Validation failed: root: must not have additional properties` 那种重发即可的噪音，
  在这里变成了可判定的 `BAD_INPUT`（会明确说是哪个字段）。

### 发布路径（手册 §8.4）在 CLI 上的写法

```bash
# 1) 打开 compose（由 skill 决定）
python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/compose/post"}}'
# 2) 填正文（fill 自动清空）
python3 scripts/browser/xb.py --action '{"action":"fill","input":{"selector":"[data-testid=\"tweetTextarea_0\"]","text":"正文"}}'
# 3) 真发：Meta+Enter（Cmd+Enter）。不要点 Post button
python3 scripts/browser/xb.py --action '{"action":"press","input":{"key":"Meta+Enter"}}'
# 4) 等 8–10 秒（手册 §8.4）
python3 scripts/browser/xb.py --action '{"action":"wait","input":{"kind":"timeout","timeout":9000}}'
```

> ⚠️ **不要盲 retry**：Cmd+Enter 第二次会触发 X 的反重复拦截（手册 §8.4）。
> 真发验证用 search 拿 own_post 的 URL，不要查 profile / with_replies / home feed。

---

## 6. 读 likes / replies 的唯一合法口径（手册 §8.5）

```bash
# likes：必须有 aria-label，形如 "1,234 Likes. Like"
python3 scripts/browser/xb.py --action '{"action":"query","input":{"kind":"dom","selector":"[data-testid='"'"'like'"'"']"}}'
# → data.aria_label = "1,234 Likes. Like"

# replies
python3 scripts/browser/xb.py --action '{"action":"query","input":{"kind":"dom","selector":"[data-testid='"'"'reply'"'"']"}}'
# → data.aria_label = "12 Replies. Reply"
```

- **页面级 selector 只返回首个匹配**；detail 页每条帖都有自己的 like 按钮，
  首个匹配可能跟目标帖完全无关 —— `data.matches[]` 会列出前 N 个（默认 5）的 `aria_label` 供核对，
  确认目标帖后再用 `inspect` 拿 `ref` 精确操作。
- **详情页底部大数字是 VIEWS 不是 likes**，`query kind=text` 读到的也是 views。
- **不要用 likes 做跨帖对比**（样本量不够）。

---

## 7. 传输路径：CDP attach 与 persistent context 怎么切

优先级（写死在 `xb.py`，从高到低）：

1. `--cdp URL`
2. 环境变量 `XB_CDP`
3. `private/browser.yaml` 的 `cdp`
4. 默认 `http://127.0.0.1:9222`

**路径 A：CDP attach（推荐，登录态最稳）**

Chrome 带着 `--remote-debugging-port=9222` 在跑 → `xb.py` 直接 `connect_over_cdp`，
不重启浏览器、不动 profile，登录态天然复用。

```bash
# 手动起（或让 xb.py 自己拉起，见下）
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$HOME/.shortbot-browser-profile" \
  --remote-debugging-port=9222 \
  --remote-allow-origins='*' \
  --no-first-run --no-default-browser-check &
```

- `--remote-allow-origins=*` 不能省：CDP WebSocket 握手会因 Origin 被 403 拒。
  本工具自己 spawn 时一定会带这个参数（Playwright 的 `connect_over_cdp` 不发 Origin，但手动调试要用）。
- **`--ensure` 语义（默认开启）**：`xb.py` 发现 endpoint 不通、且该 profile 没有别的 Chrome 占用时，
  会用 `channel="chrome"` 的等价参数自己拉起 Chrome 并 attach，之后每次调用都只 attach。
  这就是「连续两次调用不重启 Chrome、不丢登录态」。
- spawn 成功后会把 endpoint 记到 `.state/endpoint.json`（Chrome 只有 `--remote-debugging-port=0` 才写
  `DevToolsActivePort`，显式端口不写，所以自己记一份）；下次配置的 endpoint 变了但老实例还活着，会先试记录的那个。
- `--ephemeral`：不要常驻进程时用。CDP 死了就 `launch_persistent_context` 起一个，跑完关掉
  （profile 里的 cookie 仍然会留在磁盘上，登录态不丢，丢的是 tab 状态）。
  ⚠️ **发帖流程不要用 `--ephemeral`**：它每次调用都是新进程，下次调用会重新加载页面，
  `fill` 填进去的正文会丢，`press` 就打空了。发帖（`fill` → `press` 分两次调用）必须走默认的常驻路径。
  `--ephemeral` 只适合「一次调用内做完」的只读动作（navigate+query+截图本来就该分调用，所以只读场景也别用它）。

**路径 B：persistent context（兜底）**

CDP 不通且 `--ephemeral` 时会 `chromium.launch_persistent_context(user_data_dir=..., channel="chrome")`，
进程随调用退出。下次调用会按 `.state/last_page.json` **自动恢复上次的 URL**（模拟「同一个 tab」），
所以 `navigate` → `query` 这种分两次调用的流程仍然成立。

**profile 目录**：`private/browser.yaml#user_data_dir`，默认 `~/.shortbot-browser-profile`。

> 🔴 **绝对不要**把 `user_data_dir` 指到 `~/Library/Application Support/Google/Chrome`：
> ① macOS TCC 会让非 Chrome.app 进程读它时 `Operation not permitted`；
> ② Chrome 155 在默认 profile 上**不监听** `--remote-debugging-port`（进程起得来、端口不开）。
> `xb.py` 里对这两个路径做了硬拒（会直接报 `BROWSER_UNAVAILABLE` 并说明原因）。

**同一 profile 只能有一个 Chrome 实例**。`xb.py` 在 spawn / persistent 前会 `pgrep` 检查，
如果 profile 已被一个**没开调试端口**的 Chrome 占着，会明确报错而不是盲目再拉一个
（历史上盲目 spawn 会被 Chrome 的 singleton 转交给老进程，把窗口搞没；已加保护）。

---

## 8. 登录态：需要人工登录一次

**登录态不在任何可拷贝的文件里**，它在 profile 目录的 cookie 里（`~/.shortbot-browser-profile/Default/Cookies`）。
`xb.py` **不执行任何登录动作**（不填账号密码、不点登录、不碰验证码），只做检测：

- 判定范围按**当前页面**走（和旧 `mcp_browser` 的语义一致）：
  - 当前页是 `x.com` / `twitter.com` → 用当前页 + cookie 判定
  - 当前页是 `xiaohongshu.com` → XHS 分支（best-effort：`creator.xiaohongshu.com` 且无登录弹窗/密码框才算已登录；**未实测**，XHS 自动发布本来就是禁止的）
  - 其它 / `about:blank` → 临时 tab 探 `https://x.com/home`（探完立刻关掉，不动当前页）
  - 显式传 `input.url` → 临时 tab 探那个 URL
- 判定为已登录（X）：`auth_token` cookie 存在，或页面出现账号菜单 / `[data-testid='AppTabBar_Profile_Link']` / 发帖按钮；且没被重定向到 `/i/flow/login`、`/i/jf/onboarding`
- `handle`：从 profile 链接或账号菜单文本里解析 `@xxx`，解析不到就给 `null`（**不猜**）
- 未登录时 `logged_in=false` 属于**正常结果**，退出码仍是 0

切换方法：让 Frank 在那台机器上、用**同一个 profile** 打开 Chrome（或 `xb.py --action '{"action":"navigate"...}'` 把窗口调出来），
手动登录一次。之后同一个 profile 的 `login_state` 会自动从 `false` 变 `true`，不需要改任何配置。
加 `XB_DEBUG=1` 可以看到判定依据（`has_auth_token` / `dom_signal` / `login_wall`）。

---

## 9. cron / 非交互 agent 调用范式

```bash
#!/usr/bin/env bash
# 只读动作，带「浏览器不可用 → 零动作」兜底
set -uo pipefail
XB="python3 /Users/fangchen/shortbot/scripts/browser/xb.py"

out=$($XB --timeout-ms 45000 --action '{"action":"navigate","input":{"url":"https://x.com/home"}}' 2>>logs/xb.err)
code=$?

case $code in
  0) echo "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["data"]["url"])' ;;
  2) echo "[skip] 浏览器不可用，本轮零动作" ; echo "$out" >> logs/xb-unavailable.log ;;
  *) echo "[fail:$code] $out" ; echo "$out" >> logs/xb-fail.log ;;
esac
```

- 只读 `data`，**不要**解析 stderr（那是给人看的）
- exit 2 → 本轮跳过，**别重试**；exit 1 → 看 `error.code` 决定是否换 selector
- 同一时刻只跑一个 xb.py（内置 `.state/xb.lock` 会串行化，但共享的是同一个 tab，
  不同 bot 的 cron 之间仍需错开，现有调度 4h/12h 已经错开）
- 无 TTY 依赖、有硬超时、stdout 单行 JSON —— 适合被 cron 里的 agent 直接 `subprocess` 调

---

## 10. 已知限制 / 没做到的地方（老实写）

1. **未登录时读不到 likes/replies（环境事实，不是工具缺陷）**
   X 未登录页面会**剥离 `data-testid`**（实测整页 0 个），`[data-testid='like']` 必然 `SELECTOR_NOT_FOUND`。
   `aria-label` 读取链路本身是通的（本地 fixture 用 X 登录后同款 DOM 验证过：
   `aria-label="1,234 Likes. Like"` / `"12 Replies. Reply"` 都能原样取到）。
   **需要 Frank 人工登录一次**后，同一条命令才能读到真实计数。
   `smoke.sh` 对这种情形只打 `⚠️` 不算失败。
2. **发布路径没有在真账号上验证过**。`fill` + `Meta+Enter` 的**按键链路**已在本地 fixture 上验证
   （`submit:32chars`，证明确实触发了 Cmd+Enter 的 keydown），但「X compose 页 → 真发出」没有实测过：
   ① 未登录没法进 compose；② 硬约束禁止本工具做任何写操作验证。
   这条要等 Frank 登录后，由 publisher skill 在闸门放行后跑第一条真实发帖来验证。
3. **CDP attach 的 viewport / timezone 改不了**：这两个是 context 级参数，attach 外部 Chrome 时只能用
   Chrome 启动时的设置（`private/browser.yaml` 里的 `locale` / `timezone_id` 只在 persistent context 路径生效）。
4. **代理不会自动重试**：`proxy_mode: auto` 只是「不加代理启动」。直连失败要显式
   `proxy_mode: always` 或 `--proxy http://127.0.0.1:7897`。本机实测 x.com 直连 200，所以默认没走代理。
   🔴 **但 launchd / cron 执行器上下文里不一样**：`dsh --profile shortbot` 拉起的 `/bin/bash` 直连 x.com 实测
   **返回 000（连不上）**，必须走 `127.0.0.1:7897`。手工在交互 shell 里测是 200，很容易漏掉这个差异。
   **所以 cron 机器上建议直接把 `private/browser.yaml` 的 `proxy_mode` 改成 `always`**，
   或在 wrapper 里每次加 `--proxy http://127.0.0.1:7897`。
5. **窗口全关的自愈**：Chrome 进程还在、但窗口全关时（target 列表里没有 `type=page`），
   Playwright 会报 `Browser.setDownloadBehavior ... Browser context management is not supported`。
   `xb.py` 现在会先 `PUT /json/new?about:blank` 补一个 page target 再 attach（已实测通过）。
   但这只是**自愈**，不是修复：如果发现 Chrome 窗口没了，人肉看一眼更稳。
6. **没有实现 npx/node 版**：只用 Python 路径。`npx playwright` 存在（1.58.2）但没有对应的 JS CLI 实现；
   如果哪天 Python/uv 全挂了，需要另写一个 node 版（约 300 行），目前未做。
7. **`query kind=semantic` 是简化实现**：在 `role=button` 里按可见文字匹配，不覆盖全部旧行为
   （旧版还能按 aria/title 找链接）。需要更准的场景用 `inspect` + `ref`。
8. **`inspect` 的 ref 存在 `.state/refs.json`**，最多保留 200 条；跨机/被清掉的 ref 会 `REF_NOT_FOUND`。
9. **`--ephemeral` 模式下跨调用状态会丢**（页面重载 → `fill` 的正文没了）。发帖只用默认常驻路径，见第 7 节。

---

## 11. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| exit 2 `BROWSER_UNAVAILABLE` 且 message 提到「profile 已被占用」 | 同 profile 还有别的 Chrome 在跑，且没开调试端口 | 退出那个 Chrome，或让它带 `--remote-debugging-port=9222` 重启 |
| exit 2，attempted 里有 `Executable doesn't exist` | Chrome 没装 / 路径不对 | 装 Chrome，或设 `XB_CHROME` |
| exit 2，`uv: command not found` 且没有 playwright | 引导失败 | `bash scripts/browser/setup.sh` 或 `pip install playwright` |
| exit 1 `NAVIGATION_FAILED` + `ERR_CONNECTION*` | 网络/代理 | `--proxy http://127.0.0.1:7897` 或配置 `proxy_mode: always` |
| exit 1 `SELECTOR_NOT_FOUND`（x.com） | 未登录（testid 被剥离）或页面没加载完 | 先 `login_state`，再 `wait` 3s 后重查 |
| exit 1 `LOCK_TIMEOUT` | 有别的 xb.py 正在跑 | 本轮跳过；检查是否有僵尸 cron |
| `attach` 报 `Browser context management is not supported` | Chrome 里没有 page target（窗口全关） | 本工具已自动补 about:blank 并重试；仍失败就重启 Chrome |
| 硬超时 30s 就死 | 单步太慢（X 首屏偶发慢） | `--timeout-ms 60000`，或拆成 navigate → wait → query |

---

## 12. 文件清单

| 文件 | 作用 |
|---|---|
| `xb.py` | **主程序**（CLI + 10 个 action + 传输/锁/超时/引导） |
| `README.md` | 本文档 |
| `browser.yaml.sample` | 配置样例（真实配置在 `private/browser.yaml`，不进 git） |
| `smoke.sh` | 只读冒烟：navigate → query text → likes → screenshot |
| `selftest.py` | 离线自检（纯函数 + `--live` 用临时 profile 验证 fill/press/click，不碰真实 X） |
| `setup.sh` | 建 `scripts/browser/.venv`（可选，加速/离线） |
| `.gitignore` | 忽略 `.state/` `.venv/` `*.png` |
| `.state/` | 运行时状态：`last_page.json` / `refs.json` / `endpoint.json` / `xb.lock`（git 忽略）；可用 `XB_STATE_DIR` 改到别处 |
| `_smoke.png` | 冒烟截图证据（git 忽略） |

### 验证记录（2026-10-26 实测）

```
login_state  → {"ok":true,...,"logged_in":false,"handle":null,"url":"https://x.com/frankfika"}  exit 0
               （XB_DEBUG=1 可见证据：has_auth_token=false / dom_signal=false / login_wall=false）
navigate     → {"ok":true,...,"url":"https://x.com/frankfika","title":"陈放Frank🕊️ (@FrankFika) / X","status":200}  exit 0
query text   → 1785 字符（bio + 3 条推文），maxChars 截断生效  exit 0
query dom like → SELECTOR_NOT_FOUND（未登录，X 剥离 testid）  exit 1   ← 登录后应返回 aria_label
screenshot   → 953,538 bytes PNG（2400x1816）  exit 0
进程复用      → 连续调用 Chrome PID 不变（95106 → 95106），只 attach 不重启
--ensure 冷启动 → 自建 Chrome（9333/临时 profile）→ 第二次调用复用同一 PID 2781
               （真实 profile 上也发生过：原 Chrome 被关掉后，xb.py 自动重新拉起并 attach，profile/登录态不变）
--ephemeral   → 起 persistent context，跑完无残留进程
exit 2        → 用「CDP 指向 127.0.0.1:9999（没人监听）+ user_data_dir=/dev/null/nope（建不出来）」
               实测得到 {"ok":false,"error":{"code":"BROWSER_UNAVAILABLE"}} exit 2
               另一条触发路径也已实测：profile 被一个没开调试端口的 Chrome 占着 → 同样 exit 2
TIMEOUT       → --timeout-ms 2000 + wait 20000 → {"code":"TIMEOUT"} exit 1
LOCK          → 并发第二个调用 --lock-wait-ms 200 → {"code":"LOCK_TIMEOUT"} exit 1
```

自检（可重复执行）：

```bash
python3 scripts/browser/selftest.py            # 37 项纯单元检查：PASS 37 / FAIL 0
python3 scripts/browser/selftest.py --live     # + 11 项实链路：PASS 48 / FAIL 0（8.2s，用临时
                                               #   profile/端口 9555，跑完自动 kill 自己 spawn 的 Chrome）
```

`--live` 覆盖：navigate / dom aria-label（like + reply）/ fill / `Cmd+Enter`（读到 `submit:17chars`，
证明确实触发了页面 keydown）/ inspect+click by ref / screenshot / 浏览器不可用 exit 2。
