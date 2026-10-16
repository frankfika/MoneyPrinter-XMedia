---
name: browser-use-utils
description: 浏览器操作工具集 — 给 hot-topic-tracker / post-writer-x / publisher-x / publisher-xhs 共享使用。封装 cua_repl 抓 X 时间线、截图、登录态检测等通用动作。
---

# Browser Use 工具集

所有浏览器操作都走 `mcp__cua_repl__js`，不要混用其他浏览器栈。

## 通用动作

### 打开 URL + 等待页面稳定
```js
await cua.getState();
let tab = await cua.createBrowserTab("iab", "https://x.com/<handle>", { visible: false });
// 等待登录态加载
await new Promise(r => setTimeout(r, 2500));
```

### 截图（落地到 screenshots/）
```js
// 触发 cua 截图后通过 read_mcp_resource 拿到 ImageContent
let image = await cua.snapshot();
```

### 检测登录态
- X：URL 里有 `home` 或顶部有「Post」按钮 → logged_in
- XHS 创作者中心：URL 含 `creator.xiaohongshu.com` 且无登录弹窗 → logged_in

### 关闭 tab
```js
await cua.closeTab(tab);
```

## 标准动作模板

每个 skill 启动前：
```js
await cua.getState();
let tab = await cua.createBrowserTab("iab", URL, { visible: false });
await new Promise(r => setTimeout(r, 2500));
```

结束前：
```js
await cua.closeTab(tab);
```

## 失败兜底
- 登录墙：截图给 Fang，把 URL 写进 log
- 二次验证：把页面 URL 给 Fang，**绝不** 自己读验证码
- 限流 / 临时封：停手，写 `state/logs/browser-errors.log`
