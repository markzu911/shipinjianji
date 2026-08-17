# 跨层变更检查指南

## 系统数据流

```text
浏览器上传
  -> FastAPI 校验并写 data/jobs/<job_id>
  -> 后台线程提取音频/调用 ASR
  -> JOBS 中的 transcript + word timestamps
  -> app.js 文字编辑和删除草稿
  -> editor-suite.js 协调 art/pip iframe 与统一时间线
  -> FastAPI 归一化 overlay 和 source anchor
  -> FFmpeg 预览/最终合成
  -> data/history 持久成片
```

## 每次跨层修改必须回答

1. 权威状态在哪里：内存 job、cut draft、localStorage、`EditorTimeline` store、iframe 私有状态还是 history manifest？
2. 时间字段属于源视频还是剪后视频？转换在哪一层发生？
3. 浏览器发送的字段由哪个 Pydantic 模型和哪个 normalize 函数校验？
4. 刷新、服务重启、取消、失败后还剩什么状态？
5. 预览和导出是否消费同一份归一化数据？

## 浏览器边界

- `postMessage` 必须验证 `event.origin === window.location.origin`。
- 子页面还要验证 `event.source === window.parent`；顶层应验证来源 iframe 与声明的 `kind` 匹配。
- 消息使用显式 `type`，新增字段需要父子两侧同步更新并保留兼容默认值。
- `editor-suite:job-state`、`editor-suite:tool-state`、`editor-suite:transcript-updated` 是同页面事件契约；不要私自复制 payload 解析。
- 删除或重命名 DOM 节点前，用 `rg` 检查所有页面脚本、共享协调器和静态契约中的 selector 依赖；能力检测只能依赖完成该能力所需的稳定容器，不能依赖可选页签或状态面板。
- 修改顶层/iframe 布局后，真实浏览器必须从文字剪辑依次切换艺术字、画中画并返回，确认顶层文档未导航、公共预览未卸载、URL 参数与激活面板一致。

## API 边界

- 浏览器输入不可信。后端重复执行数值、枚举、路径和资源归属校验。
- API 错误用非 2xx + `detail`；前端解析失败时提供稳定的兜底文案。
- 轮询只在 queued/processing 等非终态继续，离开页面或取消后要停止旧轮询。

## 当前已知风险

- `JOBS` 在重启后消失，但 cut draft/history 部分持久化。
- 时间映射逻辑分布在 Python、`app.js`、`editor-suite.js` 和子工具页面。
- 顶层编辑器与两个 iframe 仍各自持有部分轨道状态。

这些风险属于后续优化目标。新改动应减少状态副本，不应增加新的私有 payload 或 HTML 快照协议。

## 验证

跨层功能至少覆盖：正常往返、空/非法字段、刷新恢复、服务重启语义、失败清理、预览与导出一致性。核心工作流再用真实浏览器验证桌面和 375px 窄屏。
