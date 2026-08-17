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

## 演进边界

当前优化规划建议未来引入版本化 `ProjectDocument`。在真正实现、迁移和测试完成前，不得让新代码假定它存在；迁移期必须保留旧 job/cut draft 兼容读取。

验证参考：`test_cut_draft_is_persisted_versioned_restored_and_cleared`、history、cleanup、settings 测试。
