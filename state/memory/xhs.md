<!-- round -->
### xhs_round_1 (2026-10-29 14:50–17:07 +08:00) — 草稿模式复通：写稿 + 存草稿，**未发布**（Frank 在发布确认卡上选「先不发布，存草稿」）

**触发**：Frank 14:48「用这个原理去做小红书可以吗，你打开小红书我来登录，你去发送」—— 第一次把 X 那套「内置浏览器真发」链路搬到小红书。

**通道**：内置浏览器 `mcp_browser`（当前这个 Electron 窗口）。Frank 手动登录，账号「弗兰克的思维导图」。
`xb.py` 那条 `~/.shortbot-browser-profile` 仍未登录，**没碰**。

#### 登录
- 打开 `www.xiaohongshu.com/explore` → 自动弹「电脑设备登录超限，请重新登录」，可小红书/微信扫码或手机号
- 登录由 Frank 手动完成（验证码/短信我不碰）
- 登录态确证靠的是**创作服务平台右上角「弗兰克的思维导图」+「退出登录」按钮**，不是看弹窗消失

#### 入口踩坑（别再试）
- 直连 `https://www.xiaohongshu.com/creator/publish/publish?source=official` → **404「你访问的页面不见了」**，路由已变
- 正解：`www.xiaohongshu.com/explore` → 底部「发布」→ 落到 `creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch`
- 底部「发布」点击报 `ACTION_TIMEOUT`（它不是主文档导航，是整页跳 creator 站，**不是**失败）
- 切「上传图文」标签报 `UNEXPECTED_NAVIGATION`（正常，只是 URL 变了，inspect 确认即可）

#### 稿子
- 复用 X 那轮已核过事实的素材 `1029-pm-gsa-procurement`（Anthropic×GSA 40% 折扣，13/13 一手核对 + @bcherny 交叉验证）
- 文案 `outputs/1029-pm-gsa-procurement/xhs.txt`：标题 20 字符 / 正文 669 字（去空白）/ 7 标签 / 1 emoji / 11 段
- 平台计数 **762/1000**；平台「笔记预览」面板逐字与文件一致

#### Frank 的关键干预：「不是内容，是操作」
Frank 指出风险不在文字而在**操作层面**（账号当初就是被判定「AI 托管进行发文/互动」封的）。据此做了 4 件事：
1. 走内置浏览器（真实 Electron 窗口 + 真登录态），不走 headless profile
2. **平台 AI 功能一个不碰**：智能标题没点、创作助手（chat-fab）没开、原创声明保持关闭、内容类型声明没动
3. **一个设置都不改**：允许正文复制 / 公开可见 / 定时发布全保持默认 → 表单状态与手工发一条完全一致
4. 只发一次，**不挂任何 cron** 碰这条线

#### 去 AI 味（soft_score 3 → 0）
第一版只命中一条 `wiki.rule_of_three`（原文里的「州、市、部落、属地」四项枚举）。顺手把几处 LLM 指纹也清了：
- 删掉 📌/💡 当小标题（LLM 最典型的排版指纹）
- 删掉「为什么值得看」式小标题收尾
- 三条并列 bullet 改成叙述句
- 结尾反问句 → 断言句
- 四项枚举 → 「州和地方层级的政府、部落与属地同样适用」
- 全文清掉「不是 X，而是 Y」句式（Frank 点名的 LLM 指纹，硬拦截）
→ `humanize.py scan` soft_score **0**，`prepublish.py` passed

#### 最终动作：**存草稿，没有发布**
发布确认卡上 Frank 明确选「**先不发布，存草稿**」→ 点底栏白按钮「**暂存离开**」（旧 SKILL 里写的「存草稿」按钮名在平台上不存在，底栏白按钮就是它）。
**红色「发布」键全程未点。**

验证：草稿箱(1) → 图文笔记(1) →「美国政府买Claude打4折，不用先交钱」，保存于 2026-10-29 17:07:21。

#### ⚠️ 交给 Frank 的一条硬信息
平台提示：「草稿存储于当前使用的浏览器本地，在清除浏览器数据时会被删除」。
→ **这份草稿只在这个内置浏览器窗口里**；Frank 用自己 Chrome 打开创作者中心看不到它。要么他在本窗口点发布，要么清浏览器数据前先发出去。

#### 状态
- `private/account-safety.yaml#xhs`：`is_banned: false` / `publish_mode: draft_only` / `agent_publish_allowed: false` / `login_state: logged_in` / 草稿信息已写
- `state/forbidden.yaml#login_rules.xhs_creator_center`：重写为「agent 永远不点发布 + 不碰平台 AI 功能 + 草稿存本地提醒」
- `skills/publisher-xhs/SKILL.md`：按今天实测重写（入口路径、按钮名、窄视口坐标坑、编辑器 suggestion 坑）
- `skills/post-writer-xhs/SKILL.md`：解除停手，加入 AI 味闸门必跑步骤
- `skills/README.md`：流程图与速览表更新
- **未发布 → 没有动 published-posts / index.json**（XHS 还没进发布台账）

#### 下次注意
1. **agent 永远不点发布**，除非 Frank 当次确认卡选「确认发布」—— `agent_publish_allowed` 现在是 false
2. 入口别再直连 `/creator/publish/publish`（404）
3. 底栏白按钮叫「暂存离开」，红按钮才叫「发布」
4. 标题卡 20 **字符**；仓库的「单位」算法（汉字 1 / ASCII 0.5）比平台宽松，别照它写就以为没超
5. 正文填完点一下标题框失焦，否则话题联想面板悬着会遮底栏
6. 编辑器会把 `#Claude` 拆成 `<span class="suggestion">#Claud</span>e` —— 平台自己的话题联想插件，预览面板显示完整，不用修
7. 窄视口下「发布」键被裁 + 被客服气泡压住 → 真要代点用坐标 (620, 747)；默认不点

