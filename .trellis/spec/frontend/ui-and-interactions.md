# UI 与交互

## DOM 和事件

- 页面脚本通过稳定 `id`、`data-*` 和事件委托连接 DOM；HTML 改名时同步更新脚本选择器和测试。
- 初始化在 defer 脚本加载后执行；可选元素使用 `?.`，必需元素缺失应尽早显露，而不是静默造成半可用页面。
- 动态列表优先在容器上事件委托，避免每次 render 累积监听器。
- 长操作要锁定相关控件、显示进度并提供取消/重试；终态后恢复交互。

## 可访问性

- 按钮用 `<button>`；纯图标按钮提供 `aria-label`/title。
- tabs 保持 `role=tablist/tab/tabpanel`、`aria-selected` 和键盘方向键行为。
- progress 同步 `aria-valuenow`；状态提示使用现有 live region/反馈组件。
- 拖动/缩放必须保留键盘替代方式和可见焦点，不依赖颜色作为唯一状态。
- 点击目标在移动端保持约 44px；文本不能溢出按钮或遮挡相邻控件。

## 响应式与视觉

- 保持现有安静、工具型工作台风格，复用 `web/styles.css` 的 token 和组件类。
- 桌面 Chrome/Edge 与 375px 窄屏都必须可完成核心流程，无横向页面溢出和控件重叠。
- 主编辑器进入 `body.has-result` 后，桌面端（`>=1001px`）的 `.header-inner`、`.page-shell` 和结果面板必须占满视口宽度，不再受 `--editor-width` 限制；上传/处理中页面、素材库和窄屏继续保留各自安全边距。浏览器回归至少覆盖 1912px 左右边界均为视口边界，以及 375px 无横向溢出。
- 固定格式元素（视频舞台、时间线、轨道、图层列表）使用稳定尺寸/比例，动态标签不得引发布局跳动。
- 时间轴子项从 grid flow 改为绝对定位以投影剪后时间时，必须同时定义横向位置/宽度和纵向 `inset`/高度；背景图或内容数据存在不代表元素可见。真实浏览器回归必须断言可见项的 `getBoundingClientRect().height > 0` 且与所属轨道高度一致。
- 剪后文案轨必须区分语义/媒体范围 `sourceStart/sourceEnd` 与纯显示范围 `layoutStart/layoutEnd`。显示范围先按删除后的 edited time 排序；相邻可见文案间隔不超过 `1.5s` 时只把前一项的 `layoutEnd` 延伸到下一项 `layoutStart`，超过阈值的真实静音保持可见。播放、高亮、seek、删除、Store 和 compose 禁止消费 `layout*`；结果面板进入可布局状态后才能首次测量时间轴，刷新、服务端 retained projection 到达和缩略帧完成不得改变首个可见几何。
- 时间轴缩略帧可以继续按源视频时间缓存，但投影到剪后时间轴时只能使用保留区采样帧，并按相邻可见帧的剪后时间中点从 `0%` 到 `100%` 连续铺设；开头删除、交错删除和结尾删除都不得留下空白。删除或恢复只重算投影，不能因此重新创建 extractor 或增加抽帧次数。
- 不新增解释功能的营销文案；状态文字只说明当前结果、错误和可执行下一步。

### 文案轨标签排版

文案轨片段的宽度只表达剪后时间范围，不能参与字符间距分配。`.cut-timeline-text-segment-label` 使用自然居中排版并保留 `word-break: break-all`；禁止使用 `text-align-last: justify`，否则删除后重绘产生的宽片段会把中文末行逐字拉满。修改该规则时，真实浏览器测试必须在删除片段后同时断言标签文本不变、`textAlign === "center"` 且 `textAlignLast !== "justify"`。

```css
.cut-timeline-text-segment-label {
  text-align: center;
  word-break: break-all;
}
```

### 全应用紧凑密度与预览锁定

应用操作界面的紧凑密度由 `styles.css` 根级 token 和限定作用域的组件规则统一投影；禁止对 `html`、`body`、工作区或预览祖先使用全局 `zoom` / `transform: scale()`。紧凑化优先减少 padding、margin、gap 和次级字号，移动端主要输入与按钮仍保持约 `44px` 命中高度。

