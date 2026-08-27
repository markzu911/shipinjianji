# 持久化与任务状态

## 当前存储模型

项目没有数据库：

- `JOBS` 和 `JOB_FILES` 是进程内 live authority，受 `JOBS_LOCK` 保护；`project-state.json` 是用于重启恢复的持久副本。
- `data/jobs/<uuid>/` 保存上传源文件、版本化任务快照、处理中间文件、独立权威的 `cut-draft.json` 和可重建的 `acoustic-alignment.json`。
- `data/history/` 保存最终版本、缩略图和 history manifest，跨重启存在。
- `data/fonts/`、`data/art-templates/`、`data/art-position-presets/` 各自使用 manifest JSON。
- `.env` 保存模型服务商配置和凭证，由 settings API 在锁内更新。

不要把 `data/jobs` 当作永久项目数据库，也不要把 `data/history` 当作可编辑工程状态。

## JSON 写入

- UTF-8，用户文本使用 `ensure_ascii=False`。
- 复合内容使用稳定、可读的 JSON；已有 manifest 保持列表/对象形状。
- 草稿和媒体输出采用同目录临时文件后 `replace`，避免读到半写入文件。
- 写 manifest 前获取领域锁；读改写必须在同一个临界区内完成。
- 声学 sidecar 同样使用同目录临时文件后 `replace`，并在进程内按 sidecar 路径串行执行“读取、缺失句段推理、写回”；锁对象必须可回收，不能随已清理 job 永久增长。
- 读取损坏或缺失的可选草稿可返回 `None`；持久库损坏应产生可诊断错误，不能悄悄覆盖为空库。

`acoustic-alignment.json` 只缓存固定 aligner/schema/model revision 与当前源媒体指纹匹配的完整句段字符证据。读取时必须重新验证字符数量、顺序、finite 单调时间、句段包络和非坍缩结构，不能仅信任磁盘中的 `validation.valid=true`。旧任务按本次草稿影响的句段惰性补齐，新转写可全量预计算；文本或源媒体 fingerprint 变化只使对应记录自然失效，不批量改写历史任务。

参考：`save_cut_draft`、`save_history_versions_unlocked`、`save_uploaded_art_templates_unlocked`、`persist_model_provider_settings`。

## 场景：剪辑草稿 PCM 指纹缓存

### 1. Scope / Trigger

修改 cut-draft 声学校准的媒体解码入口、PCM 样本消费者、缓存预算或并发策略时适用。缓存只减少同一源媒体的重复完整解码，不能缓存 range alignment 或改变声学边界算法。

### 2. Signatures

```python
FingerprintPcmCache.get_or_decode(
    media_path: Path,
    decoder: Callable[[Path], array],
    *,
    max_bytes: int,
) -> array | ReadOnlyPcmSamples

decode_cut_draft_audio_samples(media_path: Path) \
    -> array | ReadOnlyPcmSamples
```

- 环境变量：`CUT_DRAFT_PCM_CACHE_MAX_BYTES`，默认 `268435456`（256 MiB），`0` 表示禁用。
- fingerprint：解析后的绝对路径、文件大小、`mtime_ns`。

### 3. Contracts

- value 成本严格按 `len(samples) * samples.itemsize` 计费；总预算按 LRU 淘汰，单项超过预算时只返回给当前请求，不写入缓存。
- 缓存样本通过 `ReadOnlyPcmSamples` 暴露；消费者只能索引、切片或迭代，不得取得共享可变 `array` 后原地修改。
- metadata lock 只保护 fingerprint/LRU/in-flight 状态；FFmpeg decoder 必须在锁外执行。同 fingerprint 的并发 miss 共用一个 in-flight 结果，其他线程等待同一个 event。
- decode 失败不缓存失败值，必须唤醒全部 waiter；后续请求可重新 decode，并继续走既有 cut-draft 安全 fallback。
- 媒体 size 或 `mtime_ns` 改变时形成新 key，并移除同路径旧条目；淘汰和 clear 只释放内存引用，不删除媒体、sidecar 或草稿。
- 每次 cut-draft PUT 仍对最新 text/timeline ranges 执行完整边界解析。不得缓存 forced boundary、transition trust、diagnostics 或 revision。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| 预算为 `0` | 清空 LRU，当前调用直接 decoder，不复用 in-flight/cache |
| 连续相同 fingerprint | 只 decode 一次并更新 LRU 最近使用顺序 |
| 并发相同 fingerprint miss | 只有 owner decode；waiter 得到同一只读结果 |
| size/mtime 改变 | cache miss，旧路径指纹条目失效 |
| 单项大于总预算 | 返回解码结果但 entry count 不增加 |
| decoder 抛错 | 所有 waiter 收到失败，in-flight 清理，下一次允许重试 |
| 缓存命中但 ranges 改变 | 复用 PCM，仍重新计算全部物理边界和 diagnostics |

