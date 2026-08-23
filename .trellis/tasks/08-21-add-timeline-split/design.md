# 时间轴分割技术设计

## 1. Architecture Boundary

本功能继续使用现有单页编辑器所有权：

```text
app.js cut-domain state
  -> EditorProjectStore (project/cut/timeline authority)
  -> shared MediaController (one video/source/frame clock)
  -> shared timeline + preview
  -> cut-draft PUT (revision authority)
  -> compose (only deletion ranges affect output)
```

分割点是 cut 领域的结构状态，不是第二套媒体或删除状态。基础视频 clip 由 `splitPoints`、源时长和现有删除 spans 纯派生；分割本身不写 video `src`、不 seek、不调用 `load()`，也不改变 compose payload 中的媒体范围。

## 2. Persisted Domain Contract

cut draft `schemaVersion` 按现有增量迁移契约继续保持 `1`，新增可选字段：

```text
splitPoints: Array<{
  key: string,       // stable user-intent id
  sourceTime: number // source-media seconds, millisecond precision
}>

timelineRanges[].boundaryMode:
  "speech_safe" | "split_exact"  // missing => speech_safe

timelineRanges[].splitClipKey?: string
```

服务端对 split points 做有限数校验、媒体时长 clamp、毫秒归一化、按 `sourceTime/key` 排序和 1ms 去重。落在源起点/终点或无法形成最小片段的点不保存。历史草稿缺少字段时恢复为 `splitPoints: []`；旧 timeline range 缺少 mode 时按 `speech_safe`。

相邻边界使用两个稳定 sentinel `source-start` / `source-end` 与 split point key 派生 clip id：`split-clip:<left-key>:<right-key>`。新增分割只改变被拆 clip 的两个 id，其他 clip identity 保持稳定。

`split_exact` range 必须同时满足：

1. `originalStart/originalEnd` 分别匹配相邻 split 边界（允许 1ms 归一化误差）；
2. `splitClipKey` 与这对边界派生的 clip id 一致；
3. 结束严格晚于开始。

校验失败返回 400，不静默降级为 speech-safe。校验成功则物理 `start/end` 等于 `originalStart/originalEnd`，不进入 forced alignment 或 PCM snap，并记录 `split_boundary_exact` 诊断。普通 range 的现有声学路径完全不变。

## 3. Derived Clip Model

纯函数 `deriveCutSplitClips(sourceDuration, splitPoints, deleteRanges, spans)` 负责：

1. 以 `[0, ...splitPoints, sourceDuration]` 建立源时间分区；
2. 用现有删除 spans 计算每个分区的有效剪后时长；
3. 为仍有保留媒体的分区输出稳定 clip，携带 `sourceStart/sourceEnd` 与 `editedStart/editedEnd`；
4. 分割点完全落入删除区间时不显示边界，但不删除持久锚点；恢复删除范围后自动重新派生；
5. 对 `split_exact` 已删除 clip 输出位于剪后拼接点的 tombstone marker，供选择和恢复，不把被删时长重新加入时间轴尺度。

clip 和 marker 进入现有 cut timeline document；DOM 只是 Store frame 的投影。禁止用 DOM 宽度、scrollLeft 或 CSS 百分比反推持久时间。

## 4. Split Command Flow

```text
click #cutTimelineSplitButton
  -> getCutPlaybackFrameState().sourceCurrent
  -> validate: media exists + point inside retained derived clip
  -> reject endpoints/existing boundary/deleted area/min-duration violation
  -> capture one history before snapshot
  -> add one stable splitPoint
  -> dispatch CUT_STRUCTURE_CHANGED once
  -> one visible commit + one draft-save intent
  -> render derived clips, keep playhead and duration unchanged
```

按钮的 disabled 状态由同一验证函数计算，命令执行时再次验证以防帧状态变化。结构 action 增加 project `revision` 一次，但显式保持 `timingRevision` 不变；它不触发 Art/PiP cut timing reconciliation。服务端保存响应只更新 `cutDraftRevision` 时沿用 metadata-only no-op，不产生第二个用户事务。

## 5. Selection, Delete And Restore

