# 任务重启恢复与失败重试技术设计

## 1. Architecture Boundary

保持 FastAPI 单体、现有 API 和 `data/jobs` 工作目录，不引入数据库或外部队列。新增纯标准库仓库模块作为内存 job 与磁盘快照之间的唯一边界：

```text
route / background worker
  -> JOBS + JOB_FILES (live authority, JOBS_LOCK)
  -> durable transition snapshot (outside JOBS_LOCK)
  -> server/project_repository.py
  -> data/jobs/<job_id>/project-state.json (atomic replace)

app startup
  -> ProjectRepository.discover/restore
  -> running states => interrupted
  -> rebuild JOBS/JOB_FILES
  -> storage maintenance
  -> accept requests
```

`server/project_repository.py` 不导入 FastAPI 或 `server.app`。`server.app` 通过 `_project_repository()` 以当前 `DATA_DIR`、共享 repository lock 和时间函数构造适配器，保持测试 monkeypatch 和运行时目录覆盖有效。

## 2. Snapshot Contract

快照文件：`data/jobs/<uuid>/project-state.json`，schema v1：

```json
{
  "schemaVersion": 1,
  "jobId": "uuid",
  "source": {
    "filename": "source.mp4",
    "size": 123,
    "mtimeNs": 456
  },
  "job": {
    "id": "uuid",
    "status": "completed",
    "attemptId": "attempt-uuid",
    "result": {},
    "edit": null,
    "art": null,
    "pictureInPicture": null,
    "composition": null
  },
  "cutDraft": {"present": true, "revision": 7},
  "updatedAt": "ISO-8601"
}
```

Contracts:

- `source.filename` 只能是同一 job 目录下一层的 basename，并须匹配允许的视频扩展；restore 解析后确认父目录、size/mtime 和文件存在，禁止绝对路径、`..`、symlink 逃逸或第二目录引用。
- `job` 保存 JSON domain state，但省略 `cutDraft` 的完整内容、瞬时内部对象、密钥、`Path`、PCM/对齐缓存和运行进程。恢复后 `job["cutDraft"] = load_cut_draft(job_id)`。
- snapshot 写入使用唯一同目录临时文件并在 repository lock 内 `replace`；读取损坏时返回结构化 recovery failure，不覆盖原文件。
- `project-state.json` 是 job/result/subjob 的持久副本，内存仍是进程运行期唯一 live authority。cut draft 与 history 的既有文件继续各自拥有领域权威。
- 初始 queued、用户语义修改、attempt 创建、status 变化、request/result/error/history 引用和终态是 durable transition。只有 stage/progress 改变时不强制写盘。

## 3. Lock And Performance Model

更新 helper 分两段：

```text
with JOBS_LOCK:
  validate current attempt
  mutate live job
  if durable transition: deepcopy serializable snapshot

# JOBS_LOCK released
repository.save(snapshot)
```

- JSON 编码、临时文件写入、fsync/replace 和目录删除不得发生在 `JOBS_LOCK` 内。
- repository 使用独立锁协调同一 job 的 save/remove；不让 snapshot writer 在目录删除后重新创建幽灵工程。
- 不按每次 progress 写完整 transcript。后台 progress 可以在内存丢失；重启后本来就转 interrupted，不需要精确恢复百分比。
- 初始化 queued 在返回 202 前同步落盘；terminal transition 在 worker 返回前落盘。低频同步写保证 crash window，不引入常驻队列、shutdown backlog 或大量小写。
- startup 只遍历 `data/jobs` 的直接 UUID 子目录并读取小 manifest；不递归统计媒体、不 ffprobe、不加载模型。legacy source 只记录为可重试，真正 probe/ASR 在用户点击重试后发生。

## 4. Restore State Machine

### Top-Level Job

| Persisted status | Restored status | Behavior |
| --- | --- | --- |
| `queued/extracting/transcribing/processing` | `interrupted` | 保留 previousStatus/stage，error 写明确中断原因，不自动调度 |
| `completed` | `completed` | 恢复 result、source、draft 和子状态，允许继续编辑 |
| `failed/cancelled/interrupted` | 原状态 | 保持可解释终态；有 source 时可重试 |

### Subjobs

`edit/art/artSuggestion/pictureInPicture/composition` 以及动态 PIP asset 的 `queued/processing` 全部转 `interrupted`。顶层 completed 不被降级；对应工具只显示该子任务中断并允许再次创建。

恢复时设置：

- `previousStatus`、`interruptedAt`、`retryable`；
- `cancelRequested = false`；
- 原 attempt 只用于诊断，新 retry 创建新 attempt；
- output URL 只有在其文件/history 引用仍可验证时保留，否则清空并解释。

恢复完成后立即把 interrupted 投影重新写入 snapshot，使第二次重启保持稳定终态而不是再次误判为运行中。

## 5. Legacy Directory Recovery

