# 短文助手 · 本地控制台

把原来"你对着 Codex 说话、我去翻 state/ 和 outputs/"的过程，做成一个能在浏览器里点的本地面板。
**判断层没搬走** —— 面板只是壳，写稿和取舍仍然是 Codex 在做（见下面「交给 Codex」）。

## 启动

```bash
./console/start.sh          # 起服务 + 自动开浏览器
./console/start.sh --fg     # 前台跑，Ctrl+C 停
```

- 地址：`http://127.0.0.1:8848`
- **在自己的 Terminal 里跑** `./console/start.sh` 才能常驻（后台进程会随启动它的会话一起被回收）
- 端口：`SHORTBOT_CONSOLE_PORT=9000 ./console/start.sh` 可改
- 日志：`logs/console.log`

## 自检

```bash
.venv/bin/python console/selftest.py
```

29 项：全部 API 路由、路径穿越防护、边界输入、闸门与 codex 两个受控动作，
以及**只读性验证**（跑完一遍后 `state/` 和 `outputs/` 的指纹必须不变）。

## 页面

| 页 | 看什么 | 数据来源 |
|---|---|---|
| 总览 | 通道体检（能不能真发）、账号状态、冷却进度、待发备稿、最近发布 | `private/account-safety.yaml`、`state/*` |
| 备稿 | 每条备稿的素材包、已核对事实、正文、真截图、status.md；一键「交给 Codex 处理」 | `outputs/*/` |
| 已发 | 全部已发布台账，可搜 | `state/published-posts.json` |
| 互动台账 | like / reply / quote 逐条 | `state/outbound-actions.json` |
| 闸门 | 贴一段正文直接跑 `scripts/prepublish.py`；历史回执 | `state/gate-receipts.json` |
| 红线 | 禁忌清单、X/小红书文风、过滤规则 | `state/forbidden.yaml` 等 |
| 交给 Codex | 一句话指令 → 后端 `codex exec` 跑 → 输出回显 | `codex exec` |

## 只读边界

面板**不写**任何 `state/` 文件。唯一会动仓库的两处，都是调用现有脚本：

1. 「闸门」页跑 `scripts/prepublish.py` —— 它自己会往 `state/gate-receipts.json` 追加回执，这是脚本原有行为。
2. 「交给 Codex」跑 `codex exec` —— 它按你给的指令自己决定写什么。跑之前想清楚。

面板自己算出来的两个派生量，都不落盘，随时可重算：

- **闸门状态**：用 `prepublish.py` 同口径算（去掉 `# meta` 行再 sha256 前 16 位），跟回执对不上就标「回执过期」。
- **已发判定**：只认硬证据 —— 台账里出现该 `material_id` / 原文 URL / 备稿路径。X 和小红书分开算，一条稿可能小红书已发、X 没发。

## 内置浏览器

面板是 `127.0.0.1` 上的本地页。**Codex 内置浏览器目前是被 Work settings 关掉的**
（`Local browser use is disabled in Work settings`），所以：

- 面板的视觉确认这次是用 Playwright headless 做的；
- 真发 X / 小红书仍然只能走内置浏览器，且要先在里面登录。

启用步骤：Work settings → 打开 Local browser use → 在内置浏览器里登录 X 和小红书（含 2FA）。
启用后，内置浏览器可以直接打开 `http://127.0.0.1:8848`，面板和发布通道就在同一个窗口里。

## 目录

```
console/
├── serve.py      # 标准库 HTTP 服务 + JSON API（无第三方依赖）
├── start.sh      # 启动脚本
└── static/       # index.html / style.css / app.js（无构建步骤）
```
