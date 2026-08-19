# 单页编辑器艺术字面板迁移技术设计

## 1. Architecture Boundary

```text
index.html
  EditorProjectStore                 <- confirmed art overlays / selection authority
  MediaController                    <- current edited time / seek / playback
  PreviewCompositor                  <- shared art renderer + public preview
  TimelineController                 <- shared art range transactions/history
  EditorSuite
    ArtTool.mount(inspectorRoot, services)
    Pip iframe adapter               <- remains until B3

/art-text legacy page
  art-text.js adapter
    shared art model + renderer
    legacy page media/timeline/message services
```

B2 只把艺术字 inspector 迁入顶层。顶层 ArtTool 不拥有视频、预览图层、时间轴或项目数组；旧页面为回滚继续存在，但默认主编辑器不创建 art iframe。feature flag 在初始化时二选一，禁止同一会话同时运行 ArtTool 与 art iframe authority。

## 2. Shared Module Split

继续使用普通 `<script defer>` 和 UMD 风格全局：

```javascript
window.EditorArtModel
window.EditorArtRenderer
window.ArtTool
```

- `editor-art-model.js`：overlay 默认值/稳定 id、范围校验、模板效果归一化、全文轨道 cue/字符时间/source anchor、共享样式 patch、compose 前验证。所有函数接收显式输入并返回新对象，不读取 DOM、Store、URL 或 storage。
- `editor-art-renderer.js`：格式化横排/竖排文本、字符布局、模板 CSS 变量和 `character-bounce` DOM 渲染。PreviewCompositor、ArtTool 的模板/AI 草稿预览和旧页面适配器共用；使用 DOM API/`textContent`，不接受 HTML 字符串。
- `editor-art-tool.js`：root-scoped inspector view、瞬时 UI 和 API effect 编排；不包含独立 media/timeline/项目 persistence。
- `art-text.js`：B2 兼容适配器。旧页面继续创建独立 page services；可暂时保留 legacy-only video/timeline/message 代码，但领域/renderer 不得再复制。B4 删除该适配器和页面边界。

脚本顺序：

```text
timeline-model -> editor-project-store -> editor-media-controller
-> editor-art-model -> editor-art-renderer -> editor-preview-compositor
-> editor-timeline-controller -> editor-art-tool -> editor-suite -> app
```

## 3. ArtTool Contract

```javascript
ArtTool.mount(root, services) -> {
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
    dispatch(action),
    beginEffect(scope),
    isCurrentEffect(token),
  },
  media: {
    currentEditedTime(),
    seekEdited(seconds),
    subscribeFrame(listener),
  },
  commands: {
    replaceArt(art, options),
    selectArt(id),
    setArtRange(id, start, end),
    saveTranscript(text),
    refreshJob(token),
    generateCurrentPreview(),
  },
  api: { request(path, options) },
  feedback: { confirm(options), generation },
}
```

`mount` validates required services and root, builds/binds only inspector DOM, and returns an idempotent lifecycle。`deactivate` pauses visual-only work and aborts active local requests without clearing confirmed Store state。`destroy` aborts requests、清除 timer、取消 Store/media/document/window 订阅、移除 owned DOM，重复调用为 no-op。

## 4. State Ownership And Commands

Authoritative state:

```javascript
snapshot.project.art = {
  source: "original" | "edited",
  overlays: ArtOverlay[],
  assets: [],
}
snapshot.project.timeline.selection = { clipId } | null
```

Transient ArtTool state is limited to:

```javascript
{
  activeTab,
  aiDraftSuggestions,
  previewDraftId,
  busyEffect,
  fieldErrors,
  focusedControl,
}
```

每个已确认编辑都读取最新 snapshot，生成不可变 next `art` 并只调用一个 command。稳定 id 规则继续归 `EditorProjectStore`；ArtTool 在 hydrate 后不得使用数组 index 作为 identity。全文轨道样式 patch 应用于所有相同 `trackId` 的 overlay，文字/时间保持逐 cue，除非显式全文轨道重建 effect 成功。

Command matrix:

| User operation | Command/action | Timing revision |
| --- | --- | --- |
| text/style/font/layout/color/position | one `ART_STATE_CHANGED` | unchanged |
| add/delete/confirm AI overlay | one `ART_STATE_CHANGED` plus normalized timeline projection in same dispatch | changes only when clip set changes |
| start/end field or public timeline resize | `TIMELINE_CLIP_RANGE_CHANGED` | +1 once |
| selection | `SELECTION_CHANGED` | unchanged |
| transcript text save | guarded `TRANSCRIPT_TEXT_CHANGED` effect | unchanged when timing unchanged |
| rebuild full transcript track | guarded `ART_STATE_CHANGED` with overlays+timeline | +1 once if cue timing changes |

## 5. Panel DOM And UX

`index.html` 在 `#editorSuiteInspectorHost` 下提供一个隐藏 panel root。ArtTool 拥有现有设置、AI 推荐和保留文案控件，但不包含：

- `#artVideo`、`#artVideoPlayer` 和外部媒体控制；
- `#frameTimeline` 和缩略图提取；
- 页面 header/loading/error shell；
- 独立艺术字生成/结果 video 和继续链接。

