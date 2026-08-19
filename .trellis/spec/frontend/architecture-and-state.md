# 前端架构与状态

## 页面职责

- `web/index.html` + `app.js`：上传、转写、文字编辑、剪辑选择、历史和主工作流。
- `web/editor-suite.js`：顶层编辑工作台、Store 协调、工具切换、统一预览、轨道和生成/保存。
- `web/editor-art-tool.js`：只挂载到 `#editorArtPanelRoot` 的艺术字 inspector，不拥有页面、视频或时间线。
- `web/editor-pip-tool.js`：只挂载到 `#editorPipPanelRoot` 的画中画 inspector，不拥有页面、视频或时间线。
- `web/timeline-model.js`：版本化轨道文档、clip 归一化、选择、拖动/缩放和 localStorage 草稿。
- `web/transcript-follow-scroll.js`：文字播放跟随滚动的目标计算、真实行 reparent、列表 FLIP/WAAPI 动画、去重、中断和临时样式清理。
- `web/ui-feedback.js`：对话框、生成进度和通用播放器反馈。

## 加载方式

没有 ES module 或 bundler。公共脚本在页面业务脚本前以 `defer` 加载，并暴露 `window.EditorTimeline` 等全局。新增共享脚本时：

1. 明确唯一全局命名空间；
2. 在所有消费者 HTML 中保持相同加载顺序；
3. 修改静态资源时更新 HTML 的 `?v=` 版本；
4. 同步 `disable_frontend_cache` 的资源路径（如属于其覆盖范围）；
5. 更新静态资源测试。

### 文案跟随滚动模块契约

`web/transcript-follow-scroll.js` 是播放中活动文案跟随滚动的唯一实现边界，并通过 `window.TranscriptFollowScroll` 暴露 `createController()`。控制器唯一拥有真实活动行的 reparent、等高占位、单行展示层定位、一次性目标 `scrollTop` 提交、列表 FLIP/WAAPI、跟随 key、用户中断和恢复顺序；不得再对仍位于 `segmentList` 的真实行执行跟随 transform，也不得由 `app.js` 建立逐帧滚动控制器。

`app.js` 只负责确定活动行、更新 `aria-current`/播放 badge，并调用控制器的 `follow()`、`reset()` 和 `destroy()`。列表与展示层中的真实行必须经统一查询 helper 读取，所有行交互复用同一个命名事件处理器；`renderCutSegments()` 必须在替换列表内容前调用 `reset()`，先把展示层中的真实行恢复到占位位置。

控制器移动真实行前要插入不含按钮、时间 data 或可聚焦后代的等高占位，使展示行和播放按钮始终只有一份。每次换段只提交一次目标 `scrollTop`，列表通过从 `scrollDelta` 到 `0` 的 FLIP transform 表达滚动过程；中段展示层同时进入工具栏锚点。滚动目标被最大值截断时，列表阶段必须保持展示层的上一视觉位置，列表动画完成后再从该位置直接、单调地移动到新的尾部余量，不得先返回锚点再折返。换段、重渲染、关闭跟随、目标失效或收到 `wheel`、`touchstart`、`pointerdown`、滚动键意图时，必须取消旧动画、恢复原顺序并清除占位、展示层尺寸/transform、动画 class 和监听器；迟到旧动画完成回调不得写入新 DOM。`prefers-reduced-motion: reduce` 使用相同的唯一 DOM/占位结构，但即时定位且不建立运动带。

跟随 key 只能在目标行和滚动面板通过有效性校验后记录；首次调用遇到隐藏/脱离 DOM 的目标不得消耗 key，运行中的目标失效也要释放 key，使面板恢复后同一行可以重试。用户主动滚动中断则保留已跟随 key，避免后续 `timeupdate` 立即抢回滚动控制权。

### 播放帧热路径契约

剪辑预览只允许一个可取消的播放帧时钟，按 `requestVideoFrameCallback -> requestAnimationFrame -> timeupdate` 顺序降级。`play`、`pause`、`seeking`、`seeked`、`ended`、`emptied` 和销毁必须统一管理其生命周期；每次停止都递增 generation，取消后迟到的旧回调必须在读取或清空当前 callback id 前退出，不能发出旧时间或建立第二条循环。

