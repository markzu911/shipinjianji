# 单页编辑器旧运行时清理技术设计

## 1. Target Architecture

```text
index.html
  EditorProjectStore          <- project state/revision authority
  MediaController             <- one base video and playback clock
  PreviewCompositor           <- art + pip preview layers
  TimelineController          <- one public timeline/history
  EditorSuite                 <- navigation, hydration, compose and lifecycle
    ArtTool.mount(root, services)
    PipTool.mount(root, services)

/art-text --------------------307----> /?tool=art
/picture-in-picture ----------307----> /?tool=pip
```

删除后的产品中不存在 child editor document、tool iframe 或 bridge adapter。ArtTool/PipTool 只通过已注入 services 读写顶层 Store；公共 preview、timeline 与 compose 继续消费 `selectEditorFrame(snapshot)`。

## 2. Runtime Ownership Collapse

| Concern | B3 迁移期 | B4 唯一 owner |
| --- | --- | --- |
| project art/pip state | Store + legacy child projection | EditorProjectStore |
| base media/playback | MediaController + legacy page video | MediaController |
| timeline | TimelineController + legacy child stores/document | TimelineController |
| preview | PreviewCompositor + mirrored/child DOM | PreviewCompositor |
| compose payload | Store frame + legacy private payload fallback | Store frame composition selector |
| inspector | top-level tool or flag-selected iframe | ArtTool / PipTool |
| recovery | versioned top-level project draft + child storage | versioned top-level project draft |

`toolStates` 如果只服务于 legacy projection 则整体删除；顶层工具状态从 snapshot/frame 和 tool lifecycle 读取。`legacyTimelineDocument`、`frameEntries`、`toolBridgeRevisions`、`desiredToolUrls` 中只为 iframe 服务的职责一并删除。

## 3. EditorSuite Simplification

初始化前置条件变为顶层页面必须具备 Store 和两个工具依赖；不再根据全局 feature flags 建立 alternate authority。

```javascript
const projectStore = EditorProjectStore.createStore(...);
const artTool = ArtTool.mount(artPanelRoot, createArtToolServices({ requestedTemplate }));
const pipTool = PipTool.mount(pipPanelRoot, createPipToolServices());
```

- `openTool(name)` 只切换 cut stack、art root、pip root 的 active/hidden/inert 状态，并写入 `history.pushState`。
- tool links 直接使用顶层 deep link；`toolFromHref()` 读取同源 `/` URL 的 `tool=art|pip`，不识别旧页面路径作为内部运行时。
- `popstate` 从当前 URL 恢复 active tool；无效/不可用 tool 回退 cut。
- `renderJobState()` 始终 hydrate Store；`renderEditorFrame()` 始终渲染唯一 media/preview/timeline 和两个工具。
- 删除 `projectStoreEnabled` 分支、legacy compose projection、mirrored playback、iframe sync time、message handler、child CustomEvent adapter 和 unload 时的 frame cleanup。
- 保留仍有调用者的同文档 `editor-suite:refresh`、`editor-suite:transcript-updated` 与 job-state 事件；逐个以 `rg` 和行为测试确认后再删除确实无消费者的监听，不按字符串前缀批量清理。

## 4. Legacy URL Redirect Contract

FastAPI 页面路由使用 `RedirectResponse`，只改页面入口，不触碰 API router：

```text
GET /art-text?<query>
  preserve query pairs
  delete embedded and conflicting tool
  set tool=art
  -> 307 /?<query>&tool=art

GET /picture-in-picture?<query>
  preserve query pairs
  delete embedded and conflicting tool
  set tool=pip
  -> 307 /?<query>&tool=pip
```

Query 由结构化 URL encoder 构造，不拼接未转义字符串。至少覆盖空 query、job/source、已有冲突 tool、`embedded=1` 和完整模板字段。重定向 location 使用相对同源 URL，不接受目标 host 参数，因此不存在开放重定向。

内部链接直接生成目标顶层 URL，避免先命中 307：

- `app.js` 的原始/剪后艺术字、画中画入口；
- `editor-suite.js` 的 job tool links；
- `art-template-library.js` 的返回编辑器和使用模板入口。

## 5. Requested Art Template Handoff

顶层 URL adapter 是唯一 query parser：

```javascript
parseRequestedArtTemplate(location.search) -> {
  id, color, strokeColor, font, fontSize
} | null
```

