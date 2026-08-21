# 当前艺术字选择与模板 UI 证据

## Current Structure

- `web/editor-art-tool.js:50-95`：两个 tab；settings panel 同时包含实例列表、新增、全文轨、详情和模板网格。
- `web/editor-art-tool.js:301-317`：tab 使用 `aria-selected`、roving `tabIndex`、panel `hidden` 和 ArtTool scroll reset。
- `web/editor-art-tool.js:319-340`：模板网格每次渲染创建按钮、样式样例、名称和介绍 `<small>`。
- `web/editor-art-tool.js:342-383`：实例列表把 manual 逐项投影，把同 `trackId` transcript cues 聚合为一个整轨入口。
- `web/editor-art-tool.js:385-422`：设置字段从当前 Store selection 派生；transcript 模式隐藏 cue-only 字段并使用整轨标题。
- `web/editor-art-tool.js:494-504`：`renderAll()` 从 Store 重新派生 selection/list/controls，不持有 overlay 副本。
- `web/editor-art-tool.js:517-605`：模板应用、deep-link handoff 和新增实例继续复用 catalog/model/Store command。
- `web/editor-art-tool.js:904-1001`：单一事件委托处理 tab、实例选择、模板和键盘 tab 导航。
- `web/editor-art-tool.js:1036-1079`：activate/deactivate/destroy 管理可见性、inert、effect 与监听器生命周期。

## Existing Contracts

- `.trellis/spec/frontend/architecture-and-state.md:328-393`：ArtTool 只能保存瞬时 UI，Store/preview/timeline/compose 共享同一 frame；模板 handoff 与整轨选择有严格 revision 和字段保留契约。
- `.trellis/spec/frontend/ui-and-interactions.md:1-20`：tabs 必须保持 ARIA 与键盘行为，交互目标约 44px，375px 无横向溢出。
- `.trellis/spec/testing/browser-workflows.md:82-104`：真实浏览器必须锁定唯一运行时、模板单 revision、整轨入口、hidden panel 和媒体 identity；其中“两 tab/设置页包含视频文案”的旧产品契约需随本任务更新。
- `tests/app/test_frontend_contracts.py:778-845`：静态契约当前硬编码两个 tab 和 settings panel 控件归属。
- `tests/app/browser/test_editor_workflows.py:225-300`：真实浏览器当前验证两个 tab、键盘循环、scroll reset、选择列表和工具 identity。

## Decisions

- 选择页承载实例列表、新增和全文轨；设置页承载模板及其他详情字段。
- 模板使用自定义 listbox，而非原生 select，因为选项必须显示 `renderCharacters()` 的真实样式，原生 option 无法可靠承载该 DOM/CSS。
- 激活时根据 Store selection 选择默认页；成功新增/选择自动进入设置，删除最后 selection 返回选择。
- 不拆子任务：DOM 迁移、转换状态与模板下拉共享同一个 ArtTool render/event 边界和同一组浏览器验收。
