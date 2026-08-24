# 当前任务恢复与失败链路研究

## 1. 当前权威和启动顺序

- `server/app.py:347-349`：`JOBS`、`JOB_FILES`、`JOBS_LOCK` 只存在于进程内。
- `server/app.py:380`：`app_lifespan()` 启动时先执行 `run_storage_maintenance()`，随后只启动周期清理，没有恢复步骤。
- `server/app.py:12097` 附近：上传完成后才把 job/source path 写入两个内存字典，磁盘没有完整 job manifest。
- `server/app.py:12127` 附近：读取 job、原视频和 cut draft 前都要求内存 job 存在；磁盘文件无法独立让 URL 恢复。

结论：恢复必须发生在首次 storage cleanup 之前，否则旧目录可能先按 overflow/age 被删除；快照必须足以重建 public job 和安全的相对 source 引用。

## 2. 已持久化和未持久化数据

已有：

- `source.<ext>`、中间音频和生成文件；
- `cut-draft.json`，包含 revision、文字/空白/时间轴删除、split points 和 exact identity；
- `acoustic-alignment.json` 可重建 sidecar；
- `data/history` 的最终成片、transcript 和 manifest；
- 浏览器 editor draft/localStorage 中的未生成 Art/PiP Store 状态。

缺失：

- 顶层 job 状态、原始文件名、转写 result、editable segments；
- 当前 edit/art/pip/composition 子状态和最后一次请求；
- 运行 attempt identity、失败是否可重试和重启语义。

结论：任务快照不能复制 cut draft，但必须保存 job/result/substates；恢复后 `job["cutDraft"]` 从独立文件读取。未生成 Art/PiP 继续由现有浏览器草稿恢复，不在本任务复制第二套 Store。

## 3. 失败与目录删除

- `process_job()` 顶层异常会写 `failed` 后调用 `remove_job_working_directory()`，源视频随即丢失。
- `process_cut_job()` 失败只写 edit failed，目录保留，天然可用既有 `/cuts` 入口重试。
- `process_preview_composition_job()` 成功保存 history 后删除 job 目录；异常写各子状态 failed 后也删除目录。失败重试和成功后继续编辑都依赖仍在内存的 job，跨重启不可恢复。
- `tests/app/test_maintenance_history.py:163` 和 `tests/app/test_composition.py:405` 当前把立即删除固化为旧契约，实施时必须改成“保留可恢复输入、仅清理半成品”。

## 4. 前端状态

- `pollJob()` 只把 completed/failed 当终态；新增 interrupted 后必须停止轮询。
- 顶层 `#retryButton` 当前文案为“重新选择视频”，click 只调用 `resetToUpload()`；需要在 recoverable job 上改为同 job 重试，同时保留真正重新选择视频的入口。
- `renderEdit()` 没有 interrupted 分支；必须与 failed 类似地解除 inert/锁并允许重新生成。
- EditorSuite 的 `compositionReady()` 只阻止 queued/processing；failed/interrupted 理论上可以重新提交，但失败目录被删除是当前硬阻塞。`syncGenerationButton()` 已能显示 composition.error。

## 5. 性能和锁风险

`update_job()` 及子 helper 会高频写 stage/progress。如果每次都在 `JOBS_LOCK` 内深拷贝和写完整 JSON，将阻塞 GET poll 和创建请求。最小安全策略：

1. 只有初始 queued、status/attempt/结果/请求/错误/用户语义变化和终态需要 durable snapshot；纯 progress/stage 不要求逐条持久。
2. 在锁内完成内存 mutation 并只在需要时复制序列化 snapshot；释放全局锁后通过 per-job repository lock 原子写入。
3. source 使用相对文件名；媒体不复制，cut draft 不复制，PCM/forced cache 不落盘。
4. 删除/cleanup 与 snapshot replace 使用同一 repository/per-job 协调，避免目录删除后迟到写入重新创建“幽灵 job”。

## 6. Attempt 和重试

- 当前并发门禁主要依赖 status queued/processing；后台 update helper 不验证发起它的运行代次。
- retry/cancel 后旧外部响应或线程若迟到，可能覆盖新任务。
- 每次顶层或子任务开始时创建 `attemptId`，worker 显式携带；更新 helper 仅在 current attempt 匹配时提交。路由重复启动返回 409，旧回调 no-op。
- 重启恢复不续跑：所有运行态转 interrupted，并清除 cancelRequested；用户重试生成新 attempt。

## 7. Legacy 和清理

- 新快照可完整恢复；旧 UUID 目录可能只有 source/cut draft，无法证明其转写 result。
- 若合法 source 存在，可建立最小 interrupted job 并允许重新转写，但不能把旧 cut draft 自动应用到尚未重新生成且可能时间结构不同的 transcript。
- 无 source、路径越界、损坏 snapshot 或伪 UUID 不进入运行时权威。
- interrupted 不是运行中；继续受 7 天/80 个目录的默认保留策略。恢复必须先于 cleanup，让维护逻辑能基于真实状态和同一安全路径工作。

## 8. 现有验证基线

- 最近全量：`370 passed, 1 xfailed`；唯一 xfail 是服务重启恢复。
- 本轮故障审计：`40 passed, 1 xfailed`。
- 时间轴分割真实浏览器用例连续三次通过。
- 8001 健康检查显示 FFmpeg/FFprobe 和模型配置可用。
