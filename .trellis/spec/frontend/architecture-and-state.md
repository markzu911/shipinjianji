# 前端架构与状态

## 页面职责

- `web/index.html` + `app.js`：上传、转写、文字编辑、剪辑选择、历史和主工作流。
- `web/editor-suite.js`：顶层编辑工作台、工具 iframe、统一预览、轨道协调和生成/保存。
- `web/art-text.html/js`：艺术字工具，可独立页面运行，也可嵌入工作台。
- `web/picture-in-picture.html/js`：画中画工具，可独立或嵌入。
- `web/timeline-model.js`：版本化轨道文档、clip 归一化、选择、拖动/缩放和 localStorage 草稿。
- `web/transcript-follow-scroll.js`：文字播放跟随滚动的目标计算、RAF 动画、去重、中断和临时样式清理。
- `web/ui-feedback.js`：对话框、生成进度和通用播放器反馈。

## 加载方式

没有 ES module 或 bundler。公共脚本在页面业务脚本前以 `defer` 加载，并暴露 `window.EditorTimeline` 等全局。新增共享脚本时：

1. 明确唯一全局命名空间；
2. 在所有消费者 HTML 中保持相同加载顺序；
3. 修改静态资源时更新 HTML 的 `?v=` 版本；
4. 同步 `disable_frontend_cache` 的资源路径（如属于其覆盖范围）；
5. 更新静态资源测试。

### 文案跟随滚动模块契约

`web/transcript-follow-scroll.js` 是播放中活动文案跟随滚动的唯一实现边界，并通过 `window.TranscriptFollowScroll` 暴露 `createController()`。`app.js` 只负责确定活动行、更新 `aria-current`/播放 badge，并调用控制器的 `follow()`、`reset()` 和 `destroy()`；不得在入口中复制目标计算、RAF 或跟随 key 状态。

控制器在同一条可取消 RAF 时间线上同步写入面板 `scrollTop` 与活动行临时 `transform`。切换目标、列表重渲染、关闭跟随或收到 `wheel`、`touchstart`、`pointerdown`、滚动键意图时，必须取消旧帧并清除 transform、will-change、动画 class 和监听器；旧回调即使迟到也不得写入新 DOM。`prefers-reduced-motion: reduce` 直接定位，不建立动画状态。

跟随 key 只能在目标行和滚动面板通过有效性校验后记录；首次调用遇到隐藏/脱离 DOM 的目标不得消耗 key，运行中的目标失效也要释放 key，使面板恢复后同一行可以重试。用户主动滚动中断则保留已跟随 key，避免后续 `timeupdate` 立即抢回滚动控制权。

## 状态所有权

- 轨道结构优先经 `EditorTimeline.createStore` 归一化和修改，不直接散改复制对象。
- 顶层工作台负责跨工具选择、播放时间、源选择、统一预览和 iframe 生命周期。
- 子工具只维护本领域编辑状态，并通过明确消息/事件投影给顶层。
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

## iframe/事件契约

- 所有消息都有明确 `type`，父子两侧同步定义。
- 校验同源；子页校验 `event.source === window.parent`，父页校验来源 iframe。
- 发送可序列化数据，不发送 DOM 节点、函数或整份 `innerHTML`。
- 新增跨页状态前优先扩展语义 action/state projection，不增加私有 generation payload 副本。

### 内嵌工具能力检测契约

文字剪辑结果页是艺术字和画中画的顶层工作台。`supportsInlineWorkspace()` 只能依赖完成切换所必需且稳定存在的节点：

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

不要把 `.text-editor-tabbar`、某个历史面板或其他可选工具 UI 加入能力检测。删除这些节点后若仍保留依赖，`openTool()` 会退化为 `window.location.href = href`，用户将离开公共预览和时间轴。

切换契约：

- `cut`：显示 `.text-editor-panel-stack`，所有 tool iframe panel 非激活，URL 无 `tool`；
- `art`：隐藏文字面板栈，激活 art iframe panel，URL 为 `tool=art`；
- `pip`：隐藏文字面板栈，激活 pip iframe panel，URL 为 `tool=pip`；
- 三种状态都保留公共预览和时间轴 DOM，不重载顶层文档；独立工具 URL 仍可直接访问。

静态测试必须断言能力检测不包含已移除 selector，并锁定三个页面的 `editor-suite.js` 资源版本。浏览器回归必须从文字剪辑依次点击 art、pip、cut，检查 `document.title` 不变、URL 参数、激活 panel、公共预览可见以及 375px 无横向溢出。

## 禁止事项

- 不引入框架或构建系统来完成局部修改。
- 不在多个页面复制新的时间轴转换函数；先扩展共享模型或确定适配所有者。
- 不让 iframe 直接修改父页面 DOM。
- 不用完整 HTML 快照作为持久状态或跨页协议。

参考：`web/timeline-model.js`、`web/editor-suite.js` 的 message handler、`web/art-text.js` 和 `web/picture-in-picture.js` 的嵌入模式。
