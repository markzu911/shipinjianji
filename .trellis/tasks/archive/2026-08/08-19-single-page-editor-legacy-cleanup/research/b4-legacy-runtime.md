# B4 旧运行时清理证据

## Query

确认 B3 后仍存在哪些多页面/iframe 兼容职责、哪些资源和测试应删除、历史 URL 与模板库入口如何保持兼容，以及哪些 `editor-suite:*` 契约不能被误删。

## Completed Prerequisites

- B0-B3 已完成顶层 `EditorProjectStore`、唯一媒体/预览/时间轴、`ArtTool` 和 `PipTool`；B3 完整回归为 `232 passed, 1 xfailed`。
- 默认 art/pip browser tests 已断言对应 iframe 为 0（`tests/app/browser/test_editor_workflows.py:131`、`:151`、`:206`）。
- 父路线把 B4 定义为删除 iframe、`embedded=1`、message、私有 HTML/payload、旧页面/资源，并把历史 URL redirect 到顶层工具（`.trellis/tasks/08-13-project-optimization-audit/design.md:94`、`implement.md:55`）。

## Legacy Resource Inventory

| Resource | Current size | Legacy ownership |
| --- | ---: | --- |
| `web/art-text.html` | 859 lines / 38,125 bytes | standalone art document/video/timeline shell |
| `web/art-text.js` | 6,134 lines / 216,295 bytes | child Store/video/timeline/storage/message/generation |
| `web/picture-in-picture.html` | 322 lines / 18,184 bytes | standalone pip document/video/timeline shell |
| `web/picture-in-picture.js` | 2,513 lines / 92,587 bytes | child Store/video/timeline/storage/message/generation |

这些职责已由顶层共享模块覆盖；保留文件只继续维持 fallback/standalone 第二运行时。

## EditorSuite Legacy Inventory

`web/editor-suite.js` 当前 2,905 行，仍包含：

- `embeddedEditor`、`frameEntries`、`toolBridgeRevisions`、`legacyTimelineDocument` 与 `projectStoreEnabled`（`:10`、`:116`、`:118`、`:135`、`:139`）。
- art/pip fallback flags 和 `legacyToolNames()`（`:150-164`）。
- frame projection/ACK 与 `postMessage`（`:228-244`）。
- `embeddedUrl()`、`createToolFrame()`、`ensureToolFrame()`（`:1412-1502`）。
- 旧页面 tool href 生成（`:1900`、`:1905`）。
- embedded tool navigation 和全局 `message` handler（`:2125-2310`）。
- frame playback、preview drag/resize、timeline command forwarding（`:2313-2768`）。
- `projectStoreEnabled/topLevelArtEnabled/topLevelPipEnabled` 对外探针与 legacy transcript refresh projection（`:2844-2901`）。

B4 目标是删除这些 alternate branches，使 EditorSuite 只保留顶层 frame/store/controller 流程。

## Server And Internal Links

- `server/app.py:401-406` 的 no-cache 集合仍列出旧页面和旧 JS。
- `server/app.py:11718-11725` 仍直接返回两个旧 HTML，需改为同源 query-preserving redirect。
- `web/app.js:4732-4734`、`:4849-4851` 仍生成 `/art-text` 与 `/picture-in-picture` 链接。
- `web/editor-suite.js:1900-1905` 仍给 tool links 设置旧页面 URL。
- API routes 位于 `server/app.py:10803-11693`，必须完整保留；页面路由清理不能用宽泛字符串删除。

## Template Library Compatibility Gap

- `web/art-template-library.js:104` 的“返回编辑器”仍指向 `/art-text`。
- `web/art-template-library.js:511-518` 的“使用模板”跳转 `/art-text`，携带 `template`、`templateColor`、`templateStroke`、`templateFont`、`templateSize`。
- 旧消费函数 `applyRequestedTemplateSelection()` 位于 `web/art-text.js:649-722`：catalog 后校验 style/font/size/color，更新 selected overlay/track 和首选模板。
- 顶层 `ArtTool` 在 `web/editor-art-tool.js:493-518` 加载 catalog，但当前没有 query/config handoff，也不消费 `preferredArtTemplateId`。

迁移结论：模板库先改顶层 deep link，EditorSuite 解析为结构化 initial selection 并注入 ArtTool；ArtTool 等 catalog 后一次消费。不能让 root-scoped tool 自己拥有 URL parsing，也不能只依赖 localStorage，因为显式链接参数才是当前操作意图。

## Tests To Replace

Browser transitional cases：

- `test_pip_iframe_fallback_and_standalone_page_remain_usable`（`:1174`）。
- `test_text_edit_preserves_media_iframes_and_effect_timing`（`:1404`），保留行为目标但改为顶层 identity/no iframe。
- `test_iframe_revision_floor_rejects_stale_state_and_acks_local_edits`（`:1767`）。
- `test_standalone_art_page_keeps_legacy_editor_with_shared_renderer`（`:1899`）。

Static transitional sections：

- `test_editor_suite_frontend_contracts` 中 embedded/frame/message 断言（`tests/app/test_frontend_contracts.py:170` 起）。
- `test_top_level_art_and_pip_tools_have_single_authority_and_legacy_fallback`（`:761`）。
- legacy art/pip page resource tests 和 Store bridge assertions（`:830`、`:1117`、`:3103` 附近）。

替换后必须覆盖资源物理缺失、redirect/query、template handoff、源码无 bridge/flags、深链直达、媒体 identity、desktop/375px 和统一 compose，不能仅删除旧断言。

## Strings That May Remain

不能按 `editor-suite:` 前缀整体删除：

- `editor-suite:refresh`：同文档刷新通知。
- `editor-suite:transcript-updated`：同文档文字更新通知；是否仍需 listener 应按调用者核对。
- `editor-suite:job-state`：同文档 CustomEvent。
- `editor-suite:project-draft:<jobId>`：唯一版本化项目草稿 key。

应删除的是跨 window message types、ACK/revision floor、iframe projections 和 `window.message` 处理。每个剩余字符串必须能指向同文档调用者或持久化契约。

## Recommended Sequence

1. 先写 redirect 与 template handoff 回归，迁移模板库/internal links。
2. 让 EditorSuite 顶层路径成为无分支唯一 authority。
3. 删除 iframe/message/legacy projection 和旧资源。
4. 替换 transitional static/browser tests，更新 specs。
5. 跑完整 browser/app、JS syntax、diff 与 Trellis gate，再分提交归档。

这个顺序避免先删除唯一仍消费模板 query 的旧页面，也让 API 路由和顶层行为在大规模文件删除前已有保护。
