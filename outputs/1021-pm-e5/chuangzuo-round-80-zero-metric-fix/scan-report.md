# chuangzuo round 80 · 2026-10-21 12:45–12:52 +0800

## 结论：本轮零发送。本轮最重要的产出是**第二次修正自己的数据**——上一轮修正的是结论，这一轮修正的是**测量方法**。

## candidate_count
未进入扫 handle 阶段。冷却满足（178 min），密度未查（因为在数据核查阶段就停下了）。

---

## 🔴 发现：round 50 表格里的 likes 数字全是幻觉

round 79 我用 views 推翻了 round 50 的"买方减半"，当时已经觉得那组数字可疑。
本轮进一步核实：**round 50 表格里的 likes 数字（19 / 10 / 61）根本不是 likes。**

### 实测（12:45 采样，用 `[data-testid='like']` 的 aria-label 直读）

| cluster | 主题 | 时长 | views | **likes** | replies |
|---|---|---|---|---|---|
| 20 | agent 取代人 | 12.5h | 79 | **1** | 3 |
| 23 | 地图会过期 | 5.5h | 37 | **0** | 0 |
| 24 | 效率不能记账 | 4.5h | 29 | **0** | 0 |
| 25 | dry→wet lab | 3h | 29 | **0** | 0 |

round 50 写的是：
> | chuangzuo 76 (1h) | 19 | | chuangzuo 77 (48m) | 10 | | cluster 20 (8h) | 56 → 61 |

**cluster 20 在 12.5h 后只有 1 个 like，不是 61。**
76 和 77 现在是 0 likes，不是 19 和 10。

### 两轮修正的关系
- round 79 修正的是**结论**：「买方减半」的方向性判断错了 → 正确
- round 80 修正的是**数据本身**：那组 likes 数字从来就不是 likes → 上一个修正的前提也不成立

也就是说，**我基于一组不存在的数据推翻了一组也不存在的数据**。
两边都不该被继续引用。

---

## 📊 真实情况（第一次有可信基线）

**原创线在这个账号上的真实表现是：接近于零。**

4 条原创跨 12.5 小时，合计 79 views / 1 like / 3 replies。
其中唯一那个 like（cluster 20）来自 0xJun.xy，是 8 小时后的长尾——pulse round 50 已记录过这个信号。

同期 pulse 互动线：
- @dyiapianis **followed you**
- @softpoo 赞了 outbound-126

**原创线和互动线之间不是"效率差异"，是完全不同的两个量级。**

---

## 为什么本轮不发

不是因为低热期（那个结论建立在 views 上，views 口径本身没错，
21→23→29→29 的减速曲线是真的）。是因为**现在有更硬的证据表明原创线的边际收益接近零**：

在 3625 粉丝、79 views / 1 like 的真实基线上，再发一条原创，
预期收益是"多一个接近零的点"。而 pulse 的互动线正在产出 follow 和 like——
**把预算从原创挪到互动，是有数据支撑的明确改进。**

但这个决策不该由我在这一轮单方面执行：它涉及 chuangzuo 这条 cron 的存废。
按 super-bot 边界，规则/流程改动要 Frank 显式拍板。

---

## 建议（等 Frank 拍板，本轮未执行）

1. **原创线 chuangzuo 降频或暂停**，把动作预算集中到 pulse 互动线。
   依据：79 views / 1 like vs follow + like。
2. **如果继续发，改策略而不是改频率**：
   - 当前 4 条全是"中文长文 + 抽象观点 + 个人经历"
   - 试试**短句 + 具体数字 + 可验证的事实**，或者**中英双发**（英文线程读者确实在互动）
   - 互动线已经证明英文技术线程有真实反馈（@dyiapianis / @softpoo）
3. **测量方法写进 SKILL.md**：likes 必须用 `[data-testid='like']` 的 aria-label 读，
   详情页底部的数字是 views 不是 likes。这条已经在 memory 里踩坑两次了。

---

## 已发 X URL
本轮无。

## XHS 状态
停手。0 条草稿。

## 异常
- mcp_browser 偶发 `Validation failed: root: must not have additional properties`（本轮 3 次，重发即恢复）
- 一次 URL 漂移：navigate 到 cluster 23 详情页后，query dom 返回了 `x.com/i/lists/...` 的
  "469 Likes"，是页面还在加载中就 query 了。加 wait 4000ms 后正常。
  **教训：navigate 后如果 query 返回的 URL 不是目标 URL，说明页面没加载完，要等。**

## 下次启动先看
- **不要再引用 round 50 的 likes 数字，也不要引用 round 79 的"低热期"框架**——
  后者虽然 views 数据没错，但框架建立在一个错误的对照组上。
- 唯一可信的基线是本文件的表格（likes 用 aria-label 直读）。
- 已扫 handle 不变：home / AnthropicAI / GoogleDeepMind / dotey / karminski3 / howie_serious
- 本轮未新增扫描
- 跳过 topic_signature：claude-designs-protein-binders-wet-lab-paradigm（已发）