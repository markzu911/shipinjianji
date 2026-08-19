# 单页编辑器画中画面板迁移

## Goal

把画中画编辑能力迁入主编辑器顶层文档，使文字剪辑、艺术字和画中画共享同一个 `EditorProjectStore`、基础视频、播放帧时钟、预览合成器和公共时间轴。用户切换到画中画时不再创建默认 iframe，同时完整保留素材生成、选择、摆放、缩放、时间调整、组合预览、刷新恢复和统一成片能力。

## Background

- 父任务 B3 明确要求把 `picture-in-picture.js` 拆成 `PipTool.mount(root, services)`，验证素材生成、选中、拖动、无上限缩放、时间调整、艺术字组合预览和统一生成，并以 feature flag 保留 iframe 回滚路径（`.trellis/tasks/08-13-project-optimization-audit/implement.md:49`）。
- B0-B2 已建立唯一顶层 Store、MediaController、PreviewCompositor、TimelineController 和可挂载 ArtTool。当前公共 frame 已从同一 revision 派生 art、pip、timeline 与 compose DTO（`web/editor-project-store.js:889`、`web/editor-suite.js:1322`）。
- 旧画中画脚本仍创建独立 `pipTimelineStore`，读取 `embedded=1`，拥有第二个 video/时间线/缩略图提取、`sessionStorage` 草稿、`postMessage` bridge、直接 fetch、轮询和最终生成（`web/picture-in-picture.js:22`、`:90`、`:127`、`:1254`、`:1463`、`:2283`）。
- Store 已把 `project.pip.assets` 作为素材注册表、`project.pip.overlays` 作为预览/compose 使用的画中画集合，并用稳定素材 id 建立公共时间线（`web/editor-project-store.js:85`、`:205`、`:247`、`:906`）。
- 当前“无上限缩放”尚未端到端成立：旧卡片滑杆上限为 55%，拖拽受舞台剩余空间限制，顶层镜像拖拽也限制为 55%，后端拒绝宽度大于 65%（`web/picture-in-picture.js:304`、`:1783`、`web/editor-suite.js:2106`、`server/app.py:6992`）。
- 生产环境不在本任务范围；开发服务继续使用 `http://127.0.0.1:8001/`。

## Requirements

### R1. 顶层可挂载模块

- 新增 `PipTool.mount(root, services)`，返回幂等的 `activate()`、`deactivate()`、`render(frame)`、`destroy()`。
- PipTool 只能查询和创建传入 root 内的 inspector DOM，不得创建 video、时间线 Store、缩略图提取器、Web Storage key、message listener 或页面级初始化。
- 默认顶层路径直接挂载 PipTool，打开和切换画中画不得创建画中画 iframe，不得更换基础视频 `src` 或建立第二条播放循环。

### R2. 单一画中画状态所有权

- `project.pip.assets` 保存当前 job/source 下的图片和视频素材注册表；`project.pip.overlays` 只保存已启用且参与预览、时间线和 compose 的素材。
- 素材、overlay 和公共时间线使用稳定 asset id；不得用数组 index 作为编辑 identity。
- 启用、禁用、新素材确认、位置、尺寸和批量状态修改都从最新 snapshot 构造不可变 next pip state，并通过一次语义 command 提交。
- 位置/尺寸/素材状态变化只递增 project revision；新增/移除 overlay 或修改时间范围时才递增 timing revision。

### R3. 画中画完整工作流

- 顶层面板保留文案片段选择、图片/视频类型、生成方式、画幅、开始/结束时间、一键贴合、提示词、AI 提示词草稿、素材生成、生成进度、素材卡片、启用/禁用、位置、尺寸和错误反馈。
- 图片生成完成后可立即启用；视频任务在 queued/processing 时显示进度，completed 后自动变为可预览/可启用，failed 时保留可见错误但不进入 overlay。
- 面板不复制旧页的预览 video、私有时间线、最终成片区或页面 shell；公共预览、公共时间线和顶层生成按钮始终可用。

### R4. 可取消异步 effect

- 提示词、图片/视频素材创建、job 轮询都必须使用 job/effect token、`AbortController` 和可清理 timer。
- 切换 job、`deactivate()` 或 `destroy()` 后，旧请求和旧轮询不得写 UI 或覆盖新 Store revision；服务端已经创建但客户端响应被取消的素材可在下次 job 读取时按 asset id 合并。
- 只在 queued/processing 时继续轮询；终态、离开面板、取消或销毁时停止。浏览器测试中的素材生成必须 mock，不发起真实模型请求或费用。

### R5. 无任意放大上限

- 画中画宽度必须是有限数值并满足现有最小可用尺寸，但前端控件、拖拽算法、Store、预览和后端归一化不得再设置 55%/65% 或其他任意最大值。
- 尺寸控件必须允许直接输入超过 100% 的百分比且不含 `max`；拖拽放大不再由素材中心到舞台边缘的剩余空间决定上限。
- 放大后超出舞台的部分按舞台裁切；`x/y` 继续表示素材中心。浏览器预览与 FFmpeg 输出必须使用相同的中心定位/裁切语义，素材大于主画面时不能退化成固定左上角裁切。
- 后端仍拒绝 NaN、Infinity、非正时间、越界位置、低于最小尺寸和不存在/不属于当前 source 的素材。

