# 单页编辑器画中画面板迁移技术设计

## 1. Architecture Boundary

```text
index.html
  EditorProjectStore                  <- pip assets/overlays/selection authority
  MediaController                     <- one base video, seek and playback clock
  PreviewCompositor                   <- art + pip render and preview drag/resize
  TimelineController                  <- shared pip range transaction/history
  EditorSuite
    ArtTool.mount(artRoot, services)
    PipTool.mount(pipRoot, services)

/picture-in-picture legacy page
  picture-in-picture.js adapter       <- fallback/standalone only through B3
```

B3 只迁移画中画 inspector 和素材 effects。PipTool 不拥有 video、播放控制、时间线 DOM/Store、缩略图、project storage 或跨页消息。公共预览、公共时间线和 compose 继续由 B1 frame selectors 驱动。旧页面在 B3 保留，B4 再删除兼容边界。

## 2. Shared Module Split

继续使用普通 `<script defer>` 和 UMD 风格全局：

```javascript
window.EditorPipModel
window.PipTool
```

- `editor-pip-model.js`：纯函数，负责素材注册表归一化、稳定 id、source 过滤、overlay 默认值/归一化、启用集合、时间范围、timeline track、compose 前校验和 job asset 合并。不得读取 DOM、Store、URL、storage 或网络。
- `editor-pip-tool.js`：root-scoped inspector、瞬时表单状态和 API effect 编排。所有已确认变更只调用注入的 commands。
- `editor-project-store.js`：继续拥有 pip state/action/selectors；优先调用 `EditorPipModel` 构建 pip timeline 与归一化素材，避免 Store、PipTool、legacy page 出现第三套 identity/范围规则。
- `editor-preview-compositor.js`：继续是公共画中画 DOM renderer 和预览拖动/缩放所有者；修改为无任意最大宽度并保持中心裁切语义。
- `picture-in-picture.js`：B3 兼容适配器。保留旧页面 video/timeline/sessionStorage/message 代码，但素材和 overlay 的规范化优先复用 `EditorPipModel`；B4 删除。

脚本顺序：

```text
timeline-model -> editor-pip-model -> editor-project-store
-> editor-media-controller -> editor-art-model -> editor-art-renderer
-> editor-preview-compositor -> editor-timeline-controller
-> editor-art-tool -> editor-pip-tool -> editor-suite -> app
```

`editor-pip-model` 放在 Store 前，使 Store 可直接复用其纯函数；Pip model 不反向读取 Store，避免循环依赖。

## 3. PipTool Contract

```javascript
PipTool.mount(root, services) -> {
  activate(),
  deactivate(),
  render(frame),
  destroy(),
}
```

Required services:

```javascript
{
  project: {
    snapshot(),
    subscribe(listener),
    beginEffect(scope),
    isCurrentEffect(token),
  },
  media: {
    currentEditedTime(),
    seekEdited(seconds),
    editedToSource(seconds, edge),
    subscribeFrame(listener),
  },
  commands: {
    replacePip(pip, options),
    selectPip(id),
    setPipRange(id, start, end, anchors),
    generateCurrentPreview(),
  },
  api: { request(path, options) },
  feedback: { confirm(options), generation },
}
```

`mount` 校验 root 和服务，只构建 inspector DOM。`activate` 从最新 frame 恢复选择并启动必要的 pending asset 轮询。`deactivate` abort 本地请求、清 timer、停止纯视觉工作并移除面板临时 draft，但不清除 Store 中已确认素材/overlay。`destroy` 还取消 Store/media/document/window 订阅并移除 owned DOM；重复调用为 no-op。

## 4. State And Command Semantics

权威项目状态：

```javascript
snapshot.project.pip = {
  source: "original" | "edited" | "art",
  assets: PipAsset[],       // all generated records for the active source
  overlays: PipOverlay[],   // enabled records only
}
snapshot.project.timeline.selection = { clipId: `pip:${assetId}` } | null
```

PipTool 瞬时状态仅包含：

```javascript
{
  selectedTranscriptId,
  assetType,
  generationMode,
  aspectRatio,
  promptDraft,
  requestedRange,
  busyEffects,
  fieldErrors,
  active,
}
```

