# 前端规范索引

前端是原生多页面应用，没有 npm 构建步骤。脚本通过 `<script defer>` 按顺序加载，并共享 `window` 全局。

| 文档 | 适用范围 |
| --- | --- |
| [架构与状态](./architecture-and-state.md) | 页面职责、EditorProjectStore、顶层工具、历史入口和事件协议 |
| [画中画运行时](./picture-in-picture-runtime.md) | 顶层 PipTool、素材状态、异步 effect、草稿恢复和无上限缩放 |
| [UI 与交互](./ui-and-interactions.md) | DOM、可访问性、响应式、拖动和反馈 |
| [API 与媒体](./api-and-media.md) | fetch/XHR、轮询、媒体源和时间轴 |

修改前同时阅读 `../guides/project-overview.md` 和 `../guides/cross-layer-thinking-guide.md`。
