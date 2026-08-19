# 画中画运行时

## Scenario：顶层画中画面板与单一项目运行时

### 1. Scope / Trigger

修改画中画素材注册表、顶层 inspector、生成/轮询 effect、公共预览/时间线、compose 投影、历史 URL 或项目草稿时适用。主编辑器只使用顶层 `PipTool`；不存在 iframe、独立画中画编辑页或 feature flag authority。

### 2. Signatures

```javascript
PipTool.mount(root, services) -> {
  activate(), deactivate(), render(frame), destroy()
}

snapshot.project.pip = {
  source: "original" | "edited" | "art",
  assets: PipAsset[],       // 当前 job/source 的完整素材注册表
  overlays: PipOverlay[],   // 已启用且参与 preview/timeline/compose 的子集
}

sessionStorage[`editor-suite:project-draft:${jobId}`] = {
  schemaVersion: 2,
  jobId,
  serverVersion,
  art: { source, overlays, suppressedOverlays },
  pip: { source, overlays },
  selection: { clipId } | null,
  savedAt,
}
```

素材 effect 使用既有 API：`POST .../picture-in-picture/prompt`、`POST .../images|videos` 和 `GET /api/transcriptions/{jobId}`。最终生成只调用顶层 `/compose`，PipTool 不建立第二套最终生成任务。

### 3. Contracts

- `EditorProjectStore` 是 pip assets、enabled overlays 和 selection 的唯一权威；公共 preview、timeline 和 compose 从同一个 editor frame 派生，稳定 id 统一为 asset id。
- PipTool 只创建传入 root 内的 inspector DOM，不创建 video、Timeline Store、storage key、缩略图、message listener 或页面级初始化；重复生命周期调用幂等，deactivate/destroy 必须 abort request 并清 timer。
- 图片或 ready video 在一次语义 command 中合并 asset 并启用 overlay；queued/processing video 只进入 assets，completed 后自动启用一次，failed 保留错误素材但不得进入 overlays。
- 请求结果必须同时校验 lifecycle、job、source、effect token，并从最新 snapshot 按 asset id 合并；切换工具/job 后迟到响应为 no-op，不能覆盖用户已改的范围、位置、尺寸或启用状态。
- 画中画宽度必须 finite 且 `>= EditorPipModel.MIN_WIDTH`（当前 15%），不设最大值。面板 number input 不含 `max`；公共 compositor、Store、草稿和后端共用相同最小值与中心裁切语义。
- schema v2 不保存 assets；艺术字同时保存活动 `overlays` 和撤销剪辑所需的内部 `suppressedOverlays`。恢复前先从当前 job 建立注册表，再按当前 cut reconcile art 并原子恢复 art+pip+selection。未知 asset、跨两个艺术字集合的重复 id、disabled overlay、无效数值/范围/source 或非空未知 selection 使整份 v2 草稿失效。schema v1 继续只恢复 art，pip 保持服务端状态。
- `/picture-in-picture` 只返回 307 到 `/?tool=pip`，保留 `job/source` 等 query、覆盖冲突 `tool` 并删除 `embedded`；目标页面必须激活 `#editorPipPanelRoot`，运行 DOM 中 iframe 数量为 0。
- `picture-in-picture.html/js` 不存在。PipTool、公共预览、时间线和 compose 必须继续共享同一个 Store frame，禁止恢复第二个 video、storage、message 或生成 runtime。

### 4. Validation & Error Matrix

| 条件 | 处理 |
| --- | --- |
| asset 缺少稳定 id、source 不匹配或超过 20 个 | 拒绝/跳过，不创建 overlay |
| video 为 queued/processing | 继续有限轮询，只更新 assets |
| video completed 且 URL 有效 | 合并并自动启用一次，timing revision 只增加一次 |
| video failed | 停止轮询、保留错误素材、overlay 不变 |
| width 为 NaN/Infinity 或小于 15% | 前端不提交，草稿拒绝，后端再次拒绝 |
| width 为 175% 等有限大值 | preview/draft/compose/backend 原值保留，超出舞台部分居中裁切 |
| v2 selection 非空但不引用恢复后的 art/pip overlay | 整份草稿拒绝，不做部分覆盖 |
| deactivate/job switch 后旧请求返回 | no-op，不增加 revision、不写 UI/Store |

### 5. Good / Base / Bad Cases

- Good：视频素材 queued 后轮询为 completed，同一 asset id 出现在卡片、公共预览、公共时间线和 compose；175% 刷新后仍保持。
- Base：schema v1 只恢复艺术字；pip 继续使用当前服务端素材和 overlay。历史 URL 重定向后直接打开同一顶层面板。
- Bad：把 pending asset 当 overlay、把 assets 写进草稿、用数组 index 作为 identity，或在 PipTool 内创建第二个 video/timeline/storage/message runtime。

### 6. Tests Required

- Node：asset/overlay 分离、稳定 id、source filter、pending/failed、严格草稿校验、15% 最小和大于 100% 的有限 width。
- Store：art+pip+timeline+selection 一次原子恢复，revision/timingRevision 矩阵和 compose width 一致。
- 浏览器：prompt/image/video 全部 mock；覆盖 completed/failed、enable/disable、selection、position、range、175%、v2/v1 reload、无效 selection、迟到响应、历史 URL 重定向、iframe 为 0 和 375px 无溢出。
- 后端：normalize 接受 175%、拒绝非有限/过小值；真实 FFmpeg 样片断言超大 overlay 的中心裁切。

### 7. Wrong vs Correct

```javascript
// Wrong: 轮询响应用旧快照覆盖用户刚完成的编辑，并把素材数组当启用集合。
commands.replacePip({ assets: response.assets, overlays: response.assets });

// Correct: 按稳定 id 合并最新注册表，只在 ready 转换时建立 enabled overlay。
const latest = project.snapshot().project.pip;
const assets = EditorPipModel.mergeAssets(latest.assets, response.assets, {
  source: latest.source,
});
commands.replacePip({ ...latest, assets, overlays: latest.overlays });
```
