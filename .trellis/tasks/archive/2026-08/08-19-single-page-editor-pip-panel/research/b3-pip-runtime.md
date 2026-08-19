# B3 画中画运行时证据

## Scope Source

- 父路线 B3 要求 `PipTool.mount(root, services)`、同一 preview/timeline/store/media controller、素材生成与选择、拖动、无上限缩放、时间调整、art+pip 预览、统一生成和 feature flag fallback（`.trellis/tasks/08-13-project-optimization-audit/implement.md:49`）。
- B4 才删除 iframe、`embedded=1`、postMessage、旧页面/资源和旧 URL（同文件 `:55`）。
- 用户此前明确要求画中画放大不设置上限；本任务必须把该要求落实到前端、Store、预览和后端生成，而不是只改一个常量。

## Current Top-Level Runtime

- `EditorProjectStore` 已归一化 pip assets/overlays，用 `assetId/imageId` 生成稳定语义 id，并把 pip tracks 放在 cut/art 后（`web/editor-project-store.js:72`、`:85`、`:205`、`:239`）。
- `PIP_STATE_CHANGED`、`TIMELINE_CLIP_RANGE_CHANGED` 和 selectors 已能从同一 revision 产生 preview/timeline/compose（`web/editor-project-store.js:701`、`:732`、`:889`、`:919`、`:939`）。
- EditorSuite 已拥有唯一 project Store、MediaController、PreviewCompositor 和 TimelineController；B2 默认 mount ArtTool，但 pip 仍在 iframe（`web/editor-suite.js:137`、`:148`、`:154`、`:159`、`:168`、`:182`）。
- `renderEditorFrame` 同时把同一个 frame 交给 media/preview/timeline/art；顶层 pip 模块只需加入同一调用点（`web/editor-suite.js:1322`）。
- 公共 PreviewCompositor 已能按 asset registry 创建 image/video，按 overlay id 更新 pip DOM，并提供 select/move/resize 回调（`web/editor-preview-compositor.js:623`、`:640`、`:670`）。

## Legacy Ownership Inventory

`web/picture-in-picture.js` 当前 2,503 行并包含约 75 个顶层 DOM 查询。它同时拥有：

- 第二个 video、外部播放控件和播放事件（`:22`、`:524`、`:2451`）。
- 第二个 `EditorTimeline.createStore`、timeline DOM、pointer session、ruler 和 thumbnail frame extraction（`:127`、`:585`、`:728`、`:830`、`:857`）。
- URL/source/`embedded=1` 分支、sessionStorage draft、postMessage state/ACK bridge 和顶层 message listener（`:90`、`:1254`、`:1353`、`:1463`、`:1574`）。
- 页面级 `initialize()`、直接 fetch、素材轮询、最终 pip job 轮询/取消和独立 `generateVideo()`（`:1851`、`:1910`、`:2016`、`:2122`、`:2140`、`:2160`、`:2283`、`:2503`）。

因此不能把旧脚本直接加载进主页面。PipTool 必须只迁移 inspector/effects，并由注入 services 替换上述 runtime ownership。

## Asset And Overlay Semantics

- 服务端 job 用 `pictureInPictureImages`、`pictureInPictureVideos` 保存素材记录；`pictureInPicture.overlays` 保存实际合成选择（`web/editor-project-store.js:247`）。
- 旧页把 image/video records 合并为 `pictureItems`，用渲染结果决定 enabled；无渲染选择时默认 ready assets enabled（`web/picture-in-picture.js:2240`）。
- image create 直接返回 ready record；video create 可返回 queued/processing，旧页每 2 秒读取 job，terminal 后停止，错误 3.5 秒重试（`:1910`、`:1998`、`:2016`）。
- compose DTO 已明确只发送 asset/time/position/width 字段，不发送 URL/status（`web/editor-project-store.js:906`）。

迁移结论：Store `assets` 保存全量素材，`overlays` 保存 enabled 子集；状态合并按 stable asset id，不保留 `pictureItems` 第二份权威数组。

