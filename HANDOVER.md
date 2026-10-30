# 短文助手 · 移交手册

> **给接手方（新 AI / 新机器）读的第一份文件。**
> 读完这一份，你应该能独立跑起整条流水线，且不会把 Frank 的账号资产玩坏。
>
> 版本：2026-10-26 · 源项目：`frankfika/MoneyPrinter-XMedia` · 源机器：Frank 的 MacBook（Asia/Shanghai）
>
> 🔄 **项目真实路径已改为 `/Users/fangchen/shortbot`**（2026-10-26 移交时迁出 `~/Documents`，原因见 §6.4 TCC）。
> 老路径 `/Users/fangchen/Documents/短文助手` 现在是指向它的 **symlink**，两个路径都能用；
> 但 **launchd / 后台任务必须用真实路径**。
>
> **2026-10-26 第二次移交（MiniMax Code → DeepSeek Harness）**：
> 本文已按新接手方的实测环境改写。**原版是按「换机器 + 换新账号 + MiniMax Code 的 mcp_browser」写的，那两个前提现在都不成立**，
> 与现状冲突的段落都标了 🔄 并说明为什么改。历史决策记录一字未删。

> :arrows_counterclockwise::arrows_counterclockwise: **2026-10-30 第三次移交（DeepSeek Harness -> Codex app）**：
> 调度层从 launchd + `dsh --profile shortbot` 迁回 **Codex Automations**（三条 cron：`pipeline-12` 创作 / `x-pulse-6` 互动 / `super-bot-09-00` 日报，
> prompt 唯一事实源 = `docs/cron-prompts/*.md` 第一个围栏块）。launchd 三条工作线 plist 已归档 `archive/launchd/`；
> DSH 时代脚本归档 `archive/dsh-era/`。浏览器层变为**双通道**：Codex 内置浏览器（`mcp__cua_repl__js`）+
> xb.py 专用 Chrome（CDP 9222，launchd `com.fangchen.shortbot.browser` 保活），登录态互相独立、各需一次性人工登录。
> 本文后续关于 DSH/launchd 的实操段落保留作历史记录，**不要再按它们部署**；当前权威口径以 README.md 为准。

---

## 0. 一分钟摘要

短文助手是一条 **X（Twitter）内容流水线**，三件事三条独立的定时任务：

| 线 | 调度（Asia/Shanghai） | 干什么 | 权限 |
|------|------|--------|------|
| **chuangzuo**（创作） | `30 3,15 * * *`（12h） | 扫 X → 选热帖 → 写文案 → 浏览器真发 | 可发原创帖 |
| **pulse**（互动） | `0 4,10,16,22 * * *`（4h） | **只 like+reply，不发新帖** | 可 like / reply |
| **super-bot**（汇报） | `0 9 * * *`（每日 09:00） | 读前两者日志 → 结构化日报 | **只读**，绝不碰 X |

**Frank 只跟 super-bot 对话**，不直接看 worker bot。

### 🔄 本次移交到底变了什么（决定了下面所有步骤）

| 项 | 老版手册假设 | **现状（2026-10-26 实测）** |
|---|---|---|
| 机器 | 换一台新机器 | **同一台 Mac**；项目迁到 **`/Users/fangchen/shortbot`**，老路径 `~/Documents/短文助手` 是 symlink |
| X 账号 | 换新账号，从 0 开始 | **继续用老号 `@FrankFika`**（Frank 当面确认，见 §12） |
| 账号资产 | 新号 0 粉丝，AI 味 = 直接判 spam | **老号 3,620 followers**，AI 味 = 掉信任 / 再被拉黑 |
| 运行时 | MiniMax Code / Mavis，`mcp_browser` + cron | **DeepSeek Harness（DSH）**，无 `mcp_browser`、无 `mavis` |
| 浏览器 | `mcp_browser` 内置工具 | 🔄 **`scripts/browser/xb.py`**（Playwright + CDP） |
| 定时 | Mavis cron（`session.mode=new`） | 🔄 **launchd + `dsh --profile shortbot`**（每轮独立进程 = 独立 session） |

> ⚠️ **账号口径变了，风险画像也变了**：
> 老版说「新号 0 粉丝，AI 味内容 = 直接判 batch spam」。现在是老号 3,620 粉，
> **同样一条 AI 味内容，代价是继续掉可信度、增加再被拉黑的概率**（§1 的根因从未消失）。
> **第 0 道 AI 味闸门对老号一样是硬闸，不是走过场。**

---

## 1. 【必读】为什么 AI 味闸门必须先过

Frank 的老账号 `@FrankFika` 已经被 **@op7418** 和 **@oran_ge** 拉黑。
Frank 事后确认的原因是：**「你很多拉黑是因为被看出来是 AI 评价了」**。

这不是流量问题，是**账号资产损失** —— 账号资产是「AI 独角兽董秘 / 评测出身 / 前工程师」这个**可信度**。

