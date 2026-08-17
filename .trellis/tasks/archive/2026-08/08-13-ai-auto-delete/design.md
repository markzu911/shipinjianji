# Technical Design

## Architecture and Boundaries

本次改动保持后端 AI 分析和剪辑生成契约不变，主要落在原生前端三层：

1. `server/app.py`：在剪辑草稿请求与持久化对象中兼容保存 `automaticNoSpeechInitialized`，缺省值为 `false`。
2. `web/index.html`：移除 AI 建议、空白剪辑和操作记录页签/面板，检查器直接展示文字剪辑。
3. `web/app.js`：继续解析 `result.suggestions` 和 `result.noSpeechSuggestions`，仅用于首次自动建立 `selectedRanges` / `selectedNoSpeechRanges` 以及稳定展示边界；删除两套独立建议确认 UI。
4. `web/styles.css`：检查器使用单面板全高布局，并为文字删除与空白删除独立行提供复用现有 token 的恢复样式。
5. `web/editor-suite.js`：内嵌工具能力不再依赖已删除的文字页签栏；继续由文字面板栈与 iframe 宿主在视频剪辑、艺术字和画中画之间互斥切换。

`selectedRanges` 与 `selectedNoSpeechRanges` 继续分别是文字和空白删除的现有主状态。最终生成、公共时间轴、剪后时间和草稿 API 不引入第二套“自动删除”集合。

## Data Flow

### Initial Load

`renderResult(job)` 按以下顺序初始化：

1. 清空当前选择和历史运行态，解析/验证 `result.suggestions` 到内部 `currentSuggestions`。
2. 调用 `resolvePersistedCutDraft(job.cutDraft ?? null, job.id)`，同时保留返回值是否为真实草稿对象的信息。
3. 若返回草稿对象，调用 `restorePersistedCutDraft` 精确恢复全部范围与 `automaticNoSpeechInitialized`，包括空数组；若返回值为 `null`，先播种有效 AI 文字建议。
4. 当 `noSpeechStatus === "completed"` 且草稿标记不为 `true` 时，在当前选择上补入 `deletable !== false` 的空白检测结果，不清空或覆盖已恢复的文字、空白和时间轴范围，然后将标记设为 `true`。
5. 渲染文字和汇总，建立撤销历史基线，开启 `cutDraftReady`。
6. 若本次播种了默认范围、推进了空白初始化标记或需要同步较新的本地草稿，清空初始签名并调度保存，使自动选择与标记成为服务端/本地可恢复草稿；保存不调用生成接口。

必须先自动标记再建立历史基线。这样首次建议是当前项目的初始剪辑状态，用户执行“恢复”后产生一条可撤销操作，而不是让 Ctrl+Z 回到一个从未呈现给用户的加载中状态。

### Restore Deleted Text

`renderCutSegments` 将每个可编辑段的 words 同时与 `selectedRanges` 和原始 AI 建议范围匹配，按边界生成稳定的展示片段。保留片段、已删除片段和后续保留片段分别渲染成独立 `li`；每行保存来源 segment index、片段 start/end 和对应 range keys。

原始 AI 建议范围继续作为纯展示边界，即使用户恢复该范围也不移除边界。这样恢复只改变该行的删除状态，列表不会重新把它拼回前后内容。剪辑主状态仍只有 `selectedRanges`，展示边界不参与保存和生成。

事件委托优先处理恢复按钮：

1. 校验未锁定且 key 仍存在。
2. `stageCutHistoryOperation("恢复删除文字")`。
3. 从 `selectedRanges` 删除对应 key。
4. `updateSelectionSummary()`，由现有链路统一更新文本、时间、预览、时间轴、下游状态、历史和草稿。

未命中恢复按钮时，仍执行现有“点击文字打开分段编辑”逻辑。整段左侧删除按钮行为不变。

### Blank Rows

`renderCutSegments` 将文字展示片段与 `currentNoSpeechSuggestions` 映射为统一的展示记录，按 `start/end` 排序后逐行渲染。空白行携带 `data-no-speech-id`、`data-display-start/end` 和稳定 `data-display-key`，不伪造可编辑 segment index。

空白建议始终保留为展示边界：`selectedNoSpeechRanges` 中存在对应 id 时显示为已删除并可恢复；恢复后仍保留普通空白行，左侧圆圈可重新删除，正文可试听。时间戳、播放高亮和窄屏布局复用文字行容器，不保留独立空白卡片列表。

### Draft Semantics

- `null`：从未建立剪辑草稿，允许自动播种 AI 文字建议；空白分析完成时同时播种可删除空白并保存初始化标记。
- object + 缺少 `automaticNoSpeechInitialized` 或值为 `false`：历史草稿，先精确恢复全部范围，再一次性补入可删除空白并保存标记。
- object + `automaticNoSpeechInitialized: true`：空白默认值已经建立，精确恢复 `noSpeechRanges`；显式空数组表示用户已恢复全部空白。
- object + `textRanges: []`：已有明确文字草稿，始终禁止再次播种 AI 文字建议。

本地草稿比服务端新时继续优先，并触发服务端同步。恢复一个 AI 范围会保存新的显式草稿；即使所有范围均为空，仍以正常 PUT 保存空数组，不调用 DELETE 清除整个草稿。

