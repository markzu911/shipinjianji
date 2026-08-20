# 技术设计：统一艺术字预览画布与分类单行轨道

## Architecture And Ownership

权威状态继续是 `EditorProjectStore.project.art.overlays` 和 `project.pip.overlays`。本修复不把 DOM 几何或可视行写入 Store：

```text
源视频尺寸 + 预览 viewport + 预览模式
  -> PreviewCompositor 内容画布几何
       contain: min(viewport/video)
       cover:   max(viewport/video)
  -> 同一画布内渲染 art + pip

art.overlays
  -> EditorArtModel.buildTimelineTracks()
       non-transcript -> art:manual
       transcript     -> art:transcript:<trackId>
  -> TimelineController
       每条 art 逻辑轨固定一个可视行
```

服务端负责在全文文案生成和 compose 校验时使用同一个 transcript 边界归一化函数，前端只消费已经规范化的 cue。

## Preview Canvas Geometry

`EditorPreview.createCompositor()` 在外层 `editor-suite-preview-overlay` 内创建唯一 `.editor-suite-preview-canvas`，再把现有 art/pip layer 挂到 canvas 内。canvas 的 CSS 宽高等于视频 `videoWidth/videoHeight`，`transform-origin: 0 0`。

几何函数输入为 viewport、视频固有尺寸和预览模式：

```javascript
const scale = cover
  ? Math.max(viewportWidth / videoWidth, viewportHeight / videoHeight)
  : Math.min(viewportWidth / videoWidth, viewportHeight / videoHeight);
const left = (viewportWidth - videoWidth * scale) / 2;
const top = (viewportHeight - videoHeight * scale) / 2;
```

canvas 使用 `translate(left, top) scale(scale)`。艺术字内部字号、描边、阴影和安全边距直接使用视频像素值，不再预先乘外层舞台宽度比例；canvas 的整体变换完成预览缩放。PiP 的归一化位置和宽度继续相对 canvas 百分比计算。

普通预览从 stage 是否包含 `is-douyin-preview` 判断 `contain/cover`。设备 UI 仍是 canvas 的兄弟层。ResizeObserver、视频元数据就绪、frame render 和模式切换都调用同一个幂等几何同步函数；缺少有效视频尺寸时临时回退到 viewport 尺寸，元数据就绪后自动纠正。

## Pointer Coordinates

拖动和缩放使用 canvas 的 `getBoundingClientRect()` 作为坐标边界，不再使用外层 host：

- art/pip `x/y` 由指针中心相对 canvas rect 归一化并 clamp。
- PiP width 的横向/纵向增量以 canvas rect 尺寸和素材宽高比换算。
- contain 黑边不参与坐标；cover 下 canvas rect 可超出 viewport，负 left/top 仍参与换算。
- pointercancel 或未达到拖动阈值继续恢复当前 overlay，不产生 revision。

## Timeline Row Policy

逻辑轨身份保持现状：`art:manual` 与 `art:transcript:<trackId>` 永远分开。TimelineController 对 art 轨采用固定单行策略，不再因为 interval overlap 增加 lane；其他未来允许多 lane 的 track 仍可保留通用 lane 分配能力。

- 每条 art 轨的 `data-timeline-track-index` 唯一，全部 clip 的 `data-timeline-lane-index` 为 `0`。
- 后一 art 逻辑轨从前一轨下方 30px 开始，轨道总高度按 art 逻辑轨数计算。
- 同行手动 clip 可真实重叠；唯一 clip ID、Tab 顺序和艺术字列表保留全部操作入口。当前 selection、`:focus-visible` 或拖动项提高堆叠层级，避免正在编辑的目标被同轨兄弟覆盖。
- 不把 lane 或堆叠顺序写回 Timeline schema、Store 或草稿。

## Transcript Timing Invariant

新增或收敛一个服务端 transcript timing 规范化入口，并在“逐字 timing 已写回 cue”之后执行。每个 `trackId` 内按 `start/end` 排序，保证：

```text
cue.start < cue.end
previous.end <= current.start
cue.start <= each character.start < character.end <= cue.end
```

发生重叠时，以后一 cue 的真实开始时间为边界，只收紧前一 cue 的可见结束；同步把前一 cue 末尾逐字 timing 投影到边界内，保持字符数量和顺序。不得后移后一 cue、删除字符、改写 `sourceStart/sourceEnd` 或触碰媒体音轨。若在 `0.02s` 最小时长内无法形成合法区间，返回明确校验错误，而不是生成第二行或等到 compose 时静默改变。

`normalize_text_overlays()` 复用同一入口并在返回前校验不变量，使 API 生成、历史草稿提交和 compose 使用完全相同的边界。前端 `buildTranscriptTrack()` 保留服务端 cue 时间，不重新解释；测试用伪造重叠数据时应显式暴露契约错误或先走同一规范化 fixture。

## Compatibility

- overlay、timeline 和草稿 schema 不变；旧草稿加载后仍从 overlays 派生两条分类轨。
- `art:<overlayId>` selection 不变，手动/文案的单项或整轨编辑语义不变。
- compose DTO 字段不变，只消除生成阶段和 compose 阶段之间的时间边界漂移。
- 静态脚本缓存版本随 JS 变更提升。

## Risks And Mitigations

- 浏览器字体与 Pillow/FFmpeg 字体栅格存在细微差异：验收锁定画布几何、中心点、字号比例和边界容差，不要求逐像素完全一致的抗锯齿。
- 完全重叠的手动 clip 在单行中会视觉堆叠：当前选择/焦点置顶，艺术字列表继续提供所有单项入口；不通过改时间来伪造不重叠。
- 视频 metadata 晚于首帧：几何同步必须幂等并由 metadata/state/resize 路径重新触发。
- cover 模式 canvas 超出 viewport：外层继续 `overflow: hidden`，指针换算保留负偏移。
- timing 修剪过密：保持现有明确错误，不吞字符、不移动下一 cue。

## Rollback

无数据迁移。可分别回滚 PreviewCompositor canvas、TimelineController art 单行策略和服务端 timing 归一化；旧草稿与 compose schema 无需修复。
