# Codex session 模式 · cua_repl 完整链路复盘菜谱

> 目的：把"扫 → 抓图 → 写 → 发"用 cua_repl 真跑的全流程沉淀下来。下次 automation 触发，Codex agent 按这个菜谱 1 轮出 3 条完成版。
>
> 实测时间：2026-10-15 08:46-08:53+08:00，一次成功发 3 条 Gemini 4 Argon / Anthropic Singapore / OpenAI EU AI agents。
>
> 实现细节参考 `skills/publisher-x/SKILL.md`（实测步骤 1-8），本文件是端到端流程模板。

## 0. 前置

- 工具可用：`mcp__cua_repl__js` + `exec_command`
- X 登录：`https://x.com/FrankFika` 显示 `陈放Frank🕊️ (@FrankFika)` 即视为已登录
- 一次创建 1 个 `iab` tab，全流程复用
- 读 `$CODEX_HOME/automations/users-fangchen-documents-skills-readme-md-1-state-watc/memory.md` 避免重复抓已发作者

## 1. 创建 tab + 验证登录

```js
const tab = await cua.createBrowserTab("iab", "https://x.com/FrankFika", { visible: true });
// 等 load + 看 AX
await tab.playwright.waitForLoadState("domcontentloaded", { timeoutMs: 15000 });
await tab.playwright.waitForTimeout(3500);
const ax = await tab.getAXState({ disableDiffing: true, emit: false });
// 确认 AX 里有 "陈放Frank🕊️ (@FrankFika)" 字样
```

> ⚠️ X 是 SPA，DOM/CSS 选择器很多"裸 URL"，AX tree 才是稳定数据源。**永远用 `tab.getAXState()` 拿推文**。

## 2. 扫 watchlist 高优 handle timeline

按这个顺序扫（每个 handle 一次导航 → 等 3.5s → 抓 AX → 提取 status 链接 + 浏览量）：

```
高优（必扫）：
- OpenAI（GPT / ChatGPT 重大发布）
- AnthropicAI（Claude 发布 + 政策动态）
- GoogleDeepMind（Gemini 发布 + 论文）
- karpathy（已发过需 dedup，扫一下确认有否新帖）
- sama（OpenAI 个人推）
- AnthropicAI（重复扫描不是问题）

次优（候选）：
- JensenHuang, NVIDIA
- dotey, oran_ge, op7418（中文 KOL）
- deepseek_ai, Alibaba_Qwen（中国厂商）
- _akhaliq（论文 / Demo 聚合）
- testingcatalog（产品爆料）
```

每 handle 的 AX 提取逻辑：

```js
const ax = await tab.getAXState({ disableDiffing: true, emit: false });
const lines = ax.split("\n");
const found = {};
for (let i = 0; i < lines.length; i++) {
  const m = lines[i].match(/Value: x\.com\/<HANDLE>\/status\/(\d+)/);
  if (m && !found[m[1]]) {
    let time = "", views = "";
    for (let j = i; j < Math.min(lines.length, i+30); j++) {
      const t = lines[j].match(/(\d+)\s*(hour|day|minute)s?\s*ago/);
      const v = lines[j].match(/(\d+)\s+views/);
      if (t && !time) time = t[0];
      if (v && !views) views = v[0];
    }
    found[m[1]] = { id: m[1], time, views };
  }
}
```

按 views 排序 + 时间过滤（≤24h）→ 候选列表。

## 3. 过滤 + 选 3 条

对每条候选：

- **views ≥ 15000**（filter-rules.yaml#min_view_count）
- **AI 关键词命中**（filter-rules.yaml#ai_keywords 中英双表，宽松匹配）
- **不在 `state/seen-posts.json` 的 post_id 列表里**
- **原帖 paste 在 24h 内**（避免重复发老帖）

排序：优先 fresh (≤ 12h ago) + 高 views。

取前 3（README 已更新约束：候选 ≥ 3 取前 3）。

## 4. 抓每个候选的真图

每个候选准备 ≥ 2 张真图（style-x.yaml#must_have），推荐 4-6 张：

- **x-<handle>-post.png** — 原帖 modal 视角（最重要的"这就是真帖"证据）
- **x-<handle>-profile-top.png** — 该 handle profile 时间线顶部视角（证明帖在 timeline 上）
- **x-before-post.png** — 我自己发之前的 compose modal 视角
- **x-after-post.png** — 点 Post 后跳到 /home 的截图
- **x-live-post.png** — 我自己 profile 时间线顶部（"X minutes ago" 视角）