每帧更新只消费预先缓存的剪后区间、时间轴宽度/比例和文案元素索引，不得调用 `updateTime()`、重建区间、全量查询 DOM 或重建时间轴结构。文案与时间轴高亮都要分别保存“最新开始项 floor cursor”和“当前命中 active cursor”：向前播放时复用当前命中项，重叠短项结束后允许恢复仍有效的长项；向后 seek 时通过二分重新定位 floor，再重算 active，不能把两个游标合并。

## 状态所有权

- 轨道结构优先经 `EditorTimeline.createStore` 归一化和修改，不直接散改复制对象。
- 顶层工作台负责跨工具选择、播放时间、源选择、统一预览、公共时间线和工具生命周期。
- 子工具只维护本领域瞬时 UI 状态，并通过注入的语义 command 读写同一个顶层 Store。
- job 权威状态来自 API；localStorage 只用于可恢复草稿和 UI 历史，不能冒充服务端成功状态。

### 剪辑草稿判空与空白迁移契约

AI 文字默认值和空白默认值使用不同的初始化条件：

- `null` 表示服务端和本地都没有草稿，可以播种 AI 文字建议；任意草稿对象（包括 `{ textRanges: [] }`）都禁止重新播种 AI 文字建议；
- 草稿的 `automaticNoSpeechInitialized` 是空白默认值的一次性迁移标记，历史草稿缺少该字段时按 `false` 处理；
- `noSpeechStatus === "completed"` 且标记不为 `true` 时，必须先恢复草稿，再把全部 `deletable !== false` 的检测结果补入 `selectedNoSpeechRanges`，最后将标记设为 `true` 并保存；
- `automaticNoSpeechInitialized: true` 与 `noSpeechRanges: []` 是用户明确恢复全部空白的状态，刷新时不得再次播种；
- 默认状态应先写入主状态并建立撤销历史基线，再开启草稿保存，使用户后续恢复成为正常的可撤销操作。

```javascript
const persistedDraft = resolvePersistedCutDraft(job.cutDraft ?? null, job.id);
let shouldPersistAutomaticDefaults = false;
if (persistedDraft === null) {
  shouldPersistAutomaticDefaults = seedAutomaticSuggestionRanges() > 0;
} else {
  restorePersistedDraft(persistedDraft);
}

if (
  result.noSpeechStatus === "completed" &&
  !automaticNoSpeechInitialized
) {
  seedAutomaticNoSpeechRanges();
  automaticNoSpeechInitialized = true;
  shouldPersistAutomaticDefaults = true;
}

cutDraftReady = true;
if (shouldPersistAutomaticDefaults) scheduleCutDraftSave();
```

禁止用 `draft?.textRanges?.length`、`draft?.noSpeechRanges?.length`、`job.cutDraft || null` 或范围数量判断是否初始化；这些写法会把用户明确保存的空选择误当成首次打开状态。初始化标记是持久元数据，不进入撤销/重做快照。

### 文字删除展示边界契约

文字剪辑列表必须区分“剪辑主状态”和“展示边界”：

- `selectedRanges` 与 `selectedNoSpeechRanges` 分别是文字和长空白删除的主状态；保存、生成和撤销/重做只消费这两个现有集合，不新增“自动删除”副本；
- AI 建议的原始词级范围可以作为稳定展示边界，但不能作为第二套删除状态；
- `buildSegmentTextRuns` 按单词中点投影删除状态和展示边界；普通文字与“时间轴已删除”只合并 `kind`、`presentationKey` 均相同的相邻词，连续“恢复”文字则允许跨 `presentationKey` 合并为一行并聚合全部 `rangeKeys`；“恢复”状态只来自 `selectedRanges` 的 `originalStart/originalEnd`，“时间轴已删除”只来自已提交的 `timelineRanges`，文字静音扩展和 `noSpeechRanges` 不得改变文案样式；
- `currentNoSpeechSuggestions` 同样只提供稳定展示边界；文字片段与空白建议按源时间排序，每个片段独立渲染为 `li[data-display-key][data-display-start][data-display-end]`；
- 空白行用 `data-no-speech-id` 连接 `selectedNoSpeechRanges`，不伪造可编辑文字段 index；播放高亮同时比较片段时间和稳定 key。

恢复 AI 删除片段时，只从 `selectedRanges` 删除该展示行聚合的全部 range key，不移除原始建议边界。相邻的多个已删范围可以合并显示和一次恢复；中间存在保留文字时仍必须分成不同展示组。

