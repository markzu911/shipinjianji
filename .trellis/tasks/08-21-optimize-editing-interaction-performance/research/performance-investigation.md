# 剪辑交互性能排查

## 结论

删除段落的卡顿来自同一交互中叠加的四条路径：同步全量派生/渲染、删除后缩略图重新解码、重复 Store 协调和无防抖的服务端声学校准。优先消除缩略图重建、重复 hydrate 和保存放大，再根据有代表性的浏览器 fixture 决定是否需要列表虚拟化或 Store 结构重写。

## 调用链

```text
segmentList click
  -> mutate selectedRanges / selectedNoSpeechRanges
  -> updateSelectionSummary()
       -> invalidateCutPlaybackStructure()
       -> recordCutHistoryIfChanged() -> synchronous localStorage
       -> getMergedSelection()
       -> renderCutSegments() -> replaceChildren(all rows)
       -> syncEditorSuiteCutDraftState()
            -> CUT_TIMING_CHANGED
            -> renderEditorFrame(all consumers)
            -> renderJobState(currentJob) -> PROJECT_HYDRATED attempt
       -> refreshCutTimeline()
            -> render ruler/text/ranges
            -> buildCutTimelineThumbnails()
                 -> new video + N seeks + Canvas JPEG
       -> scheduleCutDraftSave()
            -> localStorage
            -> PUT full draft
                 -> decode full PCM
                 -> align all ranges
            -> apply alignment -> possible second updateSelectionSummary()
```

## Measurements

| Probe | Fixture | Result |
| --- | --- | --- |
| ProjectStore cut action | 634 chars, 18 transcript segments, 100 dispatches | median 11.27ms, P95 15.70ms, max 24.60ms |
| Full PCM decode | existing 68MB source media, 3 runs | median 190ms |
| Text range alignment with PCM loaded | 32 ranges, 18 segments, 3 runs | 429-457ms |
| Existing browser workflow | isolated one-second fixture, delete/save/reload test | passed; test call 2.34s, not an isolated click benchmark |

The Store probe excludes DOM layout, media seek, preview playback and localStorage. The backend probe is read-only and excludes HTTP/JSON/disk draft write overhead.

## Root Causes

### 1. Thumbnail cache key includes selection

`buildCutTimelineThumbnails()` includes the merged deletion signature, so every semantic cut invalidates every frame even when the source media is unchanged. A generation id prevents some stale writes but does not actively cancel the current extractor before its next await boundary.

### 2. Selection summary is an orchestration monolith

`updateSelectionSummary()` owns state derivation, history, UI, cross-tool synchronization, timeline structure, thumbnail effects and persistence. Work that is not needed for immediate feedback runs inside or immediately after the click task.

### 3. Cut synchronization re-enters job hydration

`setCutDraft()` correctly dispatches `CUT_TIMING_CHANGED`, then calls `renderJobState(currentJob)` with hydration enabled. Even when the reducer rejects an equivalent hydrate, it has already cloned and compared large state.

### 4. Persistence amplifies frequent operations

The browser saves full history synchronously and enqueues server saves without a trailing debounce. The server acoustic alignment cache stores character evidence but not decoded PCM, so every PUT launches FFmpeg for the same source.

## Constraints

- `originalStart/originalEnd` remain user semantics; physical `start/end` remain server-aligned media boundaries.
- Preview and compose must use the same saved physical ranges and revision.
- `flushCutDraftSave()` must drain edits that arrive during an in-flight save.
- A cache optimization cannot reuse a boundary when adjacent deletion state could change repeated-transition trust or retained-character protection.
- The single-page editor must retain one Store, one MediaController and one timeline authority.

## Recommended Order

1. Add deterministic browser probes and a representative long transcript fixture.
2. Make thumbnail extraction source-keyed, reusable and actively cancellable.
3. Coalesce view refresh, remove the duplicate hydrate and idle-save history.
4. Debounce/coalesce server draft writes while preserving flush semantics.
5. Add bounded PCM caching on the server.
6. Re-measure before considering keyed transcript reconciliation, virtualization or Store structural sharing.

## 2026-08-21 当前代码兼容性审计

优化方向仍对应当前瓶颈，但在最新声学边界和 ArtTool 改动后，原计划不能不经修订直接执行。

### 规划修正

1. 草稿稳定条件改用排除服务端派生 text/timeline 物理 `start/end` 的语义签名。队列分别跟踪在途请求 revision 和服务端确认 revision。旧 desired 的响应可以推进 revision，但不能应用其物理范围；下一次 latest-state 请求使用该新 revision 重建。
2. frame 合并只合并渲染和副作用。每个用户命令同步捕获自己的 before/after 历史事务，因为当前单个 `cutHistoryPendingMeta` 无法表达一次 rAF commit 前发生的两个命令。
3. 可见延迟测量结束于 commit 后的第二个 rAF，并验证目标 DOM 状态。只测第一个 rAF 回调入口会漏掉回调内的完整列表、Store 和时间轴工作，不能代表真实可见反馈。
4. PCM 缓存等价性明确覆盖完整段落跨段场景、“得/你”、“一起给”、delete-start/delete-end、下一段立即起音和保留侧 hard limit。每个 fixture 同时证明被删尾音消失且下一段起音保持完整。
5. 浏览器集成覆盖当前 ArtTool 三页签状态机和模板 listbox 的焦点/关闭行为，因为即使命令来自 cut 编辑，每次 Store frame 重绘仍会进入 ArtTool。

### 执行决定

更新后的 PRD、设计和实施计划完成复核前，任务保持 `planning`。当前活动任务仍为 `08-21-split-art-selection-template-dropdown` 时，不激活本性能任务。