```css
:root {
  --ui-compact-control-height: 36px;
  --ui-compact-control-height-small: 30px;
  --ui-compact-panel-padding: 12px;
  --ui-compact-gap: 8px;
  --timeline-ruler-height-compact: 12px;
  --timeline-row-height-compact: 22px;
  --timeline-base-track-height-compact: 60px;
  --timeline-layer-track-height-compact: 52px;
}
```

`.segment-item` 的紧凑行与 22px 控件几何是已确认的局部例外；文字层级固定为正文 12px、时间 10.8px、播放状态 8.4px、删除/空白标题 10.8px、meta 9.6px，图标与勾选字形继续保持 10–11px。短文案行保持约 32px，换行和空白说明行按内容自然增高且不得裁切；放大文字时不得同步放大播放按钮、删除圆圈或其他控件。`.editor-pip-tool-panel { zoom: 0.6 }` 同样不得被新的 compact 规则二次缩放；面板固定使用适合小字号中文 UI 的 `Microsoft YaHei UI / PingFang SC / Noto Sans CJK SC / Source Han Sans SC / system-ui` 字体栈，正文与辅助文字使用 500，标题和 `strong` 使用真实 700，禁止依赖 650/750 合成字重。其缩放前字号下限为 small/time 15px、普通文字与控件 16px、主要选项 strong 17px，使视觉字号约为 9/9.6/10.2px。PiP 文案行的时间列固定为 64px，正文继续 `minmax(0, 1fr)` 和 ellipsis，两列逻辑 gap 为 12px（视觉约 7.2px），最长 `MM:SS.d` 不能与正文重叠。radio/checkbox 必须显式保持等宽等高，外层 label/card 承担命中区域。

主文字编辑预览的外置播放器控制条是桌面密度例外：只在 `.text-editor-preview-pane #cutPreviewPlayer:not(:fullscreen)` 下使用约 24px 高控件和固定 96px 时间列，确保 `MM:SS / MM:SS` 完整可见；`max-width: 720px` 下必须恢复 44px 触控高度，并继续隐藏音量滑杆以避免横向溢出。

以下公共预览矩形及其 contain/cover、pointer mapping 必须保持不变：`.text-editor-preview-pane`、`.cut-preview-panel`、`#cutPreviewPlayer`、`#cutVideoStage`、`#cutPreviewVideo`、`#editorSuitePreviewOverlay`、`.editor-suite-preview-canvas`。紧凑样式区块不得包含这些选择器，也不能通过改变桌面工作区列比例间接缩小预览。

公共时间轴只压缩纵向几何，不改变宽度或时间映射。无效果轨时使用 `12px ruler + 22px 文案轨 + 60px 总高`；有 `n` 行效果时，controller 与 CSS 必须共同满足：

```javascript
const TIMELINE_ROW_HEIGHT = 22;
const TIMELINE_EFFECT_BASE_HEIGHT = 52;
const layerHeight = rowCount * TIMELINE_ROW_HEIGHT;
const trackHeight = TIMELINE_EFFECT_BASE_HEIGHT + layerHeight;
```

艺术字/画中画独立图层时间轴总高为 `52px`。修改任一数值时必须同步 CSS token、`editor-timeline-controller.js`、静态契约和真实浏览器多行效果轨断言，不能只改外壳高度造成 clip 或缩略帧裁切。

浏览器回归至少覆盖：1912px 下预览 panel/stage/video/canvas 的改动前后矩形误差不超过 `1px`；无效果/一行/多行轨道实际高度和所有子层 `height > 0`；375px 无横向溢出、radio 为正方形且主要控件命中高度不低于 `44px`；工具切换期间基础 video identity、`srcWrites/loadCalls` 和 source/edited time 映射不变。

### 设备预览安全区

