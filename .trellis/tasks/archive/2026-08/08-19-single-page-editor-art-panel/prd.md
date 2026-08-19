# 单页编辑器艺术字面板迁移

## Goal

在 B0/B1 的单一 `EditorProjectStore`、MediaController、PreviewCompositor 和 TimelineController 之上，把艺术字 inspector 从 iframe 迁入 `index.html` 的顶层文档。用户添加、选择、编辑、拖动、调整时间、生成全文轨道或采用 AI 推荐时，只操作同一份项目状态、同一个基础视频、同一个公共预览和同一个公共时间轴；切换工具不导航、不重载媒体，也不再启动艺术字子页面运行时。

## Background

- B1 已完成唯一媒体、公共预览、公共时间轴和原子 editor frame；顶层 preview/timeline/compose 已从同一 Store revision 派生。
- `web/art-text.js` 当前有 6107 行、约 130 个顶层 DOM 查询和 92 个事件监听；脚本加载即创建 `artTimelineStore`、读取 URL/DOM、注册全局监听并调用 `initialize()`，不能直接挂到主页面。
- 现有艺术字 iframe 仍拥有独立 `#artVideo`、时间轴、sessionStorage 草稿、overlay 数组、轮询和 `embeddedEditor`/`postMessage` 适配逻辑；这些是 B2 要消除的重复运行时。
- `web/index.html` 已有 `#editorSuiteInspectorHost`，B1 的公共视频 `#cutPreviewVideo`、`#editorSuitePreviewOverlay` 和 `#editorSuiteTimelineLayer` 已具备艺术字显示与交互能力。
- 服务端艺术字、全文轨道、AI 推荐、字体、模板和位置预设 API 已存在；B2 保持这些公开 API/schema 不变。
- 父任务已确认迁移顺序与兼容策略：B2 先迁艺术字，B3 再迁画中画，B4 才删除全部 iframe/消息协议并重定向旧工具 URL。

## Requirements

- R1. 新增 `window.ArtTool.mount(root, services)` 可挂载模块；返回 `activate()`、`deactivate()`、`render(frame)` 和 `destroy()`。模块所有 DOM 查询必须限定在 `root`，所有全局/媒体订阅必须可撤销，重复 mount/destroy 不残留监听、轮询或 DOM。
- R2. 顶层艺术字 panel 保留现有核心能力：手动添加/删除/选择、文字和样式、字体、字号、描边、排版、位置与位置预设、起止时间、匹配文案、批量应用、全文艺术字轨道、保留文案编辑、AI 推荐预览/确认/取消。
- R3. 顶层 panel 不创建 video、媒体控制器、时间轴 store、时间轴 DOM、结果 video 或独立生成按钮。定位/试听只调用注入的 MediaController；范围/选择只调用顶层 TimelineController/Store command；最终生成继续使用工作台统一 compose 按钮。
- R4. `EditorProjectStore.project.art` 是已确认艺术字状态的唯一会话权威。ArtTool 只能保留 tab、表单焦点、AI 待确认项、busy/error 等瞬时 UI；不得持有可覆盖 Store 的第二份 overlays、selection 或 timeline。
- R5. 艺术字新增、样式/文字/位置修改、删除和 AI 确认各形成一次语义 Store 提交；非时间样式只增加一次 `revision` 且不增加 `timingRevision`，时间范围变化只通过统一 range command 提交并增加一次 `revision/timingRevision`。
- R6. overlay 保留稳定 UI id、`sourceStart/sourceEnd`、`trackId/trackType` 和完整 renderer 字段。全文轨道的共享样式更新必须原子应用到同一 `trackId` 的全部 cue，普通单条 overlay 只改目标 id；Store、panel、公共预览、公共时间轴与 compose 必须一致。
- R7. 把艺术字格式化、模板效果、字符动画、范围/全文轨道计算和校验提取为无 DOM/Store 副作用的共享模块；公共 PreviewCompositor、顶层 ArtTool 和旧页面适配器不得继续复制第三套实现。
- R8. 字体/模板/位置预设、全文轨道、文案保存和 AI 推荐 effect 必须可取消并带 job/revision guard；切换 job、destroy 或较新编辑发生后，迟到响应不得覆盖当前 Store。queued/processing 轮询只在 ArtTool 激活且 token 仍有效时继续。
- R9. ArtTool 不直接读取 `sessionStorage`/`localStorage` 的项目副本，不处理 `embedded=1`，不发送/接收 `editor-suite:*` 消息。刷新恢复所需的未生成艺术字草稿由顶层 Store 的单一版本化恢复适配器负责，并明确标记为本地草稿而非服务端成功状态。
- R10. 默认启用顶层 ArtTool 时，打开艺术字不得创建 `iframe[title="艺术字设置"]`；画中画 iframe 继续存在到 B3。`window.__EDITOR_ART_PANEL_ENABLED__ === false` 时只启用原有艺术字 iframe 兼容路径，两条路径不得同时写 Store。
- R11. `/art-text` 与现有 `art-text.html` 在 B2 继续可直接访问；旧页面使用共享领域/渲染模块和兼容适配器维持当前行为。删除旧页面、`embedded=1` 与跨页消息属于 B4。
- R12. 不引入 npm、bundler、前端框架或后端 API/schema 变更；共享脚本继续使用有序 `<script defer>`、唯一 `window` 命名空间、资源版本和 no-cache 清单。