### 5. Good / Base / Bad Cases

- Good：同一媒体的两个并发 cut-draft PUT 只启动一次 FFmpeg decode，但分别按各自最新 ranges 产生完整 diagnostics/revision。
- Base：首次请求 miss 并缓存，下一次请求命中；禁用缓存后 payload 与命中路径完全一致。
- Bad：按路径字符串单独建 key，或缓存 alignment 结果；前者会在原文件被替换后复用旧音频，后者会忽略相邻删除状态和重复转场 trust 变化。

### 6. Tests Required

- 单元测试覆盖连续命中、并发去重、size/mtime 失效、实际字节 LRU、超大单项、预算 `0`、失败唤醒和失败后重试。
- API/领域等价测试对比缓存启用/禁用的 text/timeline 物理范围、`original*`、diagnostics 和 revision。
- 声学矩阵固定覆盖完整跨段转场、“得/你”、“一起给”、delete-start/delete-end、下一段立即起音和 retained-side hard limit；同时断言被删尾音消失且保留起音不受损。
- 普通应用与浏览器测试必须替换真实 FunASR 入口，不下载模型或读取用户模型目录。

### 7. Wrong vs Correct

```python
# Wrong: every PUT decodes the full media, and a path-only key can go stale.
samples = decode_cut_audio_samples(media_path)
cache[str(media_path)] = samples

# Correct: fingerprinted, bounded and read-only decode reuse.
samples = CUT_DRAFT_PCM_CACHE.get_or_decode(
    media_path,
    decode_cut_audio_samples,
    max_bytes=CUT_DRAFT_PCM_CACHE_MAX_BYTES,
)
```

## 场景：剪辑草稿空白自动初始化迁移

### 1. Scope / Trigger

- 当空白自动删除能力晚于剪辑草稿上线时，历史 `cut-draft.json` 没有字段可区分“尚未应用默认空白”与“用户已恢复全部空白”。
- 迁移在用户打开并保存对应任务时惰性完成，不批量重写 `data/jobs`。

### 2. Signatures

- `PUT /api/transcriptions/{job_id}/cut-draft`
- `CutDraftRequest.automaticNoSpeechInitialized: bool = False`
- 成功响应与 `cut-draft.json` 都包含 `automaticNoSpeechInitialized: boolean`，`schemaVersion` 保持 `1`。

### 3. Contracts

- 请求省略字段时按 `false` 处理，保证旧客户端仍可保存草稿。
- `false` 或字段缺失表示前端仍可在空白分析完成后执行一次默认空白初始化；服务端只持久化标记，不自行推断或修改删除范围。
- `true` 表示默认空白已经处理，`noSpeechRanges: []` 也必须原样保存，不能按空数组重置标记。
- 前端迁移必须保留请求里的 `textRanges`、既有 `noSpeechRanges` 和 `timelineRanges`，只补入缺失的可删除空白。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| 字段省略 | 接受请求并保存为 `false` |
| 字段为 `true` 且 `noSpeechRanges: []` | 接受并保留“已初始化但全部恢复”状态 |
| `revision` 不是当前版本 | `409`，不覆盖已有草稿与标记 |
| 任一时间范围无效 | `400`，不写入部分草稿 |
| 转写任务未完成或时长无效 | `409`，不写草稿 |

### 5. Good / Base / Bad Cases

- Good：旧草稿恢复后补入可删除空白，以同一次 PUT 保存原范围、补入范围和 `automaticNoSpeechInitialized: true`。
- Base：新草稿第一次保存即携带明确布尔值；后续只随普通草稿保存原样往返。
- Bad：用 `noSpeechRanges.length === 0` 推断未初始化，这会在用户恢复全部空白后刷新重删。

### 6. Tests Required

- API 回归：显式 `true` 往返保存；旧请求省略字段时响应为 `false`；空 `noSpeechRanges` 与 `true` 同时保留。
- 前端/浏览器回归：历史草稿首次加载保留文字和时间轴范围、补入可删空白并写入标记；恢复全部空白后刷新仍为空。
- 非可删除的整段空白不得进入 `noSpeechRanges`。