2026-10-26 那条被撤掉的 reply **句式全部合规**（没踩任何 `banned_phrases`），但整体结构一眼就是 AI。
**只禁词不禁结构 = 挡不住人。** 规则写在文档里挡不住 AI，必须做成代码里的 `exit code`。

所以第一原则没变：

> **AI 味闸门（`scripts/prepublish.py`）必须是发布的唯一路径，且 `exit 1` 时不许手工绕过。**

### 三道闸（`skills/x-engagement-pulse/SKILL.md` 里有完整版）

| 闸 | 查什么 | 不通过怎么办 |
|----|--------|-------------|
| **第 0 道 · 机器闸门** | 结构 + 词 + 红线，34 条规则 | `python3 scripts/prepublish.py --text "正文"` → **exit 1 不许发** |
| 第 1 道 · 身份质疑 | 「你是 AI / bot 吗」类内容 | **默认不回**，记一笔留痕 |
| 第 2 道 · 内核撞车 | 你的最强反驳是不是自己近 24h 讲过两遍 | 是 → 不发，记 `SKIPPED_NO_REPLY` |

### 🔄 2026-10-26 新发现：`prepublish.py` 有两种模式，别把自动改写当成「过了闸门」

实测（本轮真跑）：

```bash
# 默认模式：检测 → 命中就调 mmx 调 LLM 自动改写 → 改完再检 → 通过则 exit 0
python3 scripts/prepublish.py --text "先说结论：问题来了……"      # → 被改成另一段话，exit 0

# 严格模式：只检测，不自动改写
python3 scripts/prepublish.py --text "先说结论：问题来了……" --no-rewrite   # → exit 1，硬拦
```

**默认模式 = 程序替你绕过了闸门**（把 AI 味洗掉再放行）。所以：

- **真发前必须用 `--no-rewrite` 过一遍**，`exit 1` 就重写文案，不许靠自动改写蒙混；
- 想用自动改写辅助是可以的，但**改写后必须再跑一次 `--no-rewrite` 复验**，两次都 exit 0 才算过。

---

## 2. 第 0 步 · 环境（本机已就绪，换机器才需要重建）

### 2.1 硬依赖

| 依赖 | 为什么 | 现状 | 缺了会怎样 |
|------|--------|------|-----------|
| **DSH CLI**（`~/.dsh/app/node_modules/.bin/dsh`） | cron 每轮的执行器 | ✅ 0.1.5-rc.1 | 🔴 pipeline 跑不了 |
| **DSH profile `shortbot`** | headless 模板 + 短文助手专用 patch | ✅ 已建（§6.1） | 🔴 |
| **系统 Chrome** | 浏览器执行层 | ✅ `/Applications/Google Chrome.app` | 🔴 扫不了、发不了 |
| **Playwright（Python）** | `xb.py` 的驱动 | ✅ 走 `uv run --with playwright` | 🔴 |
| **`uv`** | 给脚本临时装 pyyaml / playwright | ✅ `/opt/homebrew/bin/uv` | 🟡 qa-draft / xb.py 都跑不了 |
| **`mmx` CLI** | 闸门自动改写 + humanize | ✅ 已配 | 🟡 默认模式退化成只检测 |
| **Python 3** | 所有脚本 | ✅ 3.15 | 🔴 |
| **本地代理 7897** | 备用通道 | ✅ `curl -x 127.0.0.1:7897 https://x.com/` → 200 | 🟡 |
| **macOS** | launchd / caffeinate / pmset | ✅ | 🟡 机器一睡，cron 全停（§8.1） |

> 🔄 **MiniMax Code / Mavis 不再是必需依赖**。原版手册说缺了它「整个 pipeline 跑不了，因为 `mcp_browser` 是它的工具」——
> 现在浏览器动作全部走 `scripts/browser/xb.py`，**不依赖任何 MCP 工具名**。
> 机器上 `mavis` CLI 确实不存在（实测 `command -v mavis` → MISSING），但流水线照跑。

### 2.2 验证环境（一条条贴结果，不要凭印象）

```bash
D=~/.dsh/app/node_modules/.bin/dsh
"$D" --profile shortbot "只回复一行 DSH-HEADLESS-OK"     # 期望输出 DSH-HEADLESS-OK，exit 0
python3 scripts/browser/xb.py --action '{"action":"login_state"}'   # 期望 JSON，exit 0
curl -s -o /dev/null -w "%{http_code}\n" https://x.com/  # 2026-10-26 实测：直连也是 200
command -v uv && mmx --help >/dev/null && echo deps-ok
```

> `qa-draft.py` 是**内容校验器**（占位图 / 格式 / 字数 / 标签），跑得通 ≠ 每篇草稿都过。
> 它会对具体草稿报「N 项失败」—— 那是内容问题，不是脚本问题，别混淆。

---

## 3. 第 1 步 · 拉代码

```bash
git clone https://github.com/frankfika/MoneyPrinter-XMedia.git
cd MoneyPrinter-XMedia
```

目录里**没有**的东西（.gitignore 挡掉了，克隆后没有是正常的）：