恢复空白片段时，只从 `selectedNoSpeechRanges` 删除对应 id，空白行继续保留并变为可试听状态。文字删除范围可能因 `adjacentSilenceBefore/After` 扩展到该空白，因此 `getMergedSelection` 必须先调用 `protectRestoredNoSpeechFromTextRanges`：仅从文字范围的前后静音扩展中扣除已恢复空白，文字原始 `originalStart/originalEnd` 仍保持删除。否则会出现“列表显示已恢复，但预览和成片仍删除”的状态漂移。

```javascript
const canMerge =
  previous?.kind === kind &&
  (kind === "restore" || previous.presentationKey === presentationKey);

// 恢复只改变剪辑状态，展示边界继续存在。
for (const key of rangeKeys) selectedRanges.delete(key);

// 空白恢复还必须约束文字范围的物理静音扩展。
const resolvedTextRanges =
  protectRestoredNoSpeechFromTextRanges([...selectedRanges.values()]);

// 自动范围必须再扣除未被语义/手动范围精确删除的文字片段。
const retainedTranscriptRanges = getRetainedTranscriptRanges(
  [...selectedRanges.values()],
  getCommittedTimelineDeleteRanges(),
);
const safeAutomaticRanges = subtractProtectedRanges(
  resolvedAutomaticRanges,
  retainedTranscriptRanges,
);
const mediaRanges = mergeCutRanges(
  [...safeAutomaticRanges, ...getCommittedTimelineDeleteRanges()],
  retainedTranscriptRanges,
);
```

前后端的保护顺序都是：按来源组装自动范围 -> 从识别文字中精确扣除语义文字删除和已提交手动删除 -> 从自动范围扣除余下保留片段 -> 在感知保留片段的前提下合并。禁止只根据“某个手动范围与词相交”就使整个词失去保护。

回归测试必须覆盖独立行的静态契约和 Node 行为契约，并在真实浏览器验证：文字与空白按源时间排序；连续已删文字跨 range key 只显示一行且一次恢复全部聚合 key；保留文字仍拆分两侧删除组；时间轴删除分组不变；单独重删只影响目标行；空白恢复后不再被文字静音扩展删除；删除空白不使相邻文字出现删除线/恢复按钮且不从预览时间轴消失；小于 `0.12s` 的短保留文字不被两侧自动范围合并；手动范围只删除词的一部分时其余部分仍保留；撤销/重做与刷新持久化正常；播放高亮命中当前片段；375px 无横向溢出且操作目标不少于 44px。

### 双层词时间戳状态契约

- `segments[].words` 是 Jieba 展示和编辑层，也是文字删除字符时序的首选来源；`segments[].asrWords` 只保留模型原始时间供声学参考和旧数据回退。
- 字符单元按段选择第一个有效层 `words -> asrWords -> segment`，再把每个带时间文本均分为字符；空数组或无效条目只触发当前段回退，不能让混合数据中的历史段落失去保护。
- 原始 `asrWords` 可以跨越自然词边界，不能作为不可分割删除单元，也不能把“给一”“得你”之类模型 token 的下一字符带入删除。
- 文案点击、AI 建议初始化、草稿恢复和撤销/重做都必须经 `canonicalizeTextSelectionRange` / `normalizeRestoredTextDeleteRange` 扩展到相交字符，并用规范后的边界重建 map key。
- `buildSegmentTextRuns` 继续逐字符投影删除状态；文字静音扩展和空白范围不能使未选字符进入恢复态。手动 `timelineRanges` 不使用字符扩展。
- 手动时间轴范围只 clamp 到媒体时长并保留用户选择的精确起止；二次确认后仍可只覆盖字符的一部分。

具体字段、回退矩阵和跨层测试见后端规格 `media-and-timeline.md` 的“ASR 原始 word 与展示分词使用双层时间契约”。

## 单页工具与历史入口契约

文字剪辑结果页是艺术字和画中画的唯一编辑器文档。`supportsInlineWorkspace()` 只能依赖完成切换所必需且稳定存在的节点：

```javascript
return Boolean(
  stage === "cut" &&
    inspector &&
    cutPanelStack &&
    inspectorHost &&
    previewOverlay &&
    timelineLayer &&
    previewVideo,
);
```

