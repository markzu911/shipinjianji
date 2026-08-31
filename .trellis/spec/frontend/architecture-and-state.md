# 前端架构与状态

## 页面职责

- `web/index.html` + `app.js`：上传、转写、文字编辑、剪辑选择、历史和主工作流。
- `web/editor-suite.js`：顶层编辑工作台、Store 协调、工具切换、统一预览、轨道和生成/保存。
- `web/editor-art-tool.js`：只挂载到 `#editorArtPanelRoot` 的艺术字 inspector，不拥有页面、视频或时间线。
- `web/editor-pip-tool.js`：只挂载到 `#editorPipPanelRoot` 的画中画 inspector，不拥有页面、视频或时间线。
- `web/timeline-model.js`：版本化轨道文档、clip 归一化、选择、拖动/缩放和 localStorage 草稿。
- `web/transcript-follow-scroll.js`：文字播放跟随滚动的目标计算、真实行 reparent、最终位置提交、去重、中断和临时样式清理。
- `web/ui-feedback.js`：对话框、生成进度和通用播放器反馈。

## 加载方式

没有 ES module 或 bundler。公共脚本在页面业务脚本前以 `defer` 加载，并暴露 `window.EditorTimeline` 等全局。新增共享脚本时：

1. 明确唯一全局命名空间；
2. 在所有消费者 HTML 中保持相同加载顺序；
3. 修改静态资源时更新 HTML 的 `?v=` 版本；
4. 同步 `disable_frontend_cache` 的资源路径（如属于其覆盖范围）；
5. 更新静态资源测试。

### 文案跟随滚动模块契约

`web/transcript-follow-scroll.js` 是播放中活动文案跟随滚动的唯一实现边界，并通过 `window.TranscriptFollowScroll` 暴露 `createController()`。控制器唯一拥有真实活动行的 reparent、等高占位、单行展示层最终定位、一次性目标 `scrollTop` 提交、跟随 key、用户中断和恢复顺序；不得对整个列表建立 FLIP/WAAPI 运动带，不得对仍位于 `segmentList` 的真实行执行跟随 transform，也不得由 `app.js` 建立逐帧滚动控制器。

`app.js` 只负责确定活动行、更新 `aria-current`/播放 badge，并调用控制器的 `follow()`、`reset()` 和 `destroy()`。列表与展示层中的真实行必须经统一查询 helper 读取，所有行交互复用同一个命名事件处理器；`renderCutSegments()` 必须在替换列表内容前调用 `reset()`，先把展示层中的真实行恢复到占位位置。

控制器必须先集中读取 item、panel、toolbar 和定位 context 的几何，再插入不含按钮、时间 data 或可聚焦后代的等高占位并移动真实行，最后一次写入目标 `scrollTop`、展示层尺寸/位置和底部余量。中段直接进入“三个当前行高”锚点；接近尾部时直接进入 clamp 后的完整可见位置。不得读取上一视觉位置、不得写列表 `transform/will-change`、不得创建 list/tail 动画阶段。换段、重渲染、关闭跟随、目标失效或收到 `wheel`、`touchstart`、`pointerdown`、滚动键意图时，必须恢复原顺序并清除占位、展示层尺寸/transform 和监听器。`prefers-reduced-motion: reduce` 与普通模式使用相同的唯一 DOM 结构和最终位置，不建立另一条实现路径。

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

### 场景：剪辑高频交互调度与草稿保存队列

#### 1. Scope / Trigger

修改文字删除/恢复、空白切换、时间轴提交、撤销/重做、剪辑缩略图、cut history 或 cut-draft 保存时，必须保持本场景。目标是合并非必要工作，不改变 `selectedRanges`、`selectedNoSpeechRanges`、timeline、声学物理边界或 Store 的权威关系。

#### 2. Signatures

```javascript
updateSelectionSummary({
  transcript?: "skip" | "reconcile" | "replace",
  timelineText?: "skip" | "reconcile" | "replace",
}) -> schedule one visible commit
flushPendingCutSelectionCommit() -> boolean
flushPendingCutCommitEffects() -> boolean
scheduleCutDraftSave({ immediate?: boolean }) -> Promise<void>
flushCutDraftSave() -> Promise<number>
cutDraftSemanticSignature(payload) -> string
cutDraftResponseStructureCompatible(requestPayload, responseDraft) -> boolean
applyPersistedCutDraftAlignment(
  draft,
  expectedSignature,
  retainedTranscript?,
  expectedJobId?,
) -> boolean
buildCutTimelineThumbnails({ force?: boolean }) -> Promise<void>
```

#### 3. Contracts