### 7. Wrong vs Correct

```javascript
// Wrong: 空数组既可能是未迁移，也可能是用户已经全部恢复。
if (!draft.noSpeechRanges.length) seedAutomaticNoSpeechRanges();

// Correct: 只读取持久化的一次性标记。
if (draft) restorePersistedCutDraft(draft);
if (
  noSpeechStatus === "completed" &&
  draft?.automaticNoSpeechInitialized !== true
) {
  seedAutomaticNoSpeechRanges();
  automaticNoSpeechInitialized = true;
}
```

## Cut-draft 分割结构的增量兼容

- 播放头分割继续使用 `cut-draft.json` 的 `schemaVersion: 1` 增量字段：`splitPoints[]`、`timelineRanges[].boundaryMode` 和可选 `splitClipKey`。历史文件缺少这些字段时分别恢复为 `[]`、`speech_safe` 和无 identity，不为此批量迁移 job 目录。
- split points 与三类删除范围必须在同一个 revision 检查、同一个 per-job lock 和同一次临时文件 `replace` 中原子保存；读写 JSON 时不得持有 `JOBS_LOCK`。
- `cut-draft.json` 是草稿权威；PUT/DELETE 响应后再 best-effort 刷新 `project-state.json` 的 present/revision metadata，分割和文字选择热路径不同步等待第二次 JSON/fsync。重启发现 metadata 漂移时以草稿文件自愈，向公开 job 返回可诊断 warning，不误降级 completed。
- `splitPoints` 与 exact identity 是用户语义，服务端响应往返时必须保留；boundary diagnostics 和 acoustic cache 仍是派生数据，不能用来推断或重建分割结构。
- API 回归必须覆盖旧草稿读取、新字段往返、revision conflict 不覆盖结构、非法 exact 请求不写部分草稿，以及删除草稿时一并清除结构字段。

## 任务状态更新

- 通过 `update_job` 或对应的 `update_edit_job`、`update_art_job`、`update_picture_in_picture_job` 更新，不直接在无锁区域修改嵌套字典。
- job/子 job 进入后台前使用 `queued`，执行中使用既有 `processing`/`extracting`/`transcribing`，完成后只能进入明确终态。
- `public_job` 是对外投影边界；新增内部字段前确认是否应暴露给浏览器。
- 运行中工作由 `job_has_running_work` 判定，清理逻辑不得删除这些目录。

## 场景：文案修改使已完成艺术字失效

### 1. Scope / Trigger

已有全文艺术字后通过 `PUT /api/transcriptions/{job_id}/editable-segments` 修改文案时适用。旧 `art-text.mp4` 已过期，但 `art.overlays` 仍是可编辑工程状态；第一次文字保存后的快照必须允许紧接着的拆分和 cut-draft 删除继续持久化。

### 2. Signatures

```python
update_transcript_track_text_for_segment(
    art: dict[str, Any],
    segment_start: float,
    segment_end: float,
    new_text: str,
) -> None
```

失效后的子任务投影：`status="interrupted"`、`retryable=True`、`outputUrl=None`，并保留 `overlays`。

### 3. Contracts

- 文字只按现有重叠 cue 分配，cue 的 `start/end/sourceStart/sourceEnd` 不移动；全文重新分段由前端 Store reconciliation 负责。
- 若旧状态不是 `interrupted`，记录 `previousStatus/previousStage`；随后写入合法非运行态 `interrupted`、可重试 stage/error、`interruptedAt/updatedAt`。
- 不使用 `status: null`，因为 `ProjectRepository` schema v1 会拒绝该子任务；不使用 `queued`，因为本路由没有创建后台 worker。
- 只清空过期 `outputUrl`；不删除输出文件、overlay、样式或用户媒体，也不自动安排生成。

### 4. Validation & Error Matrix

| 条件 | 处理 |
| --- | --- |
| 没有 transcript overlays | no-op，不改变 art 状态 |
| art 正在 `queued/processing` | editable-segments 路由返回 `409`，不做部分修改 |
| completed art 文案更新 | 降为 `interrupted + retryable`，快照 shape 校验成功 |
| 已 interrupted art 再次更新 | 保持 interrupted，刷新文字与时间戳，不把 previousStatus 覆盖成 interrupted |
| 随后的 split/delete 保存 | 可继续原子覆盖同一 `project-state.json`，不得因子任务状态返回 `500` |

