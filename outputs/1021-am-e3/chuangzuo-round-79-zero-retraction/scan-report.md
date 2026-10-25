# chuangzuo round 79 · 2026-10-21 10:40–10:45 +0800

## 结论：本轮零发送，且**撤回 round 50 / round 78 的一个结论**

## candidate_count
未进入扫 handle 阶段 —— 在开工前的账号健康度采样环节就发现前提被推翻，
继续扫候选、按原方向写稿就是在一个已被证伪的假设上再加一条。
候选扫描：**未执行**（不是扫完 0 候选，是主动中止）

## 为什么中止

cooldown 满足（54 min > 30 min），密度正常（with_replies 无手动帖），
 Frank 手动发帖 06:01/06:05/06:07 那波已过。

**唯一中止理由：上一轮的方向依据被自己的数据推翻。**

round 50（pulse）根据 1 小时点赞数得出：
> 买方/资本向内容互动率约为技术向的一半（round 76 技术向 19 likes vs round 77 买方向 10 likes）

round 78（chuangzuo）据此把方向切成 cluster 25 技术向，理由写进 material.yaml：
> "与 round 23 技术向互补"、"Frank 决定 cluster 25 走科学 × AI 应用"、流量盘子交给技术线

pulse round 51 留了一个待办：**cluster 25 的 1h 数据必须补，用来判断"买方减半"是主题问题还是整体低热期。**

本轮补齐了这个数据点，结果是：

| cluster | 主题 | 发出至今 | views | replies | likes |
|---|---|---|---|---|---|
| 23 | 技术向 · 地图会过期 | 3.5h | **37** | 0 | 0 |
| 24 | 买方向 · 效率不能记账 | 2.5h | **29** | 0 | 0 |
| 25 | 技术向 · dry→wet lab | 1.0h | **21** | 0 | 0 |

归一化到 views/小时：
- cluster 23 = 37 / 3.5 = **10.6 /h**
- cluster 24 = 29 / 2.5 = **11.6 /h**
- cluster 25 = 21 / 1.0 = **21.0 /h**

## 两个结论

**1. "买方减半"不成立。** round 50 用 likes 比较，而三帖 likes 全是 0 ——
0 和 0 比不出"减半"，那个 19 vs 10 的对比在统计上是无意义的（样本 n=2 且都是小整数）。
换成 views 同口径看，买方向（11.6/h）反而略高于更早的技术向（10.6/h）。
**round 78 因为这个结论做的方向切换，前提是错的。**

**2. 更可能的解释：账号整体处于低热期。** 三帖速率都在 10–21 views/h，
远低于 cluster 18–20 当时的 40–56 likes。这不是主题偏好问题，
是这段时间账号触达整体下来了。原因未知（可能是算法分发、时间段、
或连续发原创的边际效应），但**"换主题就能救"这个假设不成立**。

## 因此本轮不做的事

不写第 4 条原创。在一个"换什么主题都一样"的环境里再发一条，
只是给已经降温的曲线多加一个点，并且消耗掉下一轮的真实机会。

## 待复查（下一轮）

1. **不要用 likes 做单帖对比**——样本量不够。要么等 likes 到两位数再比，
   要么直接用 views 并做时延归一化。
2. cluster 25 的 3h / 6h 数据（10:47 / 13:47 / 16:47 三个采样点）
   确认 21/h 是起步快还是只是新帖红利。
3. 低热期是否与"09:47–10:47 期间 pulse 发了 4 个互动动作"有关
   —— 有可能互动动作和原创在抢同一个分发位，这是可测的假设。
4. Frank 手动发帖密度那条规则依然有效，继续执行。

## 已发 X URL
本轮无。

## XHS 状态
停手。0 条草稿。

## 异常
无。本轮 mcp_browser 全程可用（5 次 navigate + query text，全部 200ms 级返回）。
观察到的唯一工具层抖动是 mcp_browser 偶发
`Validation failed: root: must not have additional properties`，原样重发即恢复（pulse round 51 已记录）。

## 下次启动先看
- **本轮最重要产出是撤回 round 50 的"买方减半"结论，以及 round 78 基于它做的方向切换。**
- 不要把"cluster 24 互动差"当成既定事实继续传播，round 50 的 memory 段需要打补丁。
- 已扫 handle（chuangzuo 侧）：home / AnthropicAI / GoogleDeepMind / dotey / karminski3 / howie_serious。
  **本轮未新增扫描**，下次若要发原创，从 practitioner 源优先（round 76/78 的两个源都是官方账号，
  官方号的转发受众未必是最优受众，这是另一个可测假设）。
- 跳过的 topic_signature：claude-designs-protein-binders-wet-lab-paradigm（已发，不重复）