- 每个用户命令在 handler 内同步更新选择并记录自己的 before/after history transaction；同一 rAF 只能合并可见 commit 和后置 effect，不能合并两个命令的撤销边界。
- 可见 commit 在下一帧只更新删除/恢复状态、选区控件和保守的生成禁用态；精确合并范围、删除时长和统计文案进入 transcript 后置阶段。后置阶段必须用精确 merged 结果再次校正生成禁用态，显式 flush 也必须包含该统计更新。EditorSuite、时间轴结构、缩略图映射、服务端保存和 history 序列化继续在其后执行。一次 cut commit 只允许一个 `CUT_TIMING_CHANGED`，`EditorSuite.setCutDraft()` 重绘必须使用 `hydrateProject: false`；Store 拒绝等价 action 时不得继续重绘 job 状态或覆盖其他操作刚写入的状态文案。
- 文案和时间轴文字使用显式 `skip/reconcile/replace` render intent；同一帧合并时 `replace` 具有最高优先级，后来的普通选择不得把结构失效降级。取消尚未完成的 effect 时只把未执行阶段的 intent 放回队列；结构替换入口必须实际调用完整 render，不能只处理 `reconcile` 后静默跳过 `replace`。
- 普通删除/恢复按稳定 key 对账文案、时间轴文字、split clip 和待确认范围；相同 key 只更新变化属性，未受影响节点保持 identity。重复/空 key 或现有 DOM identity 不可信时允许单次完整 fallback；fallback 不能成为普通点击常态。ruler 只在时长、宽度或主刻度 signature 变化时重建，缩略图 projection signature 命中时直接跳过。
- 后置 effect 按 transcript -> Store -> timeline text/ruler -> split/range/thumbnail/draft 四阶段分散到独立任务。`flushPendingCutCommitEffects()` 必须识别当前阶段并同步排空余下阶段，生成、pagehide 和显式 flush 不能读到半提交状态。
- cut 工具激活时，公共 preview 继续消费最新 frame，但隐藏的公共效果时间轴、ArtTool 和 PipTool 不做同步重绘；切换到 art/pip 时必须从最新 Store frame 一次补齐，不能显示旧 timing revision。
- thumbnail cache key 只包含 job/source、源时长、采样数量和资源版本。删除范围只隐藏或重映射 source-time frame；同一时刻只有一个 extractor owner，source/key 切换、错误、重置和销毁都 abort 并释放旧 video source。
- 缓存 frame 的布局必须用现有 source-to-edited spans 计算剪后 `left/width`，不能只隐藏删除区间后让 Grid 将剩余帧等宽重排；剪后时长变为零时也必须取消在途 extractor 并清空旧缩略图 DOM。
- 本地 cut draft 在每次稳定编辑后立即写入恢复快照；服务端 PUT 使用约 `300ms` trailing debounce、单 in-flight 和 latest-state-wins。语义签名描述浏览器当前完整语义状态，用于 desired/ack 去重；服务端可以合法规范化文字语义边界、静音范围、时间轴语义/物理边界和 split time，因此禁止用 request/response 时间数值全等判断响应是否合法。
- in-flight identity 必须在调用 `fetch()` 前登记，保证同步抛错和异步拒绝都由同一 `finally` 释放队列；新命令取消旧 commit effect 时必须同时丢弃旧预览，服务端校准已直接同步 Store 时后续 effect 不得重复提交等价状态。
- HTTP 2xx 表示服务端已经持久化草稿。响应 revision 必须是正安全整数且严格大于请求 revision；一旦通过此门槛，前端必须先单调推进 `cutDraftRevision`，后续结构/对齐错误不得让下一请求继续使用旧 revision。
- 规范化响应使用结构命令身份校验：text/no-speech/timeline/split 各集合必须 key 非空且唯一、数量和 key 集合一致；文字、`automaticNoSpeechInitialized`、`boundaryMode` 和 `splitClipKey` 必须一致。所有合法时间数值以服务端响应为权威，未知 mode、缺失/重复/额外 key 或 split ownership 变化必须拒绝。
- 只有请求仍等于当前 desired 时才能原子安装完整服务端 text/no-speech/timeline/split snapshot；先完成全部校验和构造，再一次性替换已提交状态，并保留用户尚未提交的时间轴 pending 选区。安装后必须重建 post-normalization payload/signature，用它更新 desired、ack、history endpoint、retained projection、本地草稿和 Store，最后才显示“已保存”。
- 旧响应可以推进 acknowledged revision，但不得安装其规范化 snapshot 或覆盖较新的 desired/pending 状态；后续请求必须使用最新 revision 重放一次 latest-state PUT。
- `flushCutDraftSave()` 必须先提交待处理 frame/effect、同步落盘 dirty history、取消 debounce、排空 in-flight，并且只在当前 job 的 desired signature 已由当前 revision 确认后返回。
- history transaction 立即进入内存；localStorage 序列化通过 idle/短防抖合并，`pagehide`、document hidden 和显式 flush 必须同步写入 dirty 状态。localStorage 成功不等于服务端保存成功。

#### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| 同一 rAF 前发生两个独立命令 | 一次可见 commit、两个有序 history entry，可连续撤销两次 |
| 同一 source 上改变删除范围 | extractor 创建数为 0；只重映射/隐藏已有 frame |
| 新 source 或缩略图密度 | cancel 旧 owner，只允许新 generation 写缓存和 DOM |
| 首个 PUT 在途时继续编辑 | 不并发发送；首个响应推进 revision，随后发送一个 latest-state PUT |
| 合法规范化改变任意时间数值 | 完整安装服务端 snapshot，重建 post-normalization desired/ack/history/projection |
| 旧响应不是当前 desired | 只推进 revision，不覆盖当前已提交或 pending 状态；用新 revision 重放 latest desired |
| 2xx 响应结构缺失/重复/额外 key，或文字/mode/split ownership 变化 | 不安装、不显示成功；保留已提交 revision，使下一不同签名可补偿保存 |
| revision 非正安全整数、未递增或缺失 | 拒绝响应，不推进本地 revision，不显示成功 |
| PUT 失败 | 保留本地 dirty 状态并显示错误；下一次编辑可重试 |
| 生成前仍有 timer/in-flight/frame | `flushCutDraftSave()` 继续排空，不使用旧 revision 生成 |

#### 5. Good / Base / Bad Cases

- Good：300ms 内连续 10 次删除只产生一次可见 action 序列和最多一次常规 PUT；服务端规范化后完整安装四类集合、更新 revision/ack/history，基础 video 不 reload，history 最多序列化一次。
- Base：单次删除在下一绘制机会可见，随后异步完成时间轴、缩略图映射和草稿保存。
- Bad：把 cut revision 或删除范围放进 thumbnail key，或在接受 2xx revision 前比较 request/response 时间签名；前者会逐次重新 seek/JPEG，后者会把已持久化响应当失败，使 undo 使用旧 revision 并在刷新后恢复删除。

#### 6. Tests Required

