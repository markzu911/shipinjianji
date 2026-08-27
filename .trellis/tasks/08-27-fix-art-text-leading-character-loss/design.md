# Technical Design

## Scope

修改面限定在前端全文艺术字与 cut Store 的 reconciliation 边界，主要涉及 `web/editor-art-model.js` 与 `web/editor-project-store.js`。后端 retained transcript、声学删除边界和初次艺术字轨道生成只作为权威输入和回归对象，不改变业务算法。

## Existing Failure Flow

```text
canonical retained transcript (forced/source anchors)
  -> existing transcript art cues
  -> user edits text
  -> user splits editable transcript
  -> local retained projection (semantic anchors)
  -> user deletes split segment
  -> CUT_TIMING_CHANGED
  -> reconcile each cue by old source midpoint containment
  -> leading characters outside old cue window are discarded
  -> server canonical projection arrives with same range signature
  -> no second reconciliation; corrupted cue text persists
```

## Invariants

1. `nextCut.transcript` 决定当前保留字符身份及顺序。
2. 全文艺术字的同一 `trackId` 是 reconciliation 单元，不是单个 cue。
3. 旧 cue source anchors 只决定相邻 cue 之间优先在哪里分界；不能决定某个当前字符是否存在。
4. 当前 transcript 的每个可见字符必须恰好分配一次；输出 cue 拼接必须与当前 transcript 内容字符完全相等。
5. cue ID、样式、trackId 和 reconciliation base 支持删除、撤销和恢复；空 cue 进入 suppressed，不伪造文本。
6. 手动艺术字继续使用现有 anchored-overlay 路径，不进入全文字符分配。

## Track-Level Reconciliation

### Inputs

- 按原 track/cue 顺序合并 active 与 suppressed transcript overlays。
- 对每个 cue 读取稳定 reconciliation base；缺少 base 时使用当前 overlay 建立。
- 从 `nextCut.transcript` 生成按 edited/source 时间单调排序的可见字符 units。

### Boundary Projection

对相邻 cue 定义一个 source boundary preference，可取左 cue `sourceEnd` 与右 cue `sourceStart` 的中点或现有无重叠边界。随后用一个全局 cursor 在当前 units 中选择最接近每个 preference 的单调 split index：

- split index 只能前进，不能重复消费字符；
- units 位于首 cue 之前或末 cue 之后时仍分配给首/末可用 cue；
- cue source 区间之间有 gap、重叠或整体平移时，不产生未分配区；
- 没有可靠 source anchors 时，按旧 cue 可见字符容量比例做单调降级，但仍执行全文守恒校验。

每个 cue 从其连续 unit slice 重建 `text/start/end/sourceStart/sourceEnd/characterTimings`。slice 为空则 suppressed；非空则 active。分配结束后验证：

```text
concat(active cue content characters) == concat(next transcript content characters)
sum(active cue character timing counts) == next transcript visible character count
```

若边界偏好无法形成有效 partition，使用容量比例的确定性降级重新分配；禁止返回部分成功的缺字轨道。

## Text-Only Update Baseline

`mergeArtText()` 继续只改变 transcript cue 文案，不改变 cue 时间、source anchors、样式、手动艺术字或 timing revision。同时更新 `_cutReconciliation.overlay.text`，并使 visible/base 的 character timing 数量与新 cue 可见字符数一致。这样后续删除、撤销或无 source-anchor 降级不会复活旧文案。

## Store Behavior

- 保留 `cutTimingSignature()` 不含 transcript 文本的契约：单纯文字保存不能重定时已有艺术字。
- 真正 ranges/duration 变化时仍由一个 `CUT_TIMING_CHANGED` 原子更新 cut、art timeline、preview 和 compose。
- reconciliation 的输出必须在同一 Store snapshot 内替换全文轨道；不得异步逐 cue 写入或依赖后续 server echo 修补。

## Persisted Art Invalidation

文字保存会让旧 `art-text.mp4` 失效，但全文 overlay 仍是可编辑工程状态。`update_transcript_track_text_for_segment()` 必须把艺术字子任务从 `completed` 降为已有的合法非运行态 `interrupted`，清空过期输出 URL，并标记可重试；不能使用 repository schema 不接受的 `status: null`，也不能使用没有后台 worker 的 `queued`。这样第一次文字保存产生的 `project-state.json` 仍可校验，随后的拆分和删除可以继续原子覆盖。

## Authoritative Segment Refresh

`saveSegmentText()` 后续拆分/删除的字符规范化必须消费刚从 job API 读回的 `result.segments`。更新 `currentEditableSegments` 但保留旧 `currentSegments` 会让 `canonicalizeTextSelectionRange()` 使用修改前字符 timing，并把目标中间段扩大到后续文字。首次 job read 与 effect 被拒绝后的 refresh read 都必须通过同一个源分段同步入口更新 `currentSegments` 并失效 `transcriptCharacterUnitsCache`，再建立 live cut transcript。

## Compatibility

- 不改变 API schema、cut draft、项目快照或历史数据格式。
- 艺术字失效继续使用 schema v1 已接受的 `interrupted` 状态，不新增状态枚举或迁移文件。
- 历史 overlay 缺少 `_cutReconciliation` 或 source anchors 时使用现有兼容输入并走确定性降级。
- 现有 full-track cue 分组、ID 与样式尽量保持；字符可因删除跨 cue 重新分配，但不会凭 anchor 漂移消失。
- 初次生成的后端全文守恒校验继续保留；前端新增同等级的 reconciliation 守恒校验。

## Risks And Controls

- 重复短语可能使文本搜索歧义：不做独立短语搜索，使用全轨单调 unit cursor 和 source boundary preference。
- 大量删除可能让多个 cue 为空：允许 suppressed，恢复时从稳定 base 和当前 units 重建。
- 无 source anchors 的旧数据可能改变 cue 容量分配：使用旧 cue 字符数比例，优先守恒字符而不是保持错误的边界。
- text-only merge 可能让旧 character timings 数量不匹配：在不移动 cue start/end 的前提下统一重建该 cue 内的 timings。

## Rollback

变更限定为 ArtModel track reconciliation、Store text merge 和对应测试。若回归发现 cue ID/恢复顺序异常，可整体回退新的 track-level helper；不修改、迁移或删除任何用户草稿和媒体。