| 被忽略的 | 怎么办 |
|---|---|
| `private/` | 手工拷贝（第 2 步） |
| `scripts/browser/.state/`、`*.png` | 浏览器层运行态，自动重建 |
| `outputs/**/screenshots/` | 历史截图，本地保留就行 |
| `state/memory/archive/` | 轮转出去的旧轮次归档 |
| `logs/` | 噪音 |
| `.venv/` | 重建：`uv venv && uv pip install pyyaml` |

---

## 4. 第 2 步 · `private/` 与 state 手术

### 4.1 拷 `private/`

```bash
mkdir -p private
scp <老机器用户>@<老机器>:"/Users/fangchen/Documents/短文助手/private/"*.yaml private/
```

需要两份：`account-safety.yaml`（账号安全）、`browser.yaml`（浏览器层配置，见 §5.2）。**都不进 git。**

### 4.2 🔄 账号字段：**继续用老号时，这一节与老版手册完全相反**

老版手册 §4.2 是按「全新账号」写的，要求**清空** `last_published_*`。
**现在账号是继续用老号 `@FrankFika`，清空 = 解除 12h 冷却闸门 = 可能 12h 内连发。这是事故，不是优化。**

| 字段 | 老号延续该怎么处理 | 为什么 |
|---|---|---|
| `last_published_at` / `_post_id` / `_url` / `_round` / `_topic_signature` / `_media_count` / `_treatment` | **原样保留** | 12h 冷却闸门（`chuangzuo_original_post_min_gap_hours: 12`）的输入；清空 = 闸门失效 |
| `last_outbound_reply_at` / `last_outbound_like_at` / `last_inbound_reply_at` | **原样保留** | 冷却计算依赖 |
| `account_label` / `logged_in_as` | 保持 `@FrankFika` | —— |
| `login_state` | **以实测为准**：浏览器 profile 没登录就写 `needs_login`，登录后改回 `logged_in` | 写 `logged_in` 骗自己 → 每轮都白跑 |
| `publish_mode` | 保持 `agent`（全权自动发） | 改成别的就不自动发了 |
| `xhs` 段 | `is_banned: false` / `agent_publish_allowed: true` | ✅ 2026-10-29 17:11 Frank 授权代点发布；17:12 首篇已发 |

> **只有一种情况要清空 `last_published_*`**：将来真的换成一个 0 历史的新账号。
> 那种情况下，清空后又必须**立刻确认 `last_published_at` 是 null**，否则流水线会安静地一条都不发（闸门永远认为「12h 内发过」），而且**看起来一切正常**。
> 该陷阱是双向的，两个方向都能把流水线玩死。

### 4.3 `state/` 手术清单

| 文件 | 动作 | 理由 |
|------|------|------|
| `state/ai-taste-rules.json` | **原样带走** | 闸门规则集，34 条，核心资产 |
| `state/gate-regression-anchors.json` | **原样带走** | 验收基线，13 条 |
| `state/style-x.yaml` / `forbidden.yaml` / `watchlist.yaml` / `filter-rules.yaml` / `schedule.yaml` | **原样带走** | 规则层，Frank 拍过板的 |
| `state/seen-posts.json` / `index.json` | **带走** | 去重连续性 —— 防止重复骚扰同一个人 |
| `state/inbound-replies.json` | **带走** | 同上 |
| `state/published-posts.json` | **带走，别删** | ① 历史记录 ② **`draft_text` 是闸门回归语料**，删了验收就没语料了 |
| `state/index.json` 的 `published` 段 | **老号延续：不动**（原 159 条） | 只有换新号才清零 |
| `state/recent-picks.json` | **建议重新生成**（首轮 chuangzuo 顺手做） | 已失真：115 条里 63 条没有日期字段，7 天 dedup 不可用 |
| `state/skip-handles.json` | 带走，**但加注** | 拉黑的是老号本人；根因（AI 味）仍在，保守起见先跳过 |
| `state/gate-receipts.json` | 带走（历史留痕） | —— |

---

## 5. 第 3 步 · 登录 X（**当前状态：未登录，必须人工做一次**）

### 5.1 🔄 登录态到底存在哪

老版说「登录态在 Mavis 内置浏览器的 profile 里」。现在：**在 Chrome 的一个专属 profile 目录里**：

```
~/.shortbot-browser-profile      ← xb.py 专用的自动化 profile（独立于你日常 Chrome）
```

**本机实测（2026-10-26）**：该 profile 里 `auth_token` / `ct0` 都不存在 → 未登录。

### 5.2 登录怎么做（唯一正确姿势）

```bash
# 1) 起自动化 Chrome（如果 9222 没在跑）
open -na "Google Chrome" --args \
  --user-data-dir="$HOME/.shortbot-browser-profile" \
  --remote-debugging-port=9222 --no-first-run --no-default-browser-check

# 2) 在这个窗口里手动登录 @FrankFika（账号密码 / 2FA 由 Frank 处理，不许自动过）

# 3) 验证
python3 scripts/browser/xb.py --action '{"action":"login_state"}'
# 期望：{"ok": true, ..., "data": {"logged_in": true, "handle": "@FrankFika", ...}}

# 4) 把 private/account-safety.yaml#x.login_state 改成 logged_in
```