- 真实浏览器使用至少 600 个可见字符和 30 个既有删除范围，连续 10 次操作测量 input 到 post-commit 第二个 rAF；P95 不高于 `80ms`、最大不高于 `120ms`、同步点击 P95 不高于 `10ms`，且无新增 `>100ms` long task。
- 计数断言 extractor、基础 video `src/load()`、Store action、history 写入、PUT 数与最大并发；网络变慢或失败不能阻止删除状态在下一帧可见。
- 增量用例必须保存未受影响的文案、时间轴文字和 ruler 节点引用，操作后断言 identity 仍相同，并断言普通选择没有 transcript/timeline full replace 或 fallback。结构修改、服务端权威替换和 identity 破坏另行断言 `replace`/fallback 可恢复完整 DOM。
- 真实本地媒体连续播放至少 15 秒并跨越至少 8 个文字/空白边界；切段 rAF 超出 60Hz 基线的 P95 不高于 `16ms`、最大不高于 `32ms`，无 `>50ms` long task，且活动真实行和播放按钮始终唯一。
- 覆盖 burst、在途编辑、revision rebase、服务端文字/静音/timeline/split 规范化、失败重试、生成前 flush、刷新恢复，以及同帧两命令两次撤销。
- 结构校验必须覆盖缺失/重复/额外 key、文字变化、未知 `boundaryMode`、split ownership 变化和非法 revision；拒绝后下一不同签名必须使用已提交的新 revision 恢复同步。
- 真实浏览器必须覆盖 `规范化删除 -> undo 服务端清空 -> refresh 保持空 -> redo 用最新 revision 恢复 -> refresh`，并同时断言 API、localStorage、history 和 Store；规范化旧响应还要证明不会覆盖在途新编辑或 pending 时间轴选区。
- cut frame 前后保持 ArtTool tab、模板 listbox、selection、document/video/tool root identity。

#### 7. Wrong vs Correct

```javascript
// Wrong: every command synchronously rebuilds media and saves the full draft.
renderCutTimeline();
await saveCutDraft(buildPayload());

// Correct: commit visible state once, then coalesce non-critical effects.
updateSelectionSummary();
scheduleCutDraftSave();
```

```javascript
// Wrong: server-derived physical boundaries make an acknowledged request dirty.
const signature = JSON.stringify({ ranges, revision, diagnostics });

// Correct: signature only describes stable user intent.
const signature = cutDraftSemanticSignature(buildPersistedCutDraftPayload());
```

```javascript
// Wrong: the server committed revision N+1, but numeric normalization is
// treated as a failed write before the client accepts the revision.
if (cutDraftSemanticSignature(serverDraft) !== request.signature) throw error;
cutDraftRevision = serverDraft.revision;

// Correct: accept the durable revision first, validate command identity,
// install the complete authoritative snapshot, then acknowledge its new signature.
acceptAdvancedRevision(serverDraft.revision);
assertStructureCompatible(request.payload, serverDraft);
installNormalizedSnapshot(serverDraft);
acknowledge(cutDraftSemanticSignature(buildPersistedCutDraftPayload()));
```

### 场景：时间轴预览帧持久缓存

#### 1. Scope / Trigger

修改 `timeline-thumbnail-cache.js`、`buildCutTimelineThumbnails()`、缩略帧采样密度、IndexedDB 存储、Blob URL 生命周期或相关静态资源加载顺序时，必须保持本场景。持久缓存只是刷新性能优化，不是项目、媒体或剪辑状态的权威来源。

#### 2. Signatures

```javascript
TimelineThumbnailCache.createStore(options?) -> {
  load(signature) -> Promise<record | null>,
  save(record) -> Promise<void>,
  prune({ preserveSignature? }?) -> Promise<number>,
  close() -> void,
}

record = {
  signature: string,
  cacheVersion: number,
  jobId: string,
  sourceDuration: number,
  count: number,
  frames: Array<{ sourceTime: number, blob: Blob }>,
  byteSize: number,
  createdAt: number,
  lastAccessedAt: number,
}
```

缓存签名固定为 `cacheVersion | jobId | source URL | sourceDuration | count`。`count` 只依赖源视频时长和时间轴宽度；删除、恢复、文字拆分、split point、cut revision 和剪后时长不得进入签名或采样密度。

#### 3. Contracts

- `web/timeline-thumbnail-cache.js` 是 IndexedDB 的唯一访问边界，通过 `window.TimelineThumbnailCache` 暴露 API；`app.js` 继续唯一拥有 source-time 采样、extractor、Canvas、内存 cache 和剪后投影。
- 构建顺序必须是 `memory -> IndexedDB -> extractor`。异步读取前先登记唯一 owner；每个 `await`、Blob URL 创建和 DOM 提交前都要校验 build id、AbortSignal 和 owner identity，迟到结果不得覆盖新 source。
- IndexedDB 能力读取、同步/异步 `open()`、blocked、versionchange、transaction、记录 shape、Blob 和配额错误都必须静默降级。同步或瞬时 open 失败不得永久缓存 rejected Promise，后续 `load/save` 必须可以重试。
- 持久层只保存 `image/jpeg` Blob 和 source time，不保存 Object URL。有效命中直接创建本 document 的 Blob URL 并渲染，隐藏 extractor 创建数和逐帧 seek 数都为 0，且不得短暂显示“正在生成帧预览”。
- miss 时沿用隐藏 video 的 source-time seek；Canvas 使用异步 `toBlob("image/jpeg", 0.72)`。帧齐全后先安装内存 cache 并渲染，`save()` 和 30 天/24 条/64 MiB LRU 清理只能在后台执行，不能延迟可见结果。
- 删除、恢复和用户点击文案拆分只使用既有 source-time frames 重新计算剪后 `left/width`；禁止因此重新 seek、编码、写持久缓存或改变基础 video source。
- 替换缓存、清空任务、视频错误和页面销毁时，必须先移除 DOM 中对旧 Blob URL 的 `backgroundImage` 引用并清除 DOM cache signature，再调用 `URL.revokeObjectURL()`。先 revoke 会让 Chromium 报 `ERR_FILE_NOT_FOUND`，并可能让仍在绘制的帧变空。
- 新脚本必须在 `app.js` 前以 `defer` 加载；脚本和消费者同步提升 `?v=`，并加入 `disable_frontend_cache` 与静态资源契约。该能力不得增加后端 API/schema 或持久化视频、文案、cut draft、艺术字和合成结果。

#### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| 内存签名命中 | 直接重投影；0 IndexedDB、0 extractor、0 seek |
| IndexedDB 有效命中 | Blob 转当前 document URL 后渲染；0 extractor、0 seek、无 loading 状态 |
| `indexedDB` getter、open 或 transaction 失败 | 静默进入 extractor；编辑、播放和剪辑继续可用 |
| 记录版本、数量、时长、Blob type/size 或 source time 非法 | 删除/忽略坏记录并重新抽帧，不产生 pageerror/unhandled rejection |
| source/signature 在异步读取或编码期间变化 | abort 旧 owner；迟到结果只做自身 URL/video 清理，不写内存或 DOM |
| 删除、恢复或文字拆分改变剪后时长 | cache signature 不变；只重投影，不创建 extractor |
| 保存或 prune 失败 | 已显示帧保持；不显示产品错误 |
| 缓存替换、任务重置或卸载 | 先解除 DOM Blob 引用，再 revoke；不得出现 `ERR_FILE_NOT_FOUND` |

#### 5. Good / Base / Bad Cases

- Good：首次打开先看到完整帧，再后台写入 Blob；同一 browser context 刷新后直接复用，extractor/seek 都为 0。
- Base：浏览器禁用或回收 IndexedDB；页面仍按原流程抽帧，仅失去刷新加速。
- Bad：把剪后时长或删除 revision 放进 key，缓存 rejected open Promise，或在 DOM 仍引用 Blob URL 时 revoke；这些分别造成每次编辑重抽帧、永久失去重试和刷新资源错误。

#### 6. Tests Required

- 静态契约：脚本加载顺序、资源版本、no-cache 路径、全局 API、JPEG Blob 校验、缓存上限和 source-duration 采样密度。
- 真实 Chromium 首次生成：至少 8 张非 loading Blob 帧可见，持久记录 `byteSize` 等于帧 Blob 总和。
- 同一 BrowserContext 刷新：DOM 签名不变，extractor 创建和 thumbnail seek 都为 0，状态栏无生成提示，console/pageerror 为空。
- 失败矩阵：损坏 Blob、`indexedDB` getter 抛 `SecurityError`、同步瞬时 open 失败后重试成功，以及 age/count/bytes prune 保留当前 LRU 记录。
- 编辑投影：删除、恢复、文字拆分和 375px 下不新增 extractor，可见帧高度正确并从 `0%` 到 `100%` 连续覆盖。
- 在艺术字/画中画刷新和 context teardown 中保留 console 资源错误检查，防止 Blob URL 释放顺序回归。

#### 7. Wrong vs Correct

```javascript
// Wrong: edited state changes the persistent key and every cut re-extracts.
const signature = `${jobId}|${editedDuration}|${cutRevision}|${count}`;

// Correct: persist immutable source samples and project them into edited time.
const signature = `${cacheVersion}|${jobId}|${source}|${sourceDuration}|${count}`;
renderCutTimelineThumbnailFrames(sourceFrames, editedDuration);
```

```javascript
// Wrong: live CSS backgrounds still point at the revoked Blob URLs.
releaseCutTimelineThumbnailFrames(cache);
cutFrameTimelineThumbnails.replaceChildren();

// Correct: remove document references before releasing their URLs.
cutFrameTimelineThumbnails.replaceChildren();
delete cutFrameTimelineThumbnails.dataset.cacheSignature;
releaseCutTimelineThumbnailFrames(cache);
```

### 场景：播放头分割与精确片段删除

#### 1. Scope / Trigger

修改播放头分割、基础视频片段选择、片段删除/恢复、cut draft 结构字段、cut history 或 Store cut 轨道时适用。分割是源媒体结构状态，不是新的媒体或删除 owner；普通拖选删除的语音安全边界不得因此改变。

#### 2. Signatures

```javascript
EditorProjectStore.ACTIONS.CUT_STRUCTURE_CHANGED
normalizeCutSplitPoints(points) -> Array<{ key, sourceTime }>
deriveCutSplitClips() -> { clips, markers }
splitCutTimelineAtPlayhead() -> boolean
deleteSelectedCutSplitClip() -> Promise<boolean>
restoreSelectedCutSplitClip() -> boolean
```

```text
PUT /api/transcriptions/{job_id}/cut-draft
splitPoints[] = { key: string, sourceTime: number }
timelineRanges[].boundaryMode = "speech_safe" | "split_exact"
timelineRanges[].splitClipKey? = "split-clip:<left-key>:<right-key>"
```

#### 3. Contracts

- split point 永远持久化 source time；edited time、CSS 百分比和 scroll 坐标只能作为当前视图投影。边界使用 `source-start` / `source-end` sentinel 与稳定 point key 派生 clip key。
- 纯分割只 dispatch 一次 `CUT_STRUCTURE_CHANGED`：project revision `+1`，`timingRevision +0`，不触发 Art/PiP cut reconciliation，不改变 duration、播放头、播放状态或基础 video source。
- `cut:split-structure` 是同一 Store timeline 中的只读 cut 轨道，包含可见 clip、deleted marker 和当前 selection；不得建立第二个 timeline store。marker 不占剪后时长，即使成片时长为零也必须保持时间轴与恢复入口可操作。
- 删除完整分割片段仍写唯一 `timelineRanges`，携带 `split_exact` 与稳定 `splitClipKey`；恢复只移除对应 exact range。普通自由拖选省略 boundary metadata，继续按 `speech_safe` 保存。
- `splitPoints`、`boundaryMode`、`splitClipKey` 和 history selection 属于用户语义，必须进入草稿语义签名与历史快照；服务端派生物理 `start/end`、diagnostics、revision 和时间戳仍不得进入签名。
- clip/marker 重绘后按稳定 key 恢复键盘焦点；多个 marker 位于同一拼接点时使用实际 CSS 自定义属性分层，并在左右边缘向内堆叠。确认弹窗打开期间撤销/重做快捷键必须锁定。
- 命中已 acknowledged 的 redo 状态时取消待保存 timer，并把提示恢复为“已保存”；不能永久停留在“正在保存”。所有变更继续遵守单 in-flight、latest-state-wins 和生成前 flush。

#### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| 播放头在起点、终点、已有边界、删除区或不足最小时长 | 分割按钮 disabled；命令 no-op，无 revision/history/PUT intent |
| 历史草稿缺少 `splitPoints` / boundary metadata | 恢复为空结构；普通 timeline range 按 `speech_safe` |
| exact range 不匹配相邻 source anchors 或 clip key | 服务端 `400`，不写部分草稿 |
| `speech_safe` range 携带 `splitClipKey` | 服务端 `400`，不得借普通模式伪造分割身份 |
| 同一 split clip 重复 exact 删除 | 服务端 `400`，不得保存重叠身份 |
| 全部分割片段被删除 | edited duration 可为零；分割结构和删除状态仍在 Store/草稿/历史中，公共 timeline 保持可见但不渲染恢复 marker、占位或焦点目标 |
| Store 收到等价 structure action | no-op；revision 与 `timingRevision` 均不变 |

#### 5. Good / Base / Bad Cases

- Good：连续分割后独立删除中间片段，服务端物理端点严格等于相邻 source anchors；刷新、撤销、重做和恢复保持同一 clip identity，基础 video `src/load()` 为 0。
- Base：纯分割只改变时间轴结构与草稿 revision，预览声音、画面、总时长和当前播放位置完全不变。
- Bad：持久化 edited time、把 split clip 放进私有 DOM 状态、用 `CUT_TIMING_CHANGED` 表示纯分割，或把 exact range 送进 acoustic/PCM；这些都会造成漂移、双 owner、错误重定时或再次残留/误删语音。

#### 6. Tests Required

- 后端：split point clamp/sort/dedupe、保留 sentinel、相邻 anchor/clip-key 校验、重复 exact 拒绝、speech-safe identity 拒绝，以及 exact 路径对 forced alignment/PCM 解码调用数为 0。
- Store/Node：structure action 单 revision、`timingRevision` 不变、等价 no-op、`cut:split-structure` clip/marker/selection 投影和旧 cut state 兼容。
- 真实浏览器：连续 split、边界 disabled、选择/精确删除/恢复、全删后恢复、撤销/重做、刷新、键盘焦点、多个 marker、375px、普通拖选取消和基础 video/extractor identity 计数。
- 生成回归：纯分割不改变 compose 输出；删除片段后 preview/compose 消费同一权威 exact range，生成前等待最新 draft revision。

#### 7. Wrong vs Correct

```javascript
// Wrong: edited time drifts whenever earlier ranges change.
splitPoints.push({ key, sourceTime: cutFrameTimelineSeek.value });
store.dispatch({ type: ACTIONS.CUT_TIMING_CHANGED, payload: cut });

// Correct: anchor in source time and commit structure without retiming media.
splitPoints.push({ key, sourceTime: getCutPlaybackFrameState().sourceCurrent });
store.dispatch({ type: ACTIONS.CUT_STRUCTURE_CHANGED, payload: { cut, timeline } });
```

```python
# Wrong: exact user-created clip edges must never enter acoustic movement.
aligned = align_cut_draft_timeline_ranges_to_audio([split_range], ...)

# Correct: validate adjacent source anchors, then persist exact endpoints.
validate_split_exact_timeline_range(split_range, split_points, duration)
split_range["start"] = split_range["originalStart"]
split_range["end"] = split_range["originalEnd"]
```

### 文字删除展示边界契约

文字剪辑列表必须区分“剪辑主状态”和“展示边界”：

- `selectedRanges` 与 `selectedNoSpeechRanges` 分别是文字和长空白删除的主状态；保存、生成和撤销/重做只消费这两个现有集合，不新增“自动删除”副本；
- AI 建议的原始词级范围可以作为稳定展示边界，但不能作为第二套删除状态；
- `buildSegmentTextRuns` 按单词中点投影删除状态和展示边界；普通文字与“时间轴已删除”只合并 `kind`、`presentationKey` 均相同的相邻词，连续“恢复”文字则允许跨 `presentationKey` 合并为一行并聚合全部 `rangeKeys`；“恢复”状态只来自 `selectedRanges` 的 `originalStart/originalEnd`，“时间轴已删除”只来自已提交的 `timelineRanges`，文字静音扩展和 `noSpeechRanges` 不得改变文案样式；
- `suggestionTextRangeKeysAtTime()` 同样必须逐 range 优先读取 `originalStart/originalEnd`，只有历史 suggestion 缺少字段时才回退物理 `start/end`。声学扩展可以越过相邻未选字符的时间中点，但不得改变其 `presentationKey` 或把“人”“你身”拆成孤立行；
- `currentNoSpeechSuggestions` 同样只提供稳定展示边界；文字片段与空白建议按源时间排序，每个片段独立渲染为 `li[data-display-key][data-display-start][data-display-end]`；
- 空白行用 `data-no-speech-id` 连接 `selectedNoSpeechRanges`，不伪造可编辑文字段 index；播放高亮同时比较片段时间和稳定 key。
- `data-display-start/end` 始终保留源时间，供排序、原片试听和播放高亮使用；每行可见的 `.segment-time` 必须统一显示当前剪后时间。仍有保留内容的行显示首个保留片段的剪后起点；完整删除的文字行或空白行通过 `sourceTimeToEditedTime(sourceStart)` 折叠到成片拼接点。禁止完整删除行回退显示源时间，否则同一列表会出现 `00:28 -> 00:19` 的倒序。无障碍说明可同时保留原片区间。

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