公共 video 和 timeline 始终与 inspector 同屏。panel 起止时间控件通过 MediaController seek。公共工具栏生成按钮提交 `frame.composition`；ArtTool 可在字段旁显示校验错误，但不得调用 `/art-text` 建立第二条顶层生成路径。

375px 下 panel 是内部滚动区域且 document 不横向溢出。`deactivate()` 由 EditorSuite 配合设置 `hidden`/`inert`，隐藏控件不可 Tab 聚焦；重新激活从最新 frame 渲染并按稳定 id 恢复 selection。

## 6. API Effects And Revision Guards

现有 endpoints 保持不变：

- `GET /api/fonts`
- `GET /api/art-templates`
- `GET/POST/DELETE /api/art-position-presets`
- `POST /api/transcriptions/{job}/art-text/transcript-track`
- `PUT /api/transcriptions/{job}/transcript`
- `POST/GET/DELETE /api/transcriptions/{job}/art-text/suggestions`

每个 mutable/long-running effect 持有 `{ token, AbortController, timer }`。接收结果必须同时满足：

```javascript
token.jobId === project.snapshot().jobId
project.isCurrentEffect(token) === true
tool is not destroyed
```

网络完成先校验 response，再复查 token 后才能应用 Store。切换 job 或 destroy 时 abort fetch 并清除 polling。较新的本地 Store revision 不必拒绝不冲突的字体/模板读取，但会替换 transcript/overlays 的 effect 必须使用 project effect guard。

顶层生成不调用 legacy `generateVideo()`；它校验当前 art 后委托 `EditorSuite.generateCurrentPreview()`，请求从最新 snapshot 原子选择。

## 7. Draft Recovery

ArtTool 不访问 Web Storage。EditorSuite 拥有一个按 job id 隔离的版本化本地恢复 envelope，例如：

```javascript
{
  schemaVersion: 1,
  jobId,
  serverVersion,
  revision,
  art: { source, overlays },
  selection,
  savedAt,
}
```

adapter 只在已接受 Store commit 后持久化，不保存 pointer preview 或 AI draft review。服务端 job hydrate 后、ArtTool 首次 render 前只恢复一次。非法 JSON、schema/job 不匹配或与较新 server state 不兼容时忽略且不修改 Store。它只是恢复 metadata，不代表服务端 render 成功；生成/历史状态仍来自 job。

该 envelope 预留 B3 扩展 PiP，禁止再创建 tool-owned key。服务重启恢复仍不在 B2，因为 job API 本身尚不能跨重启恢复。

## 8. Feature Flag And Compatibility

```javascript
const topLevelArtEnabled =
  window.__EDITOR_ART_PANEL_ENABLED__ !== false &&
  Boolean(window.ArtTool && inspectorHost && projectStoreEnabled);
```

- enabled：EditorSuite mount ArtTool，不调用 `createToolFrame("art", ...)`，不使用 art message/ACK。
- disabled：不 mount ArtTool，现有 art iframe/revision floor/ACK 路径保持。
- PiP 在 B2 始终使用 B1 iframe adapter。
- `/art-text` 加载兼容 adapter 并保持独立可用。

flag 只在初始化读取一次。运行时切换不支持，因为可能创建两个 authority。回滚方式是改变 flag 后 reload，而不是并行镜像。

## 9. Testing Strategy

- Pure Node：model normalization、稳定 id、校验矩阵、全文 cue layout/source anchor、共享样式 patch 和 renderer parity。
- ArtTool Node/DOM stub：lifecycle、root-scoped query、single dispatch、effect cancellation、stale response rejection 和 destroy cleanup。
- Static：script order/version/no-cache、默认路径无 art iframe、ArtTool 无 storage/message/video/timeline ownership、legacy 资源保留。
- Browser：真实顶层控件的 manual/track/AI flows、公共 preview/timeline/compose 一致性、paused/playing identity、refresh recovery、feature flag fallback、独立 `/art-text`、desktop/375px。
- 后端 art/compose tests 保持通过，证明 API 和渲染兼容。

## 10. Rollback

1. 先落 shared model/renderer 并由 legacy tests 验证。
2. ArtTool 先作为未启用 integration point 落地，再切换 feature flag 默认值。
3. 顶层 panel 回归时，在 EditorSuite 加载前设置 `__EDITOR_ART_PANEL_ENABLED__ = false`，恢复 B1 iframe path。
4. 回滚不得删除 B0/B1 Store/media/preview/timeline 契约，也不得恢复 HTML/private payload authority。

## 11. Main Risks

- 把 6107 行整体搬入 ArtTool 会形成新 monolith 并复制 B1 renderer；共享模块边界和文件/函数 ownership 是 review gate。
- 全文轨道如果逐 cue dispatch 会产生多 revision/history；必须构造一个 next state 后单次 dispatch。
- legacy page 与顶层 panel 共存期间可能漂移；共享 model/renderer fixture 和 feature flag 互斥测试必须覆盖。
- draft hydrate 可能覆盖服务端新文字；恢复逻辑必须保留 server-updated transcript cue text，仅在版本 guard 满足时应用本地样式/时间。