普通画布预览必须完整显示源视频；显式的设备实机预览可以使用目标设备逻辑尺寸和 `object-fit: cover`，模拟全屏应用在该设备上的真实裁切。实机预览只改变显示变换，不能修改源视频、编辑坐标或导出比例。硬件安全区与应用 UI 避让区定义为设备预览容器上的命名变量。纵向 `top`、`bottom`、`height` 百分比按容器高度换算；纵向 `padding` 的百分比会按容器宽度计算，不能直接复用前者，应改用按逻辑宽度换算的 `cqw`。

设备预览的内容合成层必须共享同一个适配模式：基础视频使用 `cover` 时，艺术字和画中画画布也必须按 `cover` 缩放并居中裁切；普通预览则继续使用 `contain` 完整展示。抖音顶部、侧边和底部 UI 属于设备视口层，不参与内容画布缩放。否则视频会被放大裁切，而艺术字和画中画仍按窄视口缩小，造成相对尺寸与导出画面不一致。

`PreviewCompositor` 只创建一个 `.editor-suite-preview-canvas`，其未变换宽高等于 `videoWidth/videoHeight`，艺术字和画中画 layer 都是该 canvas 的子层。字号、描边、阴影、安全边距和 PiP 尺寸先按源视频像素计算，再由 canvas 整体执行 contain/cover 变换；不得按外层舞台宽度预缩放样式。拖动和缩放使用 canvas 的 `getBoundingClientRect()` 换算归一化坐标，普通预览黑边不参与坐标，cover 的负偏移必须保留。视频 metadata、预览容器 resize 和模式切换都要幂等重算几何。

抖音右侧操作栏按 440×956 逻辑画布使用固定节奏，不能用上下边界配合 `space-between` 自动拉伸。参考基线为：操作栏顶部 `468 / 956`、相邻项间距 `25 / 440 cqw`、头像和唱片直径 `42 / 440 cqw`、主图标 `34 / 440 cqw`、唱片底部 `93 / 956`。这样头像、四个操作项和唱片在不同预览尺寸下保持同一视觉密度，分享与唱片之间不会出现额外断层。

```javascript
const fitScale = devicePreviewEnabled ? Math.max : Math.min;
const scale = fitScale(
  previewViewport.clientWidth / composition.width,
  previewViewport.clientHeight / composition.height,
);
const left = (previewViewport.clientWidth - composition.width * scale) / 2;
const top = (previewViewport.clientHeight - composition.height * scale) / 2;
composition.element.style.transform =
  `translate(${left}px, ${top}px) scale(${scale})`;
```

回归测试应锁定普通/设备两种适配分支；浏览器验收使用同一艺术字分别切换两种模式，确认设备模式下艺术字与视频的缩放倍率一致、超出视口的内容被居中裁切、设备 UI 不随内容画布缩放且页面无横向溢出。

```css
/* Explicit iPhone 17 Pro Max full-screen device preview. */
.device-preview {
  --safe-top: 6.4854%;
  --safe-top-space: 14.0909cqw;
  --header-content-height: 5.2301%;
  --header-height: calc(var(--safe-top) + var(--header-content-height));
  aspect-ratio: 440 / 956;
  container-type: inline-size;
}

.device-preview > video {
  object-fit: cover;
}

.device-preview .top-chrome {
  height: var(--header-height);
  padding-top: var(--safe-top-space);
}
```

浏览器验收必须分别检查普通预览无裁切、设备预览使用预期裁切比例、内容区互不重叠且容器无横向溢出；静态测试同步锁定设备基线与资源版本。

## 编辑交互

