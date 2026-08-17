# 前端架构与状态

## 页面职责

- `web/index.html` + `app.js`：上传、转写、文字编辑、剪辑选择、历史和主工作流。
- `web/editor-suite.js`：顶层编辑工作台、工具 iframe、统一预览、轨道协调和生成/保存。
- `web/art-text.html/js`：艺术字工具，可独立页面运行，也可嵌入工作台。
- `web/picture-in-picture.html/js`：画中画工具，可独立或嵌入。
- `web/timeline-model.js`：版本化轨道文档、clip 归一化、选择、拖动/缩放和 localStorage 草稿。
- `web/ui-feedback.js`：对话框、生成进度和通用播放器反馈。

## 加载方式

没有 ES module 或 bundler。公共脚本在页面业务脚本前以 `defer` 加载，并暴露 `window.EditorTimeline` 等全局。新增共享脚本时：

1. 明确唯一全局命名空间；
2. 在所有消费者 HTML 中保持相同加载顺序；
3. 修改静态资源时更新 HTML 的 `?v=` 版本；
4. 同步 `disable_frontend_cache` 的资源路径（如属于其覆盖范围）；
5. 更新静态资源测试。

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
- `buildSegmentTextRuns` 按单词中点投影删除状态和展示边界，只合并 `kind` 与 `presentationKey` 均相同的相邻词；
- `currentNoSpeechSuggestions` 同样只提供稳定展示边界；文字片段与空白建议按源时间排序，每个片段独立渲染为 `li[data-display-key][data-display-start][data-display-end]`；
- 空白行用 `data-no-speech-id` 连接 `selectedNoSpeechRanges`，不伪造可编辑文字段 index；播放高亮同时比较片段时间和稳定 key。

恢复 AI 删除片段时，只从 `selectedRanges` 删除对应 range key，不移除原始建议边界。这样“保留 / 删除 / 保留”恢复后仍是三行，中间行只是从恢复按钮变为普通编辑按钮。

恢复空白片段时，只从 `selectedNoSpeechRanges` 删除对应 id，空白行继续保留并变为可试听状态。文字删除范围可能因 `adjacentSilenceBefore/After` 扩展到该空白，因此 `getMergedSelection` 必须先调用 `protectRestoredNoSpeechFromTextRanges`：仅从文字范围的前后静音扩展中扣除已恢复空白，文字原始 `originalStart/originalEnd` 仍保持删除。否则会出现“列表显示已恢复，但预览和成片仍删除”的状态漂移。

```javascript
const canMerge =
  previous?.kind === kind &&
  previous.presentationKey === presentationKey;

// 恢复只改变剪辑状态，展示边界继续存在。
for (const key of rangeKeys) selectedRanges.delete(key);

// 空白恢复还必须约束文字范围的物理静音扩展。
const resolvedTextRanges =
  protectRestoredNoSpeechFromTextRanges([...selectedRanges.values()]);
```

回归测试必须覆盖独立行的静态契约，并在真实浏览器验证：文字与空白按源时间排序；恢复前后行数不变；单独重删只影响目标行；空白恢复后不再被文字静音扩展删除；撤销/重做与刷新持久化正常；播放高亮命中当前片段；375px 无横向溢出且操作目标不少于 44px。

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
