# 技术设计：手动艺术字单轨道

## Architecture And Ownership

`EditorProjectStore.project.art.overlays` 继续是艺术字权威状态。轨道只由 `EditorArtModel.buildTimelineTracks()` 派生，不向 overlay 增加新的持久化轨道字段。

```text
art.overlays
  -> buildTimelineTracks()
       transcript overlay -> art:transcript:<trackId> 轨道
       其他 overlay       -> art:manual 轨道
  -> TimelineController 渲染逻辑轨道
       不重叠 clip -> 共用同一可视 lane
       重叠 clip   -> 同逻辑轨道内的临时可视 lane
```

预览、ArtTool inspector 和 compose 继续直接消费 overlays，不依赖轨道分组。

## Track Derivation Contract

- 手动轨道使用稳定 ID `art:manual`，名称为“手动艺术字”。
- `isTranscriptOverlay()` 为 true 的 cue 继续按各自 `trackId` 放入 `art:transcript:<trackId>`，名称为“视频文案艺术字”。
- 所有其他 overlay，包括 AI 推荐确认后的普通 overlay，都放入 `art:manual`。它们继续以 `art:<overlayId>` 作为 clip ID，并保留原 `sourceId`、时间和 payload。
- Map 在第一次看到某类轨道时插入，以保持现有 overlay 顺序对轨道相对顺序的影响；轨道内 clip 仍按 `start/end` 稳定排序。
- 空手动集合不生成 `art:manual`；删除最后一个手动 overlay 后轨道自然消失。

## Overlap Layout

`TimelineController.renderDocument()` 为每个逻辑轨道做确定性区间分 lane：

1. 按已规范化的 `start/end` 顺序遍历 clip。
2. 将 clip 放入第一个 `laneEnd <= clip.start` 的 lane；没有空闲 lane 时新增一个可视 lane。
3. 同一逻辑轨道内的 clip 共用 `data-timeline-track-index`，并以新的 `data-timeline-lane-index` 表示临时可视 lane。
4. 下一逻辑轨道的顶部偏移是前面所有 lane 数之和；层高和总时间轴高度使用可视 lane 数，因此重叠 clip 不会遮挡。

lane 只是 DOM 排布结果，不写回 Timeline schema、Store 或草稿。selection、拖动、撤销/重做仍通过唯一 clip ID 定位，不依赖 lane。

## Clip Click Position Contract

- 片段主体点击使用完整时间轴 `getBoundingClientRect()` 把 `clientX` 映射为剪后时间；滚动由 rect 的实际 `left` 自然体现，不再按片段起点 seek。
- 只有 `onSelect` 接受选择后才执行一次 seek。拒绝选择时恢复点击前的 selection DOM，且不改变播放位置。
- duration、track width、track left 或 clientX 无效时回退到片段起点；程序化 `selectClip()` 也继续默认 seek 起点。
- resize handle 未拖动时保持原有起点 seek；move/resize 超过阈值后只按瞬时片段边界预览，并在 pointerup 提交一次范围事务。

## Compatibility And Data Flow

- 不修改 overlay 或 Timeline schema 版本，旧草稿不需要迁移。
- 旧草稿的 `art:overlay:<id>` 轨道 ID 只是派生副本；EditorSuite 恢复时已使用 overlays 重建 Art timeline，clip ID `art:<overlayId>` 保持不变，selection 因此仍可恢复。
- ArtTool 中手动 overlay 继续逐项展示和编辑；本任务不把手动轨道变成批量样式操作单位。
- 文字剪辑重对齐和 project frame 派生都继续调用同一 `buildTimelineTracks()`，不增加新适配器。

## Risks And Mitigations

- 重叠遮挡：通过区间分 lane 保留所有按钮的可见性和聚焦性。
- 拖动时 lane 变化：lane 是确定性派生布局，时间区间变更时允许按新重叠关系重排，但选择始终由 clip ID 保持。
- 点击/拖动歧义：位移阈值前按主体点击处理，阈值后进入 move/resize；点击只在选择被接受后 seek 一次。
- 旧断言假设一 overlay 一轨：定向更新 ArtModel、ProjectStore 和草稿恢复测试，其他 kind 保持原行为。
- 缓存旧脚本：同步提升 `editor-art-model.js` 和 `editor-timeline-controller.js` 的资源版本及静态契约。

## Rollback

变更不写数据迁移。回滚 ArtModel 轨道分组、TimelineController lane 排布、资源版本和对应测试即可，草稿与 overlays 无需修复。
