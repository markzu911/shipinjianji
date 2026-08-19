# 技术设计

## Architecture

继续使用当前唯一运行时：`app.js` 构造实时 cut draft，`EditorProjectStore` 保存项目语义状态，`selectEditorFrame()` 一次派生 media/preview/timeline/composition，唯一 `MediaController` 在原视频上按删除范围完成实时跳播。艺术字和画中画始终写入剪后时间，不产生中间视频。

## Timeline Rendering

`frame.timeline` 继续包含 `cut/art/pip`，避免破坏 Store、selection、compose 和 controller 提交基线。`EditorTimelineController.createController()` 增加可选的可见 kind 配置，EditorSuite 为公共效果层传入 `art/pip`。controller 的 DOM 行数、高度和交互节点只按可见轨计算，内部权威 document 仍是完整 frame timeline。

这比删除 Store 的 cut 轨或建立第二份 timeline selector 更安全：文案轨仍由 `#cutFrameTimelineText` 唯一展示，effect controller 仍能基于同一 revision 提交 art/pip 事务。

## Art And Pip Inspector UI

- `.editor-art-tool-tabs` 恢复与合并前一致的两个顶层 tab，不再为其覆盖三列布局；设置面板只保留“一键添加视频文案”按钮，默认使用 `impact`（热血立体）。文案 textarea、保存按钮、分段列表和选段添加属于文字剪辑页面，不在 ArtTool 重复提供。
- 两个 tab 切换时重置 ArtTool 自身滚动容器，不改变页面或设置面板内部功能状态。
- settings 面板增加 selection 空状态；`data-art-controls` 在无 selection 时隐藏并禁用，有 selection 时恢复。
- PipTool 重绘后只调整 `[data-pip-segments]` 自身 `scrollTop`。选中项失效并回退第一项时归零；已有 selection 时按容器坐标执行最小滚动，不调用可能影响祖先的 `scrollIntoView()`。

## Cut-To-Art Reconciliation

`CUT_TIMING_CHANGED` 在 reducer 提交新 cut 之前，以 previous cut、next cut 和当前 art state 调用 `EditorArtModel` 纯函数完成同步，并在同一 revision 中同时写回 `project.cut`、`project.art` 与对应 timeline。`selectEditorFrame()` 不做二次修正，确保 preview/timeline/composition 一致。

- 全文文案轨以当前剪后 transcript 的字符单元为权威。复用现有 cue 样式和稳定 source anchor，在本地按最新字符/word timing 构造 cue；被删除字符不得继续留在 cue 文本或 `characterTimings` 中，空 cue 删除，保留 cue 使用新的剪后 `start/end`。
- 普通 overlay 仅在具有可靠文案匹配或 source anchors 时参与同步。仍能匹配当前文案时使用最近字符边界更新双坐标；完全落入删除 source 区间时进入可逆 suppressed 集合；部分保留时映射到新的剪后范围。没有可靠关联的自定义 overlay 不变。
- suppressed overlay 不进入活动 `art.overlays`、效果 timeline 或 compose，但以项目内部非合成状态保留。cut 撤销后再次 reconcile 可恢复，不能依赖刷新或服务器重新生成。
- selection 指向被隐藏 cue 时清空或落到同轨最近可见 cue；持久化草稿保存活动 overlay 和恢复所需的 suppressed 数据，旧草稿没有该字段时按空集合兼容。

## Transcript Timing

`transcript_art_text_character_timings()` 从有效 word/已有字符时间直接构造字符边界。音频 quiet range 不再把整段字符按“有声总时长”重新投影；这符合项目已有“媒体吸附不得反写文字语义”的契约。

`align_text_overlays_to_audio_activity()` 的其他调用保持兼容，本次只移除全文艺术字 word/字符同步路径中的全段压缩。历史 overlay 已保存的 `characterTimings` 不迁移，新生成轨道使用修复后边界。

## Live AI Suggestions

`ArtTextSuggestionRequest` 增加可选 `draftTranscript` 和 `draftDuration`，字段兼容旧客户端。前端在请求 AI 推荐时提交 ArtTool 当前 `transcript()` 与 `duration()`。

后端草稿分支执行与全文轨道一致的结构、数量、文本长度、有限时间校验：

- 建议和提示词时间基准：剪后 `start/end`、`draftDuration`；
- 分析媒体：原视频，不生成 edited 文件；
- 取帧时间：优先使用 segment/word `sourceStart/sourceEnd`；
- 拼图和提示词标注：对应的剪后时间，避免模型返回原片秒数。

关键帧采样由 `{mediaTime, displayTime}` 对表达，FFmpeg 使用 `mediaTime`，拼图标签和模型提示使用 `displayTime`。没有 source anchors 的旧 transcript 沿用原有单时间值路径。

确认建议时，前端通过唯一 MediaController 的 `editedToSource()` 补齐 `sourceStart/sourceEnd`，因此 Store、草稿和 compose DTO 均保留双坐标。

## Phrase Matching

在 `EditorArtModel` 增加纯函数匹配器：

1. 按 `words -> segment` 生成去空白/标点的字符单元，每个字符拥有 edited 和可选 source 边界；
2. 查找目标短语的全部出现位置；
3. 以与当前 overlay `start` 的距离排序，稳定选择最近候选；
4. 返回首字符 start、末字符 end 及 source anchors；
5. 无精确字符匹配时才回退到包含当前时间的整段。

ArtTool 的“贴合匹配文案时间”只调用该纯函数并通过既有 `setArtRange()` 提交一次语义事务。

## Compatibility And Rollback

- 新 API 字段全部可选，旧请求保持原行为。
- 旧艺术字草稿没有 suppressed/reconciliation 元数据时按普通活动 overlays 加载；无可靠 source anchors 的自定义艺术字保持原状。
- 无 cut draft 时 `mediaTime === displayTime`，现有 AI 推荐结果不变。
- controller 可见 kind 配置缺省时渲染全部轨道，避免影响现有 Node 测试或其他消费者。
- 修复按 timing、AI draft、timeline、UI 四个小提交块实现；任一块可独立回滚。

## Risks

- AI 联系表的时间标签与 FFmpeg seek 时间分离后容易再次混用，必须用结构化 frame sample 和单元测试锁定。
- 中文标点、重复短语和跨 word 文本匹配需要保留字符索引映射，不能只对 normalized 字符串切片后猜时间。
- UI 滚动修复不得调用祖先级 `scrollIntoView()`，否则会重现面板跳动。