回归测试必须覆盖独立行的静态契约和 Node 行为契约，并在真实浏览器验证：文字与空白按源时间排序，但可见时间全部按剪后时间单调不降；完整删除的文案/空白显示拼接点而非源时间；连续已删文字跨 range key 只显示一行且一次恢复全部聚合 key；保留文字仍拆分两侧删除组；时间轴删除分组不变；单独重删只影响目标行；空白恢复后不再被文字静音扩展删除；删除空白不使相邻文字出现删除线/恢复按钮且不从预览时间轴消失；小于 `0.12s` 的短保留文字不被两侧自动范围合并；手动范围只删除词的一部分时其余部分仍保留；撤销/重做与刷新持久化正常；播放高亮命中当前片段；375px 无横向溢出。文案列表是用户确认的密度特例：行、圆点、播放目标及内部排版按原值 `50%` 压缩（`64px -> 32px`、`44px -> 22px`），边框仍不少于 1 个设备像素；其他移动操作目标仍遵循通用 44px 规则。

### 双层词时间戳状态契约

- `segments[].words` 是 Jieba 展示和编辑层，也是文字删除字符时序的首选来源；`segments[].asrWords` 只保留模型原始时间供声学参考和旧数据回退。
- 字符单元按段选择第一个有效层 `words -> asrWords -> segment`，再把每个带时间文本均分为字符；空数组或无效条目只触发当前段回退，不能让混合数据中的历史段落失去保护。
- 原始 `asrWords` 可以跨越自然词边界，不能作为不可分割删除单元，也不能把“给一”“得你”之类模型 token 的下一字符带入删除。
- 文案点击、AI 建议初始化、草稿恢复和撤销/重做都必须经 `canonicalizeTextSelectionRange` / `normalizeRestoredTextDeleteRange` 扩展到相交字符，并用规范后的边界重建 map key。
- `buildSegmentTextRuns` 继续逐字符投影删除状态；文字静音扩展和空白范围不能使未选字符进入恢复态。手动 `timelineRanges` 不使用字符扩展。
- 手动时间轴范围的 `originalStart/originalEnd` 只 clamp 到媒体时长并保留用户选择的精确起止；二次确认后仍可只覆盖字符的一部分。服务端可以把物理 `start/end` 在 `0.20s` 内吸附到可靠的字符声学转换，前端必须原子应用草稿响应，同时保留 `original*` 供文字删除态、撤销/重做和 retained transcript 使用。
- `generateCut()` 与统一 compose 必须先等待草稿保存队列完成，再携带当前 `cutDraftRevision`；revision 只是服务端权威草稿的并发令牌，不得增加 ProjectStore 的用户编辑 revision。旧响应只有在 job、请求签名和 revision 仍匹配时才能更新预览。

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

## Scenario：手动与文案艺术字轨道派生

### 1. Scope / Trigger

修改 `EditorArtModel.buildTimelineTracks()`、公共效果时间轴布局、艺术字草稿恢复或艺术字 clip 选择/调时时适用。`project.art.overlays` 始终是权威状态；轨道分组和单行堆叠顺序都只能是派生结果。

### 2. Signatures

```javascript
EditorArtModel.buildTimelineTracks(overlays) -> timelineTracks
EditorTimelineController.createController(options).render(frame) -> timelineDocument
```

稳定身份：

```text
普通/AI 确认的非 transcript overlay -> art:manual
trackType=transcript 且有 trackId -> art:transcript:<trackId>
overlay clip -> art:<overlayId>
```

### 3. Contracts

- 所有非 transcript 艺术字共用唯一 `art:manual` 逻辑轨道，名称为“手动艺术字”；AI 推荐确认后的普通 overlay 也进入该轨道。
- 文案 cue 继续按 `trackId` 进入 `art:transcript:<trackId>`，名称为“视频文案艺术字”；不得与手动轨混合。
- 分组只改变 Timeline track；overlay 数量、顺序、ID、文字、样式、坐标、编辑/源时间、preview 顺序和 compose DTO 不变。空集合不生成手动轨。
- 每个 overlay 仍使用唯一 `art:<overlayId>` clip，单项选择、调时、删除和撤销/重做不得批量修改同轨其他手动 clip。
- `TimelineController` 对每条 art 逻辑轨固定使用一个可视行；所有同轨 clip 的 `data-timeline-lane-index` 为 `0`，时间重叠也不得增加高度。
- 同一逻辑轨的 clip 共用 `data-timeline-track-index`；下一逻辑轨固定从上一逻辑轨下一行开始。当前 selection、focus 或 drag 项只在派生 DOM 中置顶，不写回 Store、Timeline schema 或草稿。
- 公共效果片段主体点击必须用完整 track rect 将 `clientX` 映射为剪后时间，横向滚动后的负 `left` 也必须参与换算；只有 selection 被接受后才 seek 一次。重复点击当前 selection 属于有效点击，应 seek 但保持 Store no-op、不增加 revision。无效 duration/width/left/clientX 回退片段起点，程序化 `selectClip()` 继续默认 seek 起点，resize handle 和超过阈值的 move/resize 不改为主体点击语义。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| 没有普通艺术字 | 不生成 `art:manual` |
| 多个普通/AI overlay 不重叠或首尾相接 | 共用 `art:manual` 和同一可视行 |
| 多个普通 overlay 时间重叠 | 仍共用 `art:manual` 的同一可视行，当前项置顶 |
| 同时存在普通与 transcript overlay | 生成不同轨道 ID 和名称，clip ID 各自保持稳定 |
| 历史草稿携带 `art:overlay:<id>` | 从恢复后的 overlays 重新派生为 `art:manual`；selection 的 `art:<id>` 保持 |
| 删除最后一个普通 overlay | `art:manual` 自然消失；文案轨不变 |
| track 已横向滚动后点击片段主体 | selection 接受后仅 seek 一次，指示条落在实际点击时间 |
| selection 拒绝或 track 几何/duration 无效 | 拒绝时保留点击前 selection 且不 seek；几何无效时安全回退片段起点 |