不要把 `.text-editor-tabbar`、某个历史面板或其他可选工具 UI 加入能力检测。主编辑器不得提供跳出当前文档的工具 fallback。

切换契约：

- `cut`：显示 `.text-editor-panel-stack`，art/pip root 隐藏且 inert，URL 无 `tool`；
- `art`：文字面板隐藏且 inert，只激活 `#editorArtPanelRoot`，URL 为 `tool=art`；
- `pip`：文字面板隐藏且 inert，只激活 `#editorPipPanelRoot`，URL 为 `tool=pip`；
- 三种状态都保留同一个 document、`#cutPreviewVideo`、公共预览和公共时间线，不调用基础视频 `load()`。
- `/art-text` 与 `/picture-in-picture` 只返回 307 到 `/?tool=art|pip`：保留 query、覆盖冲突 `tool`、删除 `embedded`；同名 `/api/transcriptions/...` 路由不受影响。
- `art-text.html/js` 与 `picture-in-picture.html/js` 不存在；源码和运行 DOM 都不得重新引入工具 iframe、跨页 `postMessage`、revision floor/ACK、mirrored preview/timeline 或 feature flag authority。
- `EditorProjectStore` 只导出顶层语义状态和 frame/composition/timeline/preview selectors；不得保留 `selectCutDraftMessage`、`selectToolState`、`selectIframeProjection` 等只服务于旧 bridge 的投影。
- 模板库进入 `/?job=<id>&tool=art`。EditorSuite 只解析一次模板 query 并注入 `initialTemplateSelection`；ArtTool 等 catalog 完成后校验并消费，不直接读取 `window.location`。
- 有选中 manual overlay 时只更新该项；选中 transcript cue 时按 `trackId` 一次更新全轨；无 selection 时保存为会话首选，供新 manual 和全文轨道使用。模板应用最多增加一个 revision，不能改变 range 或 `timingRevision`。

静态测试必须断言旧资源缺失、内部链接都指向顶层 URL，且 EditorSuite 与 EditorProjectStore 均无 legacy bridge marker。浏览器回归必须覆盖三工具切换、两个历史 URL、模板 handoff、隐藏 panel inert、运行 DOM iframe 数量为 0，以及桌面/375px 无横向溢出。

### 单页编辑器原子 Frame 与统一运行时契约

#### 1. Scope / Trigger

修改顶层基础视频、播放帧时钟、公共艺术字/画中画预览、公共效果时间轴、compose 派生或工具时间范围命令时，必须遵守本契约。`EditorProjectStore` 是项目语义状态的唯一权威；顶层 view/controller 和 ArtTool/PipTool 只能消费同一个已选出的 editor frame 或发送语义 command，不能建立第二套项目状态。

#### 2. Signatures

```javascript
selectEditorFrame(snapshot) -> {
  revision,
  timingRevision,
  media: { jobId, sourceUrl, sourceDuration, cutRanges },
  preview: { art, pip },
  timeline,
  composition,
}

EditorMedia.createController(video).applyFrame(frame) -> boolean
EditorPreview.createCompositor(options).render(frame) -> boolean
EditorTimelineController.createController(options).render(frame) -> timelineDocument
```

顶层 Store subscriber 必须先执行一次 `selectEditorFrame(snapshot)`，再把同一对象传给媒体、预览、时间线和两个工具。compose 点击可以从当时最新 snapshot 重新选择一次原子 frame，但不得分别读取 preview、timeline 或工具私有缓存拼装请求。

#### 3. Contracts

