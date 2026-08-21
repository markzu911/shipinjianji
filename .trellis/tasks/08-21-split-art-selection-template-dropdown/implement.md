# 艺术字选择页面与模板下拉实施计划

## Phase 1: Contract-first Tests

- [x] 更新静态契约，锁定三个 tab/panel 的双向 ARIA、选择/设置控件归属、模板 listbox 结构和说明文案移除。
- [x] 更新现有真实浏览器 tab 工作流，覆盖三项 roving focus、panel 隐藏、滚动归零、无 selection 默认选择页和有 selection 默认设置页。
- [x] 新增选择页工作流：普通实例、视频文案整轨和新建实例成功后自动进入设置页，删除最后一项后回到选择页。
- [x] 新增模板下拉行为测试：名称/真实样式、无介绍、鼠标选择、键盘打开/导航/选择/关闭、点击外关闭和 375px overflow。

## Phase 2: Split Selection And Settings Panels

- [x] 在 `EditorArtTool` 新增 `selection` tab/panel，把实例列表、自定义文字新增、视频文案一键添加及其状态反馈迁入该 panel。
- [x] 将 `settings` panel 收敛为详情标题、设置错误、空状态和原有参数 fieldset，不复制 Store 数据或命令。
- [x] 扩展 tab 状态机：activate 按 selection 决定默认页；选择/新增/全文轨成功后进入设置；设置页失去最后 selection 时返回选择页；AI 页保持显式用户选择。
- [x] 保持三个 tab 的 roving focus、panel hidden、工具 inert、滚动归零和 deactivate/destroy 清理。
- [x] 分离选择页与设置页错误出口，确保新增、位置预设和全文轨错误在对应可见页面反馈。

## Phase 3: Replace Template Grid With Dropdown

- [x] 把 EditorArtTool 的模板 radiogroup 改为 trigger + listbox，只渲染模板名称和 `renderCharacters()` 样式样例。
- [x] 实现鼠标选择、外部点击关闭，以及 Enter/Space/Arrow/Home/End/Escape/Tab 的焦点和关闭行为。
- [x] 选择后复用现有 `commitSelectedPatch()`；验证 manual 单项和 transcript 整轨的 revision、字段与时间语义保持。
- [x] catalog 重载、deep-link handoff、无 selection 首选模板、invalid template fallback 和 destroy 后迟到响应保持现有行为。

## Phase 4: Styling And Responsive Polish

- [x] 新增稳定的 trigger/listbox/option 布局、选中/hover/focus/disabled 状态和 44px 交互尺寸。
- [x] 保持三 tab 桌面单行；在 375px 下验证模板名称换行、样例尺寸、listbox 滚动及文档/面板无横向溢出。
- [x] 更新 `styles.css` 和 `editor-art-tool.js` 资源版本；不修改仍被其他页面使用的通用模板网格样式。

## Phase 5: Integration And Spec Gate

- [x] 运行 ArtTool 静态与真实浏览器定向测试，覆盖新增、整轨、选择、模板、删除、AI 确认和刷新恢复。
- [x] 验证 cut/art/pip 切换保持同一 document/video/Store/preview/timeline，`srcWrites/loadCalls` 为 0 且 iframe 为 0。
- [x] 运行完整 browser suite、完整 pytest、全部 `web/*.js` 语法检查、compileall 和 `git diff --check`。
- [x] 使用 Trellis spec 更新流程修订艺术字 tab、panel 职责和模板下拉测试契约，再完成独立质量检查。

## Validation Commands

```powershell
node --check web/editor-art-tool.js
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "art or template or tool_switch"
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q server
Get-ChildItem web -Filter *.js | ForEach-Object { node --check $_.FullName }
git diff --check
```

## Risky Files And Review Points

- `web/editor-art-tool.js`：页签、选择、模板、catalog 与异步 effects 共处一处；检查 tab 转换不在普通 Store render 中反复触发。
- `web/styles.css`：通用 `.art-style-grid/.art-style-option` 仍可能服务其他页面；只新增或移除 EditorArtTool 专属选择器。
- `tests/app/browser/test_editor_workflows.py`：已有测试默认选择控件与设置控件同页，迁移后必须显式打开正确 tab，不能为了通过而降低 identity/revision/overflow 断言。
- `.trellis/spec/testing/browser-workflows.md`：当前明确锁定两个 tab，必须与新的用户决策同步更新。

## Rollback

- 页面结构、下拉控件、样式和测试作为同一功能提交回滚；Store、草稿、API 与持久化 schema 未变化。
- 若自定义 listbox 在目标浏览器出现不可接受的焦点问题，回滚到旧模板网格并保留已经验证的“选择/设置”页拆分，另行修复下拉，不改模板数据。
