# 修复任务重启恢复与失败重试

## Goal

让尚在保留期内的视频工程在服务重启后仍能从原地址继续访问；把重启时尚未结束的后台工作明确恢复为“已中断，可重试”，并让转写、剪辑和统一合成的临时失败不再删除原视频、转写结果、剪辑草稿、分割点或工具素材。整个修复不得让文字剪辑、播放、拖动、分割等前端热路径等待任务快照写盘。

## Background

- `server/app.py:347-349` 的 `JOBS`、`JOB_FILES` 和 `JOBS_LOCK` 是当前任务权威；`app_lifespan()` 只在启动时清理存储，没有从磁盘恢复任务。
- `GET /api/transcriptions/{job_id}`、cut draft、原视频和生成路由都先要求内存 job 存在，因此磁盘上仍有 `source.*`、`cut-draft.json` 时也会在重启后返回“任务不存在或服务已重启”。真实浏览器用例 `tests/app/browser/test_editor_workflows.py:4354` 当前以 xfail 固化此缺口。
- `process_job()` 的异常路径和 `process_preview_composition_job()` 的成功/异常路径会调用 `remove_job_working_directory()`；统一合成临时失败后源视频与草稿一并消失，同一任务不能直接重试。
- `data/jobs` 已有按天数和数量清理的明确契约。恢复能力必须继续服从保留策略，不能把临时工程变成无限期永久存储。
- 用户已接受推荐行为：重启后不自动继续 FFmpeg 或外部模型请求，而是将运行中状态转成 `interrupted`，由用户明确重试，避免重复计费和启动时资源争抢。

## Requirements

- R1：为 `data/jobs/<job_id>/` 增加版本化、原子写入的任务快照，至少保留公开 job 状态、源媒体相对引用、时长、转写结果、各子任务状态/最近请求、历史引用和必要的恢复元数据；不得把绝对路径、密钥、二进制媒体或 PCM 缓存写入快照。
- R2：`cut-draft.json` 继续单独拥有文字/空白/时间轴范围、`splitPoints`、exact identity 和 revision；任务快照只记录其存在性/已知 revision，恢复时从既有草稿文件读取，禁止复制第二份可漂移的 cut-draft 权威。
- R3：任务创建、用户语义更新、后台状态转换和终态必须落盘；纯 `stage/progress` 高频变化可以合并或跳过。JSON 序列化和文件 I/O 必须发生在 `JOBS_LOCK` 外，文字点击、播放帧、时间轴拖动和分割命令不得同步等待任务快照。
- R4：启动顺序必须先恢复仍在保留期内的任务，再运行存储维护。恢复只接受 UUID 目录、版本/shape 合法的快照和位于该 job 目录内的源媒体相对路径；损坏快照不得覆盖、删除或伪造为空任务。
- R5：顶层或子任务的 `queued`、`extracting`、`transcribing`、`processing` 在重启恢复时统一变为 `interrupted`，保留原 stage/error 作为诊断并给出“任务已中断，可重试”的公开状态；`completed`、`failed`、`cancelled` 保持其终态。不在启动时自动调用 FFmpeg、ASR 或外部生成模型。
- R6：缺少新版快照但仍有合法 `source.*` 的历史 job 目录可恢复为“需要重新分析”的最小 interrupted 任务，允许用户从原视频重试转写；不得把缺少转写结果的 legacy 目录伪装成 completed，也不得自动套用可能不再匹配的旧剪辑草稿。
- R7：为顶层转写失败/中断提供同 job 重试入口，从源视频重新执行处理；开始重试前清理本次可重建的中间/半成品，保留源视频。completed 顶层任务的剪辑、艺术字、画中画和统一合成继续复用各自现有创建入口重试。
- R8：转写失败、统一合成成功或失败后不再立即删除整个 job 目录；只删除不完整的临时输出。源媒体、转写结果、cut draft、工具素材和任务快照由现有保留天数/数量上限、用户主动清理或明确到期统一回收。
- R9：每次后台尝试都有稳定 `attemptId`。后台更新、取消和终态写回必须验证仍属于当前 attempt；旧线程、迟到模型响应或取消后的 FFmpeg 结果不得覆盖新的重试状态或删除新输出。
- R10：前端必须把 `interrupted` 当作可解释终态：停止轮询，解除操作锁，显示原错误/中断原因和明确重试动作。转写重试按钮不得继续只执行“重新选择视频”；子任务失败/中断后现有生成按钮必须重新可用。
- R11：恢复后的 completed 工程继续从同一 URL 加载同一文案、cut draft、分割点、艺术字/画中画恢复草稿和公共 Store；精确分割范围仍按已确认的 `cutDraftRevision` 进入生成，不重新执行声学边界解析。
- R12：快照读取失败、写入失败、源文件缺失、revision 过期、重复重试和 attempt 冲突必须返回可诊断错误；不得返回伪成功、无限轮询、部分覆盖快照或删除历史成片。
- R13：现有清理 API、dry-run、UUID 安全目标验证、历史版本上限和 `DATA_DIR` 覆盖保持兼容。被恢复为 interrupted 的任务不视为运行中任务，但在到期前可访问和重试。