- 可见 split clip 是可聚焦按钮；pointer/click 只选择 clip 并 seek 到点击位置，不进入自由拖选删除 handler。
- 标题区提供选中片段的图标删除操作并支持 `Delete`/`Backspace`；执行前复用现有 `appConfirm`。
- 确认删除后新增一个 `timelineRange`，范围严格等于 clip 的源边界，携带 `boundaryMode: split_exact` 和 `splitClipKey`。它与普通 timeline ranges 一起进入 `getMergedSelection()`、preview、草稿保存和 compose。
- 删除后的 clip 不占剪后时长；其拼接点显示可聚焦 marker。选择 marker 后使用恢复图标或 `Delete`/`Backspace` 移除对应 exact range。
- 相邻 deleted markers 若映射到同一拼接点，视觉上分层排列，点击目标与 aria label 仍逐项可辨；不合并语义 range，以保证逐片恢复和逐事务 undo。
- 分割点、timeline ranges 和命令前后 selection 一起进入现有 cut history snapshot。单纯切换选择不创建 history；split/delete/restore 各创建一个事务。刷新恢复结构和删除状态，瞬时 selection 默认清空。

## 6. Store And Timing Semantics

`EditorProjectStore` 新增 `CUT_STRUCTURE_CHANGED`：

- `normalizeCut()` 规范化并保留 `splitPoints`；
- structure action 同步 `project.cut` 和 cut timeline tracks，但不修改 cut ranges/duration/transcript；
- `revision += 1`，`timingRevision += 0`；
- 结构变化不调用 `EditorArtModel.reconcileArtWithCut()`；
- 删除/恢复 clip 仍经 `CUT_TIMING_CHANGED`，因为 output duration 和 source/edited mapping 已改变。

`projectTimingSignature` 不把 split point 或仅由分割产生的 clip partition 当作媒体时序改变。公共 timeline selection 继续使用稳定 clip id；Store 拒绝等价 action 后不得继续重绘或覆盖状态反馈。

## 7. Draft, History And Save Queue

- `buildPersistedCutDraftPayload()`、本地草稿、restore、semantic snapshot/signature 和 cut history snapshot 全部纳入 `splitPoints`。
- timeline range 的 semantic signature 纳入 `boundaryMode` 与 `splitClipKey`，但仍只使用 `originalStart/originalEnd`，不加入服务端派生 `start/end`、revision、诊断或时间戳。
- latest-state-wins、单 in-flight、acknowledged revision rebase 和生成前 `flushCutDraftSave()` 契约不变。
- split command 的本地恢复快照立即写入，服务端 PUT 继续约 300ms trailing debounce。纯分割也必须保存，因为刷新需要结构状态。

## 8. UI And Accessibility

- 在 `.cut-frame-timeline-heading` 右侧建立紧凑 action group，`#cutTimelineSplitButton` 使用现有 Iconify `ph:scissors-bold`，可见文字为“分割”，最小点击面积 44px。
- 时间输出与操作组使用稳定 grid/flex 约束；375px 下允许时间换行，但按钮不覆盖轨道、状态或溢出容器。
- 新增 `#cutFrameTimelineClips` overlay：边界线、选中描边和 deleted marker 不改变缩略图布局，也不遮挡播放头。
- 无效分割使用原生 `disabled`、准确 `aria-label` 和已有 live status；图标按钮有 title/tooltip。focus-visible、键盘选择、删除和恢复均可完成。
- 更新所有变更静态资源的 `?v=` cache-buster，并同步静态资源契约测试。

## 9. Compatibility, Rollback And Risks

- 历史草稿和无 split 字段的 localStorage/history 继续恢复为空结构；`schemaVersion` 保持 `1`，普通 timeline range 的响应形状和声学结果不变。
- compose 无需接收 split points；纯分割生成结果应与分割前字节语义一致。只有删除 split clip 后，compose 才消费新增 exact timeline range。
- 回滚可先隐藏/断开 split UI，但必须同时停止写入新结构；后端保留对可选字段的读取不会影响旧客户端。若回滚服务端，部署前需确认没有新客户端继续写 split points，避免旧服务静默丢字段。
- 主要风险是 source/edited 坐标混用、结构 action误增 `timingRevision`、自由拖选与 clip 点击冲突、精确 mode 被声学路径再次移动，以及连续 deleted markers 重叠。每项均需要 Node/后端契约测试和真实浏览器覆盖。