### 5. Good / Base / Bad Cases

- Good：两个时间重叠的手动艺术字在一个 `art:manual` 轨的一行中堆叠，两个按钮和列表入口都保留，选中后置顶，调时其中一个只产生一次语义提交。
- Base：一个手动艺术字和同一 `trackId` 的两个文案 cue 派生为两条逻辑轨，preview/compose 仍包含三个独立 overlay。
- Bad：按 overlay ID 创建 `art:overlay:<id>`，或为了避开重叠创建额外可视行并写入 overlay/草稿；前者重新产生一项一轨，后者制造第二份布局权威。

### 6. Tests Required

- ArtModel Node：至少两个手动项、一个 AI 普通项和两个 transcript cue，只生成一条手动轨和一条文案轨；输入 overlays 前后深比较相等。
- ProjectStore Node：旧 `art:overlay:<id>` 草稿恢复后轨道为 `art:manual`，clip selection 保持 `art:<id>`。
- TimelineController Node：重叠手动项固定 lane 0、手动/文案各一行、后续轨偏移、DOM/track 高度、置顶、滚动坐标点击、无效几何/时长回退、选择拒绝、单次 seek、程序化选择，以及 move/resize 提交语义。
- 真实浏览器：连续新增两个重叠手动艺术字，断言按钮矩形位于同一行且可从列表分别选中；点击手动和文案 clip 内部后，视频时间与指示条中心均对齐实际点击位置；调时、删除后，剩余手动项、文案轨、preview 和 compose 一致。

### 7. Wrong vs Correct

