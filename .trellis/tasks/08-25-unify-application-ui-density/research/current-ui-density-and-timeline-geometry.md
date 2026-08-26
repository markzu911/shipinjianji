# 当前 UI 密度与时间轴几何调研

## 1. 页面与资源边界

当前前端是无构建步骤的原生 HTML/CSS/JavaScript，公共样式全部集中在 `web/styles.css`：

- `web/index.html`：上传、处理、文字剪辑、艺术字、画中画和公共预览/时间轴；
- `web/settings.html`：模型与凭证设置；
- `web/font-manager.html`：字体管理；
- `web/font-library.html`：艺术字模板库；
- 四个页面均引用同一个 `styles.css?v=20260825-05`，主编辑器另引用 `app.js?v=20260825-02`。

因此视觉密度可以通过一套共享 token 和页面作用域规则统一，但每个实际变更的静态资源都必须同步 cache-buster 和前端契约测试。

## 2. 现有密度基线

### 文案列表

`web/styles.css:2410` 已将 `.segment-item` 从旧的 64px 行高缩到 32px，选择圆点与播放按钮从 44px 缩到 22px，但原时间/正文只有 6.5px/7.5px，播放状态 5px，空白标题/meta 7px/5.5px，已低于清晰阅读下限。后续保留紧凑行和控件，将这些文字提高为时间 9px、正文 10px、播放状态 7px、空白标题 9px、meta 8px，相关图标/勾选 10–11px；短行保持约 32px，换行和说明行自然增高。

本任务不应再次缩小这组控件；它是其他列表密度的视觉参考和下限，而不是可以叠加的全局比例。

### 画中画 inspector

`web/styles.css` 的 `.editor-pip-tool-panel` 后续按用户确认调整为 `zoom: 0.6`，相对上一版 0.55 视觉尺寸约再放大 9%；外层 `.editor-pip-tool` 保持 `width: 100%` 并负责滚动。规格同时要求 radio 显式等宽等高，并将视觉滚动差值按 zoom 比例换算回逻辑 `scrollTop`。0.6 缩放会放大通用 Inter/CJK fallback 与合成 650/750 字重在小物理字号下的发虚问题，因此面板改用跨平台中文 UI 字体栈，正文/辅助文字固定 500，标题/强调固定 700；原 11–12px 小字经缩放仅为 6.6–7.2px，后续统一增加 scoped 15/16/17px 下限，实际视觉约 9/9.6/10.2px，并覆盖生成资产状态与控件，不改变预览或时间轴几何。

字号提高后，原 `.pip-segment-option > span` 的 `46px minmax(0, 1fr)` 时间列无法稳定容纳 15px 的 `MM:SS.d`，时间会侵入正文。后续只在顶层面板内将其改为 `64px minmax(0, 1fr)`，继续使用 12px gap；0.6 缩放后两列实际间距约 7.2px，正文仍由 `minmax` 和 ellipsis 承担窄屏收缩。

这是已存在的局部兼容例外。新的统一密度规则不能再作用一次，也不能将该做法扩展到预览、时间轴或整个页面。

### 其他页面和面板

导航、设置、字体/模板库及多数 inspector 仍混用 44–48px 控件、12–18px 间距、18–48px 标题和 16–32px 面板 padding。当前不存在统一的 density token，页面级覆盖散落在 `styles.css` 多个阶段和响应式断点中。

## 3. 预览几何硬边界

公共预览由以下层级共同所有：

```text
.text-editor-preview-pane
  -> .cut-preview-panel
    -> #cutPreviewPlayer
      -> #cutVideoStage.cut-video-stage
        -> #cutPreviewVideo
        -> #editorSuitePreviewOverlay
          -> .editor-suite-preview-canvas
```

`PreviewCompositor` 使用预览 canvas 的 `getBoundingClientRect()` 将 pointer 坐标换算为源视频归一化坐标；普通预览使用 contain，设备预览使用 cover。以下规则不得被密度任务改变：