### R6. 公共预览、时间线和统一生成

- PipTool 只通过 MediaController seek，通过 Store 选择/修改；公共 PreviewCompositor 和 TimelineController 从同一 frame 渲染 art+pip。
- 预览拖动/缩放、面板修改和时间线调整都必须回写同一 overlay；一次用户提交只产生一次 revision transaction。
- 顶层 `generateCurrentPreview()` 继续从同一 frame 的 `composition` 提交 `/compose`，不得调用 legacy `generateVideo()` 或维护私有 generation payload。

### R7. 版本化刷新恢复

- 扩展现有 `editor-suite:project-draft:<jobId>` envelope，不新建 PipTool storage key。
- 新 schema 同时保存 art、pip 的 source/overlays 和 art/pip selection；pip assets 仍由服务端 job 注册表恢复，不复制进草稿权威。
- 兼容读取 B2 的 schema v1 art-only 草稿；损坏 JSON、job/server 不匹配、重复 id、无效范围、无效尺寸或引用不存在素材的 pip 草稿必须安全忽略。

### R8. 迁移期兼容与资源契约

- `window.__EDITOR_PIP_PANEL_ENABLED__ !== false` 且依赖存在时启用顶层 PipTool；false 时只运行现有 pip iframe bridge，两个 authority 互斥。
- B3 保留独立 `/picture-in-picture`、`picture-in-picture.html/js`、`embedded=1` 和消息桥作为 fallback/standalone 适配器；这些边界在 B4 删除。
- 普通脚本继续按依赖顺序 `defer` 加载；新增资源加入 no-cache 清单并更新 `?v=` 与静态契约。

## Acceptance Criteria

- [ ] AC1: 默认访问 `/?job=<id>&tool=pip` 显示 `#editorPipPanelRoot`，页面内不存在 `iframe[title="画中画设置"]`，且文字/艺术字/画中画切换不导航、不重载基础视频、不改变播放位置。
- [ ] AC2: 顶层 PipTool 不包含 video、Timeline Store、storage、message、缩略图或页面级初始化所有权；生命周期重复调用无监听器、timer、request 或 DOM 泄漏。
- [ ] AC3: 文案选择、AI 提示词、mock 图片生成、mock 视频 queued -> completed/failed、启用/禁用和素材选择在顶层面板可完成；迟到请求在切换工具/job 后为 no-op。
- [ ] AC4: 面板、公共预览和公共时间线选择同一稳定 asset id；拖动、位置预设、尺寸、开始/结束、时间线 move/resize、撤销/重做均只修改目标 overlay 并符合 revision/timingRevision 矩阵。
- [ ] AC5: 尺寸输入无 `max`，可提交并恢复至少 175% 宽度；预览、草稿、compose DTO 和后端 normalize 都保留该值，超出画面的中心裁切与最终 FFmpeg 定位一致，NaN/Infinity/低于最小值仍被拒绝。
- [ ] AC6: 公共预览同时显示艺术字和画中画，统一生成请求从同一 revision 发送当前 cut/art/pip 数据，且画中画素材生成浏览器用例全部 mock。
- [ ] AC7: schema v2 刷新恢复 pip source/overlays/selection 与大尺寸值，素材来自当前 job registry；schema v1 art 草稿继续恢复，损坏/跨 job/旧 server/未知 asset 草稿不覆盖 Store。
- [ ] AC8: `__EDITOR_PIP_PANEL_ENABLED__ = false` 时 pip iframe fallback 可编辑；独立 `/picture-in-picture` 继续加载并可用；默认顶层与 fallback 不同时运行。
- [ ] AC9: 桌面与 375px 下无 document 横向溢出，面板可滚动，隐藏面板 inert 且不可 Tab 聚焦，常用操作目标至少 44px。
- [ ] AC10: 画中画、compose、Store、静态、Node、浏览器和完整 `tests/app` 回归通过；已知服务重启恢复用例继续是唯一预期 xfail；生产环境未改动。

## Out Of Scope

- B4 才删除旧工具页面、`embedded=1`、`postMessage`、iframe lifecycle、旧静态资源与旧 URL，并把历史 URL 重定向到顶层工具。
- 不更换图片/视频/提示词模型，不修改现有 API 路径、素材数量上限或 source 枚举。
- 不在 B3 处理服务重启后的 job 恢复、后端领域拆分、前端框架迁移或无关视觉改版。

## Risks And Deferred Items

- 去掉宽度产品上限后，异常大的有限值会增加本地 FFmpeg 缩放成本；本任务按用户要求不设置隐藏最大值，仅保留有限数值、最小值和素材归属校验。
- 浏览器取消已提交的素材创建请求不能撤销服务端模型任务；通过下次 job 读取按 asset id 合并，避免重复或丢失已生成素材。
- 服务重启后的 job 恢复仍由 Phase A 负责，当前浏览器用例的预期 xfail 不在 B3 修复。
