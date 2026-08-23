# 当前时间轴分割数据流研究

## 结论

当前代码没有“基础视频片段”或“分割点”领域状态。时间轴底部的画面只是按剪后区间布局的缩略图，唯一可编辑 clip 是临时/已提交的删除范围。因此，仅在 DOM 上画一条分割线无法满足刷新恢复、片段独立删除、撤销/重做和统一生成；必须增加持久化的源时间分割锚点，并由锚点派生可见 clip。

同时，当前服务端会对每一个 `timelineRanges` 执行声学吸附。分割片段删除若直接复用普通手动范围，会移动用户明确建立的片段端点，重新引入尾音残留或误删下一段开头。必须为“删除完整分割片段”增加显式的精确边界模式，普通手动范围继续走原算法。

## 前端时间与渲染

- `web/index.html:492` 的 `#cutFrameTimeline` 是目标容器；标题区当前只有时间输出，轨道内依次包含标尺、文案、公共 effect layer、缩略图、删除范围和播放头。
- `web/app.js:1963` / `web/app.js:1980` 已提供 source/edited 双向映射。分割必须从当前播放帧取得 source time，持久化后再按 edited spans 投影，不能持久化 CSS 百分比或 edited time。
- `web/app.js:3576` 的 `getCutPlaybackFrameState()` 是当前唯一播放帧映射入口，可同时得到 source/edited 时间。
- `web/app.js:3779` 的 `syncCutTimelineModel()` 只建立 `cut:deletions` 轨道，clip 来源是 `timelineDeleteRanges`，没有基础视频 clip。
- `web/app.js:3861` 的 `renderCutTimelineRanges()` 只渲染当前选中的删除范围；已确认范围不会在时间轴保留恢复入口。
- `web/app.js:4278` 的轨道 pointer handler 默认开始自由拖选删除范围。新增 clip/恢复 marker 必须在该 handler 前拦截或加入明确的 `closest()` 排除，避免点击 clip 同时创建删除选区。

## 草稿、历史与保存队列

- `web/app.js:2410` 的持久 payload 只有三类 ranges；`web/app.js:2462` 的语义签名同样不含结构状态。
- `web/app.js:2504` 的恢复流程只恢复三类 ranges；旧草稿没有 split 字段时可自然兼容为 `[]`。
- `web/app.js:2918` 和 `web/app.js:3153` 的历史快照/应用流程只处理三类 ranges。分割点和命令前后 selection 必须进入同一个 history transaction，不能另建第二套 undo 栈。
- 当前保存队列按语义签名做 latest-state-wins，并将服务端物理校准与用户意图区分。`splitPoints` 和精确边界模式属于用户语义，必须进入签名；服务端派生的物理时间仍不得进入签名。

## Store 与 revision

- `web/editor-project-store.js:11` 只有 `CUT_TIMING_CHANGED`，没有结构专用 action。
- `web/editor-project-store.js:62` 的 `normalizeCut()` 不保留 split points。
- `web/editor-project-store.js:404` / `web/editor-project-store.js:413` 以 cut ranges/duration 和 timeline clip 起止计算 timing signature。若直接把分割 clip 塞进现有 timing action，会错误增加 `timingRevision`，并可能触发艺术字/PiP 时间重算。
- `web/editor-suite.js:1601` 的 `setCutDraft()` 当前统一派发 timing action。分割提交需要显式 structure action；后续服务端只回写 draft revision 时必须保持 metadata-only no-op 语义。

## 服务端持久化与声学边界

- `server/schemas.py:32` / `server/schemas.py:38` 的 `CutDraftTimelineRange` 和 `CutDraftRequest` 没有 split point、boundary mode 或 split clip identity。
- `server/app.py:4429` 的 `align_cut_draft_timeline_ranges_to_audio()` 对所有 timeline ranges 检查相邻字符转场，并可在 0.20 秒范围内移动端点。
- `server/app.py:12094` 的 cut-draft PUT 在 revision 检查前规范化 ranges、执行声学解析，再原子保存。新增 split points 应在同一请求和同一锁/revision 事务中规范化并持久化。
- compose 已经通过 cut-draft revision 读取权威删除范围；纯分割不改变输出。删除分割片段仍应转成 `timelineRanges`，这样 preview、retained transcript 与 compose 不需要第二种删除源。

## 建议的最小契约

```text
cutDraft.splitPoints[] = { key, sourceTime }

timelineRanges[] += {
  boundaryMode: "speech_safe" | "split_exact",
  splitClipKey?: string
}
```

- 缺省 `boundaryMode` 为 `speech_safe`，保证旧客户端/旧草稿行为不变。
- `split_exact` 仅允许端点匹配 `{0, duration, splitPoints.sourceTime}` 中相邻的两个边界；服务端验证后跳过声学移动，并输出诊断原因 `split_boundary_exact`。
- 可见 clip 由相邻源时间边界派生，再用已有 edited spans 计算剪后位置和宽度。完全落入删除范围的 split point/clip 隐藏，但锚点不删除。
- 已删除 split clip 的 range 保留 `splitClipKey`，在剪后拼接点渲染零时长视觉 marker 与至少 44px 的恢复点击区；恢复只移除该 exact timeline range。