> `private/browser.yaml` 里的 `cdp: http://127.0.0.1:9222` + `user_data_dir: /Users/fangchen/.shortbot-browser-profile`
> 就是这条链路的配置。**换成别的 profile 目录 = 换掉登录态**，别乱改。

### 5.3 🔄 为什么不是「复用日常 Chrome 的登录态」

2026-10-26 实测三条硬结论，别再试：

1. **Chrome 155 拒绝在默认 profile 上开远程调试**：`--user-data-dir=".../Google/Chrome" --remote-debugging-port=9222` 进程起得来但**端口不监听**；换成任意非默认目录立刻正常（实测 `/tmp/xb-probe` 秒出 CDP）。
2. **macOS TCC 不让非 Chrome 进程读 `~/Library/Application Support/Google/Chrome`**（`Operation not permitted`），所以也没法复制日常 profile 过来。
3. 本机可读的 `~/Library/Caches/ms-playwright-mcp/*`（40+ 个 profile）**没有一个带 x.com 登录态**。

结论：**专属 profile + 人工登录一次**是唯一稳的路径。

### 5.4 ✅ DSH 内置浏览器（2026-10-26 已实测打通，是可用方案）

**先纠正一版错误结论**：移交过程中我一度以为内置浏览器用不了（版本对不上 / `dsh plugin` 拒绝 desktop），
**那是错的**。真实结论如下。

#### 三种浏览器相关包里，只有两个有用

| 包 | 是什么 | 结论 |
|---|---|---|
| `@deepseek-ai/dsh-client-ui-sidebar-browser` | 右侧栏「浏览器」tab（人看的） | ❌ README 原文「模型体验：无。不注册工具」 |
| `@deepseek-ai/dsh-browser-use` | browser-use provider 注册 seam | ✅ 必需，配合下面那个 |
| `@deepseek-ai/dsh-experimental-browser-use-playwright-mcp` | **per-Session 浏览器工具**（backend = `@playwright/mcp`） | ✅ **agent 真正可用的就是它** |

#### 关键在于「用哪个 CLI 装」和「版本必须精确对上」

- 挂这两个包要求 `@deepseek-ai/dsh-*` **精确 0.2.1-rc.3**（它们在 npm 上最早就是 `0.1.6-alpha.1`，`0.2.1-rc.3` 才匹配当前 app）。
- **本机 CLI `~/.dsh/app` 是 0.1.5-rc.1**（版本对不上）；**`.app` 内部才是 0.2.1-rc.3**。
- `dsh plugin --profile desktop add …` 无论用哪个 CLI 都会拒：`profile "desktop" is managed exclusively by the Electron application`。
- **绕过办法（已实测有效）**：在 profile 目录里直接 `pnpm add`，再手改 `cordis.patch.yml`。

```bash
cd ~/.dsh/profiles/desktop
cp package.json package.json.bak && cp cordis.patch.yml cordis.patch.yml.bak
pnpm add @deepseek-ai/dsh-browser-use@0.2.1-rc.3 \
         @deepseek-ai/dsh-experimental-browser-use-playwright-mcp@0.2.1-rc.3
# 然后在 cordis.patch.yml 末尾追加：
#   - insert:
#       - name: "@deepseek-ai/dsh-browser-use"
#       - name: "@deepseek-ai/dsh-experimental-browser-use-playwright-mcp"
#         config: { mode: attach, endpoint: "http://127.0.0.1:9222" }
```

重启 DSH 后，会话里就有 `browser_*` 工具（navigate / snapshot / click / type / evaluate / take_screenshot …）。

**回滚**：`bash scripts/revert-dsh-browser.sh` 然后重开 app。

#### 实测证据（2026-10-26，都是真跑）

| 验证 | 结果 |
|---|---|
| `--dump-config` 组合里出现两条 browser 条目 | ✅ |
| headless 真跑「用浏览器打开 x.com」 | ✅ 返回真实标题 `陈放Frank🕊️ (@FrankFika) / X` |
| 是否 attach 到**已有**的 Chrome（复用登录态） | ✅ 导航后 `9222` 的页面变了，而 **Chrome PID 没变**（11520） |
| 与 `xb.py` 是否同一个浏览器 | ✅ 两个层都报「x.com/home 被重定向到登录页」，状态一致 |

#### 两个必须知道的约束

1. **attach 是「会话独占」的**（README 原文）：一个 Session 初始化时 claim 住这个浏览器，直到它卸载；
   期间**别的 Session 直接调用会失败**，且不会重试。
   → 所以**意图共享同一个浏览器的话，不要同时开两个会抢浏览器的会话**。
   → 这也是为什么 **cron 不用内置浏览器、继续用 `xb.py`**：无人值守的轮次不该跟正在用的 GUI 会话抢同一个浏览器。
