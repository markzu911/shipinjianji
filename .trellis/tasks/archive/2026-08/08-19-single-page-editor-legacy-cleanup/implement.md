# 单页编辑器旧运行时清理实施计划

## Step 1. Compatibility Tests And Template Handoff

- [x] 先新增历史页面 URL redirect、query 保留/`embedded` 剔除和 API 路由不受影响的 route tests。
- [x] 为顶层 URL adapter 增加 requested art template 解析，并通过 services/config 注入 ArtTool；ArtTool 自身不读 URL。
- [x] 在 catalog 完成后一次校验/消费模板请求，覆盖 manual、transcript track、无 selection、无效 template/font/color/size 与 timingRevision 不变。
- [x] 更新模板库返回/使用模板 URL 为 `/?job=<id>&tool=art`，保留 source 和完整模板参数。

## Step 2. Top-Level Navigation As The Only Path

- [x] 更新 `app.js` 与 EditorSuite tool links，全部生成顶层 `/?job=<id>&tool=art|pip` deep link。
- [x] 简化 `toolFromHref`、`openTool`、`popstate` 和 active panel lifecycle，只切换 cut/art/pip 顶层 root 与 URL。
- [x] 移除 `projectStoreEnabled`、art/pip top-level feature flag 和 alternate hydrate/render/compose 分支；启动时唯一创建 Store、ArtTool 与 PipTool。
- [x] 保留同文档 refresh/transcript/job event 和 project draft key，逐个确认消费者，不批量删除 `editor-suite:*`。

## Step 3. Delete Iframe And Bridge Runtime

- [x] 删除 `frameEntries`、`toolBridgeRevisions`、`desiredToolUrls`、`legacyTimelineDocument`、legacy `toolStates` 和 frame create/ensure/refresh lifecycle。
- [x] 删除 `embeddedUrl`、frame cut/time/text projection、revision floor/ACK、`postMessage`、`window.message` listener、child tool/job state handler。
- [x] 删除 mirrored preview/timeline/playback/drag/resize 与 legacy composition projection；公共 renderer/controller 只读 editor frame。
- [x] 确认 EditorSuite 不再出现 `embedded`、iframe、`timelineHtml`、`overlayHtml` 或私有 `generationPayload`。

## Step 4. Redirect Routes And Legacy Resource Deletion

- [x] 把 `/art-text` 与 `/picture-in-picture` 页面 handler 改为结构化 query redirect，保留 job/source/template 参数、覆盖 tool、移除 embedded。
- [x] 物理删除 `art-text.html/js` 和 `picture-in-picture.html/js`；不得修改同名 `/api/transcriptions/...` 业务 routes。
- [x] 清理 server no-cache 旧资源项、旧 HTML 版本引用和仓库内旧页面内部链接。
- [x] 用 `rg` 复核剩余 `editor-suite:*` 都是同文档事件或 project draft，不残留跨页 message 协议。

## Step 5. Replace Transitional Tests

- [x] 删除/改写静态 legacy page、iframe fallback、standalone 和 bridge revision 字符串断言，新增“旧文件不存在 + 唯一顶层运行时”契约。
- [x] 将 browser fallback/standalone/revision-floor 用例替换为历史 redirect、deep link、template-library handoff 和无 iframe 行为。
- [x] 改写文字保存回归：document/video/ArtTool/PipTool identity、src/currentTime/play state、art/pip timing 和 compose 保持，video `load()` 为 0。
- [x] 覆盖桌面与 375px 的 cut/art/pip 切换、隐藏面板 inert、无横向溢出、刷新、公共 timeline/preview 和统一 compose。

## Step 6. Specs, Full Verification And Commits

- [x] 更新 frontend architecture/state 与 browser workflow specs，删除迁移期 iframe/fallback/standalone 契约，记录唯一顶层 runtime 与 redirect/template compatibility。
- [x] 运行 focused route/template/frontend/browser tests、全部 browser、全部 app、全量 JS syntax、diff 和 Trellis validation。
- [x] 确认唯一 xfail 仍是 Phase A 服务重启恢复；开发服务 8001 可加载修改后代码，生产环境不动。
- [x] 按产品清理、测试、spec/task archive 和 journal 分提交，B4 可独立 revert。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_art_model.py tests/app/test_editor_project_store.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q tests/app
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
rg -n "postMessage|addEventListener\(\"message\"|embedded=1|timelineHtml|overlayHtml|generationPayload|__EDITOR_(PROJECT_STORE|ART_PANEL|PIP_PANEL)_ENABLED__" web tests/app
git diff --check
py -3 ./.trellis/scripts/task.py validate 08-19-single-page-editor-legacy-cleanup
```

Focused test filenames可按实现中新建/合并的实际文件调整；template handoff 使用真实浏览器行为覆盖，不用静态字符串断言替代。`rg` 结果允许同文档草稿 key、历史 URL 输入和明确的负向断言，任何产品代码跨页 message/iframe 命中必须解释或删除。

## Review Gates

- [x] 运行 DOM 中工具 iframe 数量恒为 0，源码没有 iframe lifecycle、跨页 message、bridge revision/ACK 或 legacy mirror owner。
- [x] Store/ArtTool/PipTool 是无 feature flag fallback 的唯一 authority，公共 preview/timeline/compose 消费同一 frame revision。
- [x] 两个历史页面 URL 正确 redirect，query 兼容且 API routes 完全不受影响。
- [x] 模板库进入顶层 ArtTool 后合法样式一次应用、无效值安全回退、无 selection 有明确默认语义、timingRevision 不变。
- [x] 四个旧文件和对应 no-cache/static assertions 已删除，仓库不存在内部旧页面链接。
- [x] 文字保存和工具切换不导航、不 reload video、不重置播放状态、不改变无关 art/pip timing。
- [x] 桌面与 375px 的深链、历史 redirect、模板、切换、恢复和 compose 均通过真实浏览器验证。
- [x] 未改生产环境、未改公开 art/pip API、未开始 B4 以外的重构。

## Suggested Commit Boundaries

1. `refactor(frontend): 移除编辑器 iframe 兼容运行时`
2. `feat(frontend): 保留旧工具链接与模板深链兼容`
3. `test(frontend): 覆盖单页唯一运行时清理`
4. `docs(trellis): 记录单页编辑器最终边界`

## Rollback Points

- 模板 deep link 和页面 redirect 可以先独立验证；若旧资源删除前失败，不进入 Step 3/4。
- B4 整体回滚通过 revert 对应独立提交恢复迁移期 adapter；不在新代码中保留 dormant fallback。
- 回滚不得撤销 B0-B3 已验证的 Store、MediaController、PreviewCompositor、TimelineController、ArtTool 与 PipTool。
