# 实施计划

- [x] 新增独立 IndexedDB Blob store，覆盖 open/load/save/shape validation/LRU prune/close 和失败降级。
- [x] 将 `buildCutTimelineThumbnails()` 调整为 memory -> persistent -> extractor 三段流程，并在所有 await 后保持 generation guard。
- [x] 改用 `canvas.toBlob()` 生成 JPEG Blob，集中创建/释放 document Object URL。
- [x] 保持删除、恢复、拆分只重投影 source-time frames，不触发持久重写或 extractor。
- [x] 在 `index.html` 加载缓存脚本并提升缓存脚本与 `app.js` 资源版本。
- [x] 增加前端契约和真实 Chromium 回归：首次保存、刷新命中零 extractor、损坏/不可用回退、LRU 清理、连续覆盖和 375px。
- [x] 运行全部 `web/*.js` 语法检查、前端契约、相关工作流、完整 browser suite 和 `git diff --check`。

## Risky Files And Rollback Points

- `web/app.js`：异步 owner 和 Object URL 生命周期；发现竞态时先回退 persistent lookup，保留 store 模块不接入。
- `web/timeline-thumbnail-cache.js`：只能是性能辅助；任何错误不得越过 `buildCutTimelineThumbnails()` 的降级边界。
- `tests/app/browser/test_editor_workflows.py`：reload 测试必须使用同一 BrowserContext 的真实 IndexedDB，不能用全局变量伪造持久命中。

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/app/test_frontend_contracts.py
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser/test_editor_workflows.py -k "thumbnail or cut_interaction"
.\.venv\Scripts\python.exe -m pytest -q tests/app/browser
.\.venv\Scripts\python.exe -m pytest -q
Get-ChildItem web -Filter '*.js' | ForEach-Object { node --check $_.FullName }
python -m compileall -q server tests/app
git diff --check
```

## Verification Evidence

- `tests/app/test_frontend_contracts.py`: 35 passed.
- `tests/app/browser/test_editor_workflows.py -k "timeline_thumbnail_cache"`: 3 passed; covers Blob persistence/reload reuse, corrupted/unavailable fallback, age/count/byte prune, and transient synchronous open recovery.
- The original full browser run reached 50 passed with one timing-only P95 failure; the unchanged performance test passed immediately on isolation at P95 `54.4ms` with `createdVideos=0` and `thumbnailSeekWrites=0`.
- A full repository rerun after the reviewer fixes passed: 486 passed in 139.88s, including the complete browser suite.
- All `web/*.js` passed `node --check`.
- `python -m compileall -q server tests/app` passed.
- `git diff --check` passed (only existing CRLF conversion warnings).
- Persistent cache and Blob URL lifecycle contracts were recorded in `.trellis/spec/frontend/architecture-and-state.md` and `.trellis/spec/testing/browser-workflows.md`.

## Reviewer Fixes

- Safely read `window.indexedDB`/`window.Blob`, so a capability getter throwing `SecurityError` cannot stop editor initialization.
- Avoid retaining a synchronously rejected IndexedDB open promise; later save/load operations retry after a transient open failure.
- Remove thumbnail DOM background references before revoking old Blob URLs during cache replacement, task reset, video error, and `beforeunload`; this removed the reload-time `ERR_FILE_NOT_FOUND` race.
