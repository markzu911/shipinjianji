# 前端 API 与媒体

## 请求规则

- 路径参数使用 `encodeURIComponent`。
- JSON 请求显式设置 `Content-Type: application/json`；上传保留 `FormData`/XHR 以支持进度。
- 非 2xx 先解析服务端 `detail`，解析失败使用稳定中文兜底；不要把 Response 当成功 payload。
- 写操作期间禁用对应按钮，避免重复创建后台任务。

## 轮询

- 创建后台任务后轮询 `GET /api/transcriptions/{job_id}` 的相应子状态。
- 只在非终态继续；`completed` 渲染结果，`failed`/`cancelled`/`interrupted` 停止并恢复控件。`interrupted` 必须显示原因和明确的同 job 重试动作。
- 新任务、页面重置、过期任务和取消操作必须递增 request generation；所有 poll/retry/upload 成功与异常分支在渲染前同时校验 generation 和 job id，防止迟到响应覆盖重选后的页面。
- 只有真正不存在/已清理的 404 走过期任务流程；恢复失败 409 和 `interrupted` 保留当前 job 与重试 UI。
- “重试处理”与“重新选择视频”是两个独立操作；重试期间按钮 disabled/`aria-busy`，重复点击或双标签冲突显示服务端 409，不新建 job。

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