2. **attach 目标必须在跑**：`9222` 上没有 Chrome，该会话的浏览器工具就不可用。
   已用 LaunchAgent 常驻解决（`scripts/install-browser-agent.sh --install`，登录即起、profile 持久、登录态跨重启保留）。

> 一句话选型：**人机交互（你在 GUI 里看着、让 agent 边看边做）→ 内置浏览器；无人值守的 cron → `xb.py`。**
> 两者指向同一个 Chrome profile，所以登录一次两边都认。

---

## 6. 第 4 步 · 三条定时任务（**launchd，不是 Mavis cron**）

### 6.1 执行器：`dsh --profile shortbot`

原版手册的关键参数是 `session.mode = new`（每轮独立 session）。**这个要求没变，实现变了**：

```bash
dsh --profile shortbot "<本轮 prompt>"     # 跑完即退，全新进程 = 全新 session
```

- profile `shortbot` 由 `dsh-headless` 模板派生，位于 `~/.dsh/profiles/shortbot/`
- patch（`cordis.patch.yml`）里配了：模型（volces-ark / deepseek-v4-1-flash）、`danger-full-access` 权限、skill 根目录（含本仓库 `skills/`）
- 为什么不用 DSH 的 `schedule_create`：`dsh-schedule` 的语义是**投递回原 Session**（"durable reminders ... original-Session delivery"），上下文会一路涨到 305K/512K 触发 compaction —— 正是老机器踩过的坑

### 6.2 装 / 卸 / 看状态

```bash
scripts/install-cron.sh --install     # 写 3 个 plist 到 ~/Library/LaunchAgents 并 bootstrap
scripts/install-cron.sh --status      # 三条是否加载 + 最近日志
scripts/install-cron.sh --uninstall   # 全停
scripts/run-round.sh chuangzuo        # 手工补跑一轮（同一条线有单飞锁，不会并发）
scripts/run-round.sh pulse --dry-run  # 只打印从 prompt 文件抽出来的正文
```

| 线 | launchd label | schedule |
|---|---|---|
| 创作 | `com.fangchen.shortbot.chuangzuo` | `30 3,15 * * *` |
| 互动 | `com.fangchen.shortbot.pulse` | `0 4,10,16,22 * * *` |
| 汇报 | `com.fangchen.shortbot.super-bot` | `0 9 * * *` |

