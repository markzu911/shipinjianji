# 单页编辑器状态核心

## Goal

建立一个由顶层编辑器持有的 `EditorProjectStore`，让文字剪辑、艺术字、画中画和合成请求读取同一份项目投影，并用语义 action、`revision`、`timingRevision` 和异步 effect guard 阻止旧响应覆盖新状态。

本阶段要直接消除“修改文案后整页刷新并从头播放”的行为，同时保证纯文字变化不会重算艺术字或画中画的时间。它是后续统一播放器、预览和时间轴的状态基础，不在本阶段迁移 iframe 工具界面。

## Background

- `web/app.js:1210-1252` 的文字保存流程在 PUT 成功后广播文案更新，并在 500ms 后无条件执行 `window.location.reload()`。
- reload 会重建顶层视频和两个工具 iframe；`web/app.js:4638-4718` 会重新设置视频源和结果状态，`web/editor-suite.js:752-788` 会重新创建或重载 iframe，因此播放位置、播放状态和在途子页面请求都会丢失。
- `PUT /editable-segments` 当前只返回 `editableSegments`（`server/app.py:10643`），但服务端同时更新 transcript 文本及艺术字字幕文案（`server/app.py:10617-10629`），所以客户端仍需要一次受保护的完整 job GET。
- 服务端更新艺术字字幕文案时刻意保留 cue 的 `start/end`（`server/app.py:8027-8089`）；纯文字更新不应进入重新匹配或改时路径。
- 当前 `editor-suite.js` 同时从 `currentJob`、cut draft 和 iframe `tool-state` 组装 compose，可能混用不同逻辑版本（`web/editor-suite.js:348-389`）。
- 项目没有服务端 project revision；现有 cut draft revision 只保护 cut draft。B0 先提供客户端 request id 和 revision guard，不宣称解决跨标签页或多客户端冲突。

## Requirements

### R1. 唯一顶层状态权威

- 新增 `web/editor-project-store.js`，通过唯一的 `window.EditorProjectStore` 暴露纯函数 selector 和 store factory。
- 顶层工作台只创建一个 store。该 store 是项目投影、revision 顺序、统一 timeline 投影和 compose 输入的权威来源。
- state 至少包含 `schemaVersion`、`jobId`、`revision`、`timingRevision`、`serverVersion`、`project.job/transcript/cut/art/pip/timeline` 与 `ui.activeTool`。
- 每次被接受的语义 action 生成一个不可变快照；同一次 preview/compose 计算必须只读取一个快照。

### R2. 文字与时间语义分离

- 支持 `projectHydrated`、`transcriptTextChanged`、`cutTimingChanged`、`artStateChanged`、`pipStateChanged`、`activeToolChanged` 和 `selectionChanged`。
- `transcriptTextChanged` 只增加 `revision`，不增加 `timingRevision`；它只更新文案、可编辑段落和允许的 cue 文本/字符映射。
- `transcriptTextChanged` 必须保留现有艺术字与画中画条目的 `start/end/sourceStart/sourceEnd`，不得更换视频 `src`、调用 `load()`、改变播放位置或触发时间重匹配。
- cut、art、pip 的规范化时间或 source anchor 真正变化时，才增加 `timingRevision`。

### R3. 旧响应保护

- store 提供 `beginEffect(scope)`、`isCurrentEffect(token)` 和 `applyEffect(token, action)`。
- effect 仅在 job 相同、scope request id 最新且 `baseTimingRevision` 兼容时可提交。
- 文字保存响应允许覆盖更晚发生的纯 UI/样式变化，但如果请求期间时间结构已变化，必须拒绝旧快照并重新获取当前 job 投影；不得把迟到的完整 job 整体覆盖到当前 store。
- `serverVersion` 只作为诊断和兼容字段，不能替代本地 request id/revision 守卫。

### R4. 无刷新文字保存

- `saveSegmentText()` 保留现有 PUT 契约，成功后执行一次带 effect token 的完整 job GET，规范化后 dispatch `transcriptTextChanged`。
- 删除文字保存路径中的定时 `window.location.reload()`，并将成功反馈改为“已同步”，不能继续提示即将刷新。
- 保存成功后必须保持顶层 document、视频 DOM、视频源、当前播放时间/播放状态以及两个 iframe DOM 的身份不变。

