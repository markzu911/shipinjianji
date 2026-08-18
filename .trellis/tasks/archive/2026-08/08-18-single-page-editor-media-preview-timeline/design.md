# 单页编辑器统一媒体预览与时间轴技术设计

## 1. Architecture Boundary

```text
index.html
  timeline-model.js
  editor-project-store.js        <- 唯一项目/timeline 权威
  editor-media-controller.js     <- 唯一基础 video/source/time/frame clock
  editor-preview-compositor.js   <- semantic art/pip renderer
  editor-timeline-controller.js  <- semantic timeline renderer/transactions/history
  editor-suite.js                <- 组装控制器与 iframe compatibility adapters
  app.js                         <- cut inspector/domain adapter

art/pip iframe
  inspector + generation + local draft
  -> semantic tool-state source/overlays/timeline
  <- semantic selection/range/position commands + revision ACK
```

B1 统一顶层运行时，不迁移两个 inspector。`EditorProjectStore` 仍是会话内唯一权威；子页局部数组/store 是临时编辑适配器，不得成为公共预览、公共时间轴或 compose 的读取源。

## 2. Atomic Editor Frame

新增纯 selector：

```javascript
selectEditorFrame(snapshot) -> {
  revision,
  timingRevision,
  media: { jobId, sourceUrl, sourceDuration, cutRanges },
  preview: { art, pip },
  timeline,
  composition,
}
```

`preview`、`timeline` 和 `composition` 均从传入的同一 snapshot 派生，不允许 selector 内再次 `getState()`。Store 的 tool state 保存完整语义 overlay：Art 保留稳定 `id` 与全部 renderer 字段；PiP 保留稳定 `id/assetId` 和 `assets` registry（URL、type、text、status）。初次 hydrate 可从 `project.job.pictureInPictureImages/Videos` 建 registry，之后由 child semantic tool-state 增量更新；不得为拿新素材而整体 hydrate child `job-state`。

`selectCompositionRequest` 必须显式从完整语义模型映射原 API DTO：删除本地 UI id、asset URL/type/status/selection 等 preview-only 字段，只输出服务端 schema 已有字段。这样 Store/preview 可以完整，compose 仍保持兼容。

Store subscriber 每次只计算一次 frame，并依次调用：

```text
mediaController.applyFrame(frame)
previewCompositor.render(frame)
timelineController.render(frame)
```

三个顶层 DOM 根记录 `data-project-revision` / `data-timing-revision`。生成按钮点击时重新从当前 snapshot 原子选择一次 frame，并提交其 `composition`。

## 3. MediaController

`web/editor-media-controller.js` 暴露 `window.EditorMedia.createController(video, options)`：

```javascript
controller.video()
controller.setSource(url, { reason, force })
controller.clearSource({ reason })
controller.setCutRanges(ranges)
controller.currentSourceTime()
controller.currentEditedTime()
controller.sourceToEdited(seconds)
controller.editedToSource(seconds)
controller.seekSource(seconds)
controller.seekEdited(seconds)
controller.play() / pause() / toggle()
controller.subscribeFrame(listener)
controller.subscribeState(listener)
controller.destroy()
```

- `setSource` 规范化 URL 后与当前 source key 比较；相同 source 是 no-op。只有新 job/显式 source change 可写 `video.src` 并调用一次 `load()`。
- `setCutRanges` 只更新排序后的时间映射，不改媒体 source、currentTime 或 playback。
- 帧时钟从 `app.js` 提取，降级顺序保持 `requestVideoFrameCallback -> requestAnimationFrame -> timeupdate`；generation guard 语义不变。
- `app.js` 仍可读取 video 尺寸/状态完成 view 渲染，但 source、seek、play/pause 和帧订阅通过 controller。`editor-suite.js` 不再建立第二个 rAF 播放同步循环，而订阅同一帧时钟投影到 iframe/compositor。
- 抖音成片镜像 video 是展示资源，不是基础播放时钟；其 currentTime/play state 只由 MediaController frame/state 订阅驱动。

## 4. PreviewCompositor

`web/editor-preview-compositor.js` 暴露：

```javascript
EditorPreview.createCompositor({
  root,
  mediaController,
  onSelect,
  onMove,
  onResize,
})
```

Compositor 只接收 `frame.preview`：

- 按 `mediaController.currentEditedTime()` 过滤 `start <= t < end` 的 art 和 pip layer。
- 艺术字 renderer 迁移现有纯文本换行、模板效果、字体、描边、字符布局和 `character-bounce` 逻辑；使用 DOM API 与 `textContent`，不接受 HTML 字符串。
- PiP renderer 用 `assetId` 查 asset index，创建 img/video，按 `x/y/width` 定位；子视频静音并由唯一 frame clock 同步 local time。
- selection 来自 Store timeline selection；交互回调只发送语义 id/坐标/尺寸，不直接修改 Store 外的权威对象。
- 渲染以 semantic signature 去重，时间帧只改变可见项/逐字动画/子视频同步，避免每帧整体重建。
- `destroy()` 断开 ResizeObserver、媒体监听和活动 pointer session。

