# Implementation Plan

## Ordered Steps

1. 在 `tests/app/test_editor_art_model.py` 增加失败回归，使用 `14.13 -> 13.90`、`15.81 -> 15.55`、`17.39 -> 17.19`、`22.19 -> 21.90` 的真实锚点漂移，锁定当前会丢“但/你/该/人”。
2. 在 `web/editor-art-model.js` 提取 transcript track reconciliation helper：按 `trackId` 合并 active/suppressed bases，建立有序 source boundary preferences，并对 `nextCut.transcript` units 做全轨单调 partition。
3. 用连续 unit slice 重建 active cue 的文本、edited/source anchors 与 `characterTimings`；空 slice 进入 suppressed。加入 track-wide 字符守恒检查和无可靠 anchors 的容量比例降级。
4. 修改 `reconcileArtWithCut()`，全文轨道走新的 track-level helper，手动/普通 anchored overlay 保持原路径；保持排序、activeIds、ID 与样式兼容。
5. 修改 `web/editor-project-store.js:mergeArtText()`，在文字保存同步可见 cue 时一并刷新 `_cutReconciliation` 文本基线和 cue 内 character timings，不改变任何 cue/工具时间字段或 `timingRevision`。
6. 扩展 `tests/app/test_editor_project_store.py`：覆盖文字更新后 canonical -> local anchor drift 的 timing change、同范围 server echo、suppressed/undo 恢复和 preview/compose 单 snapshot 一致性。
7. 扩展 `tests/app/browser/test_editor_workflows.py`：真实点击修改文案、文案拆分、删除拆出段落；断言全文艺术字与 cut transcript 内容字符完全相等，保留段首字存在，删除段不存在，基础 video 不 reload。
8. 修复 `update_transcript_track_text_for_segment()` 把失效艺术字写为 `status: null` 的工程快照问题：改用合法可重试非运行态，并补状态/连续保存的 repository/API 回归。
9. 在 `saveSegmentText()` 的正常与 stale-effect refresh 响应路径同步权威 `result.segments` 和字符 timing 缓存，保证保存后立即拆分/删除使用新文字边界。
10. 运行 ArtModel、ProjectStore、art track/API、cut draft、project repository 和浏览器定向测试；再运行完整 `tests/app`、JavaScript 语法检查和 diff hygiene。
11. 用当前本地 job 只读检查首屏关键 cue，确认时间轴、统一预览和 compose 均包含“但/你/该/其实/人”等保留首字；不得改写 `data/jobs`、history 或用户附件。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_art_model.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_editor_project_store.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_art_text_track.py tests/app/test_art_text_api.py tests/app/test_cut_draft.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_project_repository.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q tests/app
node --check web/app.js
node --check web/editor-art-model.js
node --check web/editor-project-store.js
git diff --check
```

## Risk And Rollback Points

- 先以纯 ArtModel 测试锁定字符守恒，再接入 Store；若 cue 分配出现重复/乱序，停止接入并修正 partition helper。
- Store merge 只允许文字和 cue 内 timings 变化；测试必须证明 overlay start/end/source anchors、manual art、PiP、selection 和 timingRevision 完全不变。
- 浏览器流程若触发额外基础视频 `src/load()` 或改变 cut ranges，视为越界回归，回退最近的 Store 接入修改。
- 不以“截图上看起来对”代替 `concat(cues) === concat(cut transcript)` 的机器断言。

## Pre-Start Gate

- `prd.md`、`research/root-cause.md`、`design.md` 与 `implement.md` 已完成。
- `implement.jsonl` 和 `check.jsonl` 已配置真实规范/研究上下文。
- 必须先向用户展示最终规划摘要；只有用户在该摘要之后明确批准，才运行 `task.py start` 并修改产品代码。

## Verification Results

- ArtModel/ProjectStore/cut-draft/frontend-contracts 定向检查：`120 passed`。
- 真实锚点漂移、missing/placeholder/explicit-empty projection、mixed anchors、suppressed/restore 和失效快照连续覆盖均有回归。
- 浏览器完整套件：`48 passed`；真实“修改 -> 拆分 -> 删除”断言 cut/art/timeline/preview/compose 同文案且基础 video `src/load()` 为 0。
- 完整应用套件：`467 passed`，仅 1 条既存 Starlette/httpx deprecation warning。
- `node --check`：`web/app.js`、`web/editor-art-model.js`、`web/editor-project-store.js` 通过。
- `git diff --check` 与 Trellis task validation 通过；未修改用户 job/history/媒体，未提交、推送、合并或部署。