### 5. Good / Base / Bad Cases

- Good：completed 全文艺术字执行“改文字 -> 拆分 -> 删除”，每次 PUT 成功；最终快照可加载，overlay 仍在且输出 URL 为空。
- Base：没有艺术字的 job 修改/拆分文案，既有路径不变。
- Bad：把旧成片标记为 `None` 或 `queued`；前者使下一次快照校验失败，后者制造永远没有 worker 消费的运行态。

### 6. Tests Required

- API/repository 回归必须在真实 `data/jobs/<uuid>/source.mp4` 临时目录中连续执行 text PUT 和 split PUT，再通过 `ProjectRepository.load()` 校验 `interrupted/retryable/outputUrl/overlays/editableSegments`。
- 浏览器回归不得 monkeypatch `persist_job_snapshot`；必须走真实 text/split 快照保存，并继续点击删除直至 Store/preview/compose 守恒断言。

### 7. Wrong vs Correct

```python
# Wrong: invalid schema state; the next project snapshot fails.
art["status"] = None

# Correct: legal non-running retry state with editable overlays preserved.
art["status"] = "interrupted"
art["retryable"] = True
art["outputUrl"] = None
```

## 场景：工程快照、重启恢复与 attempt 隔离

- `server/project_repository.py` 是 `project-state.json` 的唯一存储边界；只依赖标准库和构造参数，不导入 FastAPI 或 `server.app`。
- schema v1 只保存公开 job 状态、source basename/fingerprint 和 cut-draft metadata。密钥、凭证、绝对路径、PCM、进程对象和草稿全文不得入快照。
- source 必须是同一 UUID job 目录的直接子文件；校验 basename、扩展名、size、`mtime_ns`、symlink/junction 逃逸和 resolved parent。PIP asset id 必须是安全单文件名片段。
- save 在 repository lock 内使用唯一同目录临时文件、flush/fsync 和 `replace`；损坏的旧快照只返回诊断，禁止用新空状态覆盖。
- 在 `JOBS_LOCK` 内只验证、mutation 和必要的 deepcopy；JSON 编码、fsync/replace、媒体 promotion 和目录删除都在锁外。纯 stage/progress 不逐次写全量快照。
- 启动顺序固定为 restore -> 运行态投影为 `interrupted` -> 回写投影 -> maintenance；不自动重跑 FFmpeg/ASR/外部模型。legacy source-only 只恢复可重试顶层任务，GET 也不得重新挂载旧 cut draft。
- 恢复 completed 投影时验证固定输出或 history 引用；文件缺失只把对应子任务降为 `interrupted`，不伪造可读成片。
- 每次顶层/子任务/动态 PIP 尝试都携带 `attemptId`。状态写回、输出 promotion、取消和重试必须验证 current attempt 且状态仍运行；终态旧 worker 在其他任务清除 job-wide cancel 后仍为 no-op。
- 清理建计划后，删除前在 per-job/repository 锁内复查目录 `mtime_ns` 和 live running 状态；已中断工程在保留期内可访问，到期后仍按现有上限回收。
- 必测：snapshot 原子/损坏/路径/shape、legacy、状态投影、缺输出、draft metadata 自愈、100 次 progress 无写盘风暴、cancel/retry 迟到回调、双标签重试与 cleanup 二次门禁。

## 清理和历史

- `cleanup_job_directories` 只接受 UUID 目录，保护运行中任务，并支持 dry-run。
- `HISTORY_MAX_STORED` 只管理最终历史，不受临时 job 保留期影响。
- 成功保存历史或任务失败后保留 job 源媒体、草稿、工具素材和快照；只清理本 attempt 半成品，工程目录由 retention/数量上限或明确用户清理回收。
- 新的持久化目录必须同步更新 README、`.env.example`、打包清洁数据规则和测试。

## 场景：历史版本仓库边界

### 1. Scope / Trigger

- `server/history_repository.py` 唯一拥有 `data/history` 的目录、manifest 过滤与原子写入、公开投影、缩略图、版本保存和容量裁剪实现。
- 修改历史版本的磁盘布局、清单、保留上限或 `server.app` 兼容入口时适用本契约；API 路由、job 复用和周期维护协调仍由 `server.app` 拥有。

### 2. Signatures