`editor-suite.js` 删除 `renderMirroredPreview()` 对 `toolStates.overlayHtml` 的依赖；legacy feature flag 可回退旧 authority，但仍使用子页公开的 `source/overlays` 语义字段建立 preview model。

## 5. TimelineController

`web/editor-timeline-controller.js` 持有唯一顶层 timeline view/controller，不再创建第二个 project authority：

```javascript
EditorTimelineController.createController({
  root,
  track,
  store: projectStore,
  timeline: EditorTimeline,
  mediaController,
  dispatchCommand,
})
```

Controller 每次从 `selectEditorFrame(snapshot).timeline` 渲染稳定 clip DOM。`EditorTimeline.normalizeDocument`、`createStore`/pointer session 的边界算法继续复用；pointer 期间的临时 document 仅是未提交 UI preview，不能被 compose/selectors 读取。

### Transaction flow

```text
pointerdown
  -> snapshot before + stable clip id + selection action
pointermove
  -> temporary normalized clip preview + media seek
pointerup
  -> one timelineClipRangeChanged semantic action
  -> one history transaction
  -> compatibility command to owning cut/art/pip adapter
  -> child echo normalizes to no-op + ACK
pointercancel
  -> discard temporary document, render authoritative snapshot
```

Store 增加通用 timeline kind/clip action。art/pip clip range action同时更新 `project.timeline` 和对应 overlay `start/end`；cut action通过注册的 cut adapter更新现有 `timelineDeleteRanges`，随后由已有 cut draft command提交权威 ranges。所有动作保持 stable clip/source id。

History 记录已提交跨轨道事务的 before/after 语义 command，而不是 DOM/HTML。undo/redo 恢复 selection 和领域时间，截断 redo 分支；输入/textarea/contenteditable 聚焦时不截获原生 undo。cut 原有文字/空白历史继续负责非时间轴编辑，时间轴适配器在恢复时保持其既有持久化与二次确认规则。

## 6. Compatibility Message Contract

子页 `tool-state` 新增公开字段：

```javascript
{
  type: "editor-suite:tool-state",
  kind: "art" | "pip",
  source,
  overlays, // 完整语义对象，含稳定 UI id
  assets,   // PiP 素材 registry；Art 为空
  timeline,
  revision,
  timingRevision,
  changeKind,
  // legacy outputs retained until B4:
  overlayHtml,
  timelineHtml,
  generationPayload,
}
```

Store authority 父页只读取 `source/overlays/assets/timeline`。`generationPayload`、`overlayHtml`、`timelineHtml` 不进入 toolStates、Store、compositor、timeline controller 或 compose。子页继续发送 legacy 字段以保留独立页面/feature flag 回滚，但新父页不依赖它们。

父页到子页的 selection、range、position、size command 继续携带 kind/id，并附当前 revision。子页应用后发布语义 tool-state；父页先执行 revision floor/source/origin 校验，再 dispatch，成功后 ACK。相同语义回声必须是 no-op。

## 7. Integration And Rollback

1. 新增三个独立普通脚本和 Node tests；先不连接业务。
2. `editor-suite.js` 创建控制器并接 Store subscriber；`app.js` 接 MediaController 与 cut timeline adapter。
3. 子页发布公开语义字段；父页停止读取私有 payload。
4. 公共 preview 切换到 compositor，公共 effect timeline 切换到 controller。
5. 保留 `window.__EDITOR_PROJECT_STORE_ENABLED__ === false` 的启动时回滚。回滚只改变顶层 authority，不允许同一会话运行两套 Store 写入。

任一步出现 media identity/source/time 重置、预览/compose 差异、双 revision 或 iframe 回声循环时，回退该消费者接入，不删除 B0 Store/revision 契约。

## 8. Risks

- 艺术字 renderer 复制过多页面私有常量会再次漂移；优先提取可被 iframe 与顶层共同调用的纯 renderer，若短期保留旧 iframe renderer，必须用共享 Node/browser fixture 比较语义输出。
- PiP 资源可能尚在生成或失败；child semantic state 必须发布最新 registry。缺失 asset 只跳过该 layer并提供稳定诊断，不得回退解析 iframe HTML或整体 job hydrate。
- Timeline pointer live preview 与 child 回传可能交错；controller 在 active transaction 期间按 revision/token 拒绝迟到回显，结束后只接受等于或高于 floor 的语义状态。
- 统一 media frame listener 可能增加热路径工作；每帧不得调用 selector、重建 timeline 或全量查询 DOM。