### R5. iframe 兼容桥

- B0 继续保留 art/pip iframe、其内部编辑数组与现有 `EditorTimeline` store；不把 iframe 误当成最终架构。
- `editor-suite.js` 将 store projection 翻译成现有消息，并把子页面 `tool-state` 作为 `artStateChanged`/`pipStateChanged` 的适配器输入。
- 消息增加向后兼容的 `revision`、`timingRevision` 和 `changeKind`。子页面忽略已应用 revision 之前的旧消息。
- `changeKind: "transcript-text"` 在 art 中只更新 cue 文本，在 pip 中只更新 transcript 标签；两者都不得执行时间重匹配或改写条目时间。
- 现有 `event.origin` 和 `event.source` 校验必须保留。

### R6. 原子 selector 与 compose

- 提供 `selectCutDraftMessage`、`selectToolState`、`selectTimelineDocument`、`selectPreviewLayers`、`selectCompositionRequest` 和 `selectIframeProjection`。
- `selectPreviewLayers` 只返回语义模型，不包含 HTML。
- `overlayHtml`、`timelineHtml` 和私有 `generationPayload` 在 B0 只允许留在兼容桥缓存，不进入 `EditorProjectStore`。
- compose 请求必须由 `selectCompositionRequest(snapshot)` 一次性派生，不能再分别读取 `currentJob`、cut draft 和 iframe 私有 payload。

### R7. 加载、兼容与回滚

- `editor-project-store.js` 在 `timeline-model.js` 之后、`editor-suite.js` 和 `app.js` 之前加载；静态资源版本同步更新。
- 同一会话在启动时只选择 store authority 或 legacy authority，禁止两套 authority 同时写 compose/state。
- 保留一个默认开启的顶层 feature flag，关闭时可以回退到旧桥接行为；回退不得同时启用新的 guarded action 写路径。

### R8. 验证

- 增加纯 Node 行为测试、静态前端契约测试和真实浏览器工作流测试。
- 保留现有后端稳定 cue 时间测试，不在 B0 修改 API schema。
- 完整运行 `tests/app/`、真实浏览器工作流以及所有 `web/*.js` 的 `node --check`。

## Acceptance Criteria

- [ ] AC1：store 测试证明快照不可变，所有被接受的语义变化按契约增加 `revision`，纯文字/UI action 不增加 `timingRevision`，真实 timing action 才增加它。
- [ ] AC2：同 scope 的迟到 effect、不同 job 的 effect 及 base timing 已变化的 effect 都被拒绝；相同 job hydrate 不覆盖本地更新过的 art/pip 状态。
- [ ] AC3：compose selector 从同一快照生成 cut/art/pip 输入，测试可证明不会混用不同 revision。
- [ ] AC4：在非零播放位置修改文案后，顶层 document 不导航，视频元素和 `src` 不变，播放时间不回到 0，原播放/暂停状态保持，art/pip iframe 元素不被替换。
- [ ] AC5：同一浏览器用例中，艺术字 cue 文案更新但所有时间字段逐项不变；画中画条目时间逐项不变；compose 使用新文案及同一 store revision 的状态。
- [ ] AC6：静态契约确认新脚本顺序和版本正确，文字保存函数中不存在 reload，并继续校验 parent/iframe 的 origin/source。
- [ ] AC7：现有编辑器浏览器基线、`tests/app/` 全量测试和全部 `web/*.js` 语法检查通过。
- [ ] AC8：关闭 feature flag 时可恢复 legacy authority；启用时只有 store authority 参与项目投影与 compose。

## Out Of Scope

- 不在 B0 提取唯一 `MediaController`、`PreviewCompositor` 或最终统一的 `TimelineController`；这些属于 B1。
- 不把艺术字或画中画 UI 从 iframe 迁入顶层，不删除独立工具页面，不改旧 URL 跳转；这些属于 B2-B4。
- 不引入框架、bundler、ES module 或新的状态管理依赖。
- 不修改服务端 API 响应为 project snapshot，也不新增服务端 project revision。
- 不解决跨标签页、多浏览器或多用户并发编辑冲突。
- 不把 HTML 快照或 iframe 私有 generation payload 变成持久项目状态。