操作矩阵：

| 用户/系统操作 | Store command/action | timingRevision |
| --- | --- | --- |
| pending/failed asset 状态合并 | one `PIP_STATE_CHANGED` | unchanged |
| ready image/video 自动启用 | one `PIP_STATE_CHANGED` with pip+timeline | +1 once |
| enable/disable | one `PIP_STATE_CHANGED` with pip+timeline | +1 once |
| position/width/preset | one `PIP_STATE_CHANGED` | unchanged |
| panel/public timeline range | `TIMELINE_CLIP_RANGE_CHANGED` | +1 once |
| selection | `SELECTION_CHANGED` | unchanged |
| prompt/type/mode/aspect transient edit | no project action | unchanged |

图片完成响应直接加入 assets 并建立默认 overlay。视频 queued/processing 只加入 assets；轮询变为 completed 后按稳定 id 自动启用一次。failed asset 保留在 assets 供用户识别失败原因，但不进入 overlays。禁用删除 overlay/timeline clip，不删除 asset。

## 5. Source, Time And Asset Contracts

- PipTool 始终读取 `snapshot.project.pip.source` 作为提示词与素材生成 source；不从 URL 私自推导第二份 source。
- transcript 选择显示剪后 segment 时间；请求同时发送 edited `start/end` 与可用的 `sourceStart/sourceEnd`。
- range field 和公共时间线都通过同一个 `setPipRange` command；source anchor 由 MediaController 在顶层转换。
- 素材响应按 `id + source` 合并；旧 job/poll 响应必须同时通过 tool lifecycle generation、job id 和 Store effect token 校验。
- `project.pip.assets` 是预览 URL/类型/状态注册表；compose DTO 只投影 `assetId/imageId/start/end/sourceStart/sourceEnd/x/y/width`，不发送 asset URL、status 或 UI transient state。

## 6. Unlimited Enlargement And Crop Parity

宽度语义保持“素材宽度 / 主视频宽度”。有效宽度必须 finite 且不小于现有最小值，不设最大值。

- 面板使用无 `max` 的百分比 number input，允许键盘直接输入大于 100%；步进不等于上限。
- PreviewCompositor 的 resize 只按 pointer delta 和最小值计算，不再使用中心到舞台边缘的 `maximumWidth`。位置独立 clamp 到允许的中心坐标区间。
- CSS 仍以 `left/top = x/y`、`transform: translate(-50%, -50%)` 和 `width = width * 100%` 渲染；舞台 `overflow: hidden` 负责裁切。
- FFmpeg 坐标使用对小/大 overlay 都成立的 clamp：

```text
min_x = min(0, main_w - overlay_w)
max_x = max(0, main_w - overlay_w)
x = clamp(main_w * center_x - overlay_w / 2, min_x, max_x)
```

`y` 同理。这样 overlay 小于主画面时完整留在画面内，大于主画面时允许负坐标并按用户中心点裁切，不退化为左上角。

## 7. Draft Recovery

沿用唯一 key `editor-suite:project-draft:<jobId>`，写 schema v2：

```javascript
{
  schemaVersion: 2,
  jobId,
  serverVersion,
  revision,
  art: { source, overlays },
  pip: { source, overlays },
  selection: { clipId } | null,
  savedAt,
}
```

- 不保存 pip assets；hydrate 先从 server job 建立当前 asset registry，再恢复引用仍存在且 source 匹配的 overlay。
- schema v1 继续按 art-only 恢复，pip 保持 server state；下一次相关 commit 自动写 v2。
- v2 恢复一次性提交 art+pip+timeline+selection，避免两个 dispatch 产生中间 frame。
- job/server mismatch、无效 source/范围/位置/尺寸、重复 id、未知 asset 或超过素材数量上限的草稿整体拒绝，不做部分覆盖。
- draft 只是客户端恢复 metadata，不表示服务端素材或 compose 已成功。

Store 的 `PROJECT_DRAFT_RESTORED` 需扩展为同时接受 art/pip，并在一次 reducer transaction 中替换两个 timeline kind。B2 v1 行为测试保留。

