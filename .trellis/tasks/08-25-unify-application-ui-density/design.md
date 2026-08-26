# 统一全应用 UI 密度技术设计

## 1. Architecture Boundary

本任务只改变展示层和时间轴纵向几何，不改变项目状态或媒体语义：

```text
EditorProjectStore / cut draft / media clock（不变）
  -> shared EditorFrame（不变）
  -> preview compositor geometry（锁定不变）
  -> scoped UI density projection（调整）
  -> timeline vertical geometry（调整）
```

禁止新增第二套 preview、timeline、media owner 或 density runtime。CSS 是密度权威；JavaScript 只在动态效果轨必须计算像素高度时使用一个与 CSS 契约一致的行高常量。

## 2. Density Token Model

在 `:root` 增加命名清晰的紧凑密度 token，例如：

```css
--ui-compact-control-height: 36px;
--ui-compact-control-height-small: 30px;
--ui-compact-panel-padding: 12px;
--ui-compact-gap: 8px;
--ui-compact-font: 12px;
--ui-compact-font-small: 10px;
--timeline-ruler-height-compact: 15px;
--timeline-row-height-compact: 26px;
```

这些 token 通过明确页面/组件选择器投影，不能给 `html/body` 设置统一 font-size/zoom，也不能在任意预览祖先上使用 `transform: scale()`。`.segment-item` 保留紧凑行与 22px 控件，但其正文、时间、状态、空白标题/meta 提高到 10/9/7/9/8px，必要的图标和勾选为 10–11px；`.editor-pip-tool-panel` 按后续确认保持 `zoom: 0.6`，两者都不得叠加新的比例。画中画面板额外使用 `Microsoft YaHei UI / PingFang SC / Noto Sans CJK SC / Source Han Sans SC / system-ui` 字体栈、正文 500 和标题/强调 700，并以 scoped token 定义 small/time 15px、regular/control 16px、strong 17px。PiP 文案选项在同一 scoped 区域覆盖为 `64px minmax(0, 1fr)` 与 12px gap，解决放大后的时间/正文挤压，同时保持正文 ellipsis。字号提升只改善缩放后小字清晰度，短行尽量保持原高，内容不足时自然增高，不参与预览或时间轴布局缩放。

密度优先顺序：

1. 保留业务语义、焦点和命中区；
2. 压缩 margin/padding/gap；
3. 压缩次级字号、图标和装饰；
4. 仅在不影响触控的桌面控件上降低可见高度；
5. 不用整体缩放补偿宽度。

## 3. Page Profiles

### 主编辑器

- 顶部导航、状态区、工具 tabs 和生成按钮使用 compact token；工具步骤仍单行并保留可辨状态。
- 右侧文字/艺术字/画中画 inspector 的标题、卡片、表单、列表间距统一；文案列表与画中画内部沿用现有更紧凑特例。
- `.text-editor-workspace`、`#artWorkspace` 和 `.pip-workspace` 的预览列不缩小；紧凑收益优先用于右侧 inspector 的内容容量。
- 上传和处理状态页缩小非关键标题、卡片留白及步骤间距，但不改变视频上传预览比例。

### 设置、字体和模板库

- shell 保留安全边距和现有响应式列数；标题、toolbar、card、filter、field、button 使用相同 compact token。
- 字体/模板真实样式预览不是普通 UI 文字，不跟随界面字号 token 缩小到失真；只压缩其卡片 padding 和元数据区域。
- 凭证输入和破坏性操作在移动端保持约 44px 命中高度，桌面可见外观按 compact profile 收紧。

## 4. Preview Geometry Lock

以下选择器及其可见矩形是硬性不变区：

```text
.text-editor-preview-pane
.cut-preview-panel
#cutPreviewPlayer
#cutVideoStage
#cutPreviewVideo
#editorSuitePreviewOverlay
.editor-suite-preview-canvas
```

实施前浏览器测试记录矩形；实施后同 viewport、同 seeded video 下逐项比较，宽高差不超过 1px。普通 contain、抖音 cover 和 art/pip pointer mapping 都必须通过现有测试。

