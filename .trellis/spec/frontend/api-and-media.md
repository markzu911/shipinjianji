# 前端 API 与媒体

## 请求规则

- 路径参数使用 `encodeURIComponent`。
- JSON 请求显式设置 `Content-Type: application/json`；上传保留 `FormData`/XHR 以支持进度。
- 非 2xx 先解析服务端 `detail`，解析失败使用稳定中文兜底；不要把 Response 当成功 payload。
- 写操作期间禁用对应按钮，避免重复创建后台任务。

## 轮询

- 创建后台任务后轮询 `GET /api/transcriptions/{job_id}` 的相应子状态。
- 只在非终态继续；`completed` 渲染结果，`failed`/`cancelled` 停止并恢复控件。
- 新任务、页面重置、过期任务和取消操作必须使旧轮询失效，防止迟到响应覆盖新状态。
- 404 的“任务不存在或服务已重启”走现有过期任务恢复流程。

## 媒体源

- 原视频、剪辑版、艺术字版和画中画版都有独立 API；不要仅凭某个 DOM URL 推断语义。
- 选择源时同时确定 transcript/time anchor；剪后源必须使用 retained transcript 或显式映射。
- 受 job 状态保护的媒体只能在对应 API 可读后投影 source URL；处理中状态不得提前占用完成态的 source key。
- 相同 source key 只有在媒体健康或仍处于有效加载中时才跳过 `load()`；`video.error`、已开始加载后的 `NETWORK_NO_SOURCE` 或错误事件必须允许重试。`src` 写入到 `loadstart` 之间的瞬时 `NETWORK_NO_SOURCE` 仍属于本次加载，不能据此重复重载。
- Object URL 在替换/重置/卸载时 `URL.revokeObjectURL`。
- 视频 metadata 未加载前不依赖 duration/dimensions；使用现有 wait helper 和错误事件。

## 时间线

- 浏览器轨道使用 `EditorTimeline` 的 `schemaVersion: 1` 文档形状。
- clip 必须有稳定 `id`、`trackId`、`kind`、`start`、`end`、`minDuration` 和可序列化 `payload`。
- source time 与 edited time 的映射必须与后端删除区间算法一致；修改时同时更新 Python/JS 回归测试。
- 预览 payload 和最终 compose payload 由同一状态投影产生，禁止分别手拼后逐渐漂移。

参考：`web/app.js` 的 `pollJob`/`pollEdit`、`editor-suite.js` 的统一生成、`timeline-model.js`。