## 8. Async Effects And Polling

每个 effect 维护 `{ token, controller, timer, lifecycleGeneration }`：

- prompt draft：只更新当前 textarea；不进入 Store。
- create asset：响应有效时从最新 snapshot 合并 asset；图片/ready video 同次建立 overlay。
- poll assets：每轮请求使用新 token；只在同 job、同 source 且工具 active 时应用。queued/processing 使用 2s timer，错误使用有限退避并保留重试入口。
- deactivate/destroy/job switch：abort controller、清 timer、递增 lifecycle generation，并通过新 scope token 使迟到结果无效。

网络响应先校验 HTTP/payload，再复查 token 和 lifecycle。请求开始时的 base revision 发生无关变化不应丢弃素材状态，但任何会替换 pip overlays 的结果必须从最新 snapshot merge，绝不能覆盖用户刚完成的位置、尺寸、启用或时间修改。

## 9. EditorSuite Integration And Feature Flag

```javascript
const topLevelPipEnabled = Boolean(
  projectStoreEnabled &&
  window.__EDITOR_PIP_PANEL_ENABLED__ !== false &&
  window.PipTool &&
  pipPanelRoot
);
```

- enabled：mount PipTool；`openTool("pip")` 不调用 `ensureToolFrame`，iframe bridge 不接收 pip state，公共 preview/timeline/compose 直接消费 Store。
- disabled：不 mount PipTool；现有 pip iframe、revision floor、ACK、message 和 mirrored action 路径保持。
- ArtTool 与 PipTool 的 flag 独立，四种组合均只能为每个 kind 保留一个 authority。
- flag 只在初始化读取；回滚需设置 false 后 reload，禁止运行中并行切换。
- `renderEditorFrame` 同时调用 artTool/pipTool；隐藏面板配合 `hidden`/`inert` 与 deactivate，重新激活从最新 frame 渲染。

## 10. Compatibility And Rollback

1. 先落共享 Pip model 和无上限渲染/后端契约，并用 legacy/后端测试验证。
2. PipTool 先作为未启用 integration point 落地，再接入 panel 和默认 flag。
3. 默认顶层回归时，在 EditorSuite 加载前设置 `window.__EDITOR_PIP_PANEL_ENABLED__ = false`，reload 后回到 B1 iframe。
4. `/picture-in-picture`、`picture-in-picture.js`、`embedded=1` 和 message bridge 在 B3 不删除；B4 独立清理。
5. 回滚不得撤销 B0-B2 Store/media/preview/timeline/ArtTool 契约，也不得把私有 HTML 或 generation payload 恢复为权威。

## 11. Testing Strategy

- Pure Node：Pip model asset/overlay normalization、稳定 id、source filter、timeline、enable/disable、无上限 width 和 invalid finite values。
- PipTool DOM stub/Node：root-scoped lifecycle、single dispatch、effect cancellation、poll terminal state、late response rejection、destroy cleanup。
- Static：script order/version/no-cache、默认无 pip iframe、tool 不含 storage/message/video/timeline ownership、feature flag 互斥、legacy 资源保留。
- Browser：顶层 prompt/image/video mock、selection、enable/disable、position、175% width、preview/timeline range、paused/playing identity、schema v1/v2 refresh、compose、fallback、standalone、desktop/375px。
- Backend：normalize 接受大于 1 的 finite width，拒绝 invalid/min violations；真实小样片验证 oversized overlay 的中心裁切；picture-in-picture/compose 回归保持。

## 12. Main Risks

- 直接把 2,503 行 legacy 脚本包进 PipTool 会复制第二个 runtime；module ownership 和禁止项是 code review gate。
- polling job 更新很容易用旧 job snapshot 覆盖刚编辑的 overlay；必须按 asset id 合并 assets 并从最新 Store snapshot 保留 overlays。
- schema v2 如果保存 asset registry 会把过期 URL/status 变成客户端权威；draft 只保存 source/overlays。
- 移除 width 上限后 FFmpeg 定位公式必须同步，否则浏览器大图按中心裁切、成片却固定左上角。