- 时间线变化统一 clamp 到媒体 duration 和 clip 最小时长。
- 手动时间轴删除最小时长固定为一帧 `1/30s`；播放头分割与 `split_exact` 继续使用独立的 `0.1s` 最小片段保护，禁止复用同一门槛常量。
- pointer session 在 move 中预览，在 finish 时 commit；不要每个 pointermove 都发网络请求。
- 同一时间轴控件同时承担“点击确认”和“拖动调整”时，必须用明确的位移阈值区分两种语义；只有主体在阈值内完成的点击可以确认，手柄点击和超过阈值的拖动结束都不能确认。
- 极窄待确认选区的左右手柄发生视觉重叠时，上半区按离哪条边更近决定边界调整，下半区保留主体移动与二次确认；外置取消按钮的 `44px` 命中区不得侵入选区主体。
- 待确认时间轴选区打开确认弹窗后，弹窗“取消”只关闭弹窗并保留选区；删除选区应由 Delete/Backspace 或独立的取消选区动作负责，不能混用两种取消语义。
- 手动时间轴拖拽先将语义 `originalStart/originalEnd` clamp 到媒体时长并继续使用二次确认；确认后的服务端草稿可将物理 `start/end` 在 `0.20s` 内吸附到可靠语音转换。完全位于静音、没有可靠候选或无法判断用户语义时保持精确物理范围，任一端点都不得跨入下一段保留语音；界面应说明语音附近会对齐安全剪辑点。
- 播放头“分割”按钮位于剪辑时间轴标题右侧且点击区不少于 `44px`；起点、终点、已有边界、删除区和不足最小时长时原生 disabled。split clip 必须阻止自由拖选 handler，键盘 selection、Delete/Backspace、撤销/重做和重绘后焦点都按稳定 clip key 工作。
- 删除完整分割片段沿用确认弹窗，但提示必须明确边界不会被语音保护移动；删除后的片段只保留在 Store、剪辑草稿和历史中，时间轴不得渲染恢复 marker、隐藏占位或焦点目标。全部片段删除后公共 timeline 仍保持可见，用户通过全局撤销/重做恢复。
- 播放、seek、selection、drag/resize 后同步顶层和嵌入工具，但避免反馈循环。
- 点击公共效果片段主体时，必须按完整时间轴中的实际鼠标位置 seek，不能固定跳到片段起点；横向滚动后继续使用 track rect 坐标，选择接受后只 seek 一次。resize handle 未拖动、程序化选择及超过阈值的 move/resize 保持各自边界语义。
- 撤销/重做记录语义操作，但文字剪辑检查器不提供“操作记录”页签、历史列表或可见的撤销/重做按钮。历史栈与本地持久化属于内部能力，只通过 `Ctrl/Cmd+Z`、`Ctrl/Cmd+Shift+Z` 和 `Ctrl/Cmd+Y` 访问。
- 全局剪辑快捷键处理器必须忽略 `input`、`textarea`、`select` 和 `contenteditable` 目标，保留浏览器原生编辑撤销；快捷键执行后仍要刷新预览、时间轴、统计和草稿保存状态。
- 片段删除确认弹窗打开期间全局撤销/重做必须锁定，避免确认对象与历史状态错位；重做到已被服务端确认的语义签名时保存提示应立即恢复为已保存。

### 艺术字选择、设置与模板下拉

顶层 ArtTool 固定使用“选择艺术字 / 艺术字设置 / AI 推荐”三个同级 tab。“选择艺术字”只拥有实例/整轨列表、自定义文字新增和视频文案一键添加；“艺术字设置”只拥有当前 selection 的详情、空状态与参数字段，不能把选择控件重新放回设置页。

- 无艺术字 selection 时激活工具默认进入选择页，已有 selection 时默认进入设置页；从选择页新增或选择成功、或确认 AI 建议后进入设置页。只有设置页中的艺术字 selection 确实从有变无时才自动返回选择页，无 selection 下主动查看空设置页不能被无关 Store revision 打断。
- 模板使用 trigger + listbox，自始至终从当前 overlay 的 `artStyle` 派生选中值；触发器和 option 只显示模板名称及 `EditorArtRenderer.renderCharacters()` 样式样例，不渲染模板介绍。
- 触发器支持 Enter/Space/ArrowUp/ArrowDown；option 支持方向键、Home/End、Enter/Space、Escape 和 Tab。关闭、切换 tab、selection 消失、deactivate 或 destroy 后 listbox 必须隐藏且所有 option `tabIndex=-1`；Escape 将焦点还给 trigger，Tab 保持自然焦点顺序。
- 桌面三个 tab 保持单行；375px 下 trigger、option 和名称受父级宽度约束，样例不压缩，名称可换行且页面、ArtTool 都不得横向溢出。

### 公共效果时间轴艺术字分类单行

