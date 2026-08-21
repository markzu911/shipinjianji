# 艺术字选择页面与模板下拉技术设计

## 1. Design Goal

只重排顶层 `EditorArtTool` 的 UI 投影和瞬时交互状态：把实例新增/选择放入独立页签，把已选实例字段留在设置页，并将模板网格替换为可访问的自定义下拉。`EditorProjectStore`、catalog、renderer、媒体、时间轴、预览和 compose 契约保持不变。

## 2. Ownership Boundary

- `web/editor-art-tool.js` 继续是艺术字 inspector DOM、页签、模板下拉开关与焦点状态的唯一 owner。
- `project.timeline.selection` 和 `project.art.overlays` 继续是选择与艺术字数据权威；页签和下拉只保存瞬时 UI 状态，不能缓存可覆盖 Store 的 overlay 或模板副本。
- 模板 catalog 仍来自 `/api/art-templates`，样式样例继续调用 `EditorArtRenderer.renderCharacters()`；模板应用继续走 `commitSelectedPatch()` 和现有整轨更新规则。
- `EditorSuite`、公共视频、PreviewCompositor、TimelineController 和 compose 数据流不需要新增接口。

## 3. DOM Structure

`EditorArtTool` 顶部 tablist 调整为三个 tab：

```text
选择艺术字 (selection)
艺术字设置 (settings)
AI 推荐 (ai)
```

`selection` panel 包含标题/数量、`[data-art-list]`、自定义文字输入、添加错误和视频文案一键添加区域。`settings` panel 只包含详情标题、设置错误、无选择空状态和原有 fieldset。AI panel 保持现有结构。

三个 panel 延续现有 `role=tabpanel`、`aria-labelledby`、`hidden` 和 inert 外层工具语义。页签使用既有 roving `tabIndex` 与 ArrowLeft/ArrowRight/Home/End 行为，三项仍保持桌面单行和移动端稳定尺寸。

## 4. Entry And Transition State Machine

```text
activate
  -> selected overlay exists ? settings : selection

selection + add/select/full-track success
  -> Store selection commit
  -> settings

settings + delete last selected overlay
  -> selection

AI + confirm suggestions
  -> existing selection commit
  -> settings
```

Store 订阅重绘不得因为播放帧、catalog 或无关 revision 任意切换用户正在查看的 tab。仅 `activate()`、选择页的明确成功动作、AI 确认和“设置页失去最后 selection”执行上述转换；AI 页不会因为无 selection 被强制跳走。每次 tab 转换继续把 ArtTool 自身 `scrollTop` 归零并关闭模板下拉。

## 5. Template Dropdown

原生 `<select><option>` 不能跨浏览器可靠承载 `renderCharacters()` 生成的多字符效果，因此实现为单一自定义下拉：

- 触发按钮包含当前模板的两字样式样例、模板名称和现有 Iconify 的向下箭头，带 `aria-haspopup="listbox"`、`aria-expanded` 与 `aria-controls`。
- 展开容器使用 `role="listbox"`；每个模板使用可聚焦 `role="option"`，只包含两字样式样例和模板名称，并用 `aria-selected` 标识当前模板。
- 触发器 Enter/Space/ArrowDown/ArrowUp 打开并聚焦当前项；选项支持 ArrowUp/ArrowDown/Home/End，Enter/Space 提交，Escape 关闭并把焦点还给触发器；Tab 关闭后继续自然焦点顺序。
- 点击选项调用现有 `commitSelectedPatch()`，提交模板 ID、颜色、描边和 normalize 后的模板 effects，然后关闭列表。点击下拉外、切换 tab、deactivate、destroy 或 selection 消失时关闭。
- 下拉的选中值始终从 `selectedOverlay().artStyle` 派生；仅保留 `templateMenuOpen` 和当前键盘活动项等瞬时状态，不建立第二个模板值。

## 6. Rendering And Compatibility

- `renderTemplates()` 改为渲染触发器摘要与 listbox 选项，不再创建说明 `<small>` 或 radiogroup 卡片。
- catalog 迟到加载后重绘同一控件；模板 deep-link handoff、无 selection 首选模板和 fallback 逻辑保持原样。
- 普通 overlay 模板变化只更新目标；transcript representative 仍经 model 的 track-aware update 原子更新同一 `trackId` 全部 cue。
- 删除最后 selection 时设置字段隐藏并切回选择页；删除后仍有下一个 selection 时保持设置页。
- 不改模板 API、Store reducer、模型归一化、时间轴轨道或服务端渲染。

## 7. Styling And Responsive Rules

- 新控件复用现有颜色 token、边框、6px 以内圆角、44px 交互高度和 `.art-style-sample` 渲染能力。
- 触发器和 option 使用 `grid-template-columns: 56px minmax(0, 1fr) auto`；名称允许换行但不得覆盖样例或箭头。
- listbox 位于模板字段内，宽度受父级约束，设置合理 max-height 和垂直滚动；375px 下保持单列、`min-width: 0` 和 `max-width: 100%`，不得产生页面横向滚动。
- 删除仅供旧编辑器网格使用的 EditorArtTool 样式引用，但不删除其他页面仍使用的通用 `.art-style-grid/.art-style-option` 规则。

## 8. Verification And Rollback

- 静态契约锁定三 tab、panel 双向 ARIA、控件归属、模板 listbox marker、无说明文本及资源版本。
- 真实浏览器覆盖默认页、自动跳转、三 tab 键盘循环、下拉键鼠操作、普通/整轨模板更新 revision、空状态、工具切换 identity 和 375px overflow。
- 更新 `.trellis/spec/testing/browser-workflows.md` 中已过时的“两 tab/设置页含视频文案”契约，并补充本次稳定职责。
- 改动集中于 ArtTool、共享样式、资源版本和测试，可整体回滚；Store/API/schema 未迁移，无数据回滚步骤。