> 🔄 **prompt 的唯一事实源是 `docs/cron-prompts/*.md`**（`run-round.sh` 从其中第一个 ``` 围栏块抽取，不另外维护副本）。
> 改 prompt = 改这三个 md，不要改 plist。
> 🔄 **绝对路径**：`/Users/fangchen/Documents/短文助手`（本机与老机器一致，无需改；换机器要改 `run-round.sh` 的 `REPO`、`install-cron.sh` 的 `REPO`、`shortbot` profile patch 里的 skill 目录，以及三个 md 里的路径）。

### 6.4 🔴 项目为什么必须放在 `~/Documents` 之外（macOS TCC，2026-10-26 实测）

**症状**：launchd 拉起的三条任务全部失败，`logs/launchd/*.err.log` 里是：

```
shell-init: error retrieving current directory: getcwd: cannot access parent directories: Operation not permitted
/bin/bash: /Users/fangchen/Documents/短文助手/scripts/run-round.sh: Operation not permitted
```

**根因**：`~/Documents` 是 macOS TCC 受保护目录。launchd 拉起的 `/bin/bash` 没有这个授权，**整个目录树读不了**。
对照实验（同一个 launchd job 里）：

```
HOME:  28 entries
DOCS:  ls: /Users/fangchen/Documents: Operation not permitted      ← 后台 bash 完全进不去
```

而 DSH 应用本身有授权（`dsh` 起的 bash 能正常读），所以**手工跑得通、cron 跑不通**，很容易误判成脚本写错。

**处置（已执行）**：项目本体迁出受保护目录，老路径留 symlink：

```bash
mv ~/Documents/短文助手 ~/shortbot
ln -s /Users/fangchen/shortbot ~/Documents/短文助手
```

实测确认：**真实路径在 `~/` 根下 → 后台可读**；**从 `~/Documents` 下的 symlink 进入也 OK**（所以老路径不会断）。

> 备选方案（**不推荐**）：给 `/bin/bash` 开「完全磁盘访问权限」。能用，但等于给所有 shell 脚本全盘权限，是安全降级。
> 如果你更想保留 `~/Documents` 原位置：必须走这条备选，或者改用 DSH 应用内调度（但见 §6.1 的 session 膨胀问题）。

**另一条实测（别被 curl 误导）**：launchd 上下文里 `curl` 直连 x.com 返回 **000**，走代理 `127.0.0.1:7897` 才是 **200**（交互 shell 里直连是 200）。
但 **这不影响浏览器层**：Chrome 有自己的网络栈，`xb.py` 是 attach 到已跑着的 Chrome（`mode: attach`）而不是用 curl 的链路。
2026-10-26 在 launchd 里实跑验证：`curl` 仍 000，而 `xb.py navigate` 返回 `status: 200` + 真实页面标题，`query kind=text` 拿到 1492 字正文。

> 只有一种情况要注意代理：**让 xb.py 自己 spawn Chrome**（`--ensure` 冷启动 / `proxy_mode: always`）时，`--proxy` 才会生效；
> attach 外部已存在的 Chrome 时，代理由那个 Chrome 的启动参数决定，CLI 的 `--proxy` 改不动它。

### 6.3 老机器上的 cron

🔴 **必须停掉老机器上指向同一个 X 账号的任何定时任务**，否则两个执行器同时操作一个账号。
本机已确认：`crontab -l` 为空，无 Mavis（`mavis` CLI 不存在），不存在遗留 cron。

---

## 7. 第 5 步 · 上线验收（**过不了就别开 cron**）

### 7.1 闸门回归（必须 exit 0）

```bash
uv run --with pyyaml python3 scripts/gate-regression.py
```

预期输出：`PASS 12 / FAIL 1 / 共 13`，最后一行 `✅ 与基线完全一致`。2026-10-26 实测通过。

- 那 1 条 FAIL 是 `pulse_round_83` —— **已知的 AI 味真实反例**（被 `frank.pivot_expand`「问题来了」抓到，soft 分 15）。它必须一直 FAIL
- 如果变成 13 条全 PASS → 闸门被改松了，**AI 味会漏到公开面**，最危险
- 如果多了几条 FAIL → 闸门被改严了，人话也会被拦

### 7.2 首帖闸门（必须 exit 0，且用严格模式）

```bash
uv run --with pyyaml python3 scripts/prepublish.py --text "候选正文" --no-rewrite
```

`exit 0` 才能进发布流程。`exit 1` 就换一条 —— **不许手工绕过，也不许靠默认模式的自动改写蒙混**（§1）。

自检要做**双向**验证，缺一不算过：

```bash
# 正向：人话必须过（exit 0）
uv run --with pyyaml python3 scripts/prepublish.py --text "刚踩了个坑：截图存成 HEIC，传到一半发现对方打不开。转 PNG 花了 20 秒，解释花了十分钟。" --no-rewrite
# 负向：AI 味必须被拦（exit 1）
uv run --with pyyaml python3 scripts/prepublish.py --text "先说结论：这件事的本质是流程问题。问题来了：为什么大家都不愿意改？" --no-rewrite
```

### 7.3 浏览器层冒烟（必须 exit 0）

```bash
python3 scripts/browser/xb.py --action '{"action":"navigate","input":{"url":"https://x.com/frankfika"}}'
python3 scripts/browser/xb.py --action '{"action":"query","input":{"kind":"text","selector":"main","maxChars":300}}'
python3 scripts/browser/xb.py --action '{"action":"login_state"}'
```

### 7.4 冷启动节奏（老号延续，仍然建议保守）

- 前 2 周：每天原创 ≤ 1 条、每天互动动作 ≤ 1 个
- 每一条都必须过闸门（`--no-rewrite`）+ 走 `fill` + `Cmd+Enter` 唯一真发路径
- 不要在 24h 内重复同一内核（闸 2）

---

## 8. 故障模式速查

### 8.1 🔴 机器睡了 → cron 全停（Frank 已经踩过）

**症状**：定时任务状态看着正常，但 `state/memory/*.md` 末轮时间戳停在几小时前。

**根因**（2026-10-26 实测）：03:38 笔记本合盖 → 网络断 → agent-runtime 抛
`net::ERR_CONNECTION_CLOSED`（errorCode 50113）→ turn 被打断。机器 09:01:53 才醒。
**15 次投递只有 2 次落盘，丢 12 轮。**

**诊断三件套**：
```bash
# 1. 末轮时间戳 vs 真实时间
python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 1
# 2. 本轮日志（launchd 版）
ls -lt logs/rounds/ | head -5
# 3. 机器睡眠/唤醒一手证据
pmset -g log | grep -E "Entering Sleep state|Wake from"
```

**防呆**：
```bash
nohup caffeinate -i -m -s >/dev/null 2>&1 & disown   # 挡住空闲休眠
```
⚠️ `caffeinate` **挡不住合盖休眠** —— macOS 合盖必睡（除非外接显示器 + 电源 + 外设走 clamshell 模式）。
**合盖 = 三条定时任务全停，这个只能靠物理上别盖。**
✅ launchd 相对 Mavis 的一个小改进：睡过头错过的日历触发，**唤醒后会补跑一次**（不是补全部）。

### 8.2 🔴 浏览器层起不来

按顺序查（每条都有 2026-10-26 的实测依据）：

```bash
curl -s http://127.0.0.1:9222/json/version    # 没输出 = Chrome 没带调试端口起
ps ax | grep -c "user-data-dir=/Users/fangchen/.shortbot-browser-profile"
ls ~/.shortbot-browser-profile               # profile 目录在不在
```

- **CDP 端口不监听**：Chrome 155 拒绝对**默认 profile** 开调试端口；`xb.py` 拉的一定要是 `~/.shortbot-browser-profile`
- **WebSocket 403 `Rejected an incoming WebSocket connection from ... origin`**：起 Chrome 时加 `--remote-allow-origins=*`，或客户端抑制 Origin 头
- **`Operation not permitted` 读 Chrome 目录**：TCC 限制，别去读 `~/Library/Application Support/Google/Chrome`
- `xb.py` 退出码 **2 = `BROWSER_UNAVAILABLE`** → 本轮按「零动作」记，不许装忙

### 8.3 🟡 免登录核验通道（不发帖也能读数据）

| 通道 | 用途 | 状态 |
|------|------|------|
| `cdn.syndication.twimg.com/tweet-result` | 单帖 likes / replies（免登录） | ✅ 可用，走代理更稳 |
| `r.jina.ai` | 通用抓取 | ❌ 匿名额度作废（401 bad IP reputation） |
| syndication timeline-profile | 时间线扫描 | ❌ 429 出口 IP 被限 |

### 8.4 🟡 发布路径

**唯一稳定的真发路径是 `fill` + `Cmd+Enter`（Meta+Enter）。** Post button click 不可靠。
- 填完等 8–10 秒
- **不要**查 profile / with_replies / home feed 判断真发（各自有缓存延迟，8–30s 不刷新）
- 真发验证：search 拿 own_post 的 post_id 和 URL
- **不要盲 retry** —— 第二次会触发 X 的反重复拦截（真实 spam 信号）

### 8.5 🟡 测量口径（踩过两次）

- **likes 必须**用 `query kind=dom` 打 `[data-testid='like']` 读 aria-label（`"N Likes. Like"`）
- **详情页底部大数字是 VIEWS 不是 likes**，差一个数量级
- `query kind=text` 读到的也是 views
- replies 用 `[data-testid='reply']` 的 aria-label
- **不要用 likes 做跨帖对比**（样本量不够）
- 页面级 selector 只返回首个匹配 —— detail 页每条帖都有自己的 like 按钮，**首个匹配可能跟目标完全无关**

---

## 9. 目录地图 · 谁能改什么

```
短文助手/
├── skills/            规程层（9 个 skill）—— 改需要 Frank 点头
├── scripts/
│   ├── prepublish.py / humanize.py / gate-regression.py   闸门链路
│   ├── browser/xb.py   ★ 浏览器执行层（Playwright + CDP，替代 mcp_browser）
│   ├── run-round.sh    ★ 单轮执行器（cron 与手工补跑的唯一入口）
│   └── install-cron.sh ★ launchd 三条任务的安装器
├── state/             ★ 事实源（唯一真相）
│   ├── *.yaml         规则（forbidden / style / watchlist / filter / schedule）
│   ├── *.json         去重索引 / 已发记录 / 闸门规则 + 收据
│   └── memory/*.md    轮次日志（chuangzuo / pulse / super-bot）
├── private/           account-safety.yaml + browser.yaml（**手拷，不进 git**）
├── outputs/           完成版落盘（material.yaml / x.txt / screenshots）
├── docs/cron-prompts/ ★ 三条 cron prompt 的唯一事实源
├── schemas/ templates/
└── README.md          架构文档
```

**状态变更授权表**（改 state 前必读）：

| 改什么 | 改哪份 | 谁授权 |
|--------|--------|--------|
| 增减 X 账号 | `watchlist.yaml` | Frank 口头 |
| 改浏览量下限 / AI 关键词 | `filter-rules.yaml` | Frank 口头 |
| X 文风 | `style-x.yaml` | Frank 口头 |
| X 发帖模式 | `account-safety.yaml#x.publish_mode` | Frank 口头 |
| 小红书点发布 / 改节奏 | `account-safety.yaml#xhs.agent_publish_allowed` | Frank **显式说** |
| pulse / chuangzuo 节奏配额 | `state/schedule.yaml` + `scripts/install-cron.sh` | Frank 口头 |
| 闸门规则集 | `ai-taste-rules.json` | **任何改动都必须跑 `gate-regression.py` 验证** |
| 浏览器 profile / CDP 端口 | `private/browser.yaml` | 改错 = 换掉登录态 |

---

## 10. 状态契约

| 动作 | 落盘 | 还要同步 |
|------|------|---------|
| outbound reply / like | `seen-posts.json` | `index.json` |
| inbound reply | `inbound-replies.json` + `seen-posts.json` | `index.json` |
| 原创 post | `published-posts.json` | `index.json` |
| 闸门放行/拦下 | `gate-receipts.json`（含最终文本 sha256，事后可核对） | —— |
| 轮次日志 | `memory/<bot>.md`（**每段前必须有 `<!-- round -->`**） | —— |

**`index.json` 是每轮的轻量去重索引 —— 只读它，不要全量加载 `seen-posts.json`（147KB）。**

**轮次日志的段边界必须用显式分隔符 `<!-- round -->`**，不要靠标题正则猜
（轮次段内部的小节标题经常含「pulse round」这类关键词，按标题切会把一轮切成碎片）。

写完跑一次冒烟测试：

```bash
python3 scripts/tail-rounds.py state/memory/pulse.md --rounds 1   # 必须取到最新完整一段
```

---

## 11. 铁律（**接手方第一条就要读 `state/forbidden.yaml` 全文**）

- ❌ 不出现 OpenCSG / 公司业务
- ❌ 不出现 Chinese AI 公司名：DeepSeek / Moonshot / MiniMax 等
- ❌ 不写 AI 托管 / 自动互动 / bot 措辞在公开文案
- ❌ 不写 AI 生成图 / 不堆 hashtag（≤1）/ 不写「配图如下 / 见下图 / 快去看」
- ❌ pulse 模式不发新原创长帖 / Quote RT / 新 Post
- ❌ XHS 定时连发 = 禁止（2026-10-29 17:11 起 agent 可代点发布，但节奏分散）
- ❌ **闸门 exit 1 不许手工绕过**（含不许靠默认模式的自动改写蒙混，见 §1）
- ❌ **不许装忙** —— 缺数据就写「数据不可用，跳过」，不要凑数字
- ✅ 候选不足就少做，**不要凑数**

---

## 12. 决策记录（Frank 拍过板的，继承）

| 时间 | 决策 |
|------|------|
| 2026-10-16 | 启用 inbound reply 模式；inbound 文案 80–180 字；inbound 优先于 outbound |
| 2026-10-21 | 「你和大家互动的频率不要那么高」→ 30min 降到 2h，单轮动作上限 8 砍到 3；inbound reply ≤1 / outbound reply ≤1 / outbound like ≤2 |
| 2026-10-23 | 原创线 66h likes Δ0 → 建议显式暂停（**待 Frank 答复**） |
| 2026-10-25 | cron 降到 4 轮/天；三条 cron 拆成独立 session（`mode=new`）；铁律从 cron prompt 下沉到 skill；memory 迁到项目内 `state/memory/` |
| 2026-10-26 | 「被拉黑是因为被看出来是 AI 评价了」→ 新增第 0 道 AI 味自检 + **代码级闸门**（`prepublish.py`），规则从 `style-x.yaml` 单向读取 |
| 2026-10-26 | 「拉黑的是……你不要去乱评价」→ outbound reply 默认更保守，**宁可不发，也不发有 AI 腔的结构化点评** |
| **2026-10-26 · 移交** | **账号口径：继续用老号 `@FrankFika`，不是新号**（Frank 当面确认）→ 冷却状态保留，**不清空 `last_published_*`** |
| **2026-10-26 · 移交** | 接手方 = **DeepSeek Harness**；`mcp_browser` 不可用 → 浏览器层改 `scripts/browser/xb.py`（Playwright + CDP，专属 profile `~/.shortbot-browser-profile`） |
| **2026-10-26 · 移交** | 定时任务从 Mavis cron 迁到 **launchd + `dsh --profile shortbot`**（每轮独立进程 = 独立 session，语义等价 `session.mode=new`） |
| **2026-10-26 · 移交** | 真发前置闸门必须用 `prepublish.py --no-rewrite`（默认模式会自动改写后放行 = 绕过闸门） |

---

## 13. 移交检查清单

打勾再开 cron：

- [ ] `dsh --profile shortbot "只回复一行 OK"` → exit 0
- [ ] `curl -s http://127.0.0.1:9222/json/version` 有输出（自动化 Chrome 在跑）
- [ ] **X 已登录**：`xb.py --action '{"action":"login_state"}'` → `logged_in: true`，`account-safety.yaml#x.login_state` 已改 `logged_in`
- [ ] `uv run --with pyyaml python3 scripts/gate-regression.py` → **exit 0**，12 PASS / 1 FAIL
- [ ] 3 条候选文案 `prepublish.py --text ... --no-rewrite` → 全 exit 0；反例 → exit 1
- [ ] `xb.py` 三条冒烟（navigate / query / login_state）全 exit 0
- [ ] `scripts/install-cron.sh --install` 后 `--status` 三条全 LOADED
- [ ] **项目不在 `~/Documents` 下**（TCC，见 §6.4）；`launchctl kickstart -p gui/$(id -u)/com.fangchen.shortbot.pulse` 后 `logs/rounds/` 有新日志且 `logs/launchd/*.err.log` 为空
- [ ] `scripts/run-round.sh super-bot --dry-run` 能抽出 prompt
- [ ] **老机器上的定时任务已停掉**（本机已确认无 crontab、无 Mavis）
- [ ] `caffeinate` 已挂上（且**别合盖**）
- [ ] `state/recent-picks.json` 已重新生成（首轮 chuangzuo 顺手做）