对缺少 `project-state.json` 的 UUID 目录：

1. 只寻找一份合法 `source.<allowed-ext>`；无 source 或多 source 时记录 failure，不猜测。
2. 构造最小 `status=interrupted`、`recoveryKind=legacy_source_only` job，原始 filename 回退为 source basename，result 为 null。
3. 不把旧 `cut-draft.json` 投影到未完成转写的 UI；重试转写成功后，再由现有 draft 校验/恢复路径决定是否可应用。
4. 不在 startup 运行 ffprobe/ASR；点击 retry 后重新 probe 并从安全起点处理。

该路径只能恢复“原媒体仍存在”的旧任务，不能复原升级前未持久化且已丢失的 transcript/result。

## 6. Attempt Identity And Output Promotion

每个后台入口在 route lock 内生成新的 `attemptId` 并写进目标 job/subjob/asset；worker 显式接收此 id：

```python
update_edit_job(
    job_id,
    expected_attempt_id=attempt_id,
    status="completed",
    ...,
) -> bool
```

- helper 在 id 不匹配时返回 `False`，不更新状态、不持久快照。
- retry route 仍在 `JOBS_LOCK` 内检查当前状态，两个标签页竞争时只有一个能从 failed/interrupted 进入 queued，另一个返回 409。
- 生成输出先写 attempt-specific 临时路径；只有 current attempt 仍匹配时才原子提升为稳定文件或保存 history。失配/取消/失败清理本 attempt 临时文件，不能删除稳定 source、cut draft、其他 attempt 或 history。
- `RUNNING_PROCESSES` 的取消语义保持；attempt guard 是取消后的迟到回调和外部请求的第二道保护，不替代进程终止。

## 7. Retry Flows

### Top-Level Transcription

新增 `POST /api/transcriptions/{job_id}/retry`：

- 只接受 top-level `failed` 或 `interrupted` 且合法 source 存在；completed 返回 409，queued/running 返回 409。
- 删除本 attempt 可重建的 audio/半成品/sidecar，保留 source、cut draft 和用户资产。
- 重新 probe source，创建新 top-level attempt，状态设 queued 并 durable save，再调度 `process_job(job_id, attempt_id)`。

### Editing And Composition

- cut/art/pip/compose 继续使用现有 POST 创建入口；它们本来只拒绝 queued/processing。新实现为每次请求创建 attempt 并在返回 202 前保存 queued snapshot。
- failed/interrupted 后目录和 source 仍在，现有生成按钮即可重试；前端只需解除 lock、展示错误和使按钮可用。
- 统一 compose 成功保存 history 后保留工程输入与 snapshot；可删除已复制到 history 的 attempt 临时输出，但不删除 job 根目录。

## 8. Frontend Contract

- `pollJob()` 将 interrupted 加入终态集合，不无限轮询。
- `renderJob()` 新增 interrupted 分支，显示“处理已中断，可重试”；`#retryButton` 在 recoverable job 时变为“重试处理”并调用 retry API，另保留“重新选择视频”动作。
- `renderEdit()`、Art/Pip 状态渲染和 EditorSuite composition 对 interrupted 使用失败态样式，但不永久禁用控件。
- 创建 retry 后重新进入既有 queued/processing poll；重复点击时按钮 disabled/aria-busy。
- 404 仍用于真正不存在、已清理或不可恢复的 job；`handleExpiredTask()` 不再把可恢复 restart 错误误判为必须重新上传。
- 更新所有变更静态资源 cache-buster。

## 9. Cleanup, Compatibility And Rollback

- startup：restore -> persist interrupted transitions -> cleanup。cleanup 继续保护实际 running job；interrupted 受既有 7 天/80 个上限管理。
- `remove_job_working_directory()` 只供明确 cleanup/manual deletion 使用；background failure/success 改用 attempt output cleanup。
- `/api/transcriptions`、job GET、cut draft、生成和 history 响应形状保持兼容；新增字段为可选公开 metadata，新 endpoint 只扩展 OpenAPI。
- rollback 时旧版本忽略 `project-state.json`；文件不含新版本无法读取的媒体格式。若回滚成功/失败保留策略，现有 retention 仍会回收目录。
- 不新增环境变量；README 更新恢复、重试和 retention 行为。Mac 包仍创建干净 data，不打包本机 snapshot。

## 10. Risks

- 大 transcript snapshot 的低频 JSON 写可能增加 route/terminal latency；通过只在 durable transition 写、锁外 I/O 和性能测试限制。
- legacy source-only 重新转写可能产生与旧草稿不完全相同的时间轴；因此不自动应用旧 draft。
- 多阶段 compose 若仍共享固定输出名，attempt guard 只能保护状态，不能保护文件；实施必须使用 attempt-specific 临时输出或等价原子 promotion。
- 保留 job 根目录会增加临时磁盘占用；由已有 retention/max-count 管理，history 上限不变。