```javascript
// Wrong: every manual overlay becomes a logical track.
const groupId = `art:overlay:${overlay.id}`;

// Correct: semantic art tracks stay stable and each one owns one visual row.
const groupId = isTranscriptOverlay(overlay)
  ? `art:transcript:${overlay.trackId}`
  : "art:manual";
segment.dataset.timelineTrackIndex = String(trackIndex);
segment.dataset.timelineLaneIndex = "0";
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
- ArtTool 列表只做语义投影：同一 `trackId` 的 transcript cues 显示为一个“视频文案艺术字”入口并汇总段数与整轨范围，manual overlays 继续逐项显示；底层 `project.art.overlays`、公共预览、时间轴 clips 和 compose 仍保留每个 cue，禁止为了 UI 合并而压平数据。
- 点击 transcript 入口时继续提交现有 `art:<cueId>` selection。代表 cue 依次复用当前同轨 selection、命中当前剪后播放时间的 cue、按 start/end 排序后的首 cue；普通 render 和播放帧不得主动改 selection。
- transcript 入口选中后只显示整轨共享样式、坐标和位置预设；文字、方向、每行字数、start/end、匹配文案时间和应用到全部 manual 的控件必须隐藏。整轨样式仍经一次 `updateOverlay()`/Store command 按 `trackId` 更新，且精确保留每个 cue 的 `id`、`text`、`start/end`、`sourceStart/sourceEnd`、`characterTimings` 和 `timingRevision`。
- 全文轨道、位置预设和 AI 请求都必须带 AbortController 与 job/revision guard。旧请求只能清理自己的 request/busy 状态，不得取消或解锁同 scope 的新请求。
- 时间范围命令必须在同一次 Store 提交中按旧/新区间等比重映射 `characterTimings`；不能只改 overlay/clip 的 `start/end`，否则草稿恢复与 compose 校验会把逐字时间判为越界。
- 手动从文案段添加艺术字时，即使同一段被重复添加，confirmed overlay id 也必须保持唯一；待确认 AI 草稿只通过 PreviewCompositor 的瞬时预览层显示，切换工具、取消、确认和销毁都要清除，且不得进入 Store revision 或 compose DTO。
- 实时 AI 建议提交当前 `draftTranscript/draftDuration`，并继续分析原视频：取帧使用原片 `mediaTime`，拼图标签、提示词和建议范围使用剪后 `displayTime`。旧请求没有草稿时沿用原媒体与单时间值路径；确认建议时由唯一 MediaController 为 overlay 补齐 `sourceStart/sourceEnd`。
- “贴合匹配文案时间”按 `words -> asrWords -> segment` 逐字符建立时间单元，忽略空白与标点，枚举全部短语候选并稳定选择距离当前 overlay 开始时间最近的一处。返回范围使用首尾字符的剪后边界；source anchor 按实际字符边界在对应 item 的 source/edited 区间间映射，不能在已有非均匀 `characterTimings` 时重新按字符序号均分。
- `CUT_TIMING_CHANGED` 必须在一次 Store transaction 内同步 cut、art、selection 和 timeline。全文轨道按最新剪后 transcript 的字符/word 边界删减和重定时；带 source anchor 的普通艺术字按保留原片范围重映射，完全落入删除区间时移入 `art.suppressedOverlays`；无可靠文案关联的自定义艺术字保持不变。
- 全文轨道 reconciliation 的最小单元是同一 `trackId` 的所有 active/suppressed cues。`nextCut.transcript` 是字符身份与顺序的唯一权威；旧 cue 的 source/edited anchors 只能选择相邻 cue 的优先分界，不能按轨道最小/最大 source 覆盖过滤首尾字符。唯一全文 transcript track 必须消费完整当前 transcript；只有确实存在多个 legacy transcript tracks 时才允许按完整自然词单元隔离覆盖范围。
- 当前 transcript 的 `words -> asrWords -> segment` 回退定义合法切点，旧 cue 文本定义上一版已接受语义分区。边界先通过旧/新文本差分单调投影，再在合法词边界中选择；投影命中词内或会产生弱起始/孤立单字且存在安全内部候选时必须修复，没有安全候选时允许复用 cursor 使 cue suppress，不得用 source midpoint、字符容量比例或 cue 数量要求授权词内切分。
- 分配必须使用一个全轨单调 cursor，把每个当前字符恰好写入一个连续 cue slice；首尾 cue 吸收整体锚点漂移，无可靠 source anchors 时只能在同一合法边界集合中确定性降级。提交前必须校验活动 cue 拼接字符和 `characterTimings` 总数都与当前 transcript 相等，禁止返回部分成功的缺字轨道。
- `TRANSCRIPT_TEXT_CHANGED` 只改文案语义，不增加 `timingRevision` 或移动 cue/source ranges；但必须同时更新活动 cue 和 `_cutReconciliation.overlay` 的文字及逐字 timing 数量，并从同一 Store snapshot 重新派生 art timeline。`saveSegmentText()` 每次读取权威 job（包括 stale effect 的重试读取）后，必须在同一入口同步 `currentSegments`、`currentEditableSegments` 和 editable boundaries，并清空字符 cache，再构建 live cut transcript；否则用户修改后立即拆分/删除会按旧字符时间扩大范围。
- cut timing 更新暂时缺少 transcript、只带 `{}` 或空 `segments` 占位时，不得把全文艺术字误判为语义全删；继续按稳定 source range 重映射已有 cue。只有显式空 `text` 或实际 segment 投影明确为空才可 suppress 全轨。当前 transcript 有字符但 timing 缺失/无效则按旧 cue 容量构造有限正时长降级，并保留稳定 source anchors。
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
| canonical/local cue source start 向任一方向漂移 | 只改变全轨分界偏好；当前保留字符不得丢失、重复或倒序 |
| 全文轨旧 `sourceStart/sourceEnd` 比当前首尾词窄 | 仍分配完整当前 transcript；旧覆盖范围只影响时间偏好，不删除首尾字符 |
| 文案保存后立即手动拆分并删除拆出段 | 用新 job source segments 规范删除范围；cut/art/timeline/preview/compose 文本同一 |
| cut transcript 缺失、`{}` 或只有空 `segments` 占位 | 保留并按 source range 重映射已有 cue，不把不可用投影当成全文删除 |
| transcript 有当前文字但字符 timing 不可用 | 按旧 cue 容量确定性分配有限正时长，字符和 source anchors 仍守恒 |

### 5. Good / Base / Bad Cases

- Good：用户修改艺术字文字、时间和坐标，剪辑草稿随后自动保存并改变 job `updatedAt`；刷新仍恢复稳定 id、selection、时间和 compose。
- Good：canonical cue 比本地拆分投影晚 `0.2s` 开始；“但/你/该/人”等边界首字仍按当前 transcript 单调进入全轨 cues，五个消费者拼接文本一致。
- Good：旧末 cue 的 `sourceEnd=0.85`，当前末词“的”从 `0.864` 开始；“的”仍进入该全文轨 cue，显示 timing 按稳定 cue 时间重建。
- Base：首次 hydrate 只有 job id/status，没有完整 result；恢复适配器等待下一次完整响应后再校验。
- Bad：把根 `job.updatedAt` 直接写进 art 草稿，或让每个旧 cue 独立按 source midpoint/整轨 source 覆盖过滤新字符；前者造成无关保存误失效，后者会在合法锚点漂移时系统性吞掉段首或段尾字。

### 6. Tests Required

- Node/静态：ArtTool 不包含 storage/message/video/timeline store；重复 mount/destroy 可撤销；Store 原子恢复覆盖错误 job/version、等价 no-op、cut-to-art 删减/撤销和陈旧草稿 reconcile；整轨 style-only 更新对 cue 身份、文字、编辑/源时间、字符 timing 和 timing revision 做前后快照。
- ArtModel/Store：用双向 source anchor 漂移、窄于当前首尾词的旧 source 覆盖和缺失/mixed anchors 断言全轨字符、顺序、timing 数量守恒；覆盖词内旧坏边界、其他位置编辑、重复/完整替换、text-only reconciliation base、suppressed 恢复、selection、manual overlay 和相同 timing signature server echo。
- 真实浏览器：同轨多 cue 只显示一个入口，manual 仍逐项显示；代表 cue 选择稳定，整轨/manual 控件往返恢复；style 一次 revision 且 timing 不变，删除整轨从 preview/timeline/compose 同时消失，仅有整轨时删除后恢复空选择文案；375px 无溢出且入口不少于 44px。另需真实点击“修改文案 -> 拆分 -> 删除拆出段”，断言 cut/art/timeline/preview/compose 文本守恒、方向边界采用新字符时间、cutDraft 自动保存后 reload 仍恢复 art、`tool=art` 保留且媒体同页不发生 `src/load()`。
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

```javascript
// Wrong: expose every transcript cue as an independently styled list row.
for (const overlay of art.overlays) renderOverlayEntry(overlay);

// Correct: group only the inspector view and keep cue data unchanged.
for (const entry of overlayListEntries(art.overlays)) renderOverlayEntry(entry);
```

```javascript
// Wrong: old physical coverage decides which current characters exist.
const trackUnits = nextUnits.filter(unit =>
  unit.sourceEnd > trackStart && unit.sourceStart < trackEnd);

// Correct: the current transcript owns character identity; old anchors only
// rank legal semantic boundaries for one complete full-track partition.
const legalSplits = transcriptSemanticSplitIndexes(nextUnits);
const partition = partitionTranscriptTrack(trackCues, nextUnits, legalSplits);
assertTrackCharactersConserved(partition, nextUnits);
```

## 禁止事项

- 不引入框架或构建系统来完成局部修改。
- 不在多个页面复制新的时间轴转换函数；先扩展共享模型或确定适配所有者。
- 不重新引入工具 iframe、跨页消息桥或 feature flag 第二 authority。
- 不用完整 HTML 快照作为持久状态或工具协议。

参考：`web/editor-project-store.js`、`web/editor-suite.js`、`web/editor-art-tool.js`、`web/editor-pip-tool.js`。
