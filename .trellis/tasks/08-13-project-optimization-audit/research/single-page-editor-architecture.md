# 单页编辑器架构研究

## 结论

当前界面虽然共享主预览和时间轴外观，但文字剪辑位于 `index.html/app.js`，艺术字和画中画分别运行在两个 iframe 中。三方通过 `editor-suite.js` 的 `postMessage`、HTML 快照和私有 payload 协调，属于多文档工作台，不是真正的单页编辑器。

目标不应是把 `app.js`、`art-text.js` 和 `picture-in-picture.js` 拼成一个文件，而是把三个页面的运行边界改为同一文档中的三个功能模块，并建立唯一的客户端权威状态。

## 当前证据

- `web/index.html` 同时加载 `editor-suite.js` 与 `app.js`，并拥有 `#cutPreviewVideo`、公共 preview overlay 和 inspector host。
- `web/editor-suite.js` 的 `createToolFrame()` 为艺术字和画中画创建 iframe，并通过 `embedded=1` 启动子工具。
- `web/art-text.js` 与 `web/picture-in-picture.js` 各自持有 overlays/items、timeline store、选择、播放投影和 sessionStorage 草稿。
- `web/app.js`、`web/editor-suite.js`、`web/art-text.js`、`web/picture-in-picture.js` 各自维护部分时间轴或项目状态。
- 纯文字保存接口只返回 `editableSegments`，服务端更新后的完整 transcript/art 状态需要额外刷新；这使不同运行时可能暂时使用不同 revision。
- 项目没有 npm、bundler 或 ES module；共享脚本使用 `<script defer>` 与唯一 `window` 全局。

## 目标运行时

```text
index.html（唯一编辑文档）
  EditorProjectStore（唯一客户端项目状态）
    persistent: transcript / cut / art / pip / revision
    ui: activeTool / selection / busy / errors
  MediaController（唯一 video 与播放帧时钟）
  TimelineController（唯一 EditorTimeline store）
  PreviewCompositor（从 selectors 渲染 art + pip）
  InspectorHost
    CutTool.mount(root, services)
    ArtTool.mount(root, services)
    PipTool.mount(root, services)
```

服务端 job/project snapshot 继续是持久权威；浏览器只保留一个对应 revision 的 `EditorProjectStore`。所有写操作通过语义 command 进入 store/effect，成功响应一次性应用规范化 snapshot，禁止各面板自行覆盖其他领域。

## 状态与时间契约

- `transcriptTextChanged` 只改变文字和字符映射，保留已有 art cue 的 `start/end/sourceStart/sourceEnd`。
- `cutRangesChanged`、`artTimingChanged`、`pipTimingChanged` 才允许改变时间结构，并递增 `timingRevision`。
- source time 是持久锚点；edited time 由统一 time-map selector 派生。
- preview layers 和 compose payload 使用同一个 project revision 和同一组 selectors。
- 播放时间由唯一 video/controller 拥有；面板切换和普通保存不替换 `src` 或调用 `load()`。

## 无构建系统下的模块边界

迁移期继续使用按顺序加载的普通脚本和唯一全局，不引入框架：

- `editor-project-store.js` -> `window.EditorProjectStore`
- `editor-media-controller.js` -> `window.EditorMedia`
- `editor-preview-compositor.js` -> `window.EditorPreview`
- `cut-tool.js` -> `window.CutTool`
- `art-tool.js` -> `window.ArtTool`
- `pip-tool.js` -> `window.PipTool`

每个工具只暴露 `mount(root, services)`、`activate()`、`deactivate()`、`destroy()`；工具不得查询或修改其他面板 DOM，不拥有第二个 project/timeline store。

## 推荐迁移顺序

1. 建立真实浏览器基线，锁定文字保存、三工具切换、刷新恢复和统一生成。
2. 引入 `EditorProjectStore`、统一 action/selectors 和 revision，但用适配器继续喂给现有 iframe。
3. 将公共 video、播放帧时钟、preview compositor 和 timeline 的所有权完全移到顶层。
4. 先迁移艺术字为顶层可挂载模块，保留旧 iframe feature flag 作为回滚。
5. 再迁移画中画；验证艺术字与画中画组合拖动、缩放、时间调整和生成。
6. 删除 iframe、`postMessage`、HTML 快照、私有 generation payload 和 embedded 分支。
7. 将旧独立 URL 改为主编辑器 tool 参数跳转，验证历史链接兼容后删除旧页面资源。

## 主要风险

- 现有子工具大量顶层 DOM 查询和初始化副作用，不能直接把脚本挂到 `index.html`；必须先改造成显式 `mount()` 工厂。
- 艺术字与画中画都包含独立播放、时间轴、草稿和生成逻辑，迁移时最容易产生双监听、双保存或两个播放时钟。
- 纯文字修改和时间变化当前没有完整区分；若先移除刷新而未建立 action/revision 契约，艺术字 cue 仍可能被重新计时。
- 静态源码契约不足以保护跨工具迁移，必须先增加真实浏览器工作流测试。

## 不推荐方案

- 不直接把三个 JS 文件合并。
- 不让 iframe 通过 `window.parent` 直接操作顶层 store 作为最终方案。
- 不用自定义事件替换 `postMessage` 后继续保留三套状态；这只是换协议名称。
- 不在同一阶段同时换框架、引入 bundler、重写 UI 和修改后端时间语义。