## UI and Accessibility

- 文字剪辑是检查器内唯一可见面板，不渲染单一页签栏或历史工具栏；桌面与移动端都占满可用检查器高度。
- 内部撤销/重做栈仍在每次语义剪辑操作后更新并持久化，但只通过 `Ctrl/Cmd+Z`、`Ctrl/Cmd+Shift+Z` 和 `Ctrl/Cmd+Y` 访问。
- 全局快捷键处理器在事件目标为输入框、文本域、选择框或可编辑节点时立即返回，保留浏览器原生编辑历史。
- 删除范围呈现为独立列表行中的 `button`，视觉使用现有危险色、删除线和轻量边界，不做卡片嵌套。
- 每个展示片段使用自己的源时间范围；已删除行仍显示原片起始时间，保留行显示剪后时间。
- 每条文字行末尾使用独立的纯图标播放按钮；按 `data-display-start/end` 定位公共预览，已删除行试听期间仅在当前展示范围内暂停自动跳过删除区间。
- `aria-label` 使用“恢复已删除文字：…”；按钮支持 Enter/Space 的原生行为。
- `:focus-visible` 提供至少 2px 明确描边；hover/pressed 只改变颜色、边界和背景，不改变布局尺寸。
- 窄屏按钮通过内边距/行高保证 44px 最小触控高度，允许文字自然换行，避免横向滚动。
- 空白行正文使用“空白 N.N 秒”作为主标签，并附带片头/片尾/中段与音频状态；已删除和已恢复状态不能只靠颜色区分。
- 不增加页面内教学文案。删除线和可点击样式本身表达状态，操作后的现有历史/保存状态提供反馈。
- 艺术字位置输入以百分比投影既有 overlay `x/y`；有效输入实时调用 `updateSelectedOverlay`，回车或失焦负责最终 clamp，拖动和套用预设通过统一渲染链路反向同步输入值。
- 坐标输入在“位置预设”内使用双列 `number` 控件和独立 `%` 单位，范围 `5–95`、步长 `0.1`；控件高度不少于 44px，375px 仍保持双列且不溢出。

### Inline Tool Continuity

`supportsInlineWorkspace()` 只检查稳定的工作台节点：cut stage、检查器、文字面板栈、iframe 宿主、公共 overlay、时间轴层和预览视频。文字页签栏已从产品中删除，不能继续作为能力开关。

`renderActiveTool()` 在 `cut` 状态显示 `.text-editor-panel-stack`，在 `art` / `pip` 状态隐藏该栈并激活对应 iframe panel；URL 只通过 History API 更新 `tool` 参数。独立页面 URL 仍作为 iframe 来源和直接访问兜底，但主工作台具备稳定节点时不得导航离开。

## Compatibility

- 后端建议响应字段和草稿 `schemaVersion: 1` 不变；新增可选布尔字段 `automaticNoSpeechInitialized`，旧客户端省略时服务端按 `false` 保存。
- 历史任务若没有草稿，会在首次打开新版页面时自动建立建议草稿，这是预期的新行为。
- 历史任务已有草稿时先保持原选择；仅在缺少空白初始化标记时补入可删除空白并原地升级草稿，不批量改写磁盘数据。
- 标记写入后，空白选择为空也是明确用户状态，不再重新播种。
- `ignoredSuggestions` 是仅存在于旧 AI 建议页的临时 UI 状态，没有持久数据迁移需求。
- HTML/CSS/JS 静态资源版本按项目规范递增，并同步静态资产契约测试。

## Risks and Mitigations

- 风险：恢复某个词时误删整段选择。缓解：恢复按钮绑定 Map key，不使用段落 start/end。
- 风险：刷新重新应用 AI 删除。缓解：以草稿对象存在性而非 range 数量作为播种条件，并立即保存初始空/非空状态。
- 风险：历史草稿每次刷新都重新应用空白删除。缓解：初始化条件只读取持久化布尔标记，补入范围后在同一次草稿 PUT 中将标记推进为 `true`。
- 风险：音频扩展后视觉 range 与 Map key 不同。缓解：key 始终使用原始建议 range，命中逻辑使用 `originalStart/originalEnd`，剪辑使用扩展后的 `start/end`。
- 风险：移除 DOM 后顶层必需 selector 为空导致脚本启动失败。缓解：删除对应 selector、渲染、锁定和事件代码，而不是留下半可选代码。
- 风险：自动标记多条建议导致历史噪音。缓解：自动播种作为初始基线，不单独写入撤销历史；用户后续恢复才产生历史项。
- 风险：删除可选 UI 节点后共享协调器误判内嵌工作台不可用并跳转独立页面。缓解：能力检测只依赖稳定容器，静态测试禁止引用已删除 selector，浏览器覆盖 art/pip/cut 三向切换。

## Rollback

产品代码改动集中在 `web/index.html`、`web/app.js`、`web/styles.css` 和前端契约测试。若回滚，可恢复旧建议渲染事件并移除初始自动播种与局部恢复按钮；操作记录 UI 与内部历史逻辑相互独立，不涉及服务端数据迁移。
