# 修复实时编辑器时间轴、面板和艺术字时间

## Goal

保持文字剪辑、艺术字和画中画在同一页面、同一原视频播放器和同一虚拟剪后时间轴上实时工作；修复重复文案轨、工具面板状态错位，以及艺术字被静音检测或原片/剪后坐标混用导致的时间错误。

## Background

- `#cutFrameTimelineText` 已显示剪后文案，`EditorTimelineController` 又把 Store 中的 `cut` 轨渲染进 `#editorSuiteTimelineLayer`，因此出现两条相同文案轨。
- B2 迁移前的独立艺术字页面只有“艺术字设置”和“AI 推荐”两个顶层 tab，“视频文案”是设置流程内的功能；迁移后的 `EditorArtTool` 错把它提升为第三个 tab。切换 tab 时同一滚动容器还会保留旧位置，未选择 overlay 时仍显示整套禁用表单。
- 画中画文案列表拥有独立滚动条，重绘或选择回退后没有同步可视位置，可能出现顶部显示 `00:00.2-00:02.2`、列表却停在 `00:30` 的状态。
- 当前样本原片中“我”开始于 `7.29s`，删除 `0-4.08s` 后应开始于约 `3.21s`。音频静音区间 `8.04-14.12s` 与句尾 word 重叠后，现有字符时间重排把“我”提前到 `3.1101s`。
- 全文艺术字接口已经提交实时 `draftTranscript/draftDuration`；AI 推荐接口尚未提交草稿，仍可能按原片 transcript 和 184 秒时长生成建议。
- 拆分前的 `art-text.js` 会在每次 cut draft 变化后重建全文艺术字轨道，并按文案与 source anchors 重映射或隐藏普通艺术字；旧运行时删除后，这段同步逻辑没有迁入 `EditorProjectStore`，当前 `CUT_TIMING_CHANGED` 只更新 cut 与 cut timeline，导致已添加艺术字不会随文案删除而删减。

## Requirements

- R1：文字删除后立即更新虚拟剪后时间轴；艺术字和画中画可直接添加、预览、拖动和调整时间，不得要求先生成剪后视频。
- R2：页面只显示一条剪后文案轨。`#cutFrameTimelineText` 是唯一文案展示轨；`#editorSuiteTimelineLayer` 只渲染艺术字和画中画效果，但 Store 继续保留完整 `cut/art/pip` 语义轨道。
- R3：艺术字只保留“艺术字设置”和“AI 推荐”两个顶层 tab；设置面板只提供“一键添加视频文案”入口，默认使用“热血立体”模板。文案编辑、保存文案、文案分段列表和“添加所选文案”继续由文字剪辑页面负责，不得在艺术字面板重复出现。切换后内容从稳定位置开始；未选择艺术字时显示空状态而不是空白禁用表单。
- R4：画中画文案选择、顶部时间范围和列表可视位置始终一致；重绘不得让外层面板发生意外滚动。
- R5：有效的 `segments[].words` 和已有字符时间是艺术字同步的权威。静音区间不得重排或压缩与 word 时间重叠的字符；静音只可作为缺失可靠时间时的降级参考。
- R6：AI 艺术字推荐必须接收当前 `draftTranscript/draftDuration`。草稿存在时，建议 `start/end` 使用剪后时间；从原视频提取关键帧时通过 `sourceStart/sourceEnd` 使用原片时间，并以对应剪后时间标注给模型。
- R7：确认 AI 建议或手动贴合文案后，overlay 保存剪后 `start/end` 和原片 `sourceStart/sourceEnd`。短语匹配使用 word/字符级边界；重复短语选择距离当前时间最近的候选，不默认第一处整段。
- R8：预览、公共时间轴和 compose 继续消费同一个 `EditorProjectStore` frame，不新增播放器、iframe、页面、私有时间轴或中间视频。
- R9：既有无剪辑任务、已生成 edit、历史艺术字草稿和旧 AI 请求字段继续兼容。
- R10：`CUT_TIMING_CHANGED` 必须在同一次 Store 事务中同步艺术字。全文文案艺术字按最新剪后 transcript 的字符/word 边界重建，删除文字对应的 cue 或 cue 内容立即消失；具有文案/source anchors 的普通艺术字按保留内容重映射，完全落入删除区间时暂时隐藏；无文案关联或无可靠锚点的自定义艺术字保持不变。撤销删除时，被暂时隐藏的艺术字必须可恢复；预览、效果时间轴、草稿和 compose 只消费同步后的同一 frame。

## Acceptance Criteria

- [ ] AC1：删除 `0-4.08s` 后，无需生成视频即可进入艺术字/画中画，基础 video 节点、source key、播放状态和 document identity 保持不变。
- [ ] AC2：公共时间轴 DOM 中剪后文案只出现一次；效果层没有 `data-effect-kind="cut"`，art/pip clip 仍可选择和调整。
- [ ] AC3：桌面和 375px 下艺术字顶层 tab 只有“艺术字设置”和“AI 推荐”，不存在第三个“视频文案”tab；设置面板只显示“一键添加视频文案”，默认模板为“热血立体”，不显示文案输入、保存、分段列表或“添加所选文案”。切换 tab 后首个有效内容不被 sticky tabbar 遮挡；无 selection 时不显示空白输入矩阵。
- [ ] AC4：画中画列表重绘、切换工具和 selection 回退后，选中项在列表可视区域内，顶部时间与其 `start/end` 一致，外层面板不被 `scrollIntoView` 带动。
- [ ] AC5：样本“我也这么想”的剪后开始时间为约 `3.21s`，允许时间舍入误差 `0.01s`；与句尾重叠的静音区间不会把它改为 `3.11s`。
- [ ] AC6：AI 推荐请求携带实时草稿；后端提示词和建议范围使用剪后时间，关键帧从对应原片时间提取，确认后 overlay 具有完整 source anchors。
- [ ] AC7：“贴合匹配文案时间”对段内短语返回首尾字符边界；相同短语出现多次时命中距离当前 overlay 最近的一处。
- [ ] AC8：相关 Node/API/静态测试、完整 `tests/app/`、完整浏览器工作流通过；桌面和 375px 无横向溢出、页面错误、额外 video 或 iframe。
- [ ] AC9：先添加全文文案艺术字，再删除一个字符、一个完整 cue 和跨 cue 文案时，预览、时间轴和 compose 中对应艺术字立即删减且其余文字时间正确前移；撤销后恢复。具有 source anchors 且完全被删除的普通艺术字暂时消失，未关联文案的自定义艺术字不受影响。

## Out Of Scope

- 不提前生成 `edited.mp4` 或其他中间视频供艺术字、画中画使用。
- 不更换 ASR、VAD、AI 多模态模型或引入前端框架、播放器组件。
- 不重写 EditorProjectStore、时间轴模型或 FFmpeg 合成架构。
- 不修改生产环境或推送远程仓库。

## Key Decisions

- UI/overlay 的 `start/end` 统一为剪后时间；`sourceStart/sourceEnd` 仅保存原片锚点。
- 静音检测不能覆盖可靠的文字语义时间；修复必须删除全段重排原因，不能使用固定 `+0.10s` 补偿。
- AI 实时草稿继续分析原视频画面，但原片取帧时间与剪后显示标签分离。
- 公共 frame 保留完整语义 timeline，只在效果时间轴 controller 的显示投影中排除 `cut`。
- cut-to-art 同步属于 Store/model 语义层，不放回 ArtTool UI 事件或建立第二份艺术字状态；隐藏项保留可逆的原始锚点，供撤销恢复。

## Open Questions

无阻塞问题。
