# 单页编辑器统一媒体预览与时间轴

## Goal

在 B0 的 `EditorProjectStore` 之上建立唯一顶层媒体、公共预览和公共时间轴运行时。用户在文字剪辑、艺术字和画中画之间切换、保存或调整时间范围时，始终使用同一个基础视频、播放时钟、项目 revision 和时间轴文档；公共预览与最终 compose 不再因 iframe DOM/私有 payload 漂移。

## Background

- B0 已建立不可变项目快照、`revision` / `timingRevision`、effect guard、原子 compose selector 和 iframe revision/ACK 兼容桥。
- 顶层 `#cutPreviewVideo` 已是用户看到的公共基础视频，但播放帧时钟仍由 `app.js` 私有创建，`editor-suite.js` 另有事件+rAF 同步循环。
- 顶层仍创建第二个 `EditorTimeline` store，并从 iframe 的 `timelineHtml` 重建公共效果轨道。
- 公共 overlay 仍通过 iframe 的 `overlayHtml` 注入；Store 已有语义 art/pip overlay，但尚无顶层 compositor。
- Store authority 路径的 compose 已由 selector 派生，但 iframe 仍把语义状态包在私有 `generationPayload` 内供父页解析。

## Requirements

- R1. 新增唯一顶层 `MediaController`，绑定现有 `#cutPreviewVideo`，唯一拥有基础视频源变更、source/edited 时间转换和可取消播放帧时钟。
- R2. 新任务首次载入、显式清空或用户选择另一视频时允许更新媒体源；保存文案、保存版本、切换 cut/art/pip、普通 Store revision 和 iframe ACK 不得替换 `src` 或调用 `load()`。
- R3. 新增 `PreviewCompositor`，只消费同一 Store snapshot 的 `selectPreviewLayers` 语义模型，按当前 edited playback time 渲染艺术字与画中画，并支持已有选择、拖动、画中画缩放和视频素材同步。
- R4. 公共预览不得读取或注入 `overlayHtml`。art/pip 语义投影必须保留稳定 UI id、完整渲染字段和画中画素材 registry；Store 可用当前 job 素材作为初始回退，但新生成素材不得依赖 child `job-state` 整体 hydrate。compose selector 显式映射到原 API DTO，公开 payload 结构保持不变。
- R5. 新增唯一顶层 `TimelineController`，只消费同一 Store snapshot 的规范化 timeline document；公共 art/pip 轨道不得读取或注入 `timelineHtml`，`editor-suite.js` 不再持有第二个顶层 timeline store。
- R6. cut/art/pip 使用稳定 clip id 和同一 selection。选择、move、start resize、end resize、键盘微调、pointer cancel、undo/redo 由 TimelineController 形成事务，并通过语义适配器同步现有 cut UI 与 art/pip iframe；一次提交最多增加一次 project revision。
- R7. Pointer move 允许持有非权威临时预览；pointerup 才提交一次，pointercancel 恢复原始值且不增加 revision/history。时间边界继续复用 `EditorTimeline` 的 duration/minDuration/locked 规则。
- R8. 扩展 iframe `tool-state` 的公开语义字段 `source`、`overlays`、`assets`、`timeline`。Store authority 的父页不得读取 `generationPayload`；旧 HTML/私有字段可继续由子页发送，但仅作为 B2-B4 前的兼容输出。
- R9. 预览层、时间轴和 compose 必须由一次原子 editor frame selector 从同一 `snapshot.revision` 派生；DOM 暴露当前 revision 供真实浏览器回归核对。
- R10. 保留现有同源与 `contentWindow` 校验、iframe revision floor/ACK、独立 `/art-text` 和 `/picture-in-picture` 页面及 feature flag 回滚路径。
- R11. 不引入前端框架、bundler 或后端 API/schema 变更；继续使用有顺序的 `<script defer>` 与唯一 `window` 命名空间。

## Acceptance Criteria

- [x] AC1. 页面只创建一个顶层 MediaController 和一个播放帧时钟；重复 play 不产生第二循环，pause/seek/ended/emptied/destroy 正确取消旧回调并阻止迟到 callback。
- [x] AC2. 在非零时间、暂停和播放两种状态下依次切换 cut/art/pip、修改文案和保存版本，`#cutPreviewVideo` 节点、`src/currentSrc`、`currentTime` 与播放状态按操作语义保持，期间没有 `load()`。
- [x] AC3. 公共艺术字/画中画 DOM 由语义模型生成；`editor-suite.js` 和新 compositor 不消费 `overlayHtml`，Store authority 不读取 `generationPayload`。
- [x] AC4. 公共预览按当前时间显示正确 art/pip 项，艺术字文本/样式/字符动画与画中画图片/视频位置尺寸保持；顶层拖动/缩放后 Store、iframe 表单和 compose payload 一致。
- [x] AC5. 公共效果时间轴由规范化 timeline document 生成；`editor-suite.js` 不创建 `EditorTimeline.createStore()`，新 controller 不消费 `timelineHtml`。
- [x] AC6. cut/art/pip 的选择、移动、两端缩放、键盘微调、取消、交错 undo/redo 和 redo 分支截断均通过；删除当前 clip 才清空选择，非当前工具投影不抢占选择。
- [x] AC7. 每个已提交时间轴事务只产生一次 revision；时间变化只增加一次 `timingRevision`，iframe 回声和 ACK 不产生第二次提交。
- [x] AC8. 同一浏览器断言公共预览、公共时间轴与 compose request 的 `revision` 相同，cut ranges、art overlays 和 pip overlays 与 Store 当前快照一致。
- [x] AC9. 桌面与 375px 下工具切换不导航、不创建重复可交互时间轴、不横向溢出；现有 iframe identity 和独立页面入口保持。
- [x] AC10. 全部 `web/*.js` 通过语法检查；focused Node/静态/浏览器回归、完整 `tests/app` 和 `git diff --check` 通过。

## Out Of Scope

- 不把艺术字 inspector、生成逻辑和草稿迁出 iframe；属于 B2。
- 不把画中画 inspector、生成逻辑和草稿迁出 iframe；属于 B3。
- 不删除 iframe、`embedded=1`、`postMessage`、旧独立页面或兼容字段；属于 B4。
- 不改变文字字符级删除、声学吸附、二次确认、服务端 compose 或持久化语义。
- 不重排大文件、拆 CSS、引入框架或修改生产环境。

## Constraints And Risks

- 子工具在 B2/B3 前仍保留局部编辑状态；B1 必须把它们限制为 Store command 适配器，避免回声循环和双 revision。
- Art 当前 generation DTO 会删除本地 `id`；PiP compose overlay 只有 `assetId` 且新素材可能只存在 child runtime。B1 必须保留独立的完整语义预览模型，再显式投影 compose DTO。
- 艺术字预览包含模板样式和逐字动画；顶层 renderer 必须复用或等价迁移现有纯渲染逻辑，不能退化为普通文本。
- cut 的语义历史覆盖文字/空白删除，而 TimelineController 只统一时间轴事务；适配时不得破坏既有全局 cut undo/redo 行为。
