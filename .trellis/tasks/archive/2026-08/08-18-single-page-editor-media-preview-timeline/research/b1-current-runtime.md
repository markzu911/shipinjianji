# B1 当前媒体、预览与时间轴运行时研究

- Date: 2026-08-18
- Scope: B1 顶层统一运行时，只读检查

## 结论

B0 已统一项目/compose authority，但顶层 view/runtime 仍有三处副本：`app.js` 私有帧时钟、`editor-suite.js` 私有 timeline store，以及 iframe HTML snapshot 驱动的公共 preview/timeline。B1 最小正确边界是把这三处改为显式 controller，并保留 iframe 作为 inspector/command adapter。

## 媒体证据

- `web/index.html:350` 的 `#cutPreviewVideo` 是公共基础视频。
- `web/app.js:3828` 定义可取消帧时钟，`web/app.js:3961` 私有创建；它已有 rVFC/RAF/timeupdate 降级和 generation guard。
- `web/editor-suite.js:1064` 另建 rAF，把同一 video time 推给 iframe/镜像媒体。
- `web/app.js:4756-4758` 在 job 结果载入时直接设置 src/load；`web/app.js:4559-4561` 清空时直接 pause/remove src/load。
- `web/editor-suite.js:794-831` 重复实现 source/edited 时间转换。

## 公共预览证据

- `web/editor-suite.js:934-997` 从 `toolStates.overlayHtml` 创建 canvas 并设置 `innerHTML`。
- Art 在 `web/art-text.js:2859-2911` 创建 `.preview-overlay`，并于 `:2920` 发布 innerHTML。
- PiP 在 `web/picture-in-picture.js:1014-1063` 创建 `.pip-preview-item`，于 `:1158` 发布 innerHTML。
- Art 语义 renderer 还包含 `renderArtTextCharacters` (`web/art-text.js:412`)、`applyPreviewStyle` (`:2230`) 和 `positionPreviewOverlay` (`:2385`)；B1 顶层实现不能退化这些效果。
- Art generation DTO 在 `web/art-text.js:2936-2939` 删除本地 `id`，顶层无法可靠关联 selection/timeline；B1 semantic projection 必须保留 id，再由 compose selector删除。
- PiP compose overlay 仅包含 assetId/time/x/y/width (`web/picture-in-picture.js:1174-1187`)；实际 URL/type 在 child `pictureItems` 中。Store 模式收到 child `job-state` 时不会整体 hydrate (`web/editor-suite.js:1472-1495`)，所以 B1 tool-state 需直接发布素材 registry，不能只 join 旧 job。

## 时间轴证据

- `web/timeline-model.js:98` 提供 normalize/store/selection/range/pointer session，但 `commit()` 只有 callback，没有 history/undo/redo/cancel rollback。
- `web/editor-project-store.js:378` 合并 timeline kind，`:593` 已有规范化 selector。
- `web/editor-suite.js:133` 又创建 timeline store；`:999` 从 iframe `timelineHtml` 重建公共效果 DOM；`:1824` 自行处理选择、move、resize。
- Cut 在 `web/app.js:229` 持有私有 store，真实状态仍为 `timelineDeleteRanges`/`selectedTimelineRangeId`；`:3168` 重建，`:3500` 新建选区，`:3597` 调整，`:3752` 键盘修改。
- Art 在 `web/art-text.js:200`、PiP 在 `web/picture-in-picture.js:127` 各持有局部 store；这些局部 store 在 B2/B3 前保留为 inspector adapter。
- Cut 的 undo/redo 是独立语义历史 (`web/app.js:2719`)；Art/PiP commit 只保存局部草稿。B1 需为顶层跨轨道时间事务增加统一 history，同时不破坏 cut 的非时间轴历史。

## 当前测试与缺口

- `tests/app/test_frontend_contracts.py:2737` 覆盖 EditorTimeline selection/move/resize/boundary/persistence，但未覆盖 controller/history/cancel。
- `tests/app/test_editor_project_store.py` 覆盖不可变、revision、竞态和 compose；组合 timeline 尚未覆盖三类轨道、history、稳定 UI id、preview asset registry 和显式 compose DTO 映射。
- `tests/app/browser/test_editor_workflows.py:82` 验证 iframe 选择、公共预览和播放时间保持；未验证顶层时间轴 move/resize/cancel/undo/redo。
- 浏览器测试必须新增 video `load()` 监控、公共 DOM revision 与 compose revision 对齐、semantic renderer、跨轨道事务和 375px 验证。

## 迁移限制

- 不迁移 Art/PiP inspector、生成逻辑和 sessionStorage 草稿。
- 不删除 iframe、独立 URL、postMessage 或 legacy fields。
- 不改变 cut 字符/声学/二次确认语义。
- 不在 frame 热路径重跑 selectors 或重建 timeline。
