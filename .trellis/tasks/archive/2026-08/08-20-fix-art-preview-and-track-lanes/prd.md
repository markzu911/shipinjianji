# 统一艺术字预览与轨道布局

## Goal

让编辑器中的艺术字预览与最终生成视频使用同一套视频画布坐标和缩放规则，并让公共时间轴始终以一行“手动艺术字”和另一行“视频文案艺术字”展示，避免预览误导和同类艺术字意外新增可视行。

## Background

- 用户截图中的源视频为竖屏 `720x1280`。普通预览舞台是横向容器，视频通过 `object-fit: contain` 居中显示，但 `web/editor-preview-compositor.js:368` 和 `web/editor-preview-compositor.js:553` 仍使用整个舞台宽高计算字号与 `x/y`，因此艺术字比最终生成结果约大 2.7 倍，并可越过视频内容进入左右黑边。
- `web/styles.css:11998` 已定义 `.editor-suite-preview-canvas`，但 `web/editor-preview-compositor.js:334` 没有创建或同步该内容画布，艺术字和画中画直接铺满外层 preview overlay。
- `web/editor-art-model.js:768` 已将所有非 transcript overlay 派生到唯一 `art:manual`，并将文案 cue 派生到 `art:transcript:<trackId>`；两类逻辑轨身份已经分离。
- `web/editor-timeline-controller.js:84` 会把同一逻辑轨中时间重叠的 clip 分配到额外可视 lane。该布局让逻辑上一条轨在页面中看起来像多条轨，与用户明确要求的“一类一行”不符。
- `server/app.py:5067` 在生成文案 cue 时先消除重叠，但 `server/app.py:5083` 随后又用逐字时间重写 cue 起止点，可能重新引入毫秒级重叠。`normalize_text_overlays()` 在 compose 前还会再次裁切，因此页面时间轴、实时预览和最终生成可能消费不同的边界。
- 用户已明确：所有手动添加及 AI 确认的非 transcript 艺术字必须在同一行；视频文案艺术字必须在另一行，两类不能混在同一行。

## Requirements

- R1：普通预览必须按真实视频内容矩形渲染艺术字和画中画。视频使用 `contain` 时，内容层使用同一缩放和居中偏移；左右或上下留黑区域不属于可编辑画布。
- R2：设备预览使用 `cover` 时，视频、艺术字和画中画必须共享同一个内容画布变换；设备 UI 不进入该变换，且切换预览模式不能修改 overlay 的权威 `x/y`、字号或导出参数。
- R3：艺术字字号、描边、阴影、位置、安全边距和 PiP 尺寸都以源视频像素画布计算，再整体缩放到预览；预览尺寸变化、视频元数据就绪和模式切换后必须重新同步几何。
- R4：拖动艺术字和画中画、缩放画中画时，指针坐标必须相对实际内容画布换算；普通预览黑边和设备预览裁切不能造成保存后的 `x/y/width` 漂移。
- R5：所有非 transcript overlay，包括手动新增和 AI 推荐确认项，只派生一条 `art:manual` 逻辑轨并固定占一条可视行；即使时间重叠也不得扩展第二行。
- R6：所有同一 `trackId` 的 transcript cue 只派生一条 `art:transcript:<trackId>` 逻辑轨并固定占一条可视行；它必须与 `art:manual` 使用不同轨道 ID、名称和行位置。
- R7：文案 cue 的 `start/end` 与 `characterTimings` 必须在生成、浏览器 Store、实时预览和 compose 归一化中保持同一非重叠边界。相邻 cue 可首尾相接，但前一 cue 不得覆盖后一 cue 的开始时间。
- R8：修正边界只能改变艺术字的可见时间，不得修改或裁剪基础视频音频，也不得吞掉下一段文案内容、下一段首字时间或其源时间锚点。
- R9：手动艺术字时间重叠时，各 overlay 仍保留唯一 clip ID、独立 Store 数据和单项编辑能力；时间轴保持单行，当前 selection/focus 的片段置于可交互层，完整单项选择继续可从艺术字列表进入。
- R10：不新增第二份预览坐标、轨道或 lane 持久状态；历史草稿继续由 overlays 派生，无 schema 迁移。

## Acceptance Criteria

- [x] AC1（R1-R3）：对 `720x1280` 视频和横向预览舞台，预览内容层的宽高、缩放与居中偏移等于视频 `contain` 矩形；艺术字中心、字号和边界均落在该矩形内，并与同帧导出结果在允许的浏览器字体栅格误差内一致。
- [x] AC2（R2、R3）：切换设备预览后，内容层按 `cover` 居中裁切，艺术字与视频缩放倍率一致，设备 UI 尺寸和位置不随内容层缩放。
- [x] AC3（R4）：在普通预览和设备预览分别拖动艺术字、拖动及缩放 PiP，提交的 `x/y/width` 与内容画布中的目标位置一致；普通预览黑边点击或拖动不会按外层舞台误算。
- [x] AC4（R5、R6）：给定两个完全重叠的手动艺术字、一个 AI 普通艺术字和多 cue 文案轨，时间轴恰好显示一行“手动艺术字”和一行“视频文案艺术字”，两行 track ID 不同，任何同类 clip 都不新增第三行。
- [x] AC5（R7、R8）：构造逐字时间跨越相邻 cue 边界的全文文案，生成结果满足 `previous.end <= current.start`，逐字时间仍位于所属 cue 内，全部文案字符、下一 cue 起点和源时间锚点保持；媒体音轨与视频时长不变。
- [x] AC6（R7）：服务端返回、Store overlays、公共时间轴、PreviewCompositor 和 composition DTO 对每个 transcript cue 的起止时间一致，不再由 compose 阶段静默产生另一套边界。
- [x] AC7（R9、R10）：重叠手动艺术字的 ID、文字、样式、坐标、时间、preview/compose 数据保持独立；从艺术字列表选择、修改或删除任一项只影响目标项，刷新旧草稿后仍为两条分类行。
- [x] AC8：桌面和 375px 浏览器无页面横向溢出、无控件遮挡导致的流程阻断、无未处理 console/page/network 错误；相关 Node、后端、浏览器和全量测试通过。

## Out Of Scope

- 不把手动艺术字与视频文案艺术字合并成同一行或同一逻辑轨。
- 不合并多个 overlay/cue 为一个业务对象，不批量改写手动艺术字的内容、样式或显示时间。
- 不改变视频本身的剪辑、音频删除边界、转写文本或 AI 分段语义。
- 不新增前端框架、第二个 Store、草稿 schema 版本或独立预览运行时。