## Acceptance Criteria

- [ ] AC1：新建并完成转写的任务在清空进程内 `JOBS/JOB_FILES`、重启测试服务后，从原 URL 恢复 completed 状态、原视频、文案、cut draft revision 和 split points，不再进入已知 404 xfail。
- [ ] AC2：分别在顶层转写、剪辑和统一合成处于 queued/processing 时模拟重启，恢复后对应状态为 interrupted，轮询停止、页面无永久 busy/inert，且没有自动启动 FFmpeg 或模型调用。
- [ ] AC3：顶层 interrupted/failed 任务点击“重试处理”后只创建一个新 attempt；首次模拟失败、第二次成功时 job id 和源文件 identity 不变，旧 attempt 的迟到更新为 no-op。
- [ ] AC4：统一合成模拟 FFmpeg 失败后 job 目录、source、cut draft、分割点及工具素材仍存在；再次提交同一最新 revision 后生成完成并保存历史版本。
- [ ] AC5：统一合成成功后当前工程在保留期内仍可刷新和跨服务重启继续编辑；历史成片不依赖 job 目录且保持可下载。
- [ ] AC6：快照采用同目录临时文件加 `replace`；并发状态转换不会生成半 JSON。损坏快照被隔离并给出诊断，原文件不被空内容覆盖。
- [ ] AC7：legacy UUID 目录仅含合法 source 时恢复为可重试 interrupted；缺 source、路径越界或伪 UUID 目录被拒绝且不进入 `JOBS/JOB_FILES`。
- [ ] AC8：任务状态热循环至少 100 次纯 progress 更新时，不进行 100 次完整快照写入；持有 `JOBS_LOCK` 时不执行 JSON 写盘，正常编辑浏览器性能门禁和媒体 identity 计数不回退。
- [ ] AC9：取消后立即重试、重试后旧响应迟到、重复点击重试和两个标签页同时重试均最多保留一个 current attempt，并返回明确 409 或 no-op。
- [ ] AC10：现有任务清理、history、cut draft、时间轴精确分割、普通声学范围、统一 compose、浏览器 375px 和完整 pytest 回归通过；`data/jobs`、`data/history`、用户媒体和密钥不进入测试或提交。

## Out of Scope

- 不引入数据库、Redis、分布式队列、微服务或跨机器任务恢复。
- 不从 FFmpeg 中间帧、ASR token 或外部模型 provider task 的内部进度自动续跑；用户重试从对应任务的安全起点重新执行。
- 不把完整 `EditorProjectStore` 改造成跨浏览器/多人协作的服务端项目文档；本期复用现有浏览器 editor draft 与服务端 job/cut draft 权威。
- 不保证已超过保留期限、已被手动清理、源媒体缺失或升级前已删除工作目录的任务可恢复。
- 不改变 `split_exact`、普通声学边界、媒体编码参数、历史容量策略或现有技术栈。