## Acceptance Criteria

- [x] AC1. 默认路径点击艺术字后，顶层 `#editorSuiteInspectorHost` 显示可操作 panel，页面中没有艺术字 iframe；`document`、`#cutPreviewVideo`、MediaController、TimelineController 和播放帧时钟 identity 不变。
- [x] AC2. 手动新增艺术字后可完成选择、文字/模板/字体/排版/颜色/位置/时间修改、批量设置和删除；每项立即反映到 Store、公共预览、公共时间轴与 compose DTO。
- [x] AC3. 一键全文轨道、保留文案编辑与重新布局保持词级时间、统一样式、每 cue 字数/重叠校验和 source anchor；纯文案修改不改变已有 cue 时间。
- [x] AC4. AI 推荐请求、进度、待确认预览、采用/取消和清空状态可用；迟到、跨 job 或 destroy 后响应不修改 Store，外部 AI 在测试中全部被 mock。
- [x] AC5. 公共预览拖动、panel 坐标输入和公共时间轴 move/start/end resize 双向同步同一稳定 id；一次用户提交只产生一次 revision，pointercancel 不产生 revision/history。
- [x] AC6. 在非零时间的 paused/playing 状态下切换 cut/art/pip、保存文字与保存版本，媒体节点/source/currentTime/play state 保持，期间没有 `src` 写入或 `load()`。
- [x] AC7. 顶层艺术字 panel 不包含独立 video、独立时间轴、独立最终生成/结果播放器，不访问项目 sessionStorage，不注册 message handler；同一页面只有一个公共可交互时间轴。
- [x] AC8. 刷新后顶层 Store 从单一版本化本地草稿恢复未生成艺术字 overlays、selection 和时间；恢复不冒充服务端完成状态，job 不匹配、schema 不兼容或损坏草稿被安全忽略。
- [x] AC9. feature flag 关闭时旧艺术字 iframe 路径仍可用；独立 `/art-text?job=...` 页面保持可编辑。默认路径与 fallback 路径互斥，不产生双 revision。
- [x] AC10. 桌面与 375px 下 panel 可滚动、无横向溢出、tab/字段/删除确认可键盘操作；切换工具后隐藏 panel 不可聚焦，重新激活保持 Store selection。
- [x] AC11. compose 请求与最新原子 editor frame 的 art source/overlays/revision 一致；公开 API/OpenAPI、画中画行为和生产环境不变。
- [x] AC12. 新增共享模块与全部 `web/*.js` 通过 `node --check`；focused Node/静态/真实浏览器回归、完整 `tests/app`、`git diff --check` 和 Trellis 校验通过。

## Out Of Scope

- 不迁移画中画 inspector、素材生成或画中画 iframe；属于 B3。
- 不删除所有 iframe、`postMessage`、`embedded=1`、旧 `/art-text` 页面或旧工具 URL；属于 B4。
- 不实现服务重启后的工程恢复、跨标签页冲突或服务端 ProjectDocument；属于 Phase A。
- 不改变服务端艺术字渲染、AI 模型、compose schema、历史格式或时间语义。
- 不整体重写 `styles.css`、改变视觉语言或顺带迁移框架。

## Risks And Constraints

- 旧脚本把领域逻辑、DOM、媒体、时间轴、API 和兼容消息交织在一起；必须先建立共享纯逻辑与服务接口，再迁 UI，避免复制一个新的巨型脚本。
- AI 待确认项是合法的局部瞬时状态，但已确认 overlays 只能来自 Store；两者必须有明确视觉和提交边界。
- 全文轨道同时包含共享样式和逐 cue 文字/时间，更新粒度错误会造成整轨改时或单 cue 样式漂移。
- 本地草稿仅用于浏览器刷新恢复；服务重启缺口继续保持现有精确 xfail，不得在 B2 宣称已经解决。
