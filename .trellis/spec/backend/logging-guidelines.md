# 日志与诊断

## 当前事实

项目目前主要依赖 Uvicorn 访问日志和 job 状态中的 `progress`、`message`、`error` 字段，没有成型的结构化日志层。不要在规范中假定已有日志框架。

## 新增诊断信息的规则

- 优先记录稳定标识：`job_id`、素材 ID、阶段、耗时、FFmpeg 返回码和终态。
- 用户界面所需进度写入 job 状态；运维诊断才进入服务日志，两者不要混用。
- 外部服务失败日志可记录服务商、模型、HTTP 状态和安全摘要，不记录 API Key、Authorization、完整用户文稿、图片字节或完整提示词。
- FFmpeg 失败保留足以定位问题的命令阶段和 stderr 尾部；不要记录包含大量 `drawtext` 文案的完整命令。

## 现有静默点

`periodic_storage_cleanup` 会捕获异常以保证维护循环继续运行。修改该路径时应增加安全的 warning 级诊断，但不能让一次清理失败终止应用。

## 未来结构化日志字段

引入日志封装时统一字段：`event`、`jobId`、`assetId`、`stage`、`durationMs`、`status`、`errorType`。这是一项演进规则，不代表当前已经完成。

参考：`server/app.py` 的 `periodic_storage_cleanup`、`run_ffmpeg`、各 `process_*` 函数。
