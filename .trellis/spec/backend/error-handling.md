# 错误处理

## 边界分工

- 路由边界用 `HTTPException(status_code=..., detail=...)` 返回可直接展示的中文错误。
- 领域归一化函数用 `ValueError` 表示无效输入；路由捕获后映射为 4xx。
- 媒体、外部 API 和文件 I/O 失败可抛出 `RuntimeError` 或原始异常，由后台任务捕获并写入对应 job 子状态。
- 用户取消使用 `GenerationCancelledError`，不要把取消标记为普通失败。

## 后台任务状态

所有后台任务必须形成终态：`completed`、`failed` 或 `cancelled`。异常路径必须：

1. 更新正确的 job 或子 job，而不是只抛出线程；
2. 写入用户可理解的 `error`；
3. 删除失败生成的临时文件/工作目录，或明确保留可恢复输入；
4. 不覆盖已经成功的原视频和历史成片。

参考实现：`process_job`、`process_cut_job`、`process_preview_composition_job`、`mark_job_cancelled`。

## 外部服务错误

- 服务商响应必须先检查 HTTP 状态和结构，再读取业务字段。
- 面向用户的错误不得暴露 API Key、请求头、内部 URL 查询参数或完整服务商响应。
- 已有专用映射应复用，例如 `seedance_user_facing_error` 和版权限制重试逻辑。
- 缺少凭证是明确的配置错误，不得伪装成空结果或静默回退为成功。

## 恢复失败、中断与 404

- 保留期内且 `project-state.json`/source 合法的任务应在启动时恢复；运行态投影为可解释的 `interrupted`，不返回重启 404，不自动续跑。
- 快照 JSON/schema/shape/source fingerprint 损坏时，已知 job id 的 GET/retry 返回可诊断 `409`，保留原快照不覆盖。
- `404` 只表示真正不存在、已过保留期、已明确清理或源文件已缺失。前端不得把 `interrupted`/`409` 误当成必须重新上传。
- 后台终态写回必须带 current `attemptId`；迟到回调、已取消尝试和非运行终态的后续输出提升均为 no-op。

## 禁止事项

- 禁止 `except Exception: pass`。定时维护循环允许继续运行，但也应保留可诊断信息。
- 禁止返回成功状态码并在 payload 中隐藏失败。
- 禁止把 Python 异常文本原样返回给浏览器，除非已确认不含敏感信息且它就是既有用户消息。
- 禁止失败后留下可被当作完整成片读取的半文件；输出使用临时文件并在成功后替换。

验证参考：`tests/test_app.py` 中缺少任务、凭证缺失、生成失败清理、Seedance 用户错误和取消相关测试。