抓图代码（modal / profile 通用）：

```js
const fs = await import("fs");
const shot = await tab.screenshot({ fullPage: false });
fs.mkdirSync("/path/to/screenshots", { recursive: true });
fs.writeFileSync("/path/to/screenshots/x-name.png", shot);
```

存好后 `ls /path/to/screenshots/` 确认非空。

> ⚠️ 不要硬塞图。openai.com 被 Cloudflare verify 拦 / anthropic.com/news 全 404 → 用 X 帖内 link card / chart 作证据就够了。

## 5. 写 material.yaml + x.txt

### material.yaml 字段

参考已有的 `outputs/1015-pm/karpathy-frontier-5000/material.yaml` 模板。关键字段：

```yaml
material_id: 1015-am-01
slot: am
scanned_at: '2026-10-15T08:46:00+08:00'
author:
  name: Google DeepMind
  handle: GoogleDeepMind
  lang: en
original:
  url: https://x.com/GoogleDeepMind/status/2110039274922131792
  post_id: '2110039274922131792'
  posted_at: '2026-10-14T00:05:00+00:00'
metrics:
  views: 2300000
  likes: 6100
  retweets: 1000
  replies: 351
  bookmarks: 1500
ai_match: true
summary: >-
  一句话中文摘要（带 1-2 个数字）
evidence_links:
  - https://x.com/<HANDLE>/status/<POST_ID>
treatment_hint: quote_retweet
source: hot-topic-tracker cua_repl scan
```

### x.txt 字段

按 `state/style-x.yaml` 写：

- voice: zh-CN 口语爆款风（对标 @canghe / @NFTCPS）
- length: 180-320 字（min 80, max 500）
- 结构：冲击钩子（数字 / 反差）+ body（步骤 / 数字）+ ending（轻收尾，不写"快去看"）
- must_have: ≥ 1 个具体数字 / 链接 + ≥ 2 张真图 + 原帖 x.com 链接（X 自动 quote embed）
- forbidden: "配图如下" / "见上图" / "快去看" / "一定要" / "AI 总结" / "一键" / "保姆级"
- emoji: 0-2 个
- hashtag: 0-1 个

文件末尾加 meta 行（脚本自动追加）：

```
# material_id: 1015-am-01
# treatment: quote_retweet
# screenshots: x-name1.png, x-name2.png
```

> ⚠️ x.com 链接放正文末尾（不是第一条），X 会自动渲染成 Quote Repost 卡片，不需要手动点 Quote。

## 6. 在 x.com/compose/post 真发

完整实测流程（publisher-x/SKILL.md 实测有效段）：

```js
const base = "/path/to/output/<candidate>";

// 6.1 打开 compose
await tab.goto("https://x.com/compose/post");
await tab.playwright.waitForLoadState("domcontentloaded", { timeoutMs: 15000 });
await tab.playwright.waitForTimeout(3500);

// 6.2 拿 AX 找 textarea + Choose Files + Post button 索引
const ax = await tab.getAXState({ disableDiffing: true, emit: false });
let taIdx = -1, filesIdx = -1;
for (const l of ax.split("\n")) {
  const tm = l.match(/^\s*(\d+)\s+text entry area/);
  if (tm && taIdx < 0) taIdx = parseInt(tm[1]);
  const fm = l.match(/^\s*(\d+)\s+button\s+Choose Files/);
  if (fm && filesIdx < 0) filesIdx = parseInt(fm[1]);
}

// 6.3 点 textarea + paste 正文
await tab.click(taIdx);
await tab.playwright.waitForTimeout(800);
const body = fs.readFileSync(base + "/x.txt", "utf8").split("\n")
  .filter(l => !l.startsWith("# ")).join("\n").trim();
await tab.paste(null, body, { format: "text" });
await tab.playwright.waitForTimeout(2500);

// 6.4 附图：filechooser event + setFiles
const fcPromise = tab.playwright.waitForEvent("filechooser", { timeoutMs: 8000 });
await tab.click(filesIdx);
await tab.playwright.waitForTimeout(1200);
const fc = await fcPromise;
await fc.setFiles([
  base + "/screenshots/x-<handle>-post.png",
  base + "/screenshots/x-<handle>-profile-top.png"
]);
await tab.playwright.waitForTimeout(7000);

// 6.5 找 Post button + pre-post 截图
const ax2 = await tab.getAXState({ disableDiffing: true, emit: false });
let postIdx = -1;
for (const l of ax2.split("\n")) {
  const m = l.match(/^\s*(\d+)\s+button\s+Post\s*$/);
  if (m) { postIdx = parseInt(m[1]); break; }
}
const before = await tab.screenshot({ fullPage: false });
fs.writeFileSync(base + "/screenshots/x-before-post.png", before);

// 6.6 点 Post + 验证跳 /home
if (postIdx > 0) {
  await tab.click(postIdx);
  await tab.playwright.waitForTimeout(5500);
  const newUrl = await tab.url();
  // 期望: https://x.com/home（modal 关了跳回首页）
}
```

