# B2 艺术字运行时证据

## Query

确认 B1 后艺术字仍有哪些独立运行时职责，并确定把 inspector 迁入顶层所需的最小安全模块、状态/API 边界、兼容路径和测试面。

## Confirmed Current State

- `web/art-text.js` 共 6107 行；开头直接查询约 130 个页面 DOM 节点（`web/art-text.js:10-149`），脚本尾部直接注册 UI/媒体/window/document 监听并调用 `requestLatestEditorCutDraft(); initialize();`（`web/art-text.js:5780-6107`）。它不是可挂载模块。
- 脚本仍创建独立 `artTimelineStore`（`web/art-text.js:200-203`）、独立 `#artVideo`/`#frameTimeline`（`web/art-text.html:117-218`）、sessionStorage 草稿（`web/art-text.js:2148-2182`）和 embedded/message bridge（`web/art-text.js:2807-3511`）。
- `renderPreview()` 仍构建私有 overlay DOM，并由 `notifyEditorHost()` 发布 HTML、timeline、语义 overlays 和 legacy generation payload（`web/art-text.js:2859-2967`）；B1 顶层已经不消费 HTML/private payload，但 child 仍运行整套逻辑。
- `initialize()` 会重新获取 job、给 `artVideo.src` 添加时间戳并恢复 child draft（`web/art-text.js:5662-5739`）。把该脚本直接加载到 `index.html` 会产生第二媒体源、第二时间轴和第二 authority。
- 艺术字脚本注册约 92 个事件监听；其中 window pointer/message/resize、document visibility/fullscreen 和轮询 timer 都需要显式 destroy 才能安全挂载。
- 顶层 `index.html` 已有 `#editorSuiteInspectorHost`（`web/index.html:599-605`）、唯一公共视频（`web/index.html:353`）、公共 preview（`web/index.html:446`）和公共 timeline layer（`web/index.html:511`）。
- B1 的 Store 已保存完整 semantic art overlays 和稳定 id，并通过 `selectEditorFrame()` 同时派生 preview/timeline/composition（`web/editor-project-store.js:798-865`）。
- B1 的 PreviewCompositor 已包含艺术字换行、模板、字符布局和逐字动画实现；旧 `art-text.js` 仍有同类 renderer（`web/art-text.js:412-516`），因此 B2 必须提取共享 renderer，不能新增第三份。
- EditorSuite 目前仍用 `createToolFrame()` 创建 art/pip iframe、用 revision floor/ACK 和 messages 适配 Store。B2 只替换 art entry；PiP entry 继续原样存在。

## Existing API Surface

- 字体：`GET /api/fonts`（`web/art-text.js:243`）。
- 模板：`GET /api/art-templates`（`web/art-text.js:355`）。
- 位置预设：`GET/POST /api/art-position-presets`、`DELETE /api/art-position-presets/{id}`（`web/art-text.js:2530-2613`）。
- 全文轨道：`POST /api/transcriptions/{job}/art-text/transcript-track`（`web/art-text.js:4663-4969`）。
- 文案保存：`PUT /api/transcriptions/{job}/transcript`（`web/art-text.js:4971-5040`）。
- AI 推荐：`POST/GET/DELETE /api/transcriptions/{job}/art-text/suggestions`（`web/art-text.js:5042-5411`）。
- 旧艺术字生成：`POST .../art-text` 或 `POST .../compose`（`web/art-text.js:5586-5660`）。顶层 B2 应只走 EditorSuite 的原子 compose。

## Required Ownership After B2

| Concern | Owner after B2 |
| --- | --- |
| confirmed art source/overlays | EditorProjectStore |
| selected clip/range/history | top-level TimelineController + Store |
| current time/seek/playback | MediaController |
| actual preview DOM | PreviewCompositor |
| compose DTO | `selectEditorFrame(snapshot).composition` |
| settings/AI/transcript inspector DOM | ArtTool |
| unconfirmed AI suggestions/form error/tab | ArtTool transient state |
| refresh recovery | top-level versioned Store draft adapter |
| legacy standalone media/timeline/messages | `/art-text` adapter until B4 |

## Migration Constraints

1. ArtTool must be root-scoped and lifecycle-owned; no top-level query/listener side effects at script evaluation.
2. Full-track operations build one next art/timeline state and dispatch once; per-cue dispatch would multiply revision/history.
3. Start/end fields and public timeline must share the same semantic range command and stable overlay id.
4. Text/template/font/layout/position changes do not change timingRevision.
5. AI draft preview cannot enter compose until confirm; accepted suggestions become Store overlays atomically.
6. Top-level ArtTool cannot access Web Storage or message APIs. A single Store recovery adapter replaces the child session draft.
7. Feature flag chooses top-level module or art iframe once at boot. PiP iframe remains active.
8. Legacy `/art-text` stays usable and reuses the shared model/renderer; deletion is deferred to B4.

## Required Browser Changes

- Existing `test_tool_switch_keeps_selection_preview_and_playback_position` locates `iframe[title="艺术字设置"]`; default B2 test must instead assert that iframe count is zero and operate inside the top-level art panel.
- B1 timeline test currently waits for art iframe ACK after range commit; B2 default path must assert a single Store action without ACK, while a separate feature-flag fallback test retains the ACK scenario.
- Revision-floor stale-art-message coverage remains only for fallback compatibility; default top-level behavior must prove no art message listener/bridge is required.
- Add top-level manual style/time/full-track/AI/refresh cases and keep the existing compose, media identity, 375px and external-network isolation assertions。

## Recommended Minimal Sequence

1. Extract/test shared art model and renderer while legacy page still owns UI.
2. Add atomic art commands and top-level recovery adapter.
3. Implement root-scoped ArtTool and its effect guards.
4. Mount behind feature flag, leaving art iframe fallback and PiP unchanged.
5. Convert browser workflows to the default top-level path; add explicit fallback/standalone tests.

This sequence preserves B0/B1 authority and provides a reload-only rollback without reintroducing iframe DOM/private payload as preview or compose inputs.
