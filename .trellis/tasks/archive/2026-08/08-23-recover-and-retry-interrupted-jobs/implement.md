# 任务重启恢复与失败重试实施计划

## Phase 0: Baseline And Failure Contracts

- [x] 固定当前 OpenAPI、maintenance/history、cut draft、composition failure 和浏览器 restart xfail 基线。
- [x] 先增加失败测试：snapshot 原子写/损坏/路径越界、restore 状态矩阵、legacy source-only、JOBS_LOCK 外 I/O、纯 progress 写入计数和 attempt stale no-op。
- [x] 记录正常编辑性能与 `src/load()/iframe/extractor` identity 基线，证明本任务不触碰媒体热路径。

Rollback point：只增加测试和研究证据，不改变运行时。

## Phase 1: Project Repository

- [x] 新增 `server/project_repository.py`，实现 schema v1 snapshot、UUID/source 相对路径验证、原子 save/load/discover 和 repository 协调锁；模块不得导入 FastAPI/`server.app`。
- [x] 在 `server.app` 保留薄适配器 `_project_repository()`，每次读取当前 `DATA_DIR`；重导出必要 class/lock identity 供兼容测试。
- [x] 定义 snapshot sanitization：保存 job/result/substates，剥离 cutDraft 全文、绝对路径、内部进程和不可序列化对象；记录 cut draft revision/ref。
- [x] 覆盖同 job 并发 save、失败 replace、损坏 JSON、未知 schema、source fingerprint/path escape 和不同 `DATA_DIR`。

Rollback point：仓库尚未接入 lifespan/worker，可整体撤回新模块。

## Phase 2: Durable Transitions And Startup Restore

- [x] 重构 `update_job` 及所有子 update helper，增加可选 expected attempt guard、bool accepted 返回和 durable transition 分类；内存 mutation 在 `JOBS_LOCK` 内，snapshot deepcopy/write 在锁外。
- [x] 补齐路由内直接 mutation 的 snapshot 调用：上传、文字/分段更新、cut draft metadata、cut/art/pip/compose queued、取消、history 引用和素材状态。
- [x] 实现 startup discover/restore，严格按 restore -> interrupted persist -> storage maintenance 顺序；完成/失败/取消保持，所有 running 状态转 interrupted。
- [x] 实现 legacy source-only 最小恢复，不启动 ffprobe/model；记录 recovery failures 供日志/测试诊断。
- [x] 更新 cleanup 与 repository remove 协调，防止 snapshot 迟到重建已删除目录。

Rollback point：保留快照写入但关闭 startup restore 时，旧运行行为可恢复且快照无副作用。

## Phase 3: Attempts And Retry

- [x] 为顶层转写、cut、art、art suggestion、PIP 图片/视频、PIP 合成和统一 compose 分配 attemptId，并贯穿 worker update/cancel/terminal。
- [x] 使用 attempt-specific 临时输出和 current-attempt promotion；迟到 callback 只清理自身临时文件。
- [x] 新增 top-level retry API，校验 failed/interrupted/source/current attempt，清理可重建中间文件、重新 probe 并在 durable queued 后调度处理。
- [x] 移除 `process_job` failure 和 `process_preview_composition_job` success/failure 的整 job 目录删除；保留工程输入，依赖 retention 回收。
- [x] 证明两个并发 retry 只有一个 202，另一个 409；cancel 后 retry + 旧回调不覆盖新状态或文件。

Rollback point：attempt 字段为向后兼容可选；若重试入口失败，可先隐藏 UI/禁用 endpoint，不删除已保存工程。

## Phase 4: Frontend Recovery UX

- [x] `renderJob/pollJob` 支持 interrupted 终态、错误信息和停止轮询。
- [x] `#retryButton` 在可恢复任务时执行同 job retry，busy 期间不可重复；提供独立重新选择视频入口。
- [x] `renderEdit`、EditorSuite composition、Art/Pip/asset 状态将 interrupted 映射为可重试且解除 inert/operation lock。
- [x] 404 仅对真正缺失/过期 job 走 expired flow；恢复成功不弹“需要重新上传”。
- [x] 更新 HTML/CSS/JS 与所有引用 cache-buster，完成桌面/375px、键盘焦点和中文 live status。

Rollback point：前端可先回退 retry 控件但继续识别 interrupted，防止无限 poll。

## Phase 5: Integration And Validation

- [x] 单元/API：repository、schema、restore matrix、retry/attempt、cleanup/history、cut draft split exact 和 compose authoritative revision。
- [x] 真实失败：首次 transcription/FFmpeg compose 失败保留目录，第二 attempt 成功；半成品不可读取。
- [x] 真实浏览器：completed reload/restart、running restart -> interrupted、one-click retry、cut split points、Art/Pip Store draft、统一 compose、375px 和 media identity。
- [x] 将 restart 浏览器 xfail 改为正常通过；不得新增函数级 xfail 或依赖真实外部模型。
- [x] 性能：100 次 progress 更新的 snapshot 写次数受限，写盘 spy 断言 `JOBS_LOCK` 未持有；已有剪辑交互性能门禁不回退。
- [x] 更新 README 与任务验证证据。
- [x] 由主会话通过 Trellis quality check 复核并按需更新 backend/frontend/testing spec。

## Validation Commands

```powershell
node --check web/app.js
node --check web/editor-suite.js
.\.venv\Scripts\python.exe -m pytest tests/app/test_project_repository.py tests/app/test_maintenance_history.py -q
.\.venv\Scripts\python.exe -m pytest tests/app/test_cut_draft.py tests/app/test_cut_rendering.py tests/app/test_composition.py -q
.\.venv\Scripts\python.exe -m pytest tests/app/test_frontend_contracts.py tests/app/browser/test_editor_workflows.py -k "restart or interrupted or retry or timeline_split or composition" -q
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

## Implementation Evidence (2026-08-23)

- `python -m py_compile server/app.py server/project_repository.py`：通过。
- `node --check web/app.js web/editor-suite.js web/editor-pip-tool.js`：通过。
- repository/cut-draft/maintenance/PIP/Art 扩展定向回归：88 passed。
- composition/frontend contract/cut rendering/transcription suggestions：59 passed。
- template handoff 真实浏览器回归：2 passed。
- restart/interrupted 真实浏览器回归：2 passed。
- 全量 `pytest -q`：391 passed，1 个已有 Starlette deprecation warning。
- `git diff --check`：通过（仅 Git 的 LF/CRLF 转换提示）。

## Risky Files And Review Gates

- `server/app.py`：JOBS mutation、lifespan、所有后台 worker、cleanup、retry route；每阶段限制范围并要求独立测试。
- `server/project_repository.py`：路径、锁和原子 I/O；必须独立导入测试并验证动态 `DATA_DIR`。
- `web/app.js` / `web/editor-suite.js`：终态轮询和锁恢复；浏览器验证不能只靠静态字符串。
- `tests/app/browser/conftest.py`：restart fixture 必须模拟真实进程内状态清空但保留临时磁盘，不能读取用户 `data/jobs`。
- 任何实现若需要自动续跑外部 provider、数据库或完整 ProjectDocument 服务端迁移，必须回到规划阶段，不在本任务扩 scope。
