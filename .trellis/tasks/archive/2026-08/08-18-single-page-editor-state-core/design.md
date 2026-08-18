# 单页编辑器状态核心技术设计

## 1. Architecture Boundary

B0 在现有原生脚本架构中增加一个顶层状态核心，不改变页面结构：

```text
index.html
  timeline-model.js
  editor-project-store.js       <- state/actions/selectors/effect guards
  editor-suite.js               <- creates one store + compatibility bridge
  app.js                        <- dispatches hydrate/cut/text actions

editor-suite.js
  EditorProjectStore snapshot   <- authoritative project projection
  legacy HTML bridge cache      <- overlayHtml/timelineHtml only
  art iframe                    <- temporary local editor
  pip iframe                    <- temporary local editor
```

服务端 job 仍是持久权威。浏览器 store 是当前页面会话内唯一的项目投影权威。`EditorTimeline` 继续负责时间轴文档规范化，B0 不复制 clip 模型，也不移除子工具内部 store。

## 2. Module Contract

`web/editor-project-store.js` 是可在浏览器和 Node 测试中加载的普通脚本。浏览器导出 `window.EditorProjectStore`，Node 测试可以使用兼容导出；不引入构建步骤。

```javascript
const store = EditorProjectStore.createStore(initialState, {
  timeline: EditorTimeline,
});

store.getState();
store.dispatch(action);
store.subscribe(listener);
store.beginEffect(scope);
store.isCurrentEffect(token);
store.applyEffect(token, action);
store.select(selector);
store.destroy();
```

`dispatch` 和 `applyEffect` 返回：

```javascript
{
  accepted: true,
  revision: 12,
  timingRevision: 4,
}
```

无效 action 或迟到 effect 返回 `accepted: false`，不得通知 subscriber 或创建新快照。

## 3. State Shape

```javascript
{
  schemaVersion: 1,
  jobId: "",
  revision: 0,
  timingRevision: 0,
  serverVersion: "",
  project: {
    job: null,
    transcript: null,
    editableSegments: [],
    cut: {
      active: false,
      ranges: [],
      sourceDuration: 0,
      duration: 0,
      transcript: null,
    },
    art: { source: "original", overlays: [] },
    pip: { source: "original", overlays: [] },
    timeline: { duration: 0, tracks: [], selection: null },
  },
  ui: { activeTool: "cut" },
}
```

快照需递归复制并冻结 store 拥有的输入，避免 iframe payload、job fetch 结果或调用方后续原地修改污染历史快照。对大型媒体对象不做存储；state 只保存可序列化项目模型。

## 4. Action Semantics

| Action | revision | timingRevision | 关键行为 |
| --- | --- | --- | --- |
| `projectHydrated`（新 job） | +1 | +1 | 重置所有项目域并规范化 timeline |
| `projectHydrated`（同 job） | +1 | 仅 timing 变化时 +1 | 默认保留本地更新过的 art/pip；只合并允许的 server 投影 |
| `transcriptTextChanged` | +1 | 不变 | 更新 transcript/editable text 和 art cue 文本，保留所有时间锚点 |
| `cutTimingChanged` | +1 | +1 | 更新 cut ranges/time map 与 cut track |
| `artStateChanged` | +1 | 时间/source anchor 变化时 +1 | 接收 art iframe 语义投影 |
| `pipStateChanged` | +1 | 时间/source anchor 变化时 +1 | 接收 pip iframe 语义投影 |
| `activeToolChanged` | UI 快照变化 | 不变 | 不创建/替换 iframe |
| `selectionChanged` | UI/timeline selection 变化 | 不变 | 不改变 clip timing |

art/pip timing 比较只使用规范化的 `source`、`start/end/sourceStart/sourceEnd` 和稳定条目 id。文字、样式、位置、尺寸以及选择变化不算 timing change。

`transcriptTextChanged` 合并 server art 时以当前 store 的 overlay 数量、id 和时间字段为骨架，只按稳定 id/字幕轨道字符映射合并新文本。它不得整体替换 `job.art` 或 `project.art`。

## 5. Effect Guard

store 为每个 scope 保存单调 request id：

```javascript
{
  scope: "transcript-save",
  requestId: 7,
  baseRevision: 11,
  baseTimingRevision: 4,
  jobId: "job-123",
}
```

接受条件：

1. token 的 `jobId` 与当前 store 相同；
2. token 是该 scope 最新 request id；
3. 当前 `timingRevision` 等于 token 的 `baseTimingRevision`，除非 action 显式声明自己的安全 rebase 规则；
4. store 尚未 destroy。

文字保存执行顺序：