- 页面只创建一个绑定 `#cutPreviewVideo` 的 `MediaController`；它唯一拥有基础视频 `src/load()`、source/edited 时间转换和播放帧时钟。普通 revision、保存和工具切换只调用 `applyFrame` 的同源 no-op 路径，不得替换媒体节点或重新加载。
- `PreviewCompositor`、`TimelineController` 和 compose 只消费同一 frame 的 `preview`、`timeline`、`composition`；三个公共 DOM 根必须暴露一致的 `data-project-revision` 和 `data-timing-revision`。
- `frame.timeline` 始终保留完整 `cut/art/pip` 语义轨道；公共效果层只通过 `TimelineController` 的 `visibleKinds` 投影 `art/pip`。剪后文案只由 `#cutFrameTimelineText` 展示，禁止为了去重从 Store 删除 `cut` 轨或创建第二份 timeline document。
- source mutation 只允许新 job 首次加载、显式清空或显式选择另一媒体。`setCutRanges()` 只更新时间映射，不修改 `src/currentTime/playback`。
- 时间轴 `pointermove` 只更新 controller 内的临时 document；`pointerup` 从当前权威 `frame.timeline` 生成并提交一次语义事务；`pointercancel` 丢弃临时 document，不增加 revision/history，未选 clip 的 cancel 也不得为了 selection 单独提交。
- art/pip range 由 TimelineController 在 pointerup 直接提交一个顶层语义事务；pointermove 只保留瞬时预览，不形成第二次 revision。非当前工具的 command 不得抢占全局 selection。
- `asrWords`、工具 DOM 和私有 UI 状态均不是公共预览、时间轴或 compose 的权威输入。PiP 素材通过 Store asset registry 查找；完整 UI 模型由 selector 显式裁剪为公开 compose DTO。
- 同一媒体帧只触发一次 compositor 时间同步；热路径不得重新运行 selector、重建整条时间轴、全量查询 DOM 或建立额外 rAF/rVFC 循环。

#### 4. Validation & Error Matrix

| 条件 | 处理 |
| --- | --- |
| frame 缺少 `media` | `MediaController.applyFrame` 返回 `false`，不改媒体源 |
| `jobId + sourceUrl` 与当前 source key 相同 | 更新 revision/时间映射；不写 `src`、不调用 `load()` |
| 新 job 或显式 source change | 写入新 source 并只加载一次；TimelineController 清空 pointer/history |
| pointerup 前 Store 收到新 frame | 临时预览仍非权威；提交时以最新 `frame.timeline` 为基线 |
| `pointercancel` | 恢复权威 frame；revision、timingRevision、history 不变 |
| 等价语义 command | Store no-op；不得重复提交、改 selection 或增加 revision |
| 非当前工具投影携带 selection | 接收其语义轨道，但保留当前全局 selection |
| PiP asset 不存在或尚未完成 | 跳过该预览媒体并保留语义 layer；禁止回退解析 HTML/job-state |

#### 5. Good / Base / Bad Cases

- Good：revision 18 的 frame 同时渲染 preview/timeline 并产生 compose；art 拖动在 pointerup 提交为 revision 19，三个 DOM 根、ArtTool 和 compose 都显示 19。
- Base：重复切换 cut/art/pip 或保存版本时 frame revision 可以变化，但 `#cutPreviewVideo` 节点、source key、currentTime 和播放状态保持，`load()` 计数不变。
- Bad：subscriber 分别调用多个 selector，时间轴在 pointermove 直接 dispatch，或父页从 `generationPayload`/HTML 重建公共状态；这些做法会产生混合 revision、双历史或预览与导出漂移。

#### 6. Tests Required

- Node MediaController：同源 no-op、显式 clear/change、source/edited 映射、rVFC/RAF/timeupdate 降级、重复 play 单 pending callback，以及迟到 callback generation guard。
- Node Store/selector：一次 snapshot 派生同 revision 的 preview/timeline/composition，稳定 art/pip id、asset registry、显式 compose DTO、跨 kind 轨道顺序、inactive selection 所有权和等价 command no-op。
- Node TimelineController：move/start/end、键盘微调、pointercancel 回滚、单次 commit、跨轨道 undo/redo、redo 分支截断、job change 清空 history。
- 静态契约：顶层只创建一个 MediaController/TimelineController，不消费 `overlayHtml`、`timelineHtml`、`generationPayload`，脚本顺序和 no-cache 资源完整。
- 真实浏览器：暂停和播放状态下切换/保存时 document、video、ArtTool、PipTool identity 不变且 iframe 为 0；pointercancel 无 revision，pointerup 单 revision；preview/timeline/compose revision 相同；375px 无重复交互轨道或横向溢出。

#### 7. Wrong vs Correct

```javascript
// Wrong: independently derive consumers and commit transient pointer state.
preview.render(selectPreviewLayers(store.getState()));
timeline.render(selectTimelineDocument(store.getState()));
compose(selectCompositionRequest(store.getState()));
store.dispatch(pointerMoveAction);

// Correct: select one immutable frame and keep pointer preview local.
const frame = EditorProjectStore.selectEditorFrame(snapshot);
mediaController.applyFrame(frame);
previewCompositor.render(frame);
timelineController.render(frame);

// On pointerup, the controller submits one transaction based on frame.timeline.
onCommit(transaction);
```