公共效果时间轴中的逻辑轨和可视行语义必须一致。手动及 AI 确认的非 transcript 艺术字共用 `art:manual`，视频文案艺术字继续使用 `art:transcript:<trackId>`；每条艺术字逻辑轨固定占一条可视行，同轨 clip 重叠不得增加第二行。

- 同一艺术字逻辑轨的 clip 使用相同 `data-timeline-track-index`，且 `data-timeline-lane-index` 恒为 `0`；手动轨和文案轨的 track index 必须不同。
- 每个 clip 仍是独立 `<button>`，保留唯一 ID、可见焦点、键盘微调和 resize handle；当前 selection、focus 或 drag 项提高堆叠层级，艺术字列表继续提供所有单项入口。
- 单行堆叠只能改变派生 DOM 的 `top/z-index` 和容器高度，不能改变 clip ID、时间、selection、Store revision、preview 或 compose。
- 其他允许多 lane 的效果轨可继续使用通用 lane 分配；不得把其策略套回艺术字轨。
- 浏览器验收检查重叠手动艺术字的矩形处于同一行、当前项可操作、单 clip 调时/删除，以及手动/文案两行在桌面和 375px 均无横向溢出。

### 艺术字手动坐标契约

艺术字位置的权威状态始终是 overlay 的归一化 `x/y`，允许范围为 `0.05–0.95`。手动输入只把该状态投影成 `5%–95%` 的百分比，不得新增独立坐标状态；拖动画布、套用位置预设和手动输入都必须通过 `updateSelectedOverlay` 或同一轨道共享更新链路修改权威状态。

- `input` 中合法的 `5–95` 数值实时更新预览；回车或 `change` 再 clamp 越界值并回写格式化结果。
- 渲染、拖动和套用预设后同步两个输入；当前正在编辑的输入不能被同步渲染覆盖，否则用户无法输入多位数或小数。
- 全文艺术字轨道的 `x/y` 继续由 `TRANSCRIPT_STYLE_FIELDS` 批量应用到每个 cue。
- X/Y 使用可见标签、独立 `%` 单位、`0.1` 步长、焦点态和至少 44px 高度；375px 下两列不能产生卡片或页面横向溢出。

```javascript
function commitPositionCoordinate(axis, input, options = {}) {
  const overlay = selectedOverlay();
  const rawPercent = Number(input.value);
  if (!Number.isFinite(rawPercent) || input.value.trim() === "") {
    if (options.finalize) {
      input.value = formatPositionPercent(overlay[axis]);
    }
    return;
  }
  if (!options.finalize && !input.validity.valid) return;
  const percent = clamp(rawPercent, 5, 95);
  updateSelectedOverlay({ [axis]: percent / 100 });
}

if (document.activeElement !== positionXPercent) {
  positionXPercent.value = formatPositionPercent(overlay.x);
}
```

静态测试应锁定 X/Y DOM、资源版本和提交入口；浏览器测试应输入普通值与越界值，检查提示、画布位置、回写值、控制台错误以及桌面/375px 的 `scrollWidth <= clientWidth`。

### 文字行播放契约

每条文字展示行必须提供独立的播放按钮，按钮与删除圆圈、恢复按钮和文字编辑按钮是兄弟节点，事件委托先处理播放按钮并立即返回。播放使用行上的源时间 `data-display-start/end` 调用公共 `seekCutPreview`，然后播放原视频；它不能打开文字编辑弹窗，也不能改变 `selectedRanges`、草稿或撤销历史。纯图标按钮使用播放图标和说明性 `aria-label`/title；文案列表是经用户确认的密度特例，整行从 `64px` 压缩到 `32px`，圆点和播放目标从 `44px` 等比压缩到 `22px`，不得用 `transform: scale()` 造成宽度缺失。

已删除文字同样必须能试听。点击其播放按钮时，只在该展示行的源时间范围内临时绕过剪辑预览的“跳过已删除区间”逻辑；播放到展示行末时必须保存终点、暂停、清除临时范围，再把播放头校准到行末，避免校准产生的新 `timeupdate` 再次命中旧范围。用户执行其他 seek 时也立即清除临时范围，后续公共播放恢复正常跳过删除内容。当前行高亮优先命中该临时范围，因此已删除行试听时也显示 `aria-current` 和“播放中”。

