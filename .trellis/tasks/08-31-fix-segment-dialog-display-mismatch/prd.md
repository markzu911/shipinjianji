# 修复文案展示片段与编辑弹窗不一致

## Goal

点击因删除范围拆出的文案展示片段时，编辑弹窗必须显示并操作用户实际点击的文字和时间范围，不能把同一父段内已删除或未显示的文字带入弹窗，也不能因重复短语修改错误实例。

## Background

- 截图中列表展示片段为“你身边人人都觉得一个月赚一万就顶天了，”，弹窗却显示其父可编辑段的完整文字“你身边你身边人人都觉得你身边人人都觉得一个月赚一万就顶天了，”。
- `web/app.js:737` 的 `buildSegmentTextRuns()` 会按删除状态把一个 `currentEditableSegments` 项拆成多个独立展示行。
- 展示行已持有 `data-display-text`、`data-semantic-start/end` 和父 `data-segment-index`，但 `web/app.js:1522` 的 `openSegmentEditDialog(segmentIndex)` 只按父索引读取 `currentEditableSegments[segmentIndex].text` 和整段时间。
- 因此这是展示片段与编辑命令粒度不一致的通用问题，不是本次性能优化的 keyed reconciliation 复用了错误节点；稳定 key 已包含 segment index、展示范围和 presentation key。

## Requirements

- R1：点击普通保留展示行时，弹窗文字和时间必须与该行的 `data-display-text`、`data-display-start/end` 一致；完整父段行保持现有行为。
- R2：展示片段身份必须由当前父段、token 字符偏移和语义范围共同确定；禁止用 `indexOf(displayText)` 定位，避免重复短语命中第一处错误实例。
- R3：保存局部展示片段时，只替换父段内对应字符区间，前后未显示文字逐字保持不变，再复用现有 `/editable-segments` 文字保存、Store、艺术字、时间轴、草稿和预览同步链路。
- R4：在局部展示片段中选择文字并拆分时，把 textarea 内偏移换算为父段字符偏移后调用现有拆分接口；不得增加第二套后端结构协议。
- R5：若 token 与父段文字不能证明字符守恒，必须拒绝打开局部弹窗或执行局部写入并提示刷新，禁止回退显示整个父段，也禁止凭模糊文本匹配覆盖数据。
- R6：删除/恢复、播放按钮、VAD/PCM 物理边界、草稿 revision、撤销/重做和 keyed reconciliation 行为保持不变。
- R7：静态资源版本必须更新，避免浏览器继续运行旧点击消费者。
- R8：局部展示片段执行合并时，只允许向没有已删除文字阻隔的一侧合并。服务端在同一次操作内先把父段中未显示的前缀/后缀隔离，再把当前片段与目标相邻段合并；被删除文字继续作为独立段保留删除、恢复和撤销能力，不能进入合并结果，也不能产生半完成的中间持久化状态。

## Acceptance Criteria

- [x] AC1：同一父段被部分删除后，点击保留展示片段，弹窗文字与该行完全一致，时间等于该行剪后显示范围；完整父段点击结果不变。
- [x] AC2：父段包含两处相同短语时，打开、保存或拆分第二处展示片段只影响第二处，第一处及已删除文字保持不变。
- [x] AC3：局部保存后，文案列表、弹窗再次打开、公共时间轴、Store cut transcript、艺术字轨道、预览和 compose 文本字符守恒。
- [x] AC4：局部拆分请求使用父段绝对字符偏移，返回的新段落文字和边界正确；基础 video `srcWrites/loadCalls` 和 thumbnail extractor 新增次数均为 0。
- [x] AC5：字符映射不可信时不执行局部覆盖，并给出稳定反馈；无静默错改。
- [x] AC6：相关 Node/前端契约、真实 Chromium 工作流、JavaScript 语法和 `git diff --check` 通过，无新增 console/page/request error。
- [x] AC7：局部片段贴着父段末尾时可“向下合并”，贴着父段开头时可“向上合并”；已删除前缀/后缀被原子隔离并保持可恢复。删除文字位于当前片段与目标方向之间时，对应合并按钮禁用，不允许跨越删除文字产生重叠段落。

## Out of Scope

- 不修改 ASR、VAD、PCM、强制对齐或最终 FFmpeg 删除边界。
- 不改变 AI 建议、删除范围、空白行或时间轴手动删除的业务语义。
- 不重写可编辑段后端模型，不新增另一套持久化 schema。

## Key Decisions

- 弹窗和命令以用户点击的展示片段为目标；父 `segmentIndex` 只用于找到权威段，不能决定弹窗显示整段。
- 被删除文字从本次合并目标中隔离，但不从 transcript、删除记录或历史中永久移除。
- 使用现有 `/editable-segments` 请求中的 `selectionStart/selectionEnd` 扩展 text/merge 语义，保持一次请求、一次并发版本校验和一次持久化。