## Scenario：顶层艺术字面板与版本化草稿恢复

### 1. Scope / Trigger

修改顶层艺术字 inspector、艺术字 effect、工具 URL/模板 handoff 或本地项目草稿时适用。唯一产品路径必须使用可挂载 `ArtTool` 和同一个 `EditorProjectStore`；历史 `/art-text` 只负责重定向到该路径。

### 2. Signatures

```javascript
ArtTool.mount(root, services) -> {
  activate(), deactivate(), render(frame), destroy()
}

// EditorSuite owns storage; ArtTool must not read it.
sessionStorage[`editor-suite:project-draft:${jobId}`] = {
  schemaVersion: 2,
  jobId,
  serverVersion, // editor-art-base-v1:<domain fingerprint>
  revision,
  art: { source, overlays, suppressedOverlays },
  pip: { source, overlays },
  selection,
  savedAt,
}
```

### 3. Contracts

- `project.art`、公共预览、公共时间轴和 compose 都从同一个 Store frame 派生；ArtTool 只保留 tab、表单焦点、AI 待确认项和 busy/error 等瞬时 UI 状态。
- 草稿 `serverVersion` 是服务端艺术字恢复基线的稳定指纹，至少覆盖 job id、服务端 transcript 文本/分段、edit 输出/文案和 art source/overlays/version。它必须排除根 job `updatedAt`、`cutDraft` 和 composition 进度等无关字段；保存剪辑草稿会更新根 `updatedAt`，直接使用它会误删仍有效的艺术字草稿。
- 只有完整 `status=completed` 且包含 `result` 的 job 才能完成草稿判定。`restoredJobs` 标记必须在成功恢复，或对完整基线明确判定 schema/job/version/shape 无效后写入；不完整首轮 hydrate 不得消耗恢复机会。
- Store 原子 `PROJECT_DRAFT_RESTORED` 仍用当前 Store `serverVersion` 防止 dispatch 期间 job 漂移；EditorSuite 在 dispatch 前校验 envelope 的领域指纹。
- 带 `?job=<same>&tool=art` 的首次页面载入必须保留 art 工具；只有同一 document 真正切换到另一个 job 时才清除旧 `tool` 参数。
- 模板 query 由 EditorSuite 解析后通过 services 注入；缺少/空 `templateSize` 必须保持 `null`，不得因 `Number(null)` 变成 20。无效 template 整体忽略，无效 font/color/size 按 catalog 和当前选中项安全回退。
- 全文轨道、位置预设和 AI 请求都必须带 AbortController 与 job/revision guard。旧请求只能清理自己的 request/busy 状态，不得取消或解锁同 scope 的新请求。
- 时间范围命令必须在同一次 Store 提交中按旧/新区间等比重映射 `characterTimings`；不能只改 overlay/clip 的 `start/end`，否则草稿恢复与 compose 校验会把逐字时间判为越界。
- 手动从文案段添加艺术字时，即使同一段被重复添加，confirmed overlay id 也必须保持唯一；待确认 AI 草稿只通过 PreviewCompositor 的瞬时预览层显示，切换工具、取消、确认和销毁都要清除，且不得进入 Store revision 或 compose DTO。
- 实时 AI 建议提交当前 `draftTranscript/draftDuration`，并继续分析原视频：取帧使用原片 `mediaTime`，拼图标签、提示词和建议范围使用剪后 `displayTime`。旧请求没有草稿时沿用原媒体与单时间值路径；确认建议时由唯一 MediaController 为 overlay 补齐 `sourceStart/sourceEnd`。
- “贴合匹配文案时间”按 `words -> asrWords -> segment` 逐字符建立时间单元，忽略空白与标点，枚举全部短语候选并稳定选择距离当前 overlay 开始时间最近的一处。返回范围使用首尾字符的剪后边界；source anchor 按实际字符边界在对应 item 的 source/edited 区间间映射，不能在已有非均匀 `characterTimings` 时重新按字符序号均分。
- `CUT_TIMING_CHANGED` 必须在一次 Store transaction 内同步 cut、art、selection 和 timeline。全文轨道按最新剪后 transcript 的字符/word 边界删减和重定时；带 source anchor 的普通艺术字按保留原片范围重映射，完全落入删除区间时移入 `art.suppressedOverlays`；无可靠文案关联的自定义艺术字保持不变。
- `suppressedOverlays` 是项目内部可逆状态，不进入 preview、公共效果时间轴或 compose DTO，但必须随 schema v2 草稿持久化。撤销文字删除或恢复旧草稿时重新 reconcile，使用稳定 overlay id 恢复；若 selection 指向被隐藏项，只能回退到同一 transcript track 中最近的活动 cue，否则清空。