播放跟随滚动以文字面板为 scroll container，并读取 sticky `.cut-toolbar` 的实际位置和高度。工具栏尚未吸顶时，基础锚点要使用面板 scrollport、真实 padding、sticky inset 和工具栏实高计算其最终吸顶位置；工具栏吸顶后基础锚点为 `toolbar.getBoundingClientRect().bottom + 8`。活动行的常规目标 top 在基础锚点上增加 `3 * itemRect.height`，必须使用当前真实行高而不是固定像素；接近面板底部时再 clamp 到 `panelRect.bottom - itemRect.height`，保证活动行完整可见。不能只用 `panelRect.top + toolbarHeight` 推算，因为面板 padding、边框或 sticky 偏移会让活动行被工具栏遮挡。控制器先读取全部几何，再把真实活动行移入展示层并在原位置保留无交互等高占位，最后直接写入目标 `scrollTop`、展示层最终 top/size 和底部余量；不得复制行、按钮或时间 data，不得 transform 仍位于列表中的真实行，也不得为列表、入场或尾部建立 FLIP/WAAPI 动画。目标 `scrollTop` 必须 clamp 到 `0..scrollHeight-clientHeight` 并只写一次。同一 `data-display-key` 只调度一次；切换行、重渲染或用户滚动意图会恢复真实行原顺序并清除占位、展示层状态和监听器，`prefers-reduced-motion: reduce` 使用同一唯一 DOM 结构和终点。

```javascript
const baseAnchorTop = Math.min(currentToolbarBottom, stickyRestingBottom) + 8;
const desiredAnchorTop = baseAnchorTop + itemRect.height * 3;
const maximumAnchorTop = Math.max(
  baseAnchorTop,
  panelRect.bottom - itemRect.height,
);
const anchorTop = Math.min(desiredAnchorTop, maximumAnchorTop);
const targetScrollTop = clamp(
  panel.scrollTop + itemRect.top - anchorTop,
  0,
  panel.scrollHeight - panel.clientHeight,
);
```

```javascript
function previewTextSegment(item) {
  const start = Number(item.dataset.displayStart);
  const end = Number(item.dataset.displayEnd);
  seekCutPreview(start);
  transcriptPreviewRange = {
    start,
    end,
    displayKey: item.dataset.displayKey,
  };
  updateActiveTranscriptSegment(start, { follow: true });
  previewVideo.play();
}

// 仅试听当前已删除文字时绕过自动跳过。
if (
  transcriptPreviewRange &&
  current >= transcriptPreviewRange.start &&
  current < transcriptPreviewRange.end
) {
  return null;
}

// 到达当前展示行末时结束单段试听，并恢复公共播放语义。
if (
  transcriptPreviewRange &&
  current >= transcriptPreviewRange.end - SPEECH_BOUNDARY_EPSILON
) {
  const previewEnd = transcriptPreviewRange.end;
  previewVideo.pause();
  transcriptPreviewRange = null;
  previewVideo.currentTime = previewEnd;
}
```

浏览器回归必须检查：文字行数与播放按钮数一致；普通和已删除文字均按源时间开始播放并在各自行末自动暂停；单段结束或主动 seek 后公共播放恢复正常跳过删除内容；点击不打开编辑弹窗、不改变删除状态；活动行中段对齐 sticky 工具栏下方、尾部不被工具栏遮挡且不发生重复滚动；桌面与 375px 无横向溢出，375px 下时间置于文案上方且播放目标保持本列表约定的 `22px`。

时间轴点击/拖动复用的实现应保持类似以下分支，并覆盖主体、手柄和取消弹窗三条测试路径：

```javascript
if (!hasDragged && mode === "move") {
  requestConfirmation(range);
} else if (hasDragged) {
  commitRangeAdjustment(range);
}
// mode === "start" / "end" 且未拖动时不确认。
```

参考：`app.js` 的 tabs、cut history 和 timeline；`timeline-model.js` 的 `createPointerSession`；`ui-feedback.js`。
