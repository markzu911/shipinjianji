# 持久化与任务状态

## 当前存储模型

项目没有数据库：

- `JOBS` 和 `JOB_FILES` 保存当前进程的任务状态，受 `JOBS_LOCK` 保护；服务重启后丢失。
- `data/jobs/<uuid>/` 保存上传源文件、处理中间文件和 `cut-draft.json`。
- `data/history/` 保存最终版本、缩略图和 history manifest，跨重启存在。
- `data/fonts/`、`data/art-templates/`、`data/art-position-presets/` 各自使用 manifest JSON。
- `.env` 保存模型服务商配置和凭证，由 settings API 在锁内更新。

不要把 `data/jobs` 当作永久项目数据库，也不要把 `data/history` 当作可编辑工程状态。

## JSON 写入

- UTF-8，用户文本使用 `ensure_ascii=False`。
- 复合内容使用稳定、可读的 JSON；已有 manifest 保持列表/对象形状。
- 草稿和媒体输出采用同目录临时文件后 `replace`，避免读到半写入文件。
- 写 manifest 前获取领域锁；读改写必须在同一个临界区内完成。
- 读取损坏或缺失的可选草稿可返回 `None`；持久库损坏应产生可诊断错误，不能悄悄覆盖为空库。

参考：`save_cut_draft`、`save_history_versions_unlocked`、`save_uploaded_art_templates_unlocked`、`persist_model_provider_settings`。

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

## 任务状态更新

- 通过 `update_job` 或对应的 `update_edit_job`、`update_art_job`、`update_picture_in_picture_job` 更新，不直接在无锁区域修改嵌套字典。
- job/子 job 进入后台前使用 `queued`，执行中使用既有 `processing`/`extracting`/`transcribing`，完成后只能进入明确终态。
- `public_job` 是对外投影边界；新增内部字段前确认是否应暴露给浏览器。
- 运行中工作由 `job_has_running_work` 判定，清理逻辑不得删除这些目录。

## 清理和历史

- `cleanup_job_directories` 只接受 UUID 目录，保护运行中任务，并支持 dry-run。
- `HISTORY_MAX_STORED` 只管理最终历史，不受临时 job 保留期影响。
- 成功保存历史或任务终态失败后可以清理工作目录；不得删除历史成片或用户上传的模板/字体。
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
