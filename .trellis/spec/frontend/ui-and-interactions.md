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
- 固定格式元素（视频舞台、时间线、轨道、图层列表）使用稳定尺寸/比例，动态标签不得引发布局跳动。
- 不新增解释功能的营销文案；状态文字只说明当前结果、错误和可执行下一步。

### 设备预览安全区

普通画布预览必须完整显示源视频；显式的设备实机预览可以使用目标设备逻辑尺寸和 `object-fit: cover`，模拟全屏应用在该设备上的真实裁切。实机预览只改变显示变换，不能修改源视频、编辑坐标或导出比例。硬件安全区与应用 UI 避让区定义为设备预览容器上的命名变量。纵向 `top`、`bottom`、`height` 百分比按容器高度换算；纵向 `padding` 的百分比会按容器宽度计算，不能直接复用前者，应改用按逻辑宽度换算的 `cqw`。

设备预览的内容合成层必须共享同一个适配模式：基础视频使用 `cover` 时，艺术字和画中画画布也必须按 `cover` 缩放并居中裁切；普通预览则继续使用 `contain` 完整展示。抖音顶部、侧边和底部 UI 属于设备视口层，不参与内容画布缩放。否则视频会被放大裁切，而艺术字和画中画仍按窄视口缩小，造成相对尺寸与导出画面不一致。

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
- pointer session 在 move 中预览，在 finish 时 commit；不要每个 pointermove 都发网络请求。
- 同一时间轴控件同时承担“点击确认”和“拖动调整”时，必须用明确的位移阈值区分两种语义；只有主体在阈值内完成的点击可以确认，手柄点击和超过阈值的拖动结束都不能确认。
- 待确认时间轴选区打开确认弹窗后，弹窗“取消”只关闭弹窗并保留选区；删除选区应由 Delete/Backspace 或独立的取消选区动作负责，不能混用两种取消语义。
- 手动时间轴拖拽只将范围 clamp 到媒体时长，不吸附或扩大到文字字符边界；它与文案点击删除的字符级语义相互独立，并继续使用二次确认。
- 播放、seek、selection、drag/resize 后同步顶层和嵌入工具，但避免反馈循环。
- 撤销/重做记录语义操作，但文字剪辑检查器不提供“操作记录”页签、历史列表或可见的撤销/重做按钮。历史栈与本地持久化属于内部能力，只通过 `Ctrl/Cmd+Z`、`Ctrl/Cmd+Shift+Z` 和 `Ctrl/Cmd+Y` 访问。
- 全局剪辑快捷键处理器必须忽略 `input`、`textarea`、`select` 和 `contenteditable` 目标，保留浏览器原生编辑撤销；快捷键执行后仍要刷新预览、时间轴、统计和草稿保存状态。

### 艺术字手动坐标契约

艺术字位置的权威状态始终是 overlay 的归一化 `x/y`，允许范围为 `0.05–0.95`。手动输入只把该状态投影成 `5%–95%` 的百分比，不得新增独立坐标状态；拖动画布、套用位置预设和手动输入都必须通过 `updateSelectedOverlay` 或同一轨道共享更新链路修改权威状态。

- `input` 中合法的 `5–95` 数值实时更新预览；回车或 `change` 再 clamp 越界值并回写格式化结果。
- 渲染、拖动和套用预设后同步两个输入；当前正在编辑的输入不能被同步渲染覆盖，否则用户无法输入多位数或小数。
- 全文艺术字轨道的 `x/y` 继续由 `TRANSCRIPT_TRACK_STYLE_KEYS` 批量应用到每个 cue。
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

每条文字展示行必须提供独立的播放按钮，按钮与删除圆圈、恢复按钮和文字编辑按钮是兄弟节点，事件委托先处理播放按钮并立即返回。播放使用行上的源时间 `data-display-start/end` 调用公共 `seekCutPreview`，然后播放原视频；它不能打开文字编辑弹窗，也不能改变 `selectedRanges`、草稿或撤销历史。纯图标按钮使用播放图标、说明性 `aria-label`/title 和至少 `44px` 点击区。

已删除文字同样必须能试听。点击其播放按钮时，只在该展示行的源时间范围内临时绕过剪辑预览的“跳过已删除区间”逻辑；播放到展示行末时必须保存终点、暂停、清除临时范围，再把播放头校准到行末，避免校准产生的新 `timeupdate` 再次命中旧范围。用户执行其他 seek 时也立即清除临时范围，后续公共播放恢复正常跳过删除内容。当前行高亮优先命中该临时范围，因此已删除行试听时也显示 `aria-current` 和“播放中”。

播放跟随滚动以文字面板为 scroll container，并读取当前 sticky `.cut-toolbar` 的实际位置和高度，把活动行顶部对齐到工具栏下方固定间距。锚点必须直接使用 `toolbar.getBoundingClientRect().bottom + 8`；不能用 `panelRect.top + toolbarHeight` 推算，因为面板 padding、边框或 sticky 偏移会让活动行被工具栏遮挡。目标 `scrollTop` 必须 clamp 到 `0..scrollHeight-clientHeight`：中段行保持顶部锚点，接近尾部时面板停在最大滚动量，活动行随剩余内容自然下移。同一 `data-display-key` 只调度一次滚动；`prefers-reduced-motion: reduce` 使用即时滚动，其他情况可使用平滑滚动。

```javascript
const anchorTop = (toolbarRect?.bottom ?? panelRect.top) + 8;
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

浏览器回归必须检查：文字行数与播放按钮数一致；普通和已删除文字均按源时间开始播放并在各自行末自动暂停；单段结束或主动 seek 后公共播放恢复正常跳过删除内容；点击不打开编辑弹窗、不改变删除状态；活动行中段对齐 sticky 工具栏下方、尾部不被工具栏遮挡且不发生重复滚动；桌面与 375px 无横向溢出，375px 下时间置于文案上方并保留 `44px` 播放目标。

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
