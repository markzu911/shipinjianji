# 时间轴分割实施计划

## Phase 0: Baseline And Contract Tests

- [ ] 记录当前 cut-draft、Store revision、时间轴交互和 compose 的基线测试结果。
- [ ] 先新增失败测试：旧草稿兼容、split point 规范化、structure revision、精确边界跳过声学移动、分割按钮/clip DOM 契约。
- [ ] 明确现有文字段落 `splitSegmentButton` 测试仍独立通过。

Rollback point：此阶段只增加测试，不改变运行时。

## Phase 1: Backend Draft And Exact Boundary Contract

- [ ] 在 `server/schemas.py` 新增 split point schema、`splitPoints` 和 timeline range boundary metadata；旧字段缺省值保持兼容。
- [ ] 在 `server/app.py` 同一 cut-draft PUT 事务内规范化、排序、去重和持久化 split points，并保持 `schemaVersion: 1` 的增量兼容契约。
- [ ] 校验 `split_exact` 的相邻锚点和 `splitClipKey`；合法范围绕过 timeline acoustic alignment，物理端点严格等于语义端点并输出诊断。
- [ ] 证明普通 `speech_safe` timeline ranges 的现有声学 fixture 输出不变。
- [ ] 覆盖 revision conflict、刷新读取、无效/重复/端点 split point 和缺少新字段的历史 draft。

Rollback point：若 exact contract 无法保持普通范围兼容，回退 schema/分支，不保留前端发送新 mode。

## Phase 2: Frontend State, Mapping And History

- [ ] 在 `app.js` 增加 split point 规范化、stable id、derived clip/tombstone selector 和同一 source/edited 映射验证函数。
- [ ] 将 `splitPoints`、`boundaryMode`、`splitClipKey` 接入持久 payload、语义签名、本地草稿、服务端响应应用和 cut history snapshot。
- [ ] 在 `editor-project-store.js` 增加 `CUT_STRUCTURE_CHANGED`，使 split 只增加 project revision，不增加 timing revision或触发 Art/PiP reconciliation。
- [ ] 在 `editor-suite.js` 接入 structure change，同时保持 metadata-only server revision no-op。
- [ ] 实现 split/delete/restore 每次一个 history transaction；选择变化不写历史，undo/redo 恢复命令前后 selection。

Rollback point：Store action 与 save queue 可独立撤回；不得留下只存 localStorage、不进服务端的 split state。

## Phase 3: Timeline UI And Interaction

- [ ] 在时间轴 heading 右侧新增剪刀“分割”按钮和片段删除/恢复图标动作，使用 Iconify，点击目标至少 44px。
- [ ] 新增基础 clip overlay、稳定边界、selection 和 deleted marker；布局只读 derived clip，不改变 thumbnails/media owner。
- [ ] clip pointer/keyboard interaction 与自由拖选 handler 隔离；命令时二次验证当前 frame，保持播放头、总时长和播放状态。
- [ ] 删除 split clip 复用确认框并写 `split_exact` range；恢复只移除目标 range。
- [ ] 完成 1440px 与 375px 响应式/focus/status；更新 `app.js`、Store、CSS 等实际变更资产的 cache-buster。

Rollback point：可关闭 UI 入口并保留只读 draft compatibility；不能保留可点击但不持久化的边界。

## Phase 4: Integration And Regression

- [ ] 后端验证：schema、draft revision、exact/speech-safe 分支、compose 使用权威范围。
- [ ] 前端验证：source/edited 映射、重复/零长度拒绝、history、Store revision/timingRevision、save queue rebase。
- [ ] 真实浏览器验证：split、刷新、连续 split、select/delete/restore、undo/redo、375px 和键盘可访问性。
- [ ] identity/performance 断言：document/video/tool roots 不变，iframe=0，基础 video `src/load()`=0，split 不重建 thumbnails 或启动 extractor。
- [ ] 回归文字段落 split、自由拖选 speech-safe 删除、文字/空白恢复、ArtTool/PipTool selection、统一 compose 和生成前 draft flush。
- [ ] 运行 Trellis quality check，处理所有 P0/P1/P2 发现后再进入 spec update/commit。

## Validation Commands

```powershell
node --check web/app.js
node --check web/editor-project-store.js
node --check web/editor-suite.js
py -3 -m pytest tests/app/test_schemas.py tests/app/test_cut_draft.py tests/app/test_cut_acoustic_boundaries.py -q
py -3 -m pytest tests/app/test_editor_project_store.py tests/app/test_frontend_contracts.py -q
py -3 -m pytest tests/app/browser/test_editor_workflows.py -k "timeline_split or cut_timeline" -q
py -3 -m pytest -q
```

浏览器检查还需在桌面与 375px 截图中确认无重叠，并记录 split 前后 duration、current source/edited time、Store revision、timingRevision、video `src/load()` 和 extractor 计数。
