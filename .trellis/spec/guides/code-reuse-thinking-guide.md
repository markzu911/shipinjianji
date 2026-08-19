# 项目复用检查指南

## 先查找现有所有者

这个项目最容易漂移的逻辑不是普通 DOM 辅助函数，而是时间轴、媒体源、overlay 参数和 API payload。新增实现前先搜索：

- 时间轴：`timeline-model.js`、`sourceTimeToEditedTime`、`editedTimeToSourceTime`、`timeline_after_deletions`；
- 区间：`normalize_delete_ranges`、`normalizeOverlayRange`、`normalize_picture_in_picture_overlays`；
- 状态更新：后端 `update_*_job`，前端 `EditorTimeline.createStore` 和 `editor-suite:*` 事件；
- UI 反馈：`web/ui-feedback.js`；
- 播放器和源时间映射：`editor-media-controller.js`；时间线拖动/缩放：`editor-timeline-controller.js`；艺术字/画中画 inspector：`editor-art-tool.js`、`editor-pip-tool.js`。

## 必须复用或提取的情况

- 同一时间转换或 payload 归一化已出现两处，准备出现第三处；
- 预览和导出必须产生一致结果；
- 顶层 Store、工具、预览和 compose 都读取同一领域字段；
- Python 与 JavaScript 各自实现同一契约且一方发生字段变更。

这时应给契约确定一个所有者：浏览器时间线优先放 `web/timeline-model.js`，顶层协调放 `web/editor-suite.js`，服务端权威校验放 `server/app.py` 或提取后的领域模块。

## 不要过早抽象

- 单个页面的一次性 DOM 查询或格式化函数可以留在页面脚本。
- Python 和浏览器之间不能直接共享运行时代码；应共享清晰的数据契约并在两端测试，而不是引入构建系统只为消除几行重复。
- 不要借复用之名整体重写原生 JavaScript 或拆微服务。

## 变更检查

1. `rg` 搜索同名字段、事件 type、状态值和 API 路径。
2. 确认原视频、剪辑视频、艺术字和画中画所有消费者。
3. 更新契约所有者，再更新适配器。
4. 为两个以上消费者增加一致性测试。

特别警惕：重新引入 HTML 快照、工具私有 generation payload、重复 source/edited 时间映射或第二个媒体/时间线 owner。这些路径已在 B4 删除，不得恢复。