### 4. Validation & Error Matrix

| 条件 | 处理 |
| --- | --- |
| job 尚未 completed 或缺少 result | 暂不判定、不写 restoredJobs，等待后续完整 hydrate |
| JSON 损坏、schema/job/shape 不匹配 | 忽略草稿并标记该完整基线已决断 |
| 艺术字领域指纹不匹配 | 忽略草稿；不得覆盖新的服务端文案或 art |
| 仅 cutDraft/root updatedAt 改变 | 指纹保持一致，恢复 overlays/selection/time |
| 工具 deactivate/destroy/job 切换 | abort 当前请求；迟到响应不得 dispatch Store |
| 旧请求在新请求之后返回 | 旧请求 no-op，不能清理新请求 token/timer/busy |
| cut 删除完整 transcript cue/带锚点艺术字 | 从活动 overlays、preview、timeline、compose 移除，写入 `suppressedOverlays` |
| 撤销上述 cut 或恢复早于当前 cut 的草稿 | 在同一 revision 内 reconcile 并用稳定 id 恢复/继续隐藏 |

### 5. Good / Base / Bad Cases

- Good：用户修改艺术字文字、时间和坐标，剪辑草稿随后自动保存并改变 job `updatedAt`；刷新仍恢复稳定 id、selection、时间和 compose。
- Base：首次 hydrate 只有 job id/status，没有完整 result；恢复适配器等待下一次完整响应后再校验。
- Bad：把根 `job.updatedAt` 直接写进 art 草稿，或进入 `restoreEditorDraft()` 就先 `restoredJobs.add(jobId)`；前者造成无关保存误失效，后者会让并发首轮吞掉有效草稿。

### 6. Tests Required

- Node/静态：ArtTool 不包含 storage/message/video/timeline store；重复 mount/destroy 可撤销；Store 原子恢复覆盖错误 job/version、等价 no-op、cut-to-art 删减/撤销和陈旧草稿 reconcile。
- 真实浏览器：text/style 一次 revision 且 timing 不变，range 一次 revision/timing；cutDraft 自动保存后 reload 仍恢复 art；`tool=art` 保留；媒体同页不发生 `src/load()`。
- effect 竞态：让旧全文轨道请求忽略 abort 并迟到返回，断言旧响应 0 revision、0 overlay，新请求仍恰好提交 1 revision。
- 历史 URL/模板兼容：307 后顶层 art root 可用，manual/全文轨道/无 selection/无效参数均按单次 handoff 契约运行，DOM 中 iframe 数量始终为 0。

### 7. Wrong vs Correct

```javascript
// Wrong: unrelated cut draft writes invalidate art, and partial hydrate
// permanently consumes the only recovery attempt.
envelope.serverVersion = job.updatedAt;
restoredJobs.add(job.id);
if (!job.result) return false;

// Correct: wait for a complete baseline and fingerprint only relevant domains.
if (job.status !== "completed" || !job.result) return false;
if (envelope.serverVersion !== editorDraftServerVersion(job)) {
  restoredJobs.add(job.id);
  return false;
}
const accepted = store.dispatch(restoreAction).accepted;
restoredJobs.add(job.id);
```

## 禁止事项

- 不引入框架或构建系统来完成局部修改。
- 不在多个页面复制新的时间轴转换函数；先扩展共享模型或确定适配所有者。
- 不重新引入工具 iframe、跨页消息桥或 feature flag 第二 authority。
- 不用完整 HTML 快照作为持久状态或工具协议。

参考：`web/editor-project-store.js`、`web/editor-suite.js`、`web/editor-art-tool.js`、`web/editor-pip-tool.js`。