```python
HistoryRepository(
    *,
    data_dir: Path,
    max_stored: int,
    lock: ContextManager[Any],
    resolve_ffmpeg: Callable[[str], str],
    utc_now: Callable[[], str],
    local_now: Callable[[], datetime],
)

def _history_repository() -> HistoryRepository: ...
```

`server.app` 保留拆分前 14 个历史函数的名称和签名；适配器只把调用转发给 `_history_repository()` 返回的实例。

### 3. Contracts

- `HistoryRepository` 只依赖标准库和构造参数，不得导入 `server.app`、FastAPI、`JOBS` 或运行时环境全局。
- `HISTORY_KINDS` 与 `HISTORY_LIBRARY_LOCK` 由仓库模块创建，`server.app` 重导出同一对象；每个临时仓库实例必须共享该锁。
- `_history_repository()` 每次调用读取当前 `DATA_DIR` 和 `HISTORY_MAX_STORED`，同时传入当前 FFmpeg 解析器与时钟；不得缓存包含运行时路径或上限的实例。
- library root、manifest、版本目录和文件名保持 `data/history`、`manifest.json`、`history-<32hex>`、`video.mp4`、`transcript.json`、`thumbnail.jpg`。
- 保存版本依次原子落盘视频与 transcript、尝试生成缩略图、在锁内更新 manifest，随后删除被容量上限淘汰的目录；任一异常删除本次新建的整个版本目录。

### 4. Validation & Error Matrix

| 条件 | 结果 |
| --- | --- |
| manifest 不存在 | 返回空列表，不创建或覆盖文件 |
| manifest 无法读取、JSON 损坏或根节点不是列表 | 抛出可诊断 `RuntimeError`，不覆盖现有清单 |
| 记录 id、kind 或 `videoFilename` 不符合既有白名单 | 读取时过滤该记录 |
| history id 不是 `history-<32hex>` | 目录解析抛 `ValueError`；查找返回 `None` |
| 源视频不存在或 transcript 没有 segments 列表 | 抛 `RuntimeError`，不创建成功记录 |
| FFmpeg 缩略图失败 | 删除失败的缩略图并继续保存无缩略图版本 |
| 视频、transcript 或 manifest 保存中途失败 | 删除本次新建版本目录并继续抛出异常 |

### 5. Good / Base / Bad Cases

- Good：测试把 `server.app.DATA_DIR` 改为临时目录、把 `HISTORY_MAX_STORED` 改为 1 后，下一次旧函数调用立即写入临时目录并使用新上限。
- Base：保存版本后，视频和 transcript 已完成临时文件替换，manifest 在共享锁内包含新记录，公开投影字段和 URL 与拆分前一致。
- Bad：模块导入时创建全局仓库并捕获真实 `DATA_DIR`；这会绕过测试隔离，也会让运行时配置变更失效。

### 6. Tests Required

- 独立进程只导入 `server.history_repository`，断言 `server.app` 未进入 `sys.modules`。
- 断言 `server.app` 重导出的类、`HISTORY_KINDS` 和 `HISTORY_LIBRARY_LOCK` 与仓库模块对象同一。
- monkeypatch `server.app.DATA_DIR` 与 `HISTORY_MAX_STORED`，断言旧适配器读取当前目录和默认上限。
- 继续运行 history/maintenance 生命周期测试，覆盖真实短视频、缩略图、保存、重命名、复用、删除和容量裁剪。
- 完整回归同时校验 OpenAPI path/schema 数量和稳定哈希，防止结构拆分改变 API。

### 7. Wrong vs Correct

```python
# Wrong: 导入时捕获目录和容量，fixture 或运行时修改不会生效。
HISTORY_REPOSITORY = HistoryRepository(data_dir=DATA_DIR, max_stored=HISTORY_MAX_STORED, ...)

# Correct: 旧入口的每次调用都使用当前配置，但共享同一个模块锁。
def _history_repository() -> HistoryRepository:
    return HistoryRepository(
        data_dir=DATA_DIR,
        max_stored=HISTORY_MAX_STORED,
        lock=HISTORY_LIBRARY_LOCK,
        ...,
    )
```

## 演进边界

当前优化规划建议未来引入版本化 `ProjectDocument`。在真正实现、迁移和测试完成前，不得让新代码假定它存在；迁移期必须保留旧 job/cut draft 兼容读取。

验证参考：`test_cut_draft_is_persisted_versioned_restored_and_cleared`、history、cleanup、settings 测试。