- `.text-editor-workspace` 中预览列的最终可用宽高；
- `.cut-preview-panel`、`.cut-preview-player`、`.cut-video-stage` 的可见矩形；
- video/canvas 的 contain/cover、transform、源分辨率与 pointer mapping；
- 顶层公共 video、preview、timeline 的唯一运行时和 revision。

因此禁止在 `body`、`.page-shell`、`.text-editor-workspace`、预览 pane、video stage 或 preview canvas 上使用 `zoom`/`scale`。右侧 inspector 可以通过内部 padding、字号、控件高度和列表间距变紧凑，但工作区列比例的修改必须保证预览矩形不缩小。

## 4. 时间轴当前几何

公共剪辑时间轴的静态基础值位于 `web/styles.css:1954`：

| 几何项 | 当前值 | 目标值（约 -15%） |
| --- | ---: | ---: |
| ruler | 18px | 15px |
| 文案轨 | 30px | 26px |
| 无效果轨总高 | 92px | 78px |
| 效果轨行高 | 30px | 26px |
| 独立图层时间轴总高 | 74px | 63px |

带效果轨时不能只改 CSS。`web/editor-timeline-controller.js:146-160` 根据 lane 数写入：

```javascript
layer.style.height = `${rowCount * 30}px`;
track.style.setProperty("--editor-layer-timeline-height", `${rowCount * 30}px`);
track.style.setProperty("--editor-timeline-track-height", `${74 + rowCount * 30}px`);
```

运行时一行效果轨实际为 104px，两行为 134px；CSS 中 `.has-effect-track` 的 122px 只是 fallback，常被 inline variable 覆盖。实施时应统一为约 15% 压缩后的运行时公式，推荐 effect base 63px、row 26px：一行为 89px，两行为 115px。CSS fallback、clip 高度、top/inset、缩略图层和动态 JS 必须一起调整。

时间轴的横向宽度、时间比例、seek range、播放头 transform 和 pointer 到 source/edited time 的换算只依赖 track 宽度，不应随纵向密度改变。

## 5. 响应式和可访问性约束

- `body.has-result` 在 `>=1001px` 已要求 header 与 page shell 铺满视口；不能恢复固定 `--editor-width` 留白。
- 375px 下核心流程不得横向溢出，隐藏工具不可聚焦。
- 文案列表 22px 命中目标是用户确认的特例；其他移动端主要动作仍保留约 44px 命中区，视觉图标可以更小。
- radio/checkbox 必须显式等宽等高，避免通用 `min-height` 把圆形拉成椭圆。
- 时间轴绝对定位项必须有完整纵向几何；缩略帧实际高度应大于 0 且等于所属轨道高度。

## 6. 预期改动与测试锚点

预期产品文件：

- `web/styles.css`：密度 token、页面/组件作用域、时间轴纵向几何、响应式规则；
- `web/editor-timeline-controller.js`：效果轨动态行高常量和 inline variable；
- `web/index.html`、`web/settings.html`、`web/font-manager.html`、`web/font-library.html`：样式 cache-buster；若 controller 变更则同步其 script cache-buster；
- `tests/app/test_frontend_contracts.py`：资源版本、密度 token、预览禁缩放和时间轴数值契约；
- `tests/app/browser/test_editor_workflows.py`：桌面/375px 实际几何、预览前后不变、轨道高度和交互回归。

浏览器基线应在改动前后记录同一 viewport 下 preview panel/stage/video/canvas 的矩形，并允许最多 1px 渲染误差；时间轴则断言目标高度、内部项可见、点击定位和拖拽/分割不变。

## 7. 结论

本任务应作为展示层密度重构实施，不改变 Store、草稿、媒体源或 compose。可靠的最小方案是：共享密度 token + 页面作用域覆盖 + 独立时间轴几何常量；保留现有文案列表和画中画的已确认特例，并把预览 DOM 明确列入不可缩放区。