解析结果作为只读 `services.initialTemplateSelection` 注入 ArtTool。ArtTool 保留 `pendingTemplateSelection`，在 `loadCatalogs()` 完成后调用一次 `consumeInitialTemplateSelection()`：

1. template id 必须存在于实际 catalog；否则不应用请求。
2. color/stroke 使用现有颜色 normalize；font 必须存在于字体 catalog；fontSize clamp 到现有 20-180。
3. 合并 catalog 的 template effects，不能信任 URL 注入 animation/layout 任意对象。
4. 若选中 manual overlay，只 patch 该 id；若选中 transcript-track overlay，按稳定 `trackId` patch 全轨；一次 `replaceArt` transaction 保持 range/source anchors。
5. 若当前没有 overlay，把规范化设置保存为 ArtTool 会话内首选，供新增 manual overlay 和全文轨道使用；不新增 storage authority。
6. 标记请求已消费，后续 catalog render、activate 或 Store update 不重复 dispatch。

模板请求只改变样式字段，所以 project revision 最多增加一次，`timingRevision` 必须不变。模板库继续写现有 `preferredArtTemplateId/settings` 可供管理页显示，但顶层编辑器的权威应用来自显式 query handoff。

## 6. Resource And Cache Cleanup

物理删除：

```text
web/art-text.html
web/art-text.js
web/picture-in-picture.html
web/picture-in-picture.js
```

同步删除 `disable_frontend_cache` 中四个静态资源项与旧页面 HTML 项；保留 `/art-text`、`/picture-in-picture` 页面 route 自身的 no-store 行为可由重定向响应测试决定，API cache 规则不变。`index.html` 继续只加载共享 model/renderer/tool/suite 脚本。

测试不得再读取已删除文件。资源测试改为断言文件不存在、旧 URL 返回预期 redirect、redirect destination 加载顶层工具，以及仓库运行时源码不含被删除的 bridge 标记。

## 7. Test Migration

### Static / Route

- 删除 legacy art/pip 页面大段字符串契约，替换为资源缺失和 no-cache 清单清理断言。
- 断言两个历史页面 URL 的 307 Location、query 保留/覆盖/剔除规则，并单独断言同名 API 仍返回原状态码/schema。
- 断言 EditorSuite 不含 iframe 创建、`postMessage`、`addEventListener("message")`、`embedded`、`timelineHtml`、`overlayHtml`、`generationPayload`、fallback feature flags 和 legacy state owners。
- Node 覆盖 template parser、catalog 后一次消费、manual/track/no-selection、无效参数和 timingRevision 不变。

### Browser

- 把 fallback/standalone 三个用例改写为历史 URL redirect、顶层 deep link 和模板库 handoff 用例。
- 把 `test_text_edit_preserves_media_iframes_and_effect_timing` 改为保存文字时 document/video/tool root identity 与 effect timing 保持，且 iframe count 始终为 0。
- 继续覆盖 paused/playing、cut/art/pip 切换、selection、公共 preview/timeline、undo/redo、compose 与刷新恢复。
- 桌面和 375px 都从历史 URL与顶层深链进入，检查无二次导航、无 video reload、无横向溢出与隐藏面板 inert。

## 8. Compatibility And Rollback

- B4 不保留运行时 fallback flag；旧页面恢复只能通过 revert B4 独立提交完成。
- B0-B3 的 Store、media、preview、timeline、ArtTool、PipTool 和 draft schema 不回退。
- 实施顺序先让内部链接与模板 query 完整进入顶层，再删除 bridge 和旧文件；任一步失败都可在删除前通过 focused browser test 定位。
- 生产环境不部署、不重启、不修改；只提交 develop 分支代码。

## 9. Main Risks

- `editor-suite:*` 同时包含跨页 message 和同文档事件/storage key；按前缀全删会破坏刷新、文字更新或草稿恢复。
- EditorSuite 的 fallback 分支与正常分支交错，删除时若误删 Store hydrate/compose 代码，静态测试可能通过但真实编辑会丢状态，因此必须依赖 frame 与浏览器请求体断言。
- 模板参数必须等 catalog 后校验；初始化时直接应用会把服务器自定义模板或字体误判为无效。
- 删除巨型文件会造成大 diff；应把产品清理、测试迁移和 spec 更新分提交，便于审查与回滚。