> ⚠️ **AX index 每次重新 fetch 后会变**，所以每步操作前必须重新 `getAXState()`。Playwright locator click 在 X Draft.js 上不稳，**优先 AX index**。
>
> ⚠️ **compose modal 跳转后 textarea 索引会失效**（旧 tab 上一次的 AX 索引失效），要重新 fetch。

## 7. 抓 own post URL

```js
// after-post 截图
const after = await tab.screenshot({ fullPage: false });
fs.writeFileSync(base + "/screenshots/x-after-post.png", after);

// 去自己 profile 拿 own URL
await tab.goto("https://x.com/FrankFika");
await tab.playwright.waitForLoadState("domcontentloaded", { timeoutMs: 15000 });
await tab.playwright.waitForTimeout(3500);
const ax = await tab.getAXState({ disableDiffing: true, emit: false });
const matches = [...new Set(
  [...ax.matchAll(/Value: (x\.com\/FrankFika\/status\/\d+)/g)].map(m => m[1])
)];
// 最新的一条（首个）就是刚发的
const ownUrl = matches[0]; // e.g. x.com/FrankFika/status/2110533769727967326

// live-post 截图
const live = await tab.screenshot({ fullPage: false });
fs.writeFileSync(base + "/screenshots/x-live-post.png", live);
```

## 8. 更新 state 文件

每次发完都更新：

- **`state/published-posts.json`** — 加新条目（最前面，倒序）
- **`state/seen-posts.json`** — `entries[i].posted_to_x` 加子对象（own_post_id / url / at / treatment_used / media_count）
- **`state/account-safety.yaml#x.last_published`** — 更新 latest post
- **`x.txt` 末尾** — 加 `# posted_url: ...` + `# posted_at: ...`

Python 一把梭：

```python
import json
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
# published-posts, seen-posts, account-safety 都按上述模板更新
```

## 9. memory.md 追加

每次跑完整轮都在 `$CODEX_HOME/automations/users-fangchen-documents-skills-readme-md-1-state-watc/memory.md` 末尾追加：

```markdown
## 运行记录
- <ISO 时间>+08:00（Codex session 触发，本次）
  - 候选 N 条 → 完成版 N 条 → 已发 X N 条（URL 列表）
  - XHS 状态（停手 / 已存草稿）
  - 异常（如有）：官网 Cloudflare / 404 / watchlist handle 缺席
```

## 10. 完成态报告（给 Fang）

不发技术细节，直接给：

- candidate_count
- 完成版落盘清单（绝对路径列表，n 条）
- 已发 X URL 列表（每条带源作者 + 标题 1 句话）
- XHS 状态
- 异常 / 阻塞（如有）

最后一行固定 `::inbox-item{...}`。

## 失败兜底（不假装已发）

| 现象 | 动作 |
|------|------|
| `We've temporarily limited your login` | 立即停手，告诉 Fang，不硬刷（参考 `state/forbidden.yaml#login_rules.x_login`） |
| 验证码 / 二次验证 | 把 URL 给 Fang，让 Fang 处理 |
| textarea / Choose Files / Post click 超时 | AX index 重试；不要盲目换 locator click |
| filechooser 等不到 | 改用 `setInputFiles` via evaluate（fallback） |
| 上传图失败 / 网络错 | 重试 1 次，仍失败告诉 Fang |
| Post 后拿不到 URL | 截图当前页给 Fang，标 `posted_status: uncertain` |

## 关键不变量（每轮都遵守）

1. **不绕过二次验证**
2. **不擅自重试 > 1 次**
3. **不把失败当成功**
4. **不假装已发**（拿不到 URL = 未发）
5. **不写 OpenCSG / 公司业务相关**
6. **不用 AI 生成图**
7. **不写"配图如下 / 见上图"**
