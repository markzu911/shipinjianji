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

### 2026-08-21 浏览器长文案优化前基线

- 环境：Windows 11，Playwright Chromium headless，隔离 Uvicorn 随机本地端口；
  逻辑时长 60 秒，60 段、每段 10 个可见字符，共 600 字符，预置 30 个
  文字删除区间。草稿 PUT 使用本地 route echo，不调用外部模型或读取用户媒体。
- 测量：每次点击从 `performance.now()` 开始，在目标行 DOM 状态变化后的第二个
  `requestAnimationFrame` 结束；连续执行 10 次删除/恢复。
- 原始毫秒：`1870.5, 1924.0, 1873.8, 1878.1, 1852.5, 1894.3,
  1960.5, 1842.2, 1841.6, 2023.6`。
- 汇总：P50 `1875.95ms`，P95 `1960.5ms`，max `2023.6ms`。
- 确定性计数：新建 thumbnail video extractor `10`，history localStorage 写入
  `10`，cut-draft PUT `4`，最大 PUT 并发 `1`，基础 video `src` 写入和
  `load()` 均为 `0`。
- 结论：虽然每次选择变化没有 reload 基础 video，selection-keyed thumbnail
  重建仍持续 seek/Canvas/JPEG 并推迟绘制机会，是本 fixture 的首要成本；同步
  history 写入和无防抖 PUT 继续形成可消除的工作放大。

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

## 2026-08-21 Phase 0-4 实施结果

### 浏览器交互优化后测量

- 环境保持与优化前基线一致：Windows 11、Playwright Chromium headless、
  隔离 Uvicorn 随机端口，60 段/600 字符/30 个既有文字删除范围。
- 连续 10 次删除/恢复的 input-to-post-commit-second-rAF 原始毫秒：
  `65.5, 47.4, 54.3, 77.8, 57.5, 64.0, 45.8, 52.6, 49.5, 51.2`。
- 汇总：P50 `53.45ms`，P95 `65.5ms`，max `77.8ms`。
- 确定性计数：thumbnail extractor 新建 `0`，基础 video `src` 写入/`load()`
  均为 `0`，history localStorage 写入 `1`，可见 commit `10`；每次 commit
  仅产生 `CUT_TIMING_CHANGED`，没有 `PROJECT_HYDRATED`。
- long task 原始毫秒：`63, 80, 75, 86`，最大 `86ms`，没有超过 `200ms`。
- 草稿队列回归证明 300ms burst 合并为一次 PUT、最大并发为 1；在途编辑
  使用首个响应 revision rebase，失败后由下一次编辑重试，同帧两条命令保留
  两个独立 history entry，刷新恢复仍读取最新草稿。

### Fingerprint PCM LRU

- 新增独立 `server/pcm_cache.py`，缓存 key 为 resolved path、文件 size 和
  `mtime_ns`；共享值通过只读 Sequence 暴露，成本严格按
  `len(samples) * samples.itemsize` 计算。
- `CUT_DRAFT_PCM_CACHE_MAX_BYTES` 默认 `268435456`（256 MiB），设为 `0`
  时直接调用原 decoder。LRU 按总字节淘汰，单项超过预算时只服务当前请求而
  不缓存。
- metadata lock 只保护 cache/LRU/in-flight 状态；FFmpeg 解码在锁外执行。
  相同 fingerprint 并发 miss 共享一个 in-flight 结果，失败不缓存并唤醒全部
  等待者，下一次请求可以重新解码。
- 缓存只接入 cut-draft 完整 PCM 解码，不缓存 range alignment、transition
  trust、diagnostics 或 revision，也不修改 acoustic sidecar。
- 缓存开关等价矩阵覆盖 text/timeline、完整跨段 delete-start/delete-end、
  完整重复上下文“得/你”、“一起给”、下一段立即起音和 retained-side hard
  limit；物理范围、diagnostics 和 API revision 完全一致。

### Phase 4 定向验证

- PCM cache、acoustic alignment、cut draft、cut acoustic boundaries：
  `122 passed`。
- 与草稿/边界相关的 cut rendering：`9 passed`。
- settings 配置：`8 passed`。
- `python -m compileall -q server` 与 `git diff --check` 通过。

## 2026-08-21 Phase 5 最终性能与集成门禁

### 浏览器性能复测

- 环境：Windows 11，Playwright Chromium headless，隔离 Uvicorn 随机本地
  端口；60 段、600 个可见字符、30 个既有文字删除范围。
- input-to-post-commit-second-rAF 原始总耗时（ms）：
  `61.7, 51.6, 53.9, 66.2, 61.2, 59.3, 60.6, 51.0, 42.8, 58.0`。
- 汇总：P50 `58.65ms`，P95 `61.7ms`，max `66.2ms`。
- long task 原始毫秒：`56, 54, 90, 56`；最大 `90ms`，无 `>200ms`。
- 确定性计数：thumbnail extractor `0`，基础 video `src/load` 为 `0/0`，
  history localStorage 写入 `1`，visible commit `10`；Store action 只有一个
  `cutTimingChanged` 类型，未出现 `projectHydrated`。
- 与优化前 P95 `1960.5ms` 相比，本轮 P95 降至 `61.7ms`；门禁通过。

### 最终验证结果

- 定向浏览器竞态回归：`4 passed`。
- 完整浏览器套件：`38 passed, 1 xfailed`；xfail 是现有服务重启后
  `JOBS` 丢失的已知契约。
- 相关前后端集合：`174 passed`。
- 最终非浏览器全量 `322 passed`，与浏览器合计 `360 passed, 1 xfailed`。
- 全部 `web/*.js` `node --check`、`python -m compileall -q server`、
  Trellis context validate 和 `git diff --check` 通过。

### 最终独立审查修复

- 时间轴拖动在 pointerdown 保存 history before，提交时显式使用拖前快照；
  同一帧合并可见 commit 不再破坏拖动撤销边界。
- 取消旧 commit effect 时同步清除旧预览；时间轴确认与空白恢复的试听统一在
  commit 后执行，后续 undo 不会触发上一命令的迟到 seek/play。
- 草稿请求在调用 `fetch()` 前登记 in-flight identity，同步抛错与异步拒绝都由
  同一清理路径释放；失败后下一次编辑可重试。
- 服务端物理校准直接同步 Store 后，frame effect 不再重复提交等价 cut 状态；
  Store 拒绝等价 action 时也不再重绘并覆盖“已保存”反馈。
- source-time 缩略图使用 source-to-edited spans 投影剪后 `left/width`；全删时
  主动取消 extractor 并清空旧 DOM。