## API And Effect Inventory

- `POST /api/transcriptions/{job}/picture-in-picture/prompt`：提示词草稿，发送 text、edited range、assetType、source、aspectRatio 和 source anchors（`web/picture-in-picture.js:1873`）。
- `POST .../images|videos`：素材创建；图片通常 ready，视频可 queued（`:1946`）。
- `GET /api/transcriptions/{job}`：视频素材状态轮询（`:2020`）。
- `POST .../compose`：当前顶层统一生成所有 cut/art/pip；B3 不调用 legacy `/picture-in-picture` 最终生成路径（`web/editor-suite.js:1052`、`web/picture-in-picture.js:2160`）。
- `POST .../cancel`：顶层 generation modal 已处理统一 compose 取消；PipTool 只需取消本地素材请求/轮询，不建立第二个最终生成 lifecycle。

迁移结论：prompt/create/poll 进入 PipTool effect；最终 compose/poll/cancel 保持 EditorSuite ownership。

## Unlimited Enlargement Gap

现有实现有四层不一致：

1. `PIP_MAX_WIDTH = Infinity`，但 legacy size range 仍是 `max=55`（`web/picture-in-picture.js:88`、`:1783`）。
2. legacy pointer resize 用中心到边缘的 `maximumPictureWidthAtPosition`，素材被强制完整留在舞台内（`:304`、`:315`）。
3. 顶层镜像 pointer resize 写死 0.55 并受舞台剩余空间限制（`web/editor-suite.js:2084`）。
4. 后端 normalize 接受 finite 后仍要求 `0.15 <= width <= 0.65`（`server/app.py:6985`、`:6992`）。

FFmpeg 当前坐标为 `max(0,min(main_w-overlay_w,center-overlay_w/2))`（`server/app.py:7165`）。当 overlay 大于 main 时 `main_w-overlay_w` 为负，公式最终固定为 0，无法按中心点裁切。

迁移结论：移除所有产品最大值；保留 finite/minimum；前端以中心定位 + overflow crop 渲染，FFmpeg 使用正负边界通用 clamp。无 `max` 的 number input 保证 overlay 边角移出舞台后仍可精确缩回。

## Draft And Compatibility

- B2 当前唯一 key 是 `editor-suite:project-draft:<jobId>`，schema v1 只保存 art 与 art selection（`web/editor-suite.js:247`、`:300`、`:337`）。
- Pip legacy 另存 `sessionStorage` key（`web/picture-in-picture.js:1254`），顶层 PipTool 禁止继续使用。
- 当前 feature flag 只有 art；默认 pip 始终 `ensureToolFrame`（`web/editor-suite.js:148`、`:1549`）。
- 独立 `/picture-in-picture` 和大量静态契约仍存在（`tests/app/test_frontend_contracts.py:1077`），B3 必须保留。

迁移结论：EditorSuite draft 升 schema v2 并兼容 v1；新增独立 `topLevelPipEnabled`，默认 panel、false fallback，standalone 不变。

## Existing Coverage And Required Delta

- 当前真实浏览器覆盖三工具切换、iframe pip 选择、art+pip preview、统一 compose、文字修改保持 pip timing、375px 与 revision floor（`tests/app/browser/test_editor_workflows.py:111`、`:713`、`:811`、`:938`、`:1174`）。
- 后端覆盖 prompt/image/video asset、poll result、render、retimed range 和 compose（`tests/app/test_picture_in_picture.py`、`tests/app/test_composition.py`）。
- 静态契约当前明确要求 legacy `pipTimelineStore`、embedded draft/message、55% resize 和 standalone DOM；顶层迁移后应把默认路径断言改为 PipTool，同时单独保留 legacy page 契约（`tests/app/test_frontend_contracts.py:1077`、`:3064`）。

Required delta：新增 pure Pip model/PipTool lifecycle；把浏览器 iframe 操作改为顶层 panel；mock prompt/image/video polling；新增 175% width、schema v2/v1、fallback/standalone、late response、media identity 和中心裁切覆盖。