为了避免 inspector 变紧凑后 grid 自动重分配空间，桌面 `.text-editor-workspace` / art / pip 的列约束保持当前比例与 preview 最小宽度。不要通过增大右栏占比来展示更多控件。

## 5. Timeline Geometry Contract

### 公共剪辑时间轴

目标静态几何：

```text
ruler                18 -> 15px
text row             30 -> 26px
base track           92 -> 78px
effect row           30 -> 26px
effect runtime base  74 -> 63px
```

有 `n` 个实际效果行时：

```text
trackHeight = 63px + n * 26px
layerHeight = n * 26px
```

一行从 104px 变为 89px，两行从 134px 变为 115px，均约缩小 15%。CSS `.has-effect-track` fallback 使用一行 89px，不再保留与 runtime 不一致的 122px。

`editor-timeline-controller.js` 只写 `--editor-layer-timeline-height` 和必要的最终 track height；行高使用命名常量，禁止继续散落 `30/74`。CSS 同步调整 clip 高度、top、label line-height、ruler tick/playhead handle 和缩略图 inset，保证每一层都有正高度。

### 独立艺术字/画中画图层时间轴

总高从 74px 调整到 63px，ruler 15px、效果行 26px，其余为缩略图区域。横向时间比例、scroll width、clip `left/width`、resize handle 的横向命中区保持不变。

### 交互不变量

- track 的 `clientWidth` 和 scroll model 不变；
- source/edited time 映射、播放头 X、split anchor、selection range 不变；
- pointer 的 Y 只用于命中层级，不写入时间；压缩后 overlay 的 stacking/pointer-events 必须与修改前一致；
- 分割按钮、resize handle 和关键操作仍保留可用命中区。

## 6. Responsive And Accessibility

- 桌面 `body.has-result` 继续铺满视口，左右边界无额外空白。
- 375px 下 panel 改为单列；主要按钮/输入的命中区约 44px，紧凑视觉可通过内部图标和 padding 实现。
- radio/checkbox 设置 `inline-size == block-size`、`aspect-ratio: 1` 和 `flex: 0 0 auto`；外层 label/card 承担命中区域。
- 文案列表的 22px 控件是既有、用户确认的例外，不继续缩小。
- focus-visible、live status、ARIA 和 tab 顺序不变；紧凑布局不得隐藏错误或保存状态。

## 7. Test Strategy

静态契约：

- 锁定 compact token、时间轴 78/63/26/15 数值和 controller 命名常量；
- 禁止 preview 祖先出现 zoom/scale；
- 锁定四个页面的最新 cache-buster；
- 锁定 transcript 与 PiP 特例不被二次缩放。

真实浏览器：

- 1912px：主编辑器铺满，preview panel/stage/video/canvas 改动前后矩形不变；
- 375px：无横向页面溢出，主要控件可聚焦、radio 为圆形；
- 无效果/一行/多行效果轨分别断言 78/89/115px 左右的实际高度和所有子层 `height > 0`；
- 点击 seek、滚动、split、选择、drag/resize 的 source time 与改动前一致；
- 工具切换保持 document/video/preview/timeline identity，`srcWrites/loadCalls == 0`。

## 8. Compatibility, Rollback And Risks

没有 schema、API、Store 或持久化迁移。回滚只需恢复 CSS density section、timeline controller geometry 常量和 cache-buster。

主要风险：

- 广泛晚置 CSS 覆盖被旧的高 specificity 规则抵消；通过 computed style 浏览器断言而非字符串断言发现。
- 对 PiP 再次压缩或错误补偿 `width: 200%`；通过 panel rect/scrollWidth 测试阻止。
- preview grid 因 inspector/主 grid 改动间接缩小；通过矩形快照阻止。
- CSS 与 controller 行高不一致造成裁切或空白；通过无效果/一行/多行矩阵阻止。
- 过小文字和命中区降低可用性；正文设置可读下限，移动端保留主要命中区。