```text
beginEffect("transcript-save")
  -> PUT /editable-segments
  -> GET /api/transcriptions/{jobId}
  -> normalize text projection only
  -> applyEffect(token, transcriptTextChanged)
```

若 PUT/GET 返回时 token 已过期，不应用完整 job。若只是同一保存 scope 被更新请求取代，最新请求负责最终 GET；若 timing revision 已变化，启动一个以当前 timing revision 为基线的只读 refresh effect，并仍只提交文字投影。这样服务端已成功的文字不会因为客户端拒绝旧快照而长期不可见。

## 6. Ownership And Integration

### Initial hydration

`editor-suite.js` 创建 store 并通过 `EditorSuite` 暴露受限的语义方法/只读 selector。`app.js` 获得首个 job 后 dispatch `projectHydrated`。同 job 后续 refresh 不得整体覆盖本地更新过的 tool state。

### Cut updates

`app.js` 的 `updateSelectionSummary()` 在形成规范化 cut draft 后 dispatch `cutTimingChanged`。旧 `EditorSuite.setCutDraft()` 暂时保留为适配入口，但内部只 dispatch，不再维护第二份 compose authority。

### Tool messages

parent 收到 `tool-state` 后先保留 bridge-only HTML 字段，再把语义字段 dispatch 为 `artStateChanged` 或 `pipStateChanged`。消息处理继续同时验证 `event.origin` 与对应 iframe `contentWindow`。

store subscriber 只向 iframe 投影发生语义变化的消息；消息带 `revision`、`timingRevision`、`changeKind`。iframe 记录 `lastAppliedRevision` 并拒绝旧消息。旧消息缺少版本时按 legacy revision 处理，以支持 feature flag 回退。

### Text-only projection

- Art：只更新 transcript/cue text 和必要的字符映射，跳过 `replaceTranscriptTrackFromCutDraft()`、`retimeDraftAnchoredOverlays()` 及任何 timeline rebuild。
- PiP：只更新 transcript 文本/标签，跳过 segment rematch 及 overlay `start/end` 写回。
- Parent：不调用 `ensureToolFrame()` 的换源分支，不更换 iframe `src`。

### Compose

`selectCompositionRequest(snapshot)` 从一个快照生成现有公开请求结构：

```javascript
{
  target: "all",
  ranges,
  artOverlays,
  artSource,
  pictureInPictureOverlays,
  pictureInPictureSource,
  historyName: null,
}
```

API 字段不变。bridge-only `generationPayload` 仅可用于转换成语义 action，不能直接覆盖 selector 输出。

## 7. Selector Rules

- `selectCutDraftMessage(state)`：返回现有 cut draft 消息结构，并附带 revision/change kind。
- `selectToolState(state, kind)`：返回指定工具的语义状态，不返回 HTML。
- `selectTimelineDocument(state)`：一次调用 `EditorTimeline.normalizeDocument()`，合并 cut/art/pip tracks。
- `selectPreviewLayers(state)`：返回 art/pip 语义 layer，供 B1 compositor 使用。
- `selectCompositionRequest(state)`：从同一快照原子派生 compose。
- `selectIframeProjection(state, kind)`：只生成兼容消息需要的 cut/text/time/selection 投影。

selector 必须是纯函数；不得 fetch、改写输入、访问 DOM 或在一次选择中重新调用全局 `getState()`。

## 8. Compatibility And Rollback

默认启用 `window.__EDITOR_PROJECT_STORE_ENABLED__ !== false`。初始化时读取一次并固定 authority：

- enabled：所有 project projection 与 compose 读取 store；legacy map 仅保存 HTML bridge 数据。
- disabled：沿用现有 `currentJob`/`toolStates` authority 和消息；不同时启用 guarded text action。

实施分为可回滚的四步：

1. 新增 store、脚本引用和纯测试，不接消费者。
2. 接入 hydrate/cut/tool adapter，保留 legacy bridge。
3. 接入 guarded text save 并删除 reload。
4. compose 切换到原子 selector。

任一步出现视频/iframe identity 变化、时间漂移或 compose 差异时，停在 B0，使用 feature flag 回退，不进入 B1。

## 9. Risks

- 当前 PUT 不返回完整快照，PUT+GET 不是服务端原子事务；effect guard 只能阻止客户端旧响应覆盖，不能解决多客户端并发。
- 子工具在 B0 仍保留局部状态，适配器必须避免 store subscriber 和 iframe `tool-state` 形成回声循环。按 revision/语义签名去重，并只在投影变化时发送。
- 文字合并不能整体替换 server art，否则会丢失 iframe 中较新的未保存样式/位置。测试必须覆盖“文字更新、时间和本地非文字字段不变”。
- feature flag 不能让两套 authority 同时生效；启动后改变 flag 需要刷新页面。