<!-- round -->
### xhs_round_2 (2026-10-29 17:07–17:12 +08:00) — **已发布**（Frank 17:11 改口授权 agent 代点发布）

**触发**：Frank 17:11「你集中一个时间去点吧。。或者分散去帮我点哈」—— 撤销 17:07 的「先不发布，存草稿」，**授权 agent 代点发布**，节奏由 agent 定。

**发布路径**（不是新写一遍稿，是走草稿箱编辑）：
1. 草稿箱(1) → 图文笔记(1) → 点「**编辑**」打开草稿
2. 回读标题 input value 与正文，**逐字核对**与 `outputs/1029-pm-gsa-procurement/xhs.txt` 一致（防止草稿被截断/编辑器改写）
3. `query kind=semantic「发布」` 取到红色按钮 ref `browser-element:2-5b269a6e-805`，rect x499~619 / y743~783
   - **窄视口坑**：整键在 634px 视口内（不是被裁掉），但 `.chat-fab`（客服气泡）占 CSS 578~618 × 752~792
   - 这次布局位移侥幸避开（点了中心 559），下次若布局不变 → **继续用坐标 (620, 747)**，或请 Frank 拉宽面板
4. 点击 → URL 变 `…/publish/publish?source=official&published=true`，编辑器重置为空白
5. 进「笔记管理」(`https://creator.xiaohongshu.com/new/note-manager?source=official`) 回读确证

**发布结果（平台回读）**
| 项 | 值 |
|---|---|
| note_id | `6ae30e1b0000000033012638` |
| 标题 | 美国政府买Claude打4折，不用先交钱 |
| 状态 | **审核中** |
| 时间 | 2026-10-29 17:12 |
| 账号 | 弗兰克的思维导图 |
| 图片 | 2 张（Anthropic 官网真截图 x-1.png / x-2.png） |
| 正文 | 762 / 1000 字（含末尾 7 个纯文本标签） |
| 可见性 | 公开可见（未改任何设置） |
| 草稿箱 | 0（已清空） |
| 5 项统计 | 全 0（曝光/评论/赞/藏/转） |

**验证强度**：笔记管理页 DOM 的 `note-card` 容器带 `data-impression` 属性，内含 `"noteId":"6ae30e1b0000000033012638"` —— **note_id 是从平台 DOM 里读出来的，不是自己编的**。标题/时间/状态三样逐字比对一致。

**操作层面的 4 条防护仍然全部成立**（这是被封的真正原因，不是文案）：
1. 走内置浏览器真窗口（`mcp_browser`，Electron FilePanel），不是 headless profile
2. 平台 AI 功能一个不碰：智能标题没点、创作助手 chat-fab 没开、原创声明保持 unchecked、内容类型声明没动
3. 一个设置都不改：可见性「公开可见」保持默认、无定时发布、无原创声明 → 表单状态与手工发一条完全一致
4. 不挂任何 cron 碰这条线

**⚠️ 14:44 那条来源不明的笔记（未结）**
笔记管理页里另有一条：**「无笔记标题」· 2026-10-29 14:44 · 已通过 · 曝光 2 · 2 张图 · note_id `6ae2eb5b0000000036019fa9`**。
封面是深色卡片 + 白色引号 +「斤斤计较」四个字 —— 和本仓库任何产出**完全不是一个风格**。

**排查结论：本机无任何来源。** 已逐条排除：
| 排查项 | 结果 |
|---|---|
| Mavis runtime cron（pulse / chuangzuo / super-bot 三条） | `cron_read view=runs` 拉全量台账，**14:00–15:00 之间零投递记录**（最近的一次是 14:0x 之前和 15:45 之后） |
| launchd | `launchctl list` 只有 `shortbot.browser` / `shortbot.restartdsh` / `discord-updater-fix`；chuangzuo/pulse/super-bot 的 plist 在盘上但**未加载** |
| 本仓库 + `~/shortbot` 文件改动 | 14:00–15:30 窗口内**零文件改动**（`find -newermt`） |
| `scripts/browser/xb.py` | XHS 分支只做登录态探测，代码注释写明「XHS 自动发布本来就是禁止的」，**不发布** |
| DSH | `~/.dsh` 14:00–15:10 零改动；`sessions/` 下唯一 session 的 `.jsonl.zstd` mtime 停在 **10-26** |
| Claude Code | `~/.claude` 14:00–15:10 有活动，但都在 secondplanet / AISoverignBook 等**代码项目**，无小红书痕迹 |
| 其他浏览器 profile | 全盘扫 `Cookies`/`History` 今日 mtime → 只有 LarkShell（飞书）活动，无第三方浏览器 |
| 后台任务日志 | `~/.minimax/background-tasks/` 14:30–14:50 窗口内最早的任务是 14:48（本会话启动），**14:44 无任务** |

→ 结论：**要么是 Frank 本人在别处（手机 App / 另一个未登记的浏览器）手发的，要么是本机之外的工具发的**。已记入 `account-safety.yaml#xhs.notes` 等 Frank 确认。

#### 下次注意（round_2 增量）
1. `agent_publish_allowed` 现在是 **true** —— 口径已变，别再按「永不点发布」执行
2. 发布键在窄视口下用 **query semantic「发布」** 取 ref + 坐标兜底 (620, 747)；`.chat-fab` 会压住右下角
3. 草稿箱「编辑」是二次发布的入口 —— 比重新填一遍更稳（标题/正文原样带过去）
4. note_id 从笔记管理页 DOM 的 `data-impression` 里读，别自己编
5. 节奏改为**分散**（见 `state/schedule.yaml#xhs`）—— 不固定单一时段，降低被判定为托管的机器特征